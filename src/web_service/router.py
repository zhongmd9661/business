"""API 路由 — 认证 + 任务管理"""
import asyncio
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from loguru import logger
from sqlalchemy.orm import Session

from . import schemas
from .auth import create_token, get_admin_user, get_current_user, hash_password, verify_password
from .config import (
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_SIZE_MB,
    PROJECT_ROOT,
    UPLOAD_DIR,
)
from .models_db import Task, TaskFile, User, get_db

# --- Settings Router (public — no auth required) ---

settings_router = APIRouter()


@settings_router.get("/settings/llm")
def get_llm_settings():
    """Get current LLM configuration (base_url, api_key, model)."""
    from .config import get_app_settings
    return get_app_settings()


@settings_router.post("/settings/llm")
def set_llm_settings(data: dict):
    """Save LLM configuration and apply immediately."""
    from .config import get_app_settings, save_app_settings
    current = get_app_settings()
    allowed_keys = {"anthropic_base_url", "anthropic_auth_token", "llm_model",
                     "llm_extract_temperature", "llm_extract_max_tokens", "llm_extract_auto"}
    updates = {k: v for k, v in data.items() if k in allowed_keys and v is not None}
    if updates:
        merged = {**current, **updates}
        save_app_settings(merged)
    return {"detail": "设置已保存并立即生效", "settings": get_app_settings()}


@settings_router.post("/settings/llm/test")
async def test_llm_connection(data: dict):
    """Test LLM connection — 直接用 HTTP 请求，不依赖 anthropic 库。"""
    import os
    base_url = (data.get("anthropic_base_url") or os.environ.get("ANTHROPIC_BASE_URL")).rstrip("/")
    api_key = (data.get("anthropic_auth_token") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "lmstudio"))
    model = (data.get("llm_model") or os.environ.get("LLM_MODEL", "Qwen/Qwen3.6-27B"))

    if not base_url:
        return {"ok": False, "error": "未填写 API 地址"}

    try:
        import httpx
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # 尝试 OpenAI 兼容格式（LM Studio / Ollama 等本地模型常用）
        url_openai = f"{base_url}/v1/chat/completions"
        body_openai = {
            "model": model,
            "messages": [{"role": "user", "content": "Reply OK"}],
            "max_tokens": 16,
            "temperature": 0,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.post(url_openai, json=body_openai, headers=headers)
                if resp.status_code == 200:
                    result = resp.json()
                    reply = (result.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
                    return {
                        "ok": True,
                        "message": f"✅ 连接成功！模型 {model} 响应：{reply.strip()}",
                        "model": model,
                        "base_url": base_url,
                    }
            except Exception:
                pass

            # 如果 OpenAI 格式失败，尝试 Anthropic 兼容格式
            url_anthropic = f"{base_url}/v1/messages"
            body_anthropic = {
                "model": model,
                "messages": [{"role": "user", "content": "Reply OK"}],
                "max_tokens": 16,
                "temperature": 0,
            }
            resp = await client.post(url_anthropic, json=body_anthropic, headers=headers)
            if resp.status_code == 200:
                result = resp.json()
                reply = (result.get("content") or [{}])[0].get("text", "") or ""
                return {
                    "ok": True,
                    "message": f"✅ 连接成功！模型 {model} 响应：{reply.strip()}",
                    "model": model,
                    "base_url": base_url,
                }

        # 都失败，返回错误信息
        err_detail = f"HTTP {resp.status_code}: {resp.text[:200]}"
        return {"ok": False, "error": f"连接失败：{err_detail}"}
    except Exception as e:
        return {"ok": False, "error": f"网络错误：{str(e)}"}


# --- Auth Router ---

auth_router = APIRouter()


@auth_router.post("/auth/register")
def register(req: schemas.RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(400, "用户名已存在")
    user = User(
        username=req.username,
        hashed_password=hash_password(req.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.UserResponse.model_validate(user)


@auth_router.post("/auth/login")
def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "用户名或密码错误")
    token = create_token(user)
    return schemas.TokenResponse(access_token=token, role=user.role, username=user.username)


# --- Task Router ---

task_router = APIRouter()

# Task storage — in-memory dict for async task state
task_queue: dict[int, asyncio.Task] = {}
ocr_semaphore = asyncio.Semaphore(3)


def _validate_file(f: UploadFile) -> None:
    ext = Path(f.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: {ext}")
    if f.size and f.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"文件大小超过 {MAX_UPLOAD_SIZE_MB}MB 限制")


@task_router.post("/tasks/upload", response_model=schemas.TaskCreateResponse)
async def upload_files(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(400, "没有上传文件")

    for f in files:
        _validate_file(f)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_name = f"batch_{user.id}_{ts}"

    task = Task(
        user_id=user.id,
        batch_name=batch_name,
        status="pending",
        file_count=len(files),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Save files
    task_dir = UPLOAD_DIR / str(user.id) / str(task.id)
    task_dir.mkdir(parents=True, exist_ok=True)

    for i, f in enumerate(files):
        content = await f.read()
        fname = f"{i:03d}_{f.filename or 'unknown'}"
        fpath = task_dir / fname
        fpath.write_bytes(content)

        tf = TaskFile(
            task_id=task.id,
            filename=fname,
            file_type=Path(f.filename or "").suffix.lstrip("."),
        )
        db.add(tf)

    db.commit()

    # Start async processing
    async_task = asyncio.create_task(_process_review_task(task.id))
    task_queue[task.id] = async_task

    return schemas.TaskCreateResponse(task_id=task.id, status="pending")


@task_router.get("/tasks")
def list_tasks(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tasks = (
        db.query(Task)
        .filter(Task.user_id == user.id)
        .order_by(Task.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [schemas.TaskResponse.model_validate(t) for t in tasks]


@task_router.get("/tasks/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    return schemas.TaskResponse.model_validate(task)


@task_router.get("/tasks/{task_id}/report")
def get_report(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if not task.output_dir:
        raise HTTPException(404, "审核报告尚未生成")

    report_path = Path(task.output_dir) / "审核报告.md"
    if not report_path.exists():
        raise HTTPException(404, "审核报告文件不存在")
    return report_path.read_text(encoding="utf-8")


@task_router.get("/tasks/{task_id}/fields")
def get_fields(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    results_dir = Path(task.output_dir) / "识别结果" if task.output_dir else None
    if not results_dir or not results_dir.exists():
        return []

    fields_files = list(results_dir.glob("字段提取结果*"))
    results = []
    for ff in fields_files:
        results.append({"filename": ff.name, "content": ff.read_text(encoding="utf-8")})
    return results


@task_router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    # Remove associated files
    for tf in db.query(TaskFile).filter(TaskFile.task_id == task_id).all():
        db.delete(tf)

    # Cancel async task if running
    if task_id in task_queue:
        task_queue[task_id].cancel()
        del task_queue[task_id]

    db.delete(task)
    db.commit()
    return {"detail": "任务已删除"}


# --- Async Processing ---

async def _process_review_task(task_id: int):
    """异步处理：OCR → 提取 → 审核"""
    from . import service

    db = next(get_db())
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        task.status = "parsing"
        db.commit()

        batch_dir = UPLOAD_DIR / str(task.user_id) / str(task_id)
        if not batch_dir.exists():
            raise FileNotFoundError(f"批次目录不存在: {batch_dir}")

        async with ocr_semaphore:
            pipeline = service.get_pipeline()
            output_dir, _ = await pipeline.process_batch(batch_dir, task.batch_name)

        task.status = "completed"
        task.output_dir = str(output_dir)
        task.completed_at = datetime.now().isoformat()
        db.commit()

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "failed"
            task.error_message = str(e)
            db.commit()
    finally:
        db.close()

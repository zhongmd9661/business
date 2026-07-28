"""审核详情页 API — 提交记录的 OCR 管理、字段提取、审核校验"""
import asyncio
import hashlib
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse
from loguru import logger
from sqlalchemy.orm import Session

from .config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB, PROJECT_ROOT
from .models_db import (
    OCRRecord, ExtractedField, ReviewResult, ReceptionRecord, get_db, SessionLocal,
)
from .service_audit import (
    SLOTS, SLOT_NAMES, extract_from_markdown, run_review, generate_review_report,
    _extract_tasks, _run_async_extract,
)
from .router_ocr import _detect_file_type, _ocr_image_file, _run_ocr, _temp_dir, _files_dir, _ocr_semaphore

router = APIRouter()


# ===================================================================
# 工具函数
# ===================================================================

def _compute_file_hash(content: bytes) -> str:
    """计算文件前 1024 字节的 MD5 哈希"""
    return hashlib.md5(content[:1024]).hexdigest()[:16]


def _save_original_file(file_content: bytes, original_filename: str) -> str:
    """将原始上传文件保存到持久化目录，返回相对路径"""
    ext = Path(original_filename or "").suffix.lower()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    content_hash = hashlib.md5(file_content[:1024]).hexdigest()[:8]
    stored_name = f"{ts}_{content_hash}{ext}"
    date_dir = _files_dir / datetime.now().strftime("%Y/%m")
    date_dir.mkdir(parents=True, exist_ok=True)
    saved_path = date_dir / stored_name
    saved_path.write_bytes(file_content)
    return str(saved_path.relative_to(_files_dir))


# ===================================================================
# 记录列表
# ===================================================================

@router.get("/audit-detail/list")
def list_audit_records(
    status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    """列出所有可审核的提交记录"""
    q = db.query(ReceptionRecord)
    if status:
        q = q.filter(ReceptionRecord.status == status)
    if review_status:
        q = q.filter(ReceptionRecord.review_status == review_status)
    records = q.order_by(ReceptionRecord.id.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "serial_number": r.serial_number or "",
            "scenario": r.scenario,
            "scenario_name": r.scenario_name,
            "submitter": r.submitter,
            "date": r.date or "",
            "location": r.location or "",
            "org": r.org or "",
            "guests": r.guests or 0,
            "per_capita": r.per_capita or 0,
            "total_amount": r.total_amount or 0,
            "status": r.status or "pending",
            "ocr_status": r.ocr_status or "pending",
            "review_status": r.review_status or "pending",
            "ocr_file_count": r.ocr_file_count or 0,
            "created_at": r.created_at or "",
        }
        for r in records
    ]


# ===================================================================
# 获取完整审核数据
# ===================================================================

@router.get("/audit-detail/{serial_number}")
def get_audit_detail(serial_number: str, db: Session = Depends(get_db)):
    """获取某流水号的完整审核数据（提交记录 + OCR文件 + 提取字段 + 审核结果）"""
    record = db.query(ReceptionRecord).filter(
        ReceptionRecord.serial_number == serial_number
    ).first()
    if not record:
        raise HTTPException(404, f"未找到流水号 {serial_number}")

    # OCR 文件列表
    ocr_records = (
        db.query(OCRRecord)
        .filter(OCRRecord.serial_number == serial_number)
        .order_by(OCRRecord.created_at.asc())
        .all()
    )

    # 按槽位组织，每个槽位取最新一条
    slot_ocr_map = {}
    for ocr in ocr_records:
        if ocr.slot_name not in slot_ocr_map or ocr.created_at > slot_ocr_map[ocr.slot_name].created_at:
            slot_ocr_map[ocr.slot_name] = ocr

    ocr_list = []
    for slot in SLOTS:
        ocr = slot_ocr_map.get(slot["name"])
        ocr_list.append({
            "index": slot["index"],
            "name": slot["name"],
            "label": slot["label"],
            "rule": slot["rule"],
            "ocr_record_id": ocr.id if ocr else None,
            "original_filename": ocr.original_filename if ocr else None,
            "status": ocr.status if ocr else "missing",
            "file_type": ocr.file_type if ocr else None,
            "original_file_path": ocr.original_file_path if ocr else None,
            "created_at": ocr.created_at if ocr else None,
        })

    # 提取字段列表
    extracted = (
        db.query(ExtractedField)
        .filter(ExtractedField.serial_number == serial_number)
        .order_by(ExtractedField.created_at.asc())
        .all()
    )

    # 按槽位组织，每个槽位取最新一条
    slot_extract_map = {}
    for ef in extracted:
        if ef.slot_name not in slot_extract_map or ef.created_at > slot_extract_map[ef.slot_name].created_at:
            slot_extract_map[ef.slot_name] = ef

    extracted_list = []
    for slot in SLOTS:
        ef = slot_extract_map.get(slot["name"])
        data = {}
        if ef and ef.extracted_json:
            try:
                data = json.loads(ef.extracted_json)
            except json.JSONDecodeError:
                pass
        extracted_list.append({
            "slot_name": slot["name"],
            "field_id": ef.id if ef else None,
            "status": ef.status if ef else "missing",
            "fields": data,
            "llm_text": ef.error_message if ef and ef.error_message else "",
        })

    # 审核结果
    review_results = (
        db.query(ReviewResult)
        .filter(ReviewResult.serial_number == serial_number)
        .order_by(ReviewResult.created_at.asc())
        .all()
    )
    review_list = [
        {
            "id": r.id,
            "rule_name": r.rule_name,
            "severity": r.severity,
            "passed": r.passed,
            "detail": r.detail or "",
            "created_at": r.created_at or "",
        }
        for r in review_results
    ]

    return {
        "record": {
            "id": record.id,
            "serial_number": record.serial_number,
            "scenario": record.scenario,
            "scenario_name": record.scenario_name,
            "submitter": record.submitter,
            "date": record.date or "",
            "location": record.location or "",
            "org": record.org or "",
            "guests": record.guests or 0,
            "accompany_people": record.accompany_people or "",
            "accompany_count": record.accompany_count or 0,
            "per_capita": record.per_capita or 0,
            "total_amount": record.total_amount or 0,
            "baijiu_price": record.baijiu_price or "",
            "wine_price": record.wine_price or "",
            "gift_per": record.gift_per or "",
            "reason": record.reason or "",
            "status": record.status or "pending",
            "ocr_status": record.ocr_status or "pending",
            "review_status": record.review_status or "pending",
            "ocr_file_count": record.ocr_file_count or 0,
            "created_at": record.created_at or "",
        },
        "ocr_files": ocr_list,
        "extracted_fields": extracted_list,
        "review_results": review_list,
        "review_report": record.review_report or "",
    }


# ===================================================================
# OCR 文件上传（关联流水号，覆盖式保存）
# ===================================================================

@router.post("/audit-detail/{serial_number}/ocr")
async def upload_ocr_file(
    serial_number: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    slot_name: str = Form(""),
    username: str = Form(""),
    method: str = Form("ocr"),
    device: str = Form("gpu"),
    db: Session = Depends(get_db),
):
    """上传文件到指定槽位，执行 OCR 识别。
    覆盖式保存：同流水号+同槽位+同文件哈希 → 直接返回已有结果（不重复 OCR）
    同流水号+同槽位+不同文件 → 覆盖更新
    """
    # 验证记录存在
    record = db.query(ReceptionRecord).filter(
        ReceptionRecord.serial_number == serial_number
    ).first()
    if not record:
        raise HTTPException(404, f"未找到流水号 {serial_number}")

    if not slot_name:
        raise HTTPException(400, "必须指定 slot_name（槽位名）")

    if slot_name not in SLOT_NAMES:
        raise HTTPException(400, f"无效槽位: {slot_name}，可选: {SLOT_NAMES}")

    # 验证文件
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: {ext}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"文件大小超过 {MAX_UPLOAD_SIZE_MB}MB 限制")

    file_hash = _compute_file_hash(content)
    dedup_key = f"{serial_number}_{slot_name}_{file_hash}"

    # 去重检查：同流水号+同槽位+同文件哈希 → 直接返回已有结果
    existing = (
        db.query(OCRRecord)
        .filter(OCRRecord.serial_number == serial_number,
                OCRRecord.slot_name == slot_name,
                OCRRecord.dedup_key == dedup_key)
        .first()
    )
    if existing:
        logger.info(f"OCR 去重: {serial_number}/{slot_name} 文件未变化，直接返回")
        return {
            "record_id": existing.id,
            "status": "duplicate",
            "message": "文件未变化，跳过重复 OCR",
            "original_filename": existing.original_filename,
            "original_file_path": existing.original_file_path or "",
            "created_at": existing.created_at,
        }

    # 保存原始文件
    stored_rel_path = ""
    try:
        stored_rel_path = _save_original_file(content, file.filename or "unknown")
    except Exception as e:
        logger.warning(f"Failed to save original file: {e}")

    file_type = _detect_file_type(file.filename)

    async with _ocr_semaphore:
        # 保存临时文件
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_dir = _temp_dir / ts
        task_dir.mkdir(parents=True, exist_ok=True)
        file_path = task_dir / (file.filename or "unknown")
        file_path.write_bytes(content)

        try:
            result = await _run_ocr(file_path, task_dir, method=method, device=device)
        finally:
            if task_dir.exists():
                shutil.rmtree(task_dir, ignore_errors=True)

    # 如果有同槽位旧记录，标记为替换（保留历史但不使用）
    old_record = (
        db.query(OCRRecord)
        .filter(OCRRecord.serial_number == serial_number, OCRRecord.slot_name == slot_name)
        .order_by(OCRRecord.created_at.desc())
        .first()
    )

    # 保存新记录
    try:
        ocr_result = result.get("ocr_blocks", [])
        ocr_lines = result.get("ocr_lines", [])
        if isinstance(ocr_result, list):
            ocr_result = json.dumps(ocr_result, ensure_ascii=False)
        if isinstance(ocr_lines, list):
            ocr_lines = json.dumps(ocr_lines, ensure_ascii=False)

        new_record = OCRRecord(
            username=username or "anonymous",
            serial_number=serial_number,
            slot_name=slot_name,
            original_filename=file.filename or "unknown",
            file_type=file_type,
            markdown=result.get("markdown", ""),
            status=result.get("status", "error"),
            error_message=result.get("error", ""),
            elapsed=result.get("elapsed", 0),
            ocr_blocks=ocr_result,
            ocr_lines=ocr_lines,
            img_width=result.get("img_width", 0) or 0,
            img_height=result.get("img_height", 0) or 0,
            engine=result.get("engine", "") or "",
            original_file_path=stored_rel_path,
            dedup_key=dedup_key,
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)

        # 更新记录的 OCR 文件计数
        ocr_count = (
            db.query(OCRRecord)
            .filter(OCRRecord.serial_number == serial_number)
            .count()
        )
        record.ocr_file_count = ocr_count
        record.ocr_status = "completed"
        db.commit()

        # 如果启用了自动 LLM 提取，触发后台提取任务
        auto_extract = os.environ.get("LLM_LLM_EXTRACT_AUTO", "True").lower() in ("true", "1", "yes")
        if auto_extract:
            _extract_tasks[serial_number] = {"status": "pending", "results": [], "ocr_count": ocr_count}
            background_tasks.add_task(_run_async_extract, serial_number)
            logger.info(f"Auto-extract triggered for {serial_number}")

        return {
            "record_id": new_record.id,
            "status": "success",
            "message": "OCR 识别成功",
            "original_filename": new_record.original_filename,
            "original_file_path": stored_rel_path,
            "created_at": new_record.created_at,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save OCR record: {e}")
        return {
            "record_id": 0,
            "status": "error",
            "message": f"保存失败: {str(e)}",
        }


# ===================================================================
# 字段提取
# ===================================================================

@router.post("/audit-detail/{serial_number}/extract")
def extract_fields(
    serial_number: str,
    slot_name: Optional[str] = Query(None),
    method: str = Query("rule"),
    db: Session = Depends(get_db),
):
    """触发字段提取。
    如果指定 slot_name，只提取该槽位；否则提取所有已有 OCR 的槽位
    method: 提取方式 — "rule"（规则提取，默认）或 "llm"（大模型提取）
    """
    if method not in ("rule", "llm"):
        raise HTTPException(400, f"无效的提取方法: {method}，可选值: rule, llm")
    record = db.query(ReceptionRecord).filter(
        ReceptionRecord.serial_number == serial_number
    ).first()
    if not record:
        raise HTTPException(404, f"未找到流水号 {serial_number}")

    # 获取需要提取的槽位
    if slot_name:
        slots_to_extract = [s for s in SLOTS if s["name"] == slot_name]
    else:
        slots_to_extract = SLOTS

    results = []
    for slot in slots_to_extract:
        # 获取该槽位最新的 OCR 记录
        ocr = (
            db.query(OCRRecord)
            .filter(OCRRecord.serial_number == serial_number, OCRRecord.slot_name == slot["name"])
            .order_by(OCRRecord.created_at.desc())
            .first()
        )

        if not ocr or not ocr.markdown:
            results.append({"slot_name": slot["name"], "status": "skipped", "reason": "无 OCR 数据"})
            continue

        try:
            extracted = extract_from_markdown(ocr.markdown, slot["rule"], slot["name"], method=method)
            llm_text = extracted.pop("_llm_text", "")  # 取出原始文本，不存入 extracted_json
            extracted_json = json.dumps(extracted, ensure_ascii=False)

            # 更新或创建提取记录
            existing_ef = (
                db.query(ExtractedField)
                .filter(ExtractedField.serial_number == serial_number, ExtractedField.slot_name == slot["name"])
                .order_by(ExtractedField.created_at.desc())
                .first()
            )

            if existing_ef:
                existing_ef.extracted_json = extracted_json
                existing_ef.status = "extracted"
                existing_ef.extraction_rule = f"{method}_{slot['rule']}"
                existing_ef.updated_at = datetime.now().isoformat()
                ef_id = existing_ef.id
            else:
                ef = ExtractedField(
                    serial_number=serial_number,
                    slot_name=slot["name"],
                    ocr_record_id=ocr.id,
                    extracted_json=extracted_json,
                    extraction_rule=f"{method}_{slot['rule']}",
                    status="extracted",
                )
                db.add(ef)
                db.commit()
                db.refresh(ef)
                ef_id = ef.id

            results.append({
                "slot_name": slot["name"],
                "status": "success",
                "field_id": ef_id,
                "fields": extracted,
                "llm_text": llm_text if method == "llm" else "",
            })

        except Exception as e:
            logger.error(f"Extraction failed for {slot['name']}: {e}")
            results.append({"slot_name": slot["name"], "status": "error", "reason": str(e)})

    return {"serial_number": serial_number, "results": results}


@router.post("/audit-detail/{serial_number}/extract-async")
async def extract_fields_async(
    serial_number: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """后台异步触发 LLM 字段提取（全部 9 个槽位）。
    立即返回，前端通过 extract-status 轮询结果。
    """
    record = db.query(ReceptionRecord).filter(
        ReceptionRecord.serial_number == serial_number
    ).first()
    if not record:
        raise HTTPException(404, f"未找到流水号 {serial_number}")

    # 检查是否有 OCR 数据
    ocr_count = (
        db.query(OCRRecord)
        .filter(OCRRecord.serial_number == serial_number, OCRRecord.status == "success")
        .count()
    )
    if ocr_count == 0:
        raise HTTPException(400, "没有可用的 OCR 数据，请先上传文件并执行 OCR")

    # 重置提取任务状态
    _extract_tasks[serial_number] = {"status": "running", "results": [], "ocr_count": ocr_count}

    # 启动后台任务
    background_tasks.add_task(_run_async_extract, serial_number)

    return {
        "serial_number": serial_number,
        "status": "submitted",
        "message": f"已提交后台提取任务，共 {ocr_count} 个文件待处理",
    }


@router.get("/audit-detail/{serial_number}/extract-status")
def get_extract_status(serial_number: str):
    """查询异步提取任务状态"""
    task = _extract_tasks.get(serial_number)
    if not task:
        return {"serial_number": serial_number, "status": "none", "message": "暂无提取任务"}
    return {
        "serial_number": serial_number,
        "status": task["status"],  # running / completed / error
        "results": task.get("results", []),
        "error": task.get("error", ""),
    }


# ===================================================================
# 审核校验
# ===================================================================

@router.post("/audit-detail/{serial_number}/review")
def trigger_review(serial_number: str, db: Session = Depends(get_db)):
    """触发审核校验"""
    record = db.query(ReceptionRecord).filter(
        ReceptionRecord.serial_number == serial_number
    ).first()
    if not record:
        raise HTTPException(404, f"未找到流水号 {serial_number}")

    record.review_status = "reviewing"
    db.commit()

    try:
        results = run_review(db, serial_number)
        return {
            "serial_number": serial_number,
            "status": "completed",
            "results": results,
        }
    except Exception as e:
        record.review_status = "pending"
        db.commit()
        raise HTTPException(500, f"审核失败: {str(e)}")


# ===================================================================
# 审核报告
# ===================================================================

@router.get("/audit-detail/{serial_number}/report")
def get_review_report(serial_number: str, db: Session = Depends(get_db)):
    """获取审核报告"""
    record = db.query(ReceptionRecord).filter(
        ReceptionRecord.serial_number == serial_number
    ).first()
    if not record:
        raise HTTPException(404, f"未找到流水号 {serial_number}")

    if not record.review_report:
        raise HTTPException(404, "尚未生成审核报告，请先触发审核")

    return {"serial_number": serial_number, "report": record.review_report}


# ===================================================================
# OCR 文件列表 / 提取字段 / 审核结果
# ===================================================================

@router.get("/audit-detail/{serial_number}/ocr-files")
def get_ocr_files(serial_number: str, db: Session = Depends(get_db)):
    """获取某记录的所有 OCR 文件列表"""
    records = (
        db.query(OCRRecord)
        .filter(OCRRecord.serial_number == serial_number)
        .order_by(OCRRecord.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "slot_name": r.slot_name,
            "original_filename": r.original_filename,
            "status": r.status,
            "file_type": r.file_type,
            "original_file_path": r.original_file_path or "",
            "created_at": r.created_at,
        }
        for r in records
    ]


@router.get("/audit-detail/{serial_number}/extracted")
def get_extracted_fields(serial_number: str, db: Session = Depends(get_db)):
    """获取某记录的所有提取字段"""
    records = (
        db.query(ExtractedField)
        .filter(ExtractedField.serial_number == serial_number)
        .order_by(ExtractedField.created_at.desc())
        .all()
    )
    result = []
    for ef in records:
        data = {}
        if ef.extracted_json:
            try:
                data = json.loads(ef.extracted_json)
            except json.JSONDecodeError:
                pass
        result.append({
            "id": ef.id,
            "slot_name": ef.slot_name,
            "status": ef.status,
            "fields": data,
            "created_at": ef.created_at,
        })
    return result


@router.get("/audit-detail/{serial_number}/review-results")
def get_review_results(serial_number: str, db: Session = Depends(get_db)):
    """获取某记录的所有审核结果"""
    records = (
        db.query(ReviewResult)
        .filter(ReviewResult.serial_number == serial_number)
        .order_by(ReviewResult.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "rule_name": r.rule_name,
            "severity": r.severity,
            "passed": r.passed,
            "detail": r.detail or "",
            "created_at": r.created_at or "",
        }
        for r in records
    ]

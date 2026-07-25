"""FastAPI 应用入口"""
import asyncio
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent.parent))

# App
app = FastAPI(
    title="业务招待费智能审核系统",
    description="OCR 识别 + 规则审核 Web 服务",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件 - 使用相对路径
static_dir = Path(__file__).parent.parent.parent / "ui"
app.mount("/ui", StaticFiles(directory=str(static_dir)), name="ui")

# Web页面路由
@app.get("/standards_query")
async def standards_query():
    """返回标准查询页面"""
    page_file = static_dir / "standards_query" / "reference.html"
    if page_file.exists():
        return page_file.read_text(encoding="utf-8")
    return "<h1>标准查询页面未找到</h1>"

@app.get("/cards/{card_name}")
async def card_page(card_name: str):
    """返回卡片页面"""
    page_file = static_dir / f"{card_name}.html"
    if page_file.exists():
        return page_file.read_text(encoding="utf-8")
    return "<h1>卡片页面未找到</h1>"

@app.get("/ocr")
async def ocr_page():
    """返回OCR页面"""
    page_file = static_dir / "OCR" / "index.html"
    if page_file.exists():
        return page_file.read_text(encoding="utf-8")
    return "<h1>OCR页面未找到</h1>"


# 主页路由
@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端主页"""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>业务招待费智能审核系统</h1><p>前端文件未找到</p>"

# Sync scanner task handle
_sync_task: asyncio.Task | None = None


@app.on_event("startup")
async def on_startup():
    # 1. Init database
    from .models_db import init_db
    init_db()

    # 2. Start MinerU engine + pipeline
    from . import service
    await service.start_engine()

    # 3. Load routers (lazy to avoid circular imports)
    from . import router, router_rule, router_standards, router_standards_admin, router_application_form, router_reception_record

    app.include_router(router.task_router, prefix="/api", tags=["tasks"])
    app.include_router(router.auth_router, prefix="/api", tags=["auth"])
    app.include_router(router_rule.rule_router, prefix="/api", tags=["rules"])
    app.include_router(router_standards.router, prefix="/api", tags=["standards"])
    app.include_router(router_standards_admin.router, prefix="/api", tags=["admin-standards"])
    # 申请单生成页面不需要 /api 前缀，直接挂载
    app.include_router(router_application_form.router, tags=["application-form"])
    # 招待费提交记录
    app.include_router(router_reception_record.router, tags=["reception-records"])

    # 4. Start rule sync scanner
    from .rule_sync import start_sync_scanner
    global _sync_task
    _sync_task = start_sync_scanner()


@app.on_event("shutdown")
async def on_shutdown():
    # Stop sync scanner
    global _sync_task
    if _sync_task:
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass

    # Stop MinerU engine
    from . import service
    await service.stop_engine()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}

"""FastAPI 应用入口"""
import asyncio
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(__file__).replace("\\web_service\\app.py", "").replace("/web_service/app.py", ""))

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

# 静态文件
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 招待费智能体 UI — 挂载整个 ui 目录
ui_dir = Path(__file__).parent.parent.parent / "ui"
if ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui-static")

# 审核标准 — 挂载参考案例、政策法规等静态资源
base_dir = Path(__file__).parent.parent.parent
standards_dir = base_dir / "审核标准"
if standards_dir.exists():
    app.mount("/审核标准", StaticFiles(directory=str(standards_dir)), name="standards-static")


# 主页路由
@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端主页"""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>业务招待费智能审核系统</h1><p>前端文件未找到</p>"


# 招待费智能体 UI 快捷路由
@app.get("/ui-index", response_class=HTMLResponse)
async def ui_index():
    """招待费智能体主页"""
    ui_index_file = ui_dir / "index.html" if ui_dir.exists() else None
    if ui_index_file and ui_index_file.exists():
        return ui_index_file.read_text(encoding="utf-8")
    return "<h1>UI 目录未找到</h1>"


@app.get("/upload", response_class=HTMLResponse)
async def ui_upload():
    """文件上传页"""
    upload_file = ui_dir / "upload.html" if ui_dir.exists() else None
    if upload_file and upload_file.exists():
        return upload_file.read_text(encoding="utf-8")
    return "<h1>上传页未找到</h1>"


@app.get("/audit", response_class=HTMLResponse)
async def ui_audit():
    """智能审核页"""
    audit_file = ui_dir / "audit.html" if ui_dir.exists() else None
    if audit_file and audit_file.exists():
        return audit_file.read_text(encoding="utf-8")
    return "<h1>审核页未找到</h1>"


@app.get("/records", response_class=HTMLResponse)
async def ui_records():
    """提交记录页"""
    records_file = ui_dir / "records.html" if ui_dir.exists() else None
    if records_file and records_file.exists():
        return records_file.read_text(encoding="utf-8")
    return "<h1>记录页未找到</h1>"


@app.get("/reference", response_class=HTMLResponse)
async def ui_reference():
    """参考资料页"""
    ref_file = ui_dir / "reference.html" if ui_dir.exists() else None
    if ref_file and ref_file.exists():
        return ref_file.read_text(encoding="utf-8")
    return "<h1>资料页未找到</h1>"

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
    from . import router, router_rule, router_standards, router_standards_admin, router_application_form, router_reception_records, router_qichacha

    app.include_router(router.task_router, prefix="/api", tags=["tasks"])
    app.include_router(router.auth_router, prefix="/api", tags=["auth"])
    app.include_router(router_rule.rule_router, prefix="/api", tags=["rules"])
    app.include_router(router_standards.router, prefix="/api", tags=["standards"])
    app.include_router(router_standards_admin.router, prefix="/api", tags=["admin-standards"])
    app.include_router(router_reception_records.router, prefix="/api", tags=["reception-records"])
    app.include_router(router_qichacha.router, prefix="/api", tags=["qichacha"])
    # 申请单生成页面不需要 /api 前缀，直接挂载
    app.include_router(router_application_form.router, tags=["application-form"])

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

"""FastAPI 应用入口"""
import asyncio
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
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
    """返回招待费管理主页（新 UI）"""
    ui_index_file = ui_dir / "index.html" if ui_dir.exists() else None
    if ui_index_file and ui_index_file.exists():
        return _html_response(ui_index_file.read_text(encoding="utf-8"))
    return "<h1>UI 目录未找到</h1>"


# 招待费智能体 UI 快捷路由
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """登录/注册页面"""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return _html_response(index_file.read_text(encoding="utf-8"))
    return "<h1>登录页未找到</h1>"


@app.get("/ui-index", response_class=HTMLResponse)
async def ui_index():
    """招待费智能体主页（同 / ）"""
    ui_index_file = ui_dir / "index.html" if ui_dir.exists() else None
    if ui_index_file and ui_index_file.exists():
        return _html_response(ui_index_file.read_text(encoding="utf-8"))
    return "<h1>UI 目录未找到</h1>"


def _html_response(content: str) -> Response:
    """返回带 no-cache 头的 HTML 响应"""
    return Response(
        content=content,
        media_type="text/html; charset=utf-8",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/upload", response_class=HTMLResponse)
async def ui_upload():
    """文件上传页"""
    upload_file = ui_dir / "upload.html" if ui_dir.exists() else None
    if upload_file and upload_file.exists():
        return _html_response(upload_file.read_text(encoding="utf-8"))
    return _html_response("<h1>上传页未找到</h1>")


@app.get("/audit", response_class=HTMLResponse)
async def ui_audit():
    """智能审核页"""
    audit_file = ui_dir / "audit.html" if ui_dir.exists() else None
    if audit_file and audit_file.exists():
        return _html_response(audit_file.read_text(encoding="utf-8"))
    return _html_response("<h1>审核页未找到</h1>")


@app.get("/records", response_class=HTMLResponse)
async def ui_records():
    """提交记录页"""
    records_file = ui_dir / "records.html" if ui_dir.exists() else None
    if records_file and records_file.exists():
        return _html_response(records_file.read_text(encoding="utf-8"))
    return _html_response("<h1>记录页未找到</h1>")


@app.get("/audit-detail", response_class=HTMLResponse)
async def ui_audit_detail():
    """审核详情页"""
    detail_file = ui_dir / "audit-detail.html" if ui_dir.exists() else None
    if detail_file and detail_file.exists():
        return _html_response(detail_file.read_text(encoding="utf-8"))
    return _html_response("<h1>审核详情页未找到</h1>")


@app.get("/extraction-rules", response_class=HTMLResponse)
async def ui_extraction_rules():
    """字段提取规则配置页"""
    rules_file = ui_dir / "extraction-rules.html" if ui_dir.exists() else None
    if rules_file and rules_file.exists():
        return _html_response(rules_file.read_text(encoding="utf-8"))
    return _html_response("<h1>提取规则页未找到</h1>")


@app.get("/reference", response_class=HTMLResponse)
async def ui_reference():
    """参考资料页"""
    ref_file = ui_dir / "reference.html" if ui_dir.exists() else None
    if ref_file and ref_file.exists():
        return _html_response(ref_file.read_text(encoding="utf-8"))
    return _html_response("<h1>资料页未找到</h1>")

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

    # 3. Init app settings (base_url, api_key, model → os.environ)
    from .config import init_app_settings
    init_app_settings()

    # 4. Load routers (lazy to avoid circular imports)
    from . import router, router_rule, router_standards, router_standards_admin, router_application_form, router_reception_records, router_qichacha, router_ocr, router_audit_detail, router_extraction_rules

    app.include_router(router.settings_router, prefix="/api", tags=["settings"])
    app.include_router(router.task_router, prefix="/api", tags=["tasks"])
    app.include_router(router.auth_router, prefix="/api", tags=["auth"])
    app.include_router(router_rule.rule_router, prefix="/api", tags=["rules"])
    app.include_router(router_standards.router, prefix="/api", tags=["standards"])
    app.include_router(router_standards_admin.router, prefix="/api", tags=["admin-standards"])
    app.include_router(router_reception_records.router, prefix="/api", tags=["reception-records"])
    app.include_router(router_qichacha.router, prefix="/api", tags=["qichacha"])
    app.include_router(router_ocr.router, prefix="/api", tags=["ocr"])
    app.include_router(router_audit_detail.router, prefix="/api", tags=["audit-detail"])
    app.include_router(router_extraction_rules.router, prefix="/api", tags=["extraction-rules"])
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


@app.get("/api/qichacha-templates")
def list_qichacha_templates():
    """列出 ui资源 目录下所有图片模板文件"""
    ui_res_dir = ui_dir / "ui资源" if ui_dir.exists() else None
    if not ui_res_dir or not ui_res_dir.exists():
        return []
    img_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
    files = []
    for f in sorted(ui_res_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in img_exts:
            files.append({"name": f.name, "path": f"/ui/ui资源/{f.name}"})
    return files


# ---- 审核模板文件 ----
# 9 个上传槽位对应的模板文件映射
_AUDIT_TEMPLATE_DIR = base_dir / "审核标准" / "参考案例" / "案例标准测试材料"
_AUDIT_TEMPLATE_MAP = [
    "业务招待审批单.jpg",            # 0: 审批单
    "业务招待申请单.pdf",             # 1: 申请单
    "业务招待费报账单.pdf",           # 2: 报账单
    "【发票】_XML格式.xml",           # 3: 发票（XML格式）
    "【电子发票】_PDF格式.pdf",       # 4: 电子发票（PDF格式）
    "招待单位经营状态.PNG",           # 5: 招待单位经营状态
    "支付凭证.jpg",                   # 6: 支付凭证
    "支付流水证明.pdf",               # 7: 支付流水证明
    "活动函件.pdf",                   # 8: 活动函件
]


@app.get("/api/audit-templates")
def list_audit_templates():
    """列出审核页可用的模板文件映射"""
    result = []
    for idx, fname in enumerate(_AUDIT_TEMPLATE_MAP):
        fpath = _AUDIT_TEMPLATE_DIR / fname
        if fpath.exists():
            result.append({
                "index": idx,
                "name": fname,
                "url": f"/审核标准/参考案例/案例标准测试材料/{fname}",
            })
    return result


@app.get("/api/audit-template/{index:int}")
def get_audit_template(index: int):
    """根据上传槽位 index 返回模板文件 URL"""
    if 0 <= index < len(_AUDIT_TEMPLATE_MAP):
        fname = _AUDIT_TEMPLATE_MAP[index]
        fpath = _AUDIT_TEMPLATE_DIR / fname
        if fpath.exists():
            return {
                "index": index,
                "name": fname,
                "url": f"/审核标准/参考案例/案例标准测试材料/{fname}",
                "ext": fpath.suffix.lower(),
            }
    return {"error": "模板文件未找到"}

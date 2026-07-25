"""申请单生成 API 路由"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from ..application_form import FormGenerator

router = APIRouter()
_gen = FormGenerator()

# 申请单生成页面路径
_APPLICATION_FORM_HTML = Path(__file__).parent.parent / "application_form" / "reference.html"


@router.get("/application-form/templates", summary="获取所有场景模板")
def get_templates():
    """返回所有场景模板列表"""
    return _gen.get_all_templates()


@router.get("/application-form/templates/{template_id}", summary="获取单个场景模板")
def get_template(template_id: str):
    """根据ID获取单个场景模板"""
    result = _gen.get_template(template_id)
    if result is None:
        raise HTTPException(404, f"模板 {template_id} 不存在")
    return result


@router.get("/application-form/load/{template_id}", summary="从模板加载申请单")
def load_form(template_id: str):
    """从模板加载数据到申请单（预填）"""
    form = _gen.load_template_to_form(template_id)
    return form.to_dict()


@router.post("/application-form/validate", summary="校验申请单")
def validate_form(form: dict):
    """校验申请单完整性与合规性"""
    from ..application_form.generator import ApplicationForm
    f = ApplicationForm(**form)
    report = _gen.validate(f)
    return report.to_dict()


@router.post("/application-form/preview", summary="生成申请单HTML预览")
def preview_form(form: dict):
    """生成可打印的HTML申请单（返回HTML内容）"""
    from ..application_form.generator import ApplicationForm
    f = ApplicationForm(**form)
    return _gen.generate_html(f)


@router.post("/application-form/html", summary="生成申请单HTML")
def generate_html(form: dict):
    """生成并返回可打印的HTML申请单"""
    from ..application_form.generator import ApplicationForm
    f = ApplicationForm(**form)
    return _gen.generate_html(f)


@router.post("/application-form/json", summary="生成申请单JSON")
def generate_json(form: dict):
    """生成申请单JSON"""
    from ..application_form.generator import ApplicationForm
    f = ApplicationForm(**form)
    return {"form": form, "json": f.to_json()}


# ---- 申请单生成页面 ----

@router.get("/application-form", response_class=HTMLResponse, summary="申请单生成页面")
def application_form_page():
    """返回申请单生成 Web 页面"""
    if _APPLICATION_FORM_HTML.exists():
        return _APPLICATION_FORM_HTML.read_text(encoding="utf-8")
    return "<h1>申请单生成页面未找到</h1>", 404


@router.get("/application-form/index.html", response_class=HTMLResponse, summary="申请单生成页面（别名）")
def application_form_index():
    """返回申请单生成 Web 页面"""
    return application_form_page()

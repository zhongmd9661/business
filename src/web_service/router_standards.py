"""接待标准查询 API 路由"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from ..standards_query import query

router = APIRouter()

# 标准参考页路径
_REFERENCE_HTML = Path(__file__).parent.parent / "standards_query" / "reference.html"


@router.get("/standards/quick", summary="一键查询标准")
def quick_standards(
    personnel_level: str,
    reception_type: str,
    guest_count: int | None = None,
):
    """经办人快速查询 — 根据人员层级和招待类型返回完整标准"""
    return query.quick_lookup(personnel_level, reception_type, guest_count)


@router.get("/standards/external", summary="对外业务招待标准矩阵")
def external_standards():
    """返回对外业务招待标准矩阵"""
    return [s.to_dict() for s in __import__('..standards_query.standards', fromlist=['EXTERNAL_STANDARDS']).EXTERNAL_STANDARDS]


@router.get("/standards/internal", summary="内部业务招待标准")
def internal_standards():
    """返回内部业务招待标准"""
    return [s.to_dict() for s in __import__('..standards_query.standards', fromlist=['INTERNAL_STANDARDS']).INTERNAL_STANDARDS]


@router.get("/standards/companion", summary="陪同人数计算")
def companion_calculation(guest_count: int, reception_type: str = "外部"):
    """根据人数计算陪同人数上限"""
    return query.calculate_companion_limit(guest_count, reception_type)


@router.get("/standards/types", summary="招待类型说明")
def reception_types():
    """返回所有招待类型的详细说明"""
    return query.get_reception_type_explanations()


@router.get("/standards/prohibitions", summary="禁止性规定")
def prohibitions():
    """返回禁止性规定汇总"""
    return query.get_prohibitions()


@router.get("/standards/approval-flow", summary="审批流程")
def approval_flow():
    """返回审批流程步骤"""
    return query.get_approval_flow()


@router.get("/standards/holiday-reporting", summary="节假日报备要求")
def holiday_reporting():
    """返回节假日报备信息"""
    return query.get_holiday_reporting()


@router.get("/standards/reference", response_class=HTMLResponse, summary="标准参考页")
def reference_page():
    """返回标准参考 HTML 页面"""
    if _REFERENCE_HTML.exists():
        return _REFERENCE_HTML.read_text(encoding="utf-8")
    return "<h1>参考页未找到</h1>", 404


@router.get("/standards/templates", summary="场景接待模板列表")
def list_templates():
    """返回所有场景接待模板"""
    return query.templates.get_templates()


@router.get("/standards/templates/{template_id}", summary="单个场景模板")
def get_template(template_id: str):
    """根据ID获取单个场景模板"""
    result = query.templates.get_template_by_id(template_id)
    if result is None:
        raise HTTPException(404, f"模板 {template_id} 不存在")
    return result


@router.get("/standards/templates/by-type", summary="按类型筛选模板")
def templates_by_type(reception_type: str):
    """按招待类型筛选模板"""
    return query.templates.get_templates_by_type(reception_type)

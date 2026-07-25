"""接待标准管理 — 管理员专用 API"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .auth import get_admin_user, get_current_user
from .models_db import (
    ReceptionStandard,
    ReceptionStandardHistory,
    ReceptionTemplate,
    User,
    get_db,
)

router = APIRouter()


# ===================================================================
# 对外招待标准
# ===================================================================

@router.get("/admin/standards/external", summary="获取对外招待标准列表")
def list_external_standards(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取所有对外招待标准"""
    standards = (
        db.query(ReceptionStandard)
        .filter(ReceptionStandard.category == "external", ReceptionStandard.enabled == True)
        .order_by(
            ReceptionStandard.personnel_level,
            ReceptionStandard.sub_category,
        )
        .all()
    )
    return [_standard_to_dict(s) for s in standards]


@router.get("/admin/standards/internal", summary="获取内部招待标准列表")
def list_internal_standards(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取所有内部招待标准"""
    standards = (
        db.query(ReceptionStandard)
        .filter(ReceptionStandard.category == "internal", ReceptionStandard.enabled == True)
        .order_by(ReceptionStandard.personnel_level)
        .all()
    )
    return [_standard_to_dict(s) for s in standards]


@router.get("/admin/standards/all", summary="获取全部标准")
def list_all_standards(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取全部标准（对外+内部）"""
    external = (
        db.query(ReceptionStandard)
        .filter(ReceptionStandard.category == "external", ReceptionStandard.enabled == True)
        .order_by(ReceptionStandard.personnel_level, ReceptionStandard.sub_category)
        .all()
    )
    internal = (
        db.query(ReceptionStandard)
        .filter(ReceptionStandard.category == "internal", ReceptionStandard.enabled == True)
        .order_by(ReceptionStandard.personnel_level)
        .all()
    )
    return {
        "external": [_standard_to_dict(s) for s in external],
        "internal": [_standard_to_dict(s) for s in internal],
    }


@router.put("/admin/standards/external/{std_id}", summary="修改对外标准")
def update_external_standard(
    std_id: int,
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """更新对外招待标准"""
    std = db.query(ReceptionStandard).filter(
        ReceptionStandard.id == std_id,
        ReceptionStandard.category == "external",
    ).first()
    if not std:
        raise HTTPException(404, "标准不存在")

    old_values = _standard_to_dict(std)

    if "meal_limit" in data:
        std.meal_limit = float(data["meal_limit"])
    if "souvenir_limit" in data:
        val = data["souvenir_limit"]
        std.souvenir_limit = float(val) if val is not None else None
    if "baijiu_limit" in data:
        std.baijiu_limit = float(data["baijiu_limit"])
    if "red_wine_limit" in data:
        std.red_wine_limit = float(data["red_wine_limit"])
    if "enabled" in data:
        std.enabled = bool(data["enabled"])

    std.updated_at = datetime.now().isoformat()
    std.updated_by = admin.id
    db.commit()
    db.refresh(std)

    # 记录审计历史
    _record_history(db, std.id, "update", old_values, _standard_to_dict(std), admin.id)
    return _standard_to_dict(std)


@router.put("/admin/standards/internal/{std_id}", summary="修改内部标准")
def update_internal_standard(
    std_id: int,
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """更新内部招待标准"""
    std = db.query(ReceptionStandard).filter(
        ReceptionStandard.id == std_id,
        ReceptionStandard.category == "internal",
    ).first()
    if not std:
        raise HTTPException(404, "标准不存在")

    old_values = _standard_to_dict(std)

    if "meal_limit" in data:
        std.meal_limit = float(data["meal_limit"])
    if "souvenir_limit" in data:
        val = data["souvenir_limit"]
        std.souvenir_limit = float(val) if val is not None else None
    if "baijiu_limit" in data:
        std.baijiu_limit = float(data["baijiu_limit"])
    if "red_wine_limit" in data:
        std.red_wine_limit = float(data["red_wine_limit"])
    if "enabled" in data:
        std.enabled = bool(data["enabled"])

    std.updated_at = datetime.now().isoformat()
    std.updated_by = admin.id
    db.commit()
    db.refresh(std)

    _record_history(db, std.id, "update", old_values, _standard_to_dict(std), admin.id)
    return _standard_to_dict(std)


@router.post("/admin/standards/external", summary="新增对外标准")
def create_external_standard(
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """新增对外招待标准"""
    std = ReceptionStandard(
        category="external",
        sub_category=data.get("sub_category", "外事/商务"),
        personnel_level=data["personnel_level"],
        meal_limit=float(data.get("meal_limit", 0)),
        souvenir_limit=float(data["souvenir_limit"]) if data.get("souvenir_limit") is not None else None,
        baijiu_limit=float(data.get("baijiu_limit", 0)),
        red_wine_limit=float(data.get("red_wine_limit", 0)),
        enabled=True,
    )
    db.add(std)
    db.commit()
    db.refresh(std)

    _record_history(db, std.id, "create", None, _standard_to_dict(std), admin.id)
    return _standard_to_dict(std)


@router.post("/admin/standards/internal", summary="新增内部标准")
def create_internal_standard(
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """新增内部招待标准"""
    std = ReceptionStandard(
        category="internal",
        sub_category="",
        personnel_level=data["personnel_level"],
        meal_limit=float(data.get("meal_limit", 0)),
        souvenir_limit=float(data["souvenir_limit"]) if data.get("souvenir_limit") is not None else None,
        baijiu_limit=float(data.get("baijiu_limit", 0)),
        red_wine_limit=float(data.get("red_wine_limit", 0)),
        enabled=True,
    )
    db.add(std)
    db.commit()
    db.refresh(std)

    _record_history(db, std.id, "create", None, _standard_to_dict(std), admin.id)
    return _standard_to_dict(std)


@router.delete("/admin/standards/{std_id}", summary="禁用标准")
def disable_standard(
    std_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """禁用标准（软删除）"""
    std = db.query(ReceptionStandard).filter(ReceptionStandard.id == std_id).first()
    if not std:
        raise HTTPException(404, "标准不存在")

    old_values = _standard_to_dict(std)
    std.enabled = False
    std.updated_at = datetime.now().isoformat()
    std.updated_by = admin.id
    db.commit()

    _record_history(db, std.id, "disable", old_values, None, admin.id)
    return {"detail": "已禁用", "id": std.id}


@router.post("/admin/standards/{std_id}/enable", summary="启用标准")
def enable_standard(
    std_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """启用已禁用的标准"""
    std = db.query(ReceptionStandard).filter(ReceptionStandard.id == std_id).first()
    if not std:
        raise HTTPException(404, "标准不存在")

    old_values = _standard_to_dict(std)
    std.enabled = True
    std.updated_at = datetime.now().isoformat()
    std.updated_by = admin.id
    db.commit()

    _record_history(db, std.id, "enable", old_values, _standard_to_dict(std), admin.id)
    return {"detail": "已启用", "id": std.id}


# ===================================================================
# 陪同人数规则
# ===================================================================

@router.get("/admin/standards/companion-rules", summary="陪同人数规则")
def get_companion_rules(_admin: User = Depends(get_admin_user)):
    """获取陪同人数规则（当前为静态数据）"""
    return {
        "external": {
            "guest_limit": 5,
            "rule_desc": "招待对象≤5人时，陪餐人数可对等；>5人时，超过部分陪餐人数≤招待对象超过部分的1/2",
            "formula": "guest≤5: companion≤guest; guest>5: companion≤5+(guest-5)//2",
        },
        "internal": {
            "guest_limit": 10,
            "rule_desc": "内部招待：招待对象≤10人，陪同≤3人；>10人，陪同≤招待对象的1/3",
            "formula": "guest≤10: companion≤3; guest>10: companion≤guest//3",
        },
    }


# ===================================================================
# 禁止性规定
# ===================================================================

@router.get("/admin/standards/prohibitions", summary="禁止性规定")
def get_prohibitions(_admin: User = Depends(get_admin_user)):
    """获取禁止性规定列表"""
    from ..standards_query import standards
    return standards.PROHIBITIONS


@router.put("/admin/standards/prohibitions/{idx}", summary="修改禁止性规定")
def update_prohibition(
    idx: int,
    data: dict,
    _admin: User = Depends(get_admin_user),
):
    """修改禁止性规定（返回新值，实际修改在内存中）"""
    from ..standards_query import standards

    if idx < 0 or idx >= len(standards.PROHIBITIONS):
        raise HTTPException(404, "规定不存在")

    old = dict(standards.PROHIBITIONS[idx])
    if "条款" in data:
        standards.PROHIBITIONS[idx]["条款"] = data["条款"]
    if "规定" in data:
        standards.PROHIBITIONS[idx]["规定"] = data["规定"]
    return {"old": old, "new": standards.PROHIBITIONS[idx]}


# ===================================================================
# 招待类型说明
# ===================================================================

@router.get("/admin/standards/types", summary="招待类型说明")
def get_reception_types(_admin: User = Depends(get_admin_user)):
    """获取招待类型说明"""
    from ..standards_query import standards
    return standards.RECEPTION_TYPE_EXPLANATIONS


@router.put("/admin/standards/types/{idx}", summary="修改类型说明")
def update_reception_type(
    idx: int,
    data: dict,
    _admin: User = Depends(get_admin_user),
):
    """修改招待类型说明"""
    from ..standards_query import standards

    if idx < 0 or idx >= len(standards.RECEPTION_TYPE_EXPLANATIONS):
        raise HTTPException(404, "类型说明不存在")

    old = dict(standards.RECEPTION_TYPE_EXPLANATIONS[idx])
    for key in ("类型", "说明", "适用标准", "注意事项"):
        if key in data:
            standards.RECEPTION_TYPE_EXPLANATIONS[idx][key] = data[key]
    return {"old": old, "new": standards.RECEPTION_TYPE_EXPLANATIONS[idx]}


# ===================================================================
# 场景模板管理
# ===================================================================

@router.get("/admin/templates", summary="场景模板列表")
def list_templates(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取所有场景模板"""
    templates = (
        db.query(ReceptionTemplate)
        .filter(ReceptionTemplate.enabled == True)
        .order_by(ReceptionTemplate.id)
        .all()
    )
    return [_template_to_dict(t) for t in templates]


@router.get("/admin/templates/{template_id}", summary="单个场景模板")
def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """获取单个场景模板"""
    tpl = db.query(ReceptionTemplate).filter(
        ReceptionTemplate.template_id == template_id,
        ReceptionTemplate.enabled == True,
    ).first()
    if not tpl:
        raise HTTPException(404, f"模板 {template_id} 不存在")
    return _template_to_dict(tpl)


@router.post("/admin/templates", summary="新增场景模板")
def create_template(
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """新增场景模板"""
    if not data.get("template_id"):
        raise HTTPException(400, "template_id 必填")

    existing = db.query(ReceptionTemplate).filter(
        ReceptionTemplate.template_id == data["template_id"]
    ).first()
    if existing:
        raise HTTPException(400, f"模板ID {data['template_id']} 已存在")

    tpl = ReceptionTemplate(
        template_id=data["template_id"],
        title=data["title"],
        icon=data.get("icon", "📋"),
        icon_class=data.get("icon_class", "blue"),
        reception_type=data["reception_type"],
        category=data.get("category", ""),
        example_data=json.dumps(data.get("example", {}), ensure_ascii=False),
        notes=data.get("notes", ""),
        required_docs=data.get("required_docs", ""),
        enabled=True,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return _template_to_dict(tpl)


@router.put("/admin/templates/{template_id}", summary="修改场景模板")
def update_template(
    template_id: str,
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """修改场景模板"""
    tpl = db.query(ReceptionTemplate).filter(
        ReceptionTemplate.template_id == template_id
    ).first()
    if not tpl:
        raise HTTPException(404, f"模板 {template_id} 不存在")

    old_data = _template_to_dict(tpl)

    if "title" in data:
        tpl.title = data["title"]
    if "icon" in data:
        tpl.icon = data["icon"]
    if "icon_class" in data:
        tpl.icon_class = data["icon_class"]
    if "reception_type" in data:
        tpl.reception_type = data["reception_type"]
    if "category" in data:
        tpl.category = data["category"]
    if "example" in data:
        tpl.example_data = json.dumps(data["example"], ensure_ascii=False)
    if "notes" in data:
        tpl.notes = data["notes"]
    if "required_docs" in data:
        tpl.required_docs = data["required_docs"]
    if "enabled" in data:
        tpl.enabled = bool(data["enabled"])

    tpl.updated_at = datetime.now().isoformat()
    tpl.updated_by = admin.id
    db.commit()
    db.refresh(tpl)

    return {"old": old_data, "new": _template_to_dict(tpl)}


@router.delete("/admin/templates/{template_id}", summary="禁用场景模板")
def disable_template(
    template_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """禁用场景模板"""
    tpl = db.query(ReceptionTemplate).filter(
        ReceptionTemplate.template_id == template_id
    ).first()
    if not tpl:
        raise HTTPException(404, f"模板 {template_id} 不存在")

    tpl.enabled = False
    tpl.updated_at = datetime.now().isoformat()
    tpl.updated_by = admin.id
    db.commit()
    return {"detail": "已禁用", "id": tpl.template_id}


@router.post("/admin/templates/{template_id}/enable", summary="启用场景模板")
def enable_template(
    template_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """启用场景模板"""
    tpl = db.query(ReceptionTemplate).filter(
        ReceptionTemplate.template_id == template_id
    ).first()
    if not tpl:
        raise HTTPException(404, f"模板 {template_id} 不存在")

    tpl.enabled = True
    tpl.updated_at = datetime.now().isoformat()
    tpl.updated_by = admin.id
    db.commit()
    return {"detail": "已启用", "id": tpl.template_id}


# ===================================================================
# 审计历史
# ===================================================================

@router.get("/admin/standards/history", summary="标准修改历史")
def get_standards_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """获取标准修改历史"""
    histories = (
        db.query(ReceptionStandardHistory)
        .order_by(ReceptionStandardHistory.changed_at.desc())
        .limit(limit)
        .all()
    )
    return [_history_to_dict(h) for h in histories]


# ===================================================================
# 工具函数
# ===================================================================

def _standard_to_dict(s: ReceptionStandard) -> dict:
    return {
        "id": s.id,
        "category": s.category,
        "sub_category": s.sub_category,
        "personnel_level": s.personnel_level,
        "meal_limit": s.meal_limit,
        "souvenir_limit": s.souvenir_limit,
        "baijiu_limit": s.baijiu_limit,
        "red_wine_limit": s.red_wine_limit,
        "enabled": s.enabled,
        "updated_at": s.updated_at,
        "updated_by": s.updated_by,
    }


def _template_to_dict(t: ReceptionTemplate) -> dict:
    example = {}
    if t.example_data:
        try:
            example = json.loads(t.example_data)
        except (json.JSONDecodeError, TypeError):
            example = {}
    return {
        "id": t.id,
        "template_id": t.template_id,
        "title": t.title,
        "icon": t.icon,
        "icon_class": t.icon_class,
        "reception_type": t.reception_type,
        "category": t.category,
        "example": example,
        "notes": t.notes,
        "required_docs": t.required_docs,
        "enabled": t.enabled,
        "updated_at": t.updated_at,
        "updated_by": t.updated_by,
    }


def _history_to_dict(h: ReceptionStandardHistory) -> dict:
    old_values = {}
    new_values = {}
    if h.old_values:
        try:
            old_values = json.loads(h.old_values)
        except (json.JSONDecodeError, TypeError):
            pass
    if h.new_values:
        try:
            new_values = json.loads(h.new_values)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "id": h.id,
        "standard_id": h.standard_id,
        "action": h.action,
        "old_values": old_values,
        "new_values": new_values,
        "changed_by": h.changed_by,
        "changed_at": h.changed_at,
    }


def _record_history(
    db: Session,
    standard_id: int,
    action: str,
    old_values: dict | None,
    new_values: dict | None,
    changed_by: int | None,
):
    """记录标准修改历史"""
    history = ReceptionStandardHistory(
        standard_id=standard_id,
        action=action,
        old_values=json.dumps(old_values, ensure_ascii=False) if old_values else None,
        new_values=json.dumps(new_values, ensure_ascii=False) if new_values else None,
        changed_by=changed_by,
    )
    db.add(history)
    db.commit()

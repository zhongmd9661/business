"""字段提取规则管理 — 管理员 API"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .auth import get_admin_user
from .models_db import ExtractionRule, User, get_db

router = APIRouter()


@router.get("/admin/extraction-rules")
def list_extraction_rules(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取所有字段提取规则"""
    rules = (
        db.query(ExtractionRule)
        .filter(ExtractionRule.enabled == True)
        .order_by(ExtractionRule.id)
        .all()
    )
    return [_rule_to_dict(r) for r in rules]


@router.get("/admin/extraction-rules/all")
def list_all_extraction_rules(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取所有规则（含已禁用）"""
    rules = db.query(ExtractionRule).order_by(ExtractionRule.id).all()
    return [_rule_to_dict(r) for r in rules]


@router.get("/admin/extraction-rules/{slot_name}")
def get_extraction_rule(slot_name: str, db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取某槽位的提取规则"""
    rule = db.query(ExtractionRule).filter(
        ExtractionRule.slot_name == slot_name
    ).first()
    if not rule:
        raise HTTPException(404, f"槽位 {slot_name} 无提取规则")
    return _rule_to_dict(rule)


@router.post("/admin/extraction-rules")
def create_or_update_extraction_rule(
    data: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """新增或更新某槽位的提取规则
    Body: {"slot_name": "审批单", "rule_name": "approval_extraction", "fields": [...]}
    """
    slot_name = data.get("slot_name")
    if not slot_name:
        raise HTTPException(400, "slot_name 必填")

    fields = data.get("fields", [])
    # 验证字段结构
    for f in fields:
        if not f.get("name"):
            raise HTTPException(400, "每个字段必须有 name")

    existing = db.query(ExtractionRule).filter(
        ExtractionRule.slot_name == slot_name
    ).first()

    if existing:
        existing.rule_name = data.get("rule_name", existing.rule_name)
        existing.fields_json = json.dumps(fields, ensure_ascii=False)
        existing.updated_at = datetime.now().isoformat()
        existing.enabled = data.get("enabled", True)
        if "use_llm" in data:
            existing.use_llm = data["use_llm"]
        if "llm_prompt_template" in data:
            existing.llm_prompt_template = data["llm_prompt_template"]
        if "llm_response_schema" in data:
            existing.llm_response_schema = json.dumps(data["llm_response_schema"], ensure_ascii=False) if data["llm_response_schema"] else None
        db.commit()
        db.refresh(existing)
        return _rule_to_dict(existing)
    else:
        rule = ExtractionRule(
            slot_name=slot_name,
            rule_name=data.get("rule_name", ""),
            fields_json=json.dumps(fields, ensure_ascii=False),
            enabled=data.get("enabled", True),
            use_llm=data.get("use_llm", False),
            llm_prompt_template=data.get("llm_prompt_template"),
            llm_response_schema=json.dumps(data.get("llm_response_schema"), ensure_ascii=False) if data.get("llm_response_schema") else None,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return _rule_to_dict(rule)


@router.put("/admin/extraction-rules/{slot_name}")
def update_extraction_rule(
    slot_name: str,
    data: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """更新某槽位的提取规则"""
    rule = db.query(ExtractionRule).filter(
        ExtractionRule.slot_name == slot_name
    ).first()
    if not rule:
        raise HTTPException(404, f"槽位 {slot_name} 无提取规则")

    if "fields" in data:
        fields = data["fields"]
        for f in fields:
            if not f.get("name"):
                raise HTTPException(400, "每个字段必须有 name")
        rule.fields_json = json.dumps(fields, ensure_ascii=False)

    if "rule_name" in data:
        rule.rule_name = data["rule_name"]
    if "enabled" in data:
        rule.enabled = data["enabled"]
    if "use_llm" in data:
        rule.use_llm = data["use_llm"]
    if "llm_prompt_template" in data:
        rule.llm_prompt_template = data["llm_prompt_template"]
    if "llm_response_schema" in data:
        rule.llm_response_schema = json.dumps(data["llm_response_schema"], ensure_ascii=False) if data["llm_response_schema"] else None

    rule.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(rule)
    return _rule_to_dict(rule)


@router.delete("/admin/extraction-rules/{slot_name}")
def delete_extraction_rule(
    slot_name: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """删除某槽位的提取规则（软删除：禁用）"""
    rule = db.query(ExtractionRule).filter(
        ExtractionRule.slot_name == slot_name
    ).first()
    if not rule:
        raise HTTPException(404, f"槽位 {slot_name} 无提取规则")
    rule.enabled = False
    rule.updated_at = datetime.now().isoformat()
    db.commit()
    return {"detail": "已禁用", "slot_name": slot_name}


@router.post("/admin/extraction-rules/{slot_name}/preview")
def preview_extraction(
    slot_name: str,
    data: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """预览提取结果：传入 markdown 文本和字段定义，返回提取结果
    Body: {"markdown": "...", "fields": [...]}
    """
    markdown = data.get("markdown", "")
    fields = data.get("fields", [])

    # 如果没有传入 fields，使用数据库中的规则
    if not fields:
        rule = db.query(ExtractionRule).filter(
            ExtractionRule.slot_name == slot_name,
            ExtractionRule.enabled == True,
        ).first()
        if rule and rule.fields_json:
            try:
                fields = json.loads(rule.fields_json)
            except json.JSONDecodeError:
                fields = []

    # 导入提取函数
    from .service_audit import _kv_extract, _extract_number, _parse_date

    result = {}
    for field in fields:
        name = field.get("name", "")
        keywords = field.get("keywords", [])
        field_type = field.get("type", "text")

        value = _kv_extract(markdown, keywords)

        if field_type == "number":
            value = _extract_number(value)
        elif field_type == "date":
            value = _parse_date(value)

        result[name] = value

    return {"slot_name": slot_name, "fields": result}


@router.post("/admin/extraction-rules/{slot_name}/llm-preview")
async def preview_llm_extraction(
    slot_name: str,
    data: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """LLM 提取预览：使用大模型从 OCR markdown 文本中提取字段
    Body: {"markdown": "...", "fields": [...], "prompt_template": "..."}
    """
    markdown = data.get("markdown", "")
    fields = data.get("fields", [])
    prompt_template = data.get("prompt_template")

    # 如果没有传入 fields，使用数据库中的规则
    if not fields:
        rule = db.query(ExtractionRule).filter(
            ExtractionRule.slot_name == slot_name,
            ExtractionRule.enabled == True,
        ).first()
        if rule and rule.fields_json:
            try:
                fields = json.loads(rule.fields_json)
            except json.JSONDecodeError:
                fields = []
            # 如果有自定义提示词模板，使用它
            if prompt_template is None and rule.llm_prompt_template:
                prompt_template = rule.llm_prompt_template

    # 调用 LLM 提取（异步端点，直接 await）
    from .service_audit import extract_from_llm_async

    result = await extract_from_llm_async(markdown, slot_name)

    return {
        "slot_name": slot_name,
        "method": "llm",
        "fields": result,
    }



def _rule_to_dict(r: ExtractionRule) -> dict:
    fields = []
    if r.fields_json:
        try:
            fields = json.loads(r.fields_json)
        except (json.JSONDecodeError, TypeError):
            pass
    llm_response_schema = None
    if r.llm_response_schema:
        try:
            llm_response_schema = json.loads(r.llm_response_schema)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "id": r.id,
        "slot_name": r.slot_name,
        "rule_name": r.rule_name,
        "fields": fields,
        "enabled": r.enabled,
        "use_llm": r.use_llm if r.use_llm is not None else False,
        "llm_prompt_template": r.llm_prompt_template,
        "llm_response_schema": llm_response_schema,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }

"""审核规则管理 — 管理员 API

管理审核规则（非提取规则），即 run_review 中调用的 6 条校验规则。
规则存储在 audit_rules 表中，支持增删改查和启用/禁用。
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .auth import get_admin_user
from .models_db import AuditRule, AuditRuleHistory, User, get_db

router = APIRouter()


# ===================================================================
# 默认规则种子数据
# ===================================================================

DEFAULT_RULES = [
    {
        "category": "一致性校验",
        "rule_name": "金额一致性",
        "clause": "以发票小写金额为准，审批单、支付凭证、支付流水、报账单金额应与发票一致",
        "level": "高",
        "description": "核对发票金额与各单据金额是否一致，差异超过 0.01 元即标记为不通过",
        "check_expression": "amount_consistency",
        "source_document": "系统内置",
        "enabled": True,
    },
    {
        "category": "一致性校验",
        "rule_name": "日期一致性",
        "clause": "以审批单招待日期为基准，发票日期应≤招待日期，支付时间应≥招待日期",
        "level": "高",
        "description": "核对审批单、发票、支付凭证的日期逻辑关系",
        "check_expression": "date_consistency",
        "source_document": "系统内置",
        "enabled": True,
    },
    {
        "category": "合规性校验",
        "rule_name": "招待标准合规性",
        "clause": "人均费用和陪同人数应符合招待类型标准",
        "level": "高",
        "description": "工作餐≤60元，内部≤150元，其他公务≤200元，外事/商务≤400元；陪同人数按标准限制",
        "check_expression": "standard_compliance",
        "source_document": "系统内置",
        "enabled": True,
    },
    {
        "category": "经营风险",
        "rule_name": "单位经营状态",
        "clause": "招待单位应处于正常经营状态",
        "level": "提示",
        "description": "检查招待单位是否正常经营，异常状态需人工审核",
        "check_expression": "business_status",
        "source_document": "系统内置",
        "enabled": True,
    },
    {
        "category": "一致性校验",
        "rule_name": "支付凭证一致性",
        "clause": "支付凭证和支付流水的关键信息应一致",
        "level": "高",
        "description": "比对交易单号、金额、商户名称等关键信息",
        "check_expression": "payment_consistency",
        "source_document": "系统内置",
        "enabled": True,
    },
    {
        "category": "一致性校验",
        "rule_name": "活动函件日期",
        "clause": "活动函件日期与招待日期应相差在±7天内",
        "level": "中",
        "description": "核对活动函件中的交流时间与审批单招待日期是否匹配",
        "check_expression": "event_date",
        "source_document": "系统内置",
        "enabled": True,
    },
]


# ===================================================================
# CRUD API
# ===================================================================

@router.get("/admin/review-rules/categories")
def get_categories(db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取所有规则分类"""
    _seed_default_rules(db)
    categories = db.query(AuditRule.category).filter(AuditRule.enabled == True).distinct().all()
    return sorted(set(c[0] for c in categories))


@router.get("/admin/review-rules")
def list_review_rules(
    category: str = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """获取所有审核规则（可选按分类筛选）"""
    _seed_default_rules(db)
    q = db.query(AuditRule)
    if category:
        q = q.filter(AuditRule.category == category)
    rules = q.order_by(AuditRule.id).all()
    return [_rule_to_dict(r) for r in rules]


@router.get("/admin/review-rules/{rule_id}")
def get_review_rule(rule_id: int, db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取单条规则详情"""
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, f"规则 ID {rule_id} 不存在")
    return _rule_to_dict(rule)


@router.post("/admin/review-rules")
def create_or_update_review_rule(
    data: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """新增或更新审核规则
    Body: {"category": "...", "rule_name": "...", "clause": "...", "level": "...",
           "description": "...", "check_expression": "...", "enabled": true}
    """
    rule_name = data.get("rule_name")
    if not rule_name:
        raise HTTPException(400, "rule_name 必填")

    existing = db.query(AuditRule).filter(AuditRule.rule_name == rule_name).first()

    if existing:
        old_dict = _rule_to_dict(existing)
        for field in ("category", "clause", "level", "description", "check_expression",
                       "source_document", "enabled"):
            if field in data:
                setattr(existing, field, data[field])
        existing.updated_at = datetime.now().isoformat()
        db.commit()
        db.refresh(existing)
        _add_history(db, existing.id, "update",
                      json.dumps(old_dict, ensure_ascii=False),
                      json.dumps(_rule_to_dict(existing), ensure_ascii=False),
                      _admin.id)
        return _rule_to_dict(existing)
    else:
        rule = AuditRule(
            category=data.get("category", "自定义"),
            rule_name=rule_name,
            clause=data.get("clause", ""),
            level=data.get("level", "中"),
            description=data.get("description", ""),
            check_expression=data.get("check_expression", ""),
            source_document=data.get("source_document", "手动创建"),
            enabled=data.get("enabled", True),
            created_by=_admin.id,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return _rule_to_dict(rule)


@router.put("/admin/review-rules/{rule_id}")
def update_review_rule(
    rule_id: int,
    data: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """更新审核规则（按 ID）"""
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, f"规则 ID {rule_id} 不存在")

    old_dict = _rule_to_dict(rule)
    for field in ("category", "clause", "level", "description", "check_expression",
                   "source_document", "enabled"):
        if field in data:
            setattr(rule, field, data[field])
    rule.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(rule)

    _add_history(db, rule.id, "update",
                  json.dumps(old_dict, ensure_ascii=False),
                  json.dumps(_rule_to_dict(rule), ensure_ascii=False),
                  _admin.id)
    return _rule_to_dict(rule)


@router.delete("/admin/review-rules/{rule_id}")
def delete_review_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """删除审核规则（软删除：禁用）"""
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, f"规则 ID {rule_id} 不存在")

    old_dict = _rule_to_dict(rule)
    rule.enabled = False
    rule.updated_at = datetime.now().isoformat()
    db.commit()

    _add_history(db, rule.id, "disable",
                  json.dumps(old_dict, ensure_ascii=False), "disabled", _admin.id)
    return {"detail": "已禁用", "rule_id": rule_id}


@router.post("/admin/review-rules/{rule_id}/restore")
def restore_review_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """恢复（启用）已禁用的规则"""
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, f"规则 ID {rule_id} 不存在")

    rule.enabled = True
    rule.updated_at = datetime.now().isoformat()
    db.commit()

    _add_history(db, rule.id, "enable", "disabled", "enabled", _admin.id)
    return _rule_to_dict(rule)


@router.get("/admin/review-rules/history/{rule_id}")
def get_rule_history(rule_id: int, db: Session = Depends(get_db), _admin: User = Depends(get_admin_user)):
    """获取规则变更历史"""
    history = (
        db.query(AuditRuleHistory)
        .filter(AuditRuleHistory.rule_id == rule_id)
        .order_by(AuditRuleHistory.changed_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": h.id,
            "action": h.action,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "changed_by": h.changed_by,
            "changed_at": h.changed_at,
        }
        for h in history
    ]


# ===================================================================
# 工具函数
# ===================================================================

def _rule_to_dict(r: AuditRule) -> dict:
    """将数据库对象转为字典"""
    return {
        "id": r.id,
        "category": r.category,
        "rule_name": r.rule_name,
        "clause": r.clause,
        "level": r.level,
        "description": r.description or "",
        "check_expression": r.check_expression,
        "source_document": r.source_document or "",
        "enabled": r.enabled,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def _add_history(db: Session, rule_id: int, action: str, old_value: str, new_value: str, user_id: int):
    """记录规则变更历史"""
    h = AuditRuleHistory(
        rule_id=rule_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        changed_by=user_id,
        changed_at=datetime.now().isoformat(),
    )
    db.add(h)


def _seed_default_rules(db: Session):
    """初始化默认规则（首次调用时插入）"""
    existing = db.query(AuditRule).filter(
        AuditRule.check_expression == "amount_consistency"
    ).first()
    if existing:
        return  # 已有种子数据，跳过

    for rd in DEFAULT_RULES:
        rule = AuditRule(**{k: v for k, v in rd.items() if k != "enabled"})
        rule.enabled = rd.get("enabled", True)
        db.add(rule)
    db.commit()

"""API 路由 — 审核规则管理 + 制度文件同步"""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import schemas
from .auth import get_admin_user, get_current_user
from .config import RULES_DIR
from .models_db import (
    AuditRule,
    AuditRuleHistory,
    DocumentVersion,
    SyncHistory,
    User,
    get_db,
)

# Single router to ensure correct route ordering
rule_router = APIRouter()


# ==================== Rule CRUD ====================

@rule_router.get("/rules")
def list_rules(
    category: str = None,
    enabled: bool = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(AuditRule)
    if category:
        q = q.filter(AuditRule.category == category)
    if enabled is not None:
        q = q.filter(AuditRule.enabled == enabled)
    rules = q.order_by(AuditRule.category, AuditRule.rule_name).all()
    return [schemas.AuditRuleResponse.model_validate(r) for r in rules]


@rule_router.get("/rules/categories")
def list_categories(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cats = db.query(AuditRule.category).filter(AuditRule.enabled == True).distinct().all()
    return [c[0] for c in cats]


@rule_router.get("/rules/{rule_id}")
def get_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "规则不存在")
    return schemas.AuditRuleResponse.model_validate(rule)


@rule_router.post("/rules", status_code=201)
def create_rule(
    req: schemas.AuditRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user),
):
    rule = AuditRule(
        **req.model_dump(),
        created_by=user.id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    # Log history after commit (rule.id is now available)
    hist = AuditRuleHistory(
        rule_id=rule.id,
        action="create",
        new_value=req.model_dump_json(),
        changed_by=user.id,
    )
    db.add(hist)
    db.commit()
    # Reload rules so changes take effect immediately
    from . import service
    service.reload_rules()
    return schemas.AuditRuleResponse.model_validate(rule)


@rule_router.put("/rules/{rule_id}")
def update_rule(
    rule_id: int,
    req: schemas.AuditRuleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user),
):
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "规则不存在")

    from .schemas import AuditRuleResponse
    old_snapshot = AuditRuleResponse.model_validate(rule).model_dump_json()
    update_data = req.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(rule, key, value)

    rule.updated_at = datetime.now().isoformat()

    hist = AuditRuleHistory(
        rule_id=rule_id,
        action="update",
        old_value=old_snapshot,
        new_value=req.model_dump_json(exclude_unset=True),
        changed_by=user.id,
    )
    db.add(hist)
    db.commit()
    db.refresh(rule)
    # Reload rules so changes take effect immediately
    from . import service
    service.reload_rules()
    return schemas.AuditRuleResponse.model_validate(rule)


@rule_router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user),
):
    rule = db.query(AuditRule).filter(AuditRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "规则不存在")

    from .schemas import AuditRuleResponse
    old_snapshot = AuditRuleResponse.model_validate(rule).model_dump_json()
    hist = AuditRuleHistory(
        rule_id=rule_id,
        action="delete",
        old_value=old_snapshot,
        changed_by=user.id,
    )
    db.add(hist)
    db.delete(rule)
    db.commit()
    # Reload rules so changes take effect immediately
    from . import service
    service.reload_rules()
    return {"detail": "规则已删除"}


# ==================== Sync ====================

@rule_router.post("/rules/sync")
def trigger_sync(
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user),
):
    from .rule_sync import run_sync
    result = run_sync(db, user.id, trigger_type="manual")
    return result


@rule_router.get("/rules/sync/status")
def sync_status(
    db: Session = Depends(get_db),
    _user: User = Depends(get_admin_user),
):
    docs = db.query(DocumentVersion).all()
    pending = [d for d in docs if d.sync_status == "pending"]
    return {
        "pending_changes": len(pending),
        "documents": [
            {
                "name": d.document_name,
                "status": d.sync_status,
                "last_sync": d.parsed_at,
                "diff_summary": d.sync_diff[:200] if d.sync_diff else None,
            }
            for d in docs
        ],
    }


@rule_router.post("/rules/sync/apply")
def apply_sync(
    req: schemas.SyncApplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user),
):
    from .rule_sync import apply_sync_changes

    if not req.apply:
        for dv in db.query(DocumentVersion).filter(DocumentVersion.sync_status == "pending").all():
            dv.sync_status = "synced"
            dv.sync_diff = None
        db.commit()
        return {"detail": "已拒绝待处理的同步变更"}

    result = apply_sync_changes(db, user.id)
    return result


@rule_router.get("/rules/sync/history")
def sync_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    _user: User = Depends(get_admin_user),
):
    records = (
        db.query(SyncHistory)
        .order_by(SyncHistory.operated_at.desc())
        .limit(limit)
        .all()
    )
    return [schemas.SyncHistoryResponse.model_validate(r) for r in records]


# ===================================================================
# 制度文件查看
# ===================================================================

@rule_router.get("/rules/documents", summary="制度文件列表")
def list_rule_documents(_user: User = Depends(get_current_user)):
    """返回规则目录下的所有制度文件"""
    if not RULES_DIR.exists():
        return []
    files = []
    for fpath in sorted(RULES_DIR.rglob("*")):
        if fpath.is_file() and fpath.suffix.lower() in (
            ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
        ):
            files.append({
                "name": fpath.name,
                "path": str(fpath.relative_to(RULES_DIR)),
                "size": fpath.stat().st_size,
                "suffix": fpath.suffix.lower(),
            })
    return files


@rule_router.get("/rules/documents/{file_path:path}", summary="查看/下载制度文件")
def view_rule_document(file_path: str, _user: User = Depends(get_current_user)):
    """按路径查看或下载制度文件"""
    full_path = RULES_DIR / file_path
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(404, "文件不存在")
    # 防止路径遍历
    if not full_path.resolve().is_relative_to(RULES_DIR.resolve()):
        raise HTTPException(403, "无权访问该文件")
    return FileResponse(
        path=str(full_path),
        media_type=None,
        filename=full_path.name,
    )

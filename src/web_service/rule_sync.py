"""制度文件监控与规则同步"""
import json
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .config import RULES_DIR, RULE_SYNC_INTERVAL_MIN
from .models_db import AuditRule, DocumentVersion, SyncHistory


def scan_rules_directory(db: Session, user_id: int = None) -> list[dict]:
    """扫描制度目录，检测文件 mtime 变化"""
    if not RULES_DIR.exists():
        return []

    changed = []
    for fpath in RULES_DIR.glob("*.docx"):
        current_mtime = os.path.getmtime(fpath)
        dv = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.file_path == str(fpath))
            .first()
        )
        if not dv:
            # New document found
            dv = DocumentVersion(
                document_name=fpath.stem,
                file_path=str(fpath),
                last_mtime=current_mtime,
                sync_status="pending",
            )
            db.add(dv)
            db.commit()
            changed.append({"file": str(fpath), "action": "new"})
        elif abs(current_mtime - dv.last_mtime) > 1.0:
            dv.sync_status = "pending"
            changed.append({"file": str(fpath), "action": "modified"})

    return changed


def diff_rules(old_rules: list[dict], new_rules: list[dict]) -> dict:
    """按 clause + rule_name 对比新旧规则"""
    old_map = {(r["clause"], r["rule_name"]): r for r in old_rules}
    new_map = {(r["clause"], r["rule_name"]): r for r in new_rules}

    added = [r for k, r in new_map.items() if k not in old_map]
    deleted = [r for k, r in old_map.items() if k not in new_map]
    modified = []
    unchanged = []

    for k in old_map:
        if k in new_map:
            if old_map[k] != new_map[k]:
                modified.append({"old": old_map[k], "new": new_map[k]})
            else:
                unchanged.append(new_map[k])

    return {
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "unchanged_count": len(unchanged),
        "total_new": len(new_rules),
    }


def detect_conflicts(db: Session, parsed_rules: list[dict]) -> list[dict]:
    """检测管理员手动修改的规则与制度原文的冲突。

    如果规则的 source_document 表明它来自制度文档，
    且管理员手动修改过（数据库中的值与制度原文不一致），
    则标记为冲突，需人工介入。

    Returns:
        冲突列表，每项包含 rule_id, rule_name, db_value, doc_value
    """
    conflicts = []
    parsed_map = {}
    for pr in parsed_rules:
        key = (pr.get("clause", ""), pr.get("rule_name", ""))
        parsed_map[key] = pr

    # 检查数据库中来自制度文档的规则
    for rule in db.query(AuditRule).filter(AuditRule.source_document.isnot(None)).all():
        key = (rule.clause, rule.rule_name)
        if key not in parsed_map:
            continue

        doc_rule = parsed_map[key]
        # 比较关键字段是否有差异
        for field in ("category", "level", "description", "check_expression"):
            db_val = getattr(rule, field, "")
            doc_val = doc_rule.get(field, "")
            if db_val and doc_val and db_val != doc_val:
                conflicts.append({
                    "rule_id": rule.id,
                    "rule_name": rule.rule_name,
                    "clause": rule.clause,
                    "field": field,
                    "db_value": db_val[:200] if db_val else "",
                    "doc_value": doc_val[:200] if doc_val else "",
                    "source_document": rule.source_document,
                })

    return conflicts


def run_sync(db: Session, user_id: int, trigger_type: str = "auto") -> dict:
    """执行同步：扫描 → 解析 → 对比 → 冲突检测"""
    from .rule_parser import parse_all_documents

    changed = scan_rules_directory(db)
    if not changed:
        return {"detail": "无文件变更", "changed_files": []}

    # Parse all documents
    parsed_rules = parse_all_documents()

    # Get current rules from DB
    current_rules = []
    for rule in db.query(AuditRule).all():
        current_rules.append({
            "category": rule.category,
            "rule_name": rule.rule_name,
            "clause": rule.clause,
            "level": rule.level,
            "description": rule.description,
            "check_expression": rule.check_expression,
        })

    # Diff
    new_rules_list = []
    for pr in parsed_rules:
        new_rules_list.append({
            "category": pr.get("category", ""),
            "rule_name": pr.get("rule_name", ""),
            "clause": pr.get("clause", ""),
            "rule_level": pr.get("level", "中"),
            "description": pr.get("description", ""),
            "check_expression": pr.get("check_expression", ""),
        })

    report = diff_rules(current_rules, new_rules_list)

    # 冲突检测
    conflicts = detect_conflicts(db, parsed_rules)

    if conflicts:
        report["conflicts"] = conflicts
        report["has_conflicts"] = True
    else:
        report["has_conflicts"] = False

    # Update document versions
    for fpath in RULES_DIR.glob("*.docx"):
        dv = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.file_path == str(fpath))
            .first()
        )
        if dv:
            dv.last_mtime = os.path.getmtime(fpath)
            dv.parsed_at = datetime.now().isoformat()
            dv.sync_diff = json.dumps(report, ensure_ascii=False)
            if conflicts:
                dv.sync_status = "conflict"

    # Record sync history
    hist = SyncHistory(
        trigger_type=trigger_type,
        document_name="批量同步",
        rules_added=len(report["added"]),
        rules_modified=len(report["modified"]),
        rules_deleted=len(report["deleted"]),
        diff_report=json.dumps(report, ensure_ascii=False),
        status="pending",
        operated_by=user_id,
    )
    db.add(hist)
    db.commit()

    # 触发 webhook 通知
    _notify_sync_result(report, trigger_type)

    return {
        "detail": "同步完成，请管理员确认",
        "changed_files": len(changed),
        "diff": {
            "added": len(report["added"]),
            "modified": len(report["modified"]),
            "deleted": len(report["deleted"]),
            "unchanged": report["unchanged_count"],
        },
        "has_conflicts": report.get("has_conflicts", False),
        "conflict_count": len(conflicts),
    }


def apply_sync_changes(db: Session, user_id: int) -> dict:
    """应用同步变更"""
    from .rule_parser import parse_all_documents

    parsed_rules = parse_all_documents()

    # 冲突检测：跳过有冲突的规则，不强制覆盖
    conflicts = detect_conflicts(db, parsed_rules)
    conflict_keys = set()
    for c in conflicts:
        rule = db.query(AuditRule).filter(AuditRule.id == c["rule_id"]).first()
        if rule:
            conflict_keys.add((rule.clause, rule.rule_name))

    skipped = 0
    # Update existing rules / add new / remove deleted
    for pr in parsed_rules:
        key = (pr.get("clause", ""), pr.get("rule_name", ""))
        # 跳过有冲突的规则
        if key in conflict_keys:
            skipped += 1
            continue

        existing = (
            db.query(AuditRule)
            .filter(AuditRule.clause == key[0], AuditRule.rule_name == key[1])
            .first()
        )
        if existing:
            # Update
            for field in ("category", "level", "description", "check_expression", "source_document"):
                if pr.get(field):
                    setattr(existing, field, pr[field])
            existing.updated_at = datetime.now().isoformat()
        else:
            # Create
            new_rule = AuditRule(
                category=pr.get("category", ""),
                rule_name=pr.get("rule_name", ""),
                clause=pr.get("clause", ""),
                level=pr.get("level", "中"),
                description=pr.get("description", ""),
                check_expression=pr.get("check_expression", ""),
                source_document=pr.get("source_document", ""),
                enabled=True,
                created_by=user_id,
            )
            db.add(new_rule)

    # Update document version status
    for dv in db.query(DocumentVersion).filter(DocumentVersion.sync_status == "pending").all():
        dv.sync_status = "applied"
        dv.applied_by = user_id
        dv.applied_at = datetime.now().isoformat()
        dv.sync_diff = None

    # Update sync history
    pending_hist = (
        db.query(SyncHistory)
        .filter(SyncHistory.status == "pending")
        .order_by(SyncHistory.operated_at.desc())
        .first()
    )
    if pending_hist:
        pending_hist.status = "applied"

    db.commit()

    return {
        "detail": "同步变更已应用",
        "rules_updated": len(parsed_rules) - skipped,
        "conflicts_skipped": skipped,
    }


def _notify_sync_result(report: dict, trigger_type: str) -> None:
    """同步完成后发送通知（Webhook）"""
    import urllib.request
    import urllib.error

    webhook_url = os.environ.get("RULE_SYNC_WEBHOOK_URL", "")
    if not webhook_url:
        return

    payload = {
        "trigger_type": trigger_type,
        "timestamp": datetime.now().isoformat(),
        "diff": {
            "added": len(report.get("added", [])),
            "modified": len(report.get("modified", [])),
            "deleted": len(report.get("deleted", [])),
            "unchanged": report.get("unchanged_count", 0),
        },
        "has_conflicts": report.get("has_conflicts", False),
        "conflict_count": len(report.get("conflicts", [])),
    }

    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass  # Webhook 响应无需处理
    except Exception:
        pass  # Webhook 失败不影响同步流程


def start_sync_scanner():
    """启动定时扫描器"""
    import asyncio

    async def _periodic_scan():
        from .models_db import SessionLocal

        while True:
            try:
                db = SessionLocal()
                changed = scan_rules_directory(db)
                if changed:
                    run_sync(db, user_id=None, trigger_type="auto")
                db.close()
            except Exception as e:
                print(f"[rule_sync] 扫描错误: {e}")
            await asyncio.sleep(RULE_SYNC_INTERVAL_MIN * 60)

    return asyncio.create_task(_periodic_scan())

"""审核规则缓存 — 从数据库加载规则并提供失效更新"""
from __future__ import annotations

import threading
from typing import Optional

from sqlalchemy.orm import Session

from .models_db import AuditRule


class RuleCache:
    """内存缓存已启用的审核规则，减少数据库查询开销。

    规则变更后调用 invalidate() 重新加载。
    """

    def __init__(self):
        self._rules: list[dict] = []
        self._loaded = False
        self._lock = threading.Lock()

    @property
    def rules(self) -> list[dict]:
        return list(self._rules)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, db: Session) -> int:
        """从数据库加载所有启用的规则到缓存"""
        with self._lock:
            rules = (
                db.query(AuditRule)
                .filter(AuditRule.enabled == True)
                .order_by(AuditRule.category, AuditRule.rule_name)
                .all()
            )
            self._rules = []
            for rule in rules:
                self._rules.append({
                    "id": rule.id,
                    "category": rule.category,
                    "rule_name": rule.rule_name,
                    "clause": rule.clause,
                    "level": rule.level,
                    "description": rule.description or "",
                    "check_expression": rule.check_expression or "",
                    "source_document": rule.source_document or "",
                })
            self._loaded = True
            return len(self._rules)

    def invalidate(self) -> None:
        """标记缓存失效，下次 load 时重新加载"""
        with self._lock:
            self._loaded = False
            self._rules = []

    def get_by_category(self, category: str) -> list[dict]:
        """按分类获取规则"""
        return [r for r in self._rules if r["category"] == category]

    def get_with_expression(self) -> list[dict]:
        """获取带有 check_expression 的规则（可由规则引擎评估）"""
        return [r for r in self._rules if r.get("check_expression")]


# Global singleton
_rule_cache: Optional[RuleCache] = None


def get_rule_cache() -> RuleCache:
    global _rule_cache
    if _rule_cache is None:
        _rule_cache = RuleCache()
    return _rule_cache

"""规则表达式解析器 — 将数据库中的 JSON 规则表达式作用于提取的字段"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Optional

from .models import ExtractedFields, Finding, RuleCategory, BatchFinding, BatchReviewContext

# ---------------------------------------------------------------------------
# Field helpers — resolve field names from ExtractedFields
# ---------------------------------------------------------------------------

_FIELD_MAP: dict[str, str] = {
    "reception_date": "reception_date",
    "invoice_date": "invoice_date",
    "apply_date": "apply_date",
    "payment_date": "payment_date",
    "invoice_amount": "invoice_amount",
    "actual_amount": "actual_amount",
    "per_person_amount": "per_person_amount",
    "alcohol_price": "alcohol_price",
    "souvenir_amount": "souvenir_amount",
    "guest_count": "guest_count",
    "companion_count": "companion_count",
    "handler": "handler",
    "payee": "payee",
    "personnel_level": "personnel_level",
    "reception_type": "reception_type",
    "host_unit": "host_unit",
    "seller_name": "seller_name",
    "merchant_name": "merchant_name",
    "department": "department",
    "reimbursement_no": "reimbursement_no",
    "invoice_no": "invoice_no",
    "transaction_no": "transaction_no",
    "merchant_order_no": "merchant_order_no",
    "raw_text": "raw_text",
    # Boolean flags
    "payment_voucher_present": "payment_voucher_present",
    "payment_statement_present": "payment_statement_present",
    "official_letter_present": "official_letter_present",
    "invoice_verified": "invoice_verified",
    "expense_detail_list_present": "expense_detail_list_present",
    "grid_allocation_signed": "grid_allocation_signed",
    "has_alcohol_tobacco": "has_alcohol_tobacco",
    "bulk_alcohol": "bulk_alcohol",
    "gift_suspected": "gift_suspected",
    "tourism_suspected": "tourism_suspected",
    "is_cash_payment": "is_cash_payment",
    "has_prepaid": "has_prepaid",
    "is_holiday_reported": "is_holiday_reported",
}


def _resolve_field(f: ExtractedFields, field_name: str) -> Any:
    """从 ExtractedFields 中获取字段值"""
    attr = _FIELD_MAP.get(field_name, field_name)
    return getattr(f, attr, None)


def _resolve_text(f: ExtractedFields) -> str:
    """获取用于文本匹配的字段，优先 raw_text"""
    return f.raw_text or ""


# ---------------------------------------------------------------------------
# Expression evaluators
# ---------------------------------------------------------------------------

def _eval_keyword_match(expr: dict, f: ExtractedFields) -> Optional[tuple[bool, str]]:
    """keyword_match: 在指定字段或原始文本中匹配关键词

    {
        "type": "keyword_match",
        "field": "merchant_name",  // 可选，不指定则在 raw_text 中搜索
        "keywords": ["私人会所", "高档娱乐"],
        "mode": "any"  // "any"=任一匹配, "all"=全部匹配 (默认 any)
    }
    """
    keywords = expr.get("keywords", [])
    if not keywords:
        return None

    field = expr.get("field")
    mode = expr.get("mode", "any")

    if field:
        text = _resolve_field(f, field) or ""
    else:
        text = _resolve_text(f)

    matched = [kw for kw in keywords if kw in text]
    if mode == "all":
        is_match = len(matched) == len(keywords)
    else:
        is_match = len(matched) > 0

    if is_match:
        return (True, f"匹配到关键词: {', '.join(matched)}")
    return (False, "")


def _eval_amount_compare(expr: dict, f: ExtractedFields) -> Optional[tuple[bool, str]]:
    """amount_compare: 比较金额字段与阈值

    {
        "type": "amount_compare",
        "field": "per_person_amount",
        "operator": ">",  // >, >=, <, <=, ==, !=
        "threshold": 250,
        "condition": null  // 可选前置条件，如 {"reception_type": "商务招待"}
    }
    """
    field = expr.get("field", "per_person_amount")
    operator = expr.get("operator", ">")
    threshold = expr.get("threshold", 0)
    condition = expr.get("condition")

    value = _resolve_field(f, field)
    if value is None:
        return None

    # Check precondition
    if condition:
        for key, expected in condition.items():
            actual = _resolve_field(f, key)
            if isinstance(expected, list):
                if actual not in expected:
                    return None
            else:
                if actual != expected:
                    return None

    ops = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }
    cmp_fn = ops.get(operator)
    if cmp_fn and cmp_fn(value, threshold):
        return (True, f"{field}({value}) {operator} {threshold}")
    return (False, "")


def _eval_date_range(expr: dict, f: ExtractedFields) -> Optional[tuple[bool, str]]:
    """date_range: 检查日期字段是否在指定范围内

    {
        "type": "date_range",
        "field": "reception_date",
        "after": "2024-04-01",  // 可选
        "before": "2025-06-01",  // 可选
    }
    """
    field = expr.get("field", "reception_date")
    value = _resolve_field(f, field)
    if not isinstance(value, datetime):
        return None

    after_str = expr.get("after")
    before_str = expr.get("before")

    after = None
    before = None
    if after_str:
        try:
            after = datetime.strptime(after_str, "%Y-%m-%d")
        except ValueError:
            pass
    if before_str:
        try:
            before = datetime.strptime(before_str, "%Y-%m-%d")
        except ValueError:
            pass

    in_range = True
    if after and value < after:
        in_range = False
    if before and value >= before:
        in_range = False

    if in_range:
        return (True, f"{field}({value.strftime('%Y-%m-%d')}) 在指定范围内")
    return (False, "")


def _eval_boolean_check(expr: dict, f: ExtractedFields) -> Optional[tuple[bool, str]]:
    """boolean_check: 检查布尔标志字段的值

    {
        "type": "boolean_check",
        "field": "payment_voucher_present",
        "expected": False,  // 字段应为 False 才触发
    }
    """
    field = expr.get("field", "payment_voucher_present")
    expected = expr.get("expected", False)
    condition = expr.get("condition")

    value = _resolve_field(f, field)
    if value is None:
        return None

    # Check precondition
    if condition:
        for key, expected_val in condition.items():
            actual = _resolve_field(f, key)
            if isinstance(expected_val, list):
                if actual not in expected_val:
                    return None
            else:
                if actual != expected_val:
                    return None

    if value == expected:
        return (True, f"{field} 为 {value}")
    return (False, "")


def _eval_count_compare(expr: dict, f: ExtractedFields) -> Optional[tuple[bool, str]]:
    """count_compare: 比较数字字段（人数等）与计算值

    {
        "type": "count_compare",
        "field": "companion_count",
        "compare_field": "guest_count",  // 可选，与另一字段比较
        "operator": ">",
        "threshold": 5,  // 静态阈值，与 compare_field 二选一
        "formula": "equal_if_le_5",  // 动态公式
    }
    """
    field = expr.get("field", "companion_count")
    value = _resolve_field(f, field)
    if value is None:
        return None

    operator = expr.get("operator", ">")
    compare_field = expr.get("compare_field")
    threshold = expr.get("threshold")
    formula = expr.get("formula")

    limit = None
    if formula == "equal_if_le_5":
        # 外部陪同: guest<=5 时对等, >5 时 guest + (guest-5)//2
        guest = _resolve_field(f, compare_field or "guest_count")
        if guest is None:
            return None
        if guest <= 5:
            limit = guest
        else:
            limit = guest + (guest - 5) // 2
    elif formula == "fixed_if_le_then_ratio":
        # 内部陪同: guest<=10 时 3人, >10 时 guest//3
        guest = _resolve_field(f, compare_field or "guest_count")
        if guest is None:
            return None
        if guest <= 10:
            limit = expr.get("fixed_limit", 3)
        else:
            limit = guest // expr.get("ratio", 3)
    elif threshold is not None:
        limit = threshold
    elif compare_field:
        limit = _resolve_field(f, compare_field)
        if limit is None:
            return None

    if limit is None:
        return None

    ops = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
    }
    cmp_fn = ops.get(operator)
    if cmp_fn and cmp_fn(value, limit):
        return (True, f"{field}({value}) {operator} {limit}")
    return (False, "")


_EVALUATORS = {
    "keyword_match": _eval_keyword_match,
    "amount_compare": _eval_amount_compare,
    "date_range": _eval_date_range,
    "boolean_check": _eval_boolean_check,
    "count_compare": _eval_count_compare,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class DynamicRule:
    """单条动态规则，从数据库加载"""

    def __init__(self, rule_dict: dict):
        self.category = rule_dict.get("category", "单据完整性")
        self.rule_name = rule_dict.get("rule_name", "")
        self.clause = rule_dict.get("clause", "")
        self.level = rule_dict.get("level", "中")
        self.description = rule_dict.get("description", "")
        self.check_expression = rule_dict.get("check_expression", "")
        self.source_document = rule_dict.get("source_document", "")

    @property
    def expression(self) -> Optional[dict]:
        """解析 check_expression JSON"""
        if not self.check_expression:
            return None
        try:
            return json.loads(self.check_expression)
        except (json.JSONDecodeError, TypeError):
            return None

    def evaluate(self, f: ExtractedFields) -> Optional[Finding]:
        """对单条单据评估规则，违规则返回 Finding"""
        expr = self.expression
        if expr is None:
            return None

        expr_type = expr.get("type")
        evaluator = _EVALUATORS.get(expr_type)
        if not evaluator:
            return None

        result = evaluator(expr, f)
        if result and result[0]:  # is_match=True
            return Finding(
                category=RuleCategory(self.category) if self.category in [c.value for c in RuleCategory] else RuleCategory.PROOFREADING,
                rule=self.rule_name,
                clause=self.clause,
                level=self.level,
                message=self.description + ": " + result[1] if self.description else result[1],
            )
        return None

    def to_batch_finding(self, f: ExtractedFields, document: str = "") -> Optional[BatchFinding]:
        """评估并返回批次级别的 Finding"""
        finding = self.evaluate(f)
        if finding:
            return BatchFinding(
                category=finding.category,
                rule=finding.rule,
                clause=finding.clause,
                level=finding.level,
                message=finding.message,
                document=document,
            )
        return None


def evaluate_rule(expr_json: str, f: ExtractedFields, rule_name: str = "", clause: str = "", level: str = "中", category: str = "校对规则", description: str = "") -> Optional[Finding]:
    """便捷函数：直接用 JSON 字符串评估规则"""
    rule = DynamicRule({
        "category": category,
        "rule_name": rule_name,
        "clause": clause,
        "level": level,
        "description": description,
        "check_expression": expr_json,
    })
    return rule.evaluate(f)

"""测试规则引擎"""
import sys
sys.path.insert(0, "D:\\00_项目\\招待费智能体")

from src.expense_review_comprehensive.rule_engine import DynamicRule, evaluate_rule
from src.expense_review_comprehensive.models import ExtractedFields, RuleCategory
from src.expense_review_comprehensive.checkers import ComprehensiveChecker

# Test 1: keyword_match
rule1 = DynamicRule({
    "category": "禁止性规定",
    "rule_name": "高档场所",
    "clause": "管理办法 第十四条",
    "level": "高",
    "description": "不得安排私人会所及高档娱乐场所",
    "check_expression": '{"type": "keyword_match", "keywords": ["私人会所", "一桌餐", "高档娱乐"], "mode": "any"}',
})

f1 = ExtractedFields(raw_text="在私人会所宴请客户")
finding1 = rule1.evaluate(f1)
assert finding1 is not None, "keyword_match should match"
assert "私人会所" in finding1.message
print(f"[PASS] keyword_match: {finding1.message}")

# Test 2: keyword_match no match
f1b = ExtractedFields(raw_text="在普通餐厅用餐")
finding1b = rule1.evaluate(f1b)
assert finding1b is None, "keyword_match should not match"
print(f"[PASS] keyword_match no-match: correct")

# Test 3: amount_compare
rule2 = DynamicRule({
    "category": "金额标准",
    "rule_name": "人均金额超标",
    "clause": "管理办法 第九条",
    "level": "高",
    "check_expression": '{"type": "amount_compare", "field": "per_person_amount", "operator": ">", "threshold": 250}',
})

f2 = ExtractedFields(per_person_amount=300.0)
finding2 = rule2.evaluate(f2)
assert finding2 is not None, "amount_compare should match"
print(f"[PASS] amount_compare: {finding2.message}")

f2b = ExtractedFields(per_person_amount=200.0)
finding2b = rule2.evaluate(f2b)
assert finding2b is None, "amount_compare should not match"
print(f"[PASS] amount_compare no-match: correct")

# Test 4: boolean_check
rule3 = DynamicRule({
    "category": "单据完整性",
    "rule_name": "支付凭证缺失",
    "clause": "管理办法 第十条",
    "level": "高",
    "check_expression": '{"type": "boolean_check", "field": "payment_voucher_present", "expected": false}',
})

f3 = ExtractedFields(payment_voucher_present=False)
finding3 = rule3.evaluate(f3)
assert finding3 is not None, "boolean_check should match"
print(f"[PASS] boolean_check: {finding3.message}")

# Test 5: date_range
rule4 = DynamicRule({
    "category": "单据完整性",
    "rule_name": "新支付凭证要求",
    "clause": "管理办法 第十一条",
    "level": "高",
    "check_expression": '{"type": "date_range", "field": "reception_date", "after": "2024-04-01"}',
})

from datetime import datetime
f4 = ExtractedFields(reception_date=datetime(2025, 1, 1))
finding4 = rule4.evaluate(f4)
assert finding4 is not None, "date_range should match"
print(f"[PASS] date_range: {finding4.message}")

# Test 6: count_compare
rule5 = DynamicRule({
    "category": "陪同人数",
    "rule_name": "外部陪同超标",
    "clause": "管理办法 第十二条",
    "level": "高",
    "check_expression": '{"type": "count_compare", "field": "companion_count", "compare_field": "guest_count", "operator": ">", "formula": "equal_if_le_5"}',
})

f5 = ExtractedFields(guest_count=3, companion_count=5)
finding5 = rule5.evaluate(f5)
assert finding5 is not None, "count_compare should match (guest=3, companion=5, limit=3)"
print(f"[PASS] count_compare: {finding5.message}")

f5b = ExtractedFields(guest_count=3, companion_count=2)
finding5b = rule5.evaluate(f5b)
assert finding5b is None, "count_compare should not match (guest=3, companion=2, limit=3)"
print(f"[PASS] count_compare no-match: correct")

# Test 7: ComprehensiveChecker with dynamic rules
dynamic_rules = [
    {
        "category": "禁止性规定",
        "rule_name": "高档场所",
        "clause": "管理办法 第十四条",
        "level": "高",
        "description": "不得安排私人会所",
        "check_expression": '{"type": "keyword_match", "keywords": ["私人会所"], "mode": "any"}',
    },
    {
        "category": "金额标准",
        "rule_name": "人均金额超标",
        "clause": "管理办法 第九条",
        "level": "高",
        "check_expression": '{"type": "amount_compare", "field": "per_person_amount", "operator": ">", "threshold": 250}',
    },
]

checker = ComprehensiveChecker(dynamic_rules=dynamic_rules)
f7 = ExtractedFields(
    raw_text="在私人会所宴请",
    per_person_amount=300.0,
)
findings = checker.check_single(f7)
dynamic_findings = [f for f in findings if f.rule in ("高档场所", "人均金额超标")]
assert len(dynamic_findings) >= 2, f"Expected at least 2 dynamic findings, got {len(dynamic_findings)}"
print(f"[PASS] ComprehensiveChecker with dynamic rules: {len(dynamic_findings)} findings")

# Test 8: reload_dynamic_rules
new_rules = [
    {
        "category": "报销合规",
        "rule_name": "大额现金",
        "clause": "管理办法 第二十五条",
        "level": "高",
        "check_expression": '{"type": "boolean_check", "field": "is_cash_payment", "expected": true}',
    },
]
checker.reload_dynamic_rules(new_rules)
f8 = ExtractedFields(is_cash_payment=True)
findings8 = checker.check_single(f8)
cash_findings = [f for f in findings8 if f.rule == "大额现金"]
assert len(cash_findings) >= 1, "reload should work"
print(f"[PASS] reload_dynamic_rules: works correctly")

print("\n=== All rule_engine tests passed! ===")

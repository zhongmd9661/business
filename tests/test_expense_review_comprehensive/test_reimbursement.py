"""10.6 报销合规测试"""
from src.expense_review_comprehensive import ComprehensiveChecker, FieldExtractor, ExtractedFields, RuleCategory


def test_prior_approval_violation():
    checker = ComprehensiveChecker()
    text = (
        "申请日期: 2025-10-05\n"
        "招待日期: 2025-10-01\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    approval_findings = [fi for fi in findings if fi.rule == "事前审批"]
    assert len(approval_findings) > 0


def test_prior_approval_ok():
    checker = ComprehensiveChecker()
    text = (
        "申请日期: 2025-09-28\n"
        "招待日期: 2025-10-01\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    approval_findings = [fi for fi in findings if fi.rule == "事前审批"]
    assert len(approval_findings) == 0


def test_large_cash_payment():
    checker = ComprehensiveChecker()
    text = (
        "发票金额: 8000\n"
        "现金支付\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    cash_findings = [fi for fi in findings if fi.rule == "大额现金支付"]
    assert len(cash_findings) > 0


def test_small_cash_ok():
    checker = ComprehensiveChecker()
    text = (
        "发票金额: 3000\n"
        "现金支付\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    cash_findings = [fi for fi in findings if fi.rule == "大额现金支付"]
    assert len(cash_findings) == 0


def test_invoice_type_vat_special():
    checker = ComprehensiveChecker()
    text = "增值税专用发票"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    inv_findings = [fi for fi in findings if fi.rule == "发票类型"]
    assert len(inv_findings) > 0


def test_prepaid():
    checker = ComprehensiveChecker()
    text = "预存签单"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    prep_findings = [fi for fi in findings if fi.rule == "预存签单"]
    assert len(prep_findings) > 0


def test_split_reimbursement():
    checker = ComprehensiveChecker()
    from datetime import datetime
    fields = [
        ExtractedFields(handler="张三", reception_date=datetime(2025, 10, 1), actual_amount=3000),
        ExtractedFields(handler="张三", reception_date=datetime(2025, 10, 3), actual_amount=4000),
        ExtractedFields(handler="张三", reception_date=datetime(2025, 10, 5), actual_amount=2500),
    ]
    findings = checker.check_batch(fields)
    split_findings = [fi for fi in findings if fi.rule == "拆分报销"]
    assert len(split_findings) > 0


def test_mixed_expenses():
    checker = ComprehensiveChecker()
    f = ExtractedFields(
        reception_type="商务招待",
        raw_text="市场营销费用 招待费",
    )
    findings = checker.check_batch([f])
    mixed_findings = [fi for fi in findings if fi.rule == "混淆费用"]
    assert len(mixed_findings) > 0

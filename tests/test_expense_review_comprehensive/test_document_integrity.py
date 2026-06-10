"""10.2 单据完整性规则测试"""
from datetime import datetime

from src.expense_review_comprehensive import (
    ComprehensiveChecker, FieldExtractor, RuleCategory,
)


def test_reimbursement_no_missing():
    checker = ComprehensiveChecker()
    text = "招待日期: 2025-10-01\n发票金额: 1000"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    no_findings = [fi for fi in findings if fi.rule == "报账单号一致性"]
    assert len(no_findings) > 0


def test_expense_detail_list_missing():
    checker = ComprehensiveChecker()
    text = "招待日期: 2025-10-01\n报账单号: BZ001"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    detail_findings = [fi for fi in findings if fi.rule == "费用明细清单"]
    assert len(detail_findings) > 0


def test_payment_voucher_required_after_2024_04():
    checker = ComprehensiveChecker()
    text = "招待日期: 2025-01-01\n报账单号: BZ001\n费用明细: 有"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    voucher_findings = [fi for fi in findings if fi.rule == "支付凭证"]
    assert len(voucher_findings) > 0


def test_payment_voucher_not_required_before_2024_04():
    checker = ComprehensiveChecker()
    text = "招待日期: 2024-01-01\n报账单号: BZ001"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    voucher_findings = [fi for fi in findings if fi.rule == "支付凭证"]
    assert len(voucher_findings) == 0


def test_payment_statement_required_after_2025_09():
    checker = ComprehensiveChecker()
    text = "招待日期: 2025-10-01\n报账单号: BZ001\n支付凭证: 有"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    stmt_findings = [fi for fi in findings if fi.rule == "支付流水证明"]
    assert len(stmt_findings) > 0


def test_official_letter_required_after_2025_12_external():
    checker = ComprehensiveChecker()
    text = "招待日期: 2026-01-05\n招待类型: 商务招待\n报账单号: BZ001"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    letter_findings = [fi for fi in findings if fi.rule == "往来公函"]
    assert len(letter_findings) > 0


def test_official_letter_not_required_internal():
    checker = ComprehensiveChecker()
    text = "招待日期: 2026-01-05\n招待类型: 内部业务招待\n报账单号: BZ001"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    letter_findings = [fi for fi in findings if fi.rule == "往来公函"]
    assert len(letter_findings) == 0


def test_invoice_verification_before_2025_06():
    checker = ComprehensiveChecker()
    text = "招待日期: 2025-01-01\n报账单号: BZ001"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    inv_findings = [fi for fi in findings if fi.rule == "发票查验"]
    assert len(inv_findings) > 0


def test_grid_allocation_missing():
    checker = ComprehensiveChecker()
    text = "招待日期: 2025-01-01\n报账单号: BZ001"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    grid_findings = [fi for fi in findings if fi.rule == "网格分摊表签章"]
    assert len(grid_findings) > 0


def test_all_documents_present():
    checker = ComprehensiveChecker()
    text = (
        "招待日期: 2025-10-01\n"
        "报账单号: BZ001\n"
        "费用明细: 有\n"
        "支付凭证: 有\n"
        "支付流水: 有\n"
        "公函: 有\n"
        "发票查验: 已校验\n"
        "网格分摊表签章: 有\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    integrity_findings = [fi for fi in findings if fi.category == RuleCategory.DOCUMENT_INTEGRITY]
    assert len(integrity_findings) == 0

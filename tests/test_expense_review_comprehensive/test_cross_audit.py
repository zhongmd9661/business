"""10.7 交叉稽核测试"""
from datetime import datetime

from src.expense_review_comprehensive import (
    ComprehensiveChecker, FieldExtractor, ExtractedFields, RuleCategory,
)


def test_holiday_reporting():
    checker = ComprehensiveChecker()
    text = "招待日期: 2025-10-02"  # 国庆前后3天
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    holiday_findings = [fi for fi in findings if fi.rule == "节日招待报备"]
    assert len(holiday_findings) > 0


def test_holiday_reporting_with_report():
    checker = ComprehensiveChecker()
    text = "招待日期: 2025-10-02\n报备: 已报备"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    holiday_findings = [fi for fi in findings if fi.rule == "节日招待报备"]
    assert len(holiday_findings) == 0


def test_enterprise_status_placeholder():
    checker = ComprehensiveChecker()
    f = ExtractedFields(host_unit="某某酒店")
    findings = checker.check_batch([f])
    status_findings = [fi for fi in findings if fi.rule == "企业经营状态"]
    assert len(status_findings) > 0
    assert status_findings[0].level == "提示"


def test_duplicate_reception():
    checker = ComprehensiveChecker()
    fields = [
        ExtractedFields(
            department="市场部", host_unit="A公司",
            reception_date=datetime(2025, 10, 1),
        ),
        ExtractedFields(
            department="市场部", host_unit="A公司",
            reception_date=datetime(2025, 10, 15),
        ),
    ]
    findings = checker.check_batch(fields)
    dup_findings = [fi for fi in findings if fi.rule == "重复招待"]
    assert len(dup_findings) > 0


def test_duplicate_reception_different_months():
    checker = ComprehensiveChecker()
    fields = [
        ExtractedFields(
            department="市场部", host_unit="A公司",
            reception_date=datetime(2025, 10, 1),
        ),
        ExtractedFields(
            department="市场部", host_unit="A公司",
            reception_date=datetime(2025, 11, 1),
        ),
    ]
    findings = checker.check_batch(fields)
    dup_findings = [fi for fi in findings if fi.rule == "重复招待"]
    assert len(dup_findings) == 0  # Different months


def test_travel_mismatch_placeholder():
    checker = ComprehensiveChecker()
    f = ExtractedFields(
        host_unit="某某酒店",
        reception_date=datetime(2025, 10, 1),
    )
    findings = checker.check_batch([f])
    travel_findings = [fi for fi in findings if fi.rule == "差旅期间招待"]
    assert len(travel_findings) > 0
    assert travel_findings[0].level == "提示"

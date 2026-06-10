"""10.8 报告生成测试"""
from src.expense_review_comprehensive import (
    ComprehensiveChecker, ComprehensiveReporter, FieldExtractor,
    Finding, RuleCategory,
)


def test_report_groups_by_category():
    findings = [
        Finding(RuleCategory.DOCUMENT_INTEGRITY, "支付凭证", "第10条", "高", "缺少支付凭证"),
        Finding(RuleCategory.AMOUNT_STANDARD, "外部招待金额标准", "第15条", "高", "超标准"),
        Finding(RuleCategory.PROHIBITION, "高档场所", "风险点1", "高", "私人会所"),
    ]
    reporter = ComprehensiveReporter()
    report = reporter.generate(findings, "test.md", rules_checked=20, rules_skipped=2)
    # Should have entries for all 3 categories
    cats = {cr.category for cr in report.category_reports if cr.findings}
    assert RuleCategory.DOCUMENT_INTEGRITY in cats
    assert RuleCategory.AMOUNT_STANDARD in cats
    assert RuleCategory.PROHIBITION in cats


def test_report_high_risk():
    findings = [
        Finding(RuleCategory.DOCUMENT_INTEGRITY, "支付凭证", "第10条", "高", "缺少支付凭证"),
    ]
    reporter = ComprehensiveReporter()
    report = reporter.generate(findings, "test.md")
    assert report.has_high_risk


def test_report_no_high_risk():
    findings = [
        Finding(RuleCategory.CROSS_AUDIT, "企业经营状态", "风险点8", "提示", "人工确认"),
    ]
    reporter = ComprehensiveReporter()
    report = reporter.generate(findings, "test.md")
    assert not report.has_high_risk


def test_report_text_format():
    findings = [
        Finding(RuleCategory.DOCUMENT_INTEGRITY, "支付凭证", "第10条", "高", "缺少支付凭证"),
        Finding(RuleCategory.AMOUNT_STANDARD, "外部招待金额标准", "第15条", "中", "略超"),
    ]
    reporter = ComprehensiveReporter()
    report = reporter.generate(findings, "test.md", rules_checked=10, rules_skipped=1)
    text = reporter.format_text(report)
    assert "全面业务招待费审核报告" in text
    assert "存在高风险" in text
    assert "支付凭证" in text
    assert "外部招待金额标准" in text
    assert "第10条" in text


def test_report_summary():
    findings = [
        Finding(RuleCategory.DOCUMENT_INTEGRITY, "支付凭证", "第10条", "高", "缺少支付凭证"),
        Finding(RuleCategory.AMOUNT_STANDARD, "外部招待金额标准", "第15条", "中", "略超"),
        Finding(RuleCategory.CROSS_AUDIT, "企业经营状态", "风险点8", "提示", "人工确认"),
    ]
    reporter = ComprehensiveReporter()
    report = reporter.generate(findings, "test.md")
    summary = reporter.format_summary(report)
    assert "高风险" in summary
    assert "3 条" in summary


def test_report_empty():
    reporter = ComprehensiveReporter()
    report = reporter.generate([], "empty.md")
    assert not report.has_high_risk
    assert len(report.all_findings) == 0


def test_full_pipeline_report():
    """集成测试：从提取到报告生成"""
    text = (
        "招待日期: 2025-10-01\n"
        "发票日期: 2025-10-01\n"
        "申请日期: 2025-10-05\n"
        "发票金额: 5000\n"
        "实际金额: 5000\n"
        "人均: 500\n"
        "招待对象人数: 5\n"
        "陪同人数: 6\n"
        "招待类型: 商务招待\n"
        "省管中层\n"
        "现金支付\n"
        "私人会所\n"
    )
    extractor = FieldExtractor()
    fields = extractor.extract(text)
    checker = ComprehensiveChecker()
    findings = checker.check_single(fields)
    reporter = ComprehensiveReporter()
    report = reporter.generate(findings, "pipeline_test.md")
    assert report.has_high_risk
    assert len(report.all_findings) > 3
    text_output = reporter.format_text(report)
    assert "存在高风险" in text_output

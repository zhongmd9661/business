"""批次审核功能测试"""
from datetime import datetime

from src.expense_review_comprehensive import (
    ComprehensiveChecker,
    ComprehensiveReporter,
    RuleCategory,
)
from src.expense_review_comprehensive.models import (
    ExtractedFields,
    BatchReviewContext,
    BatchReviewReport,
    BatchFinding,
    CategoryBatchReport,
)


# ---------- 1. BatchReviewContext 聚合指标计算 ----------


def test_batch_context_aggregates_amount():
    fields = [
        ExtractedFields(actual_amount=1000.0),
        ExtractedFields(actual_amount=2000.0),
        ExtractedFields(actual_amount=500.0),
    ]
    ctx = ComprehensiveChecker._build_context(
        ["a.md", "b.md", "c.md"], fields
    )
    assert ctx.total_amount == 3500.0


def test_batch_context_aggregates_people():
    fields = [
        ExtractedFields(guest_count=5, companion_count=3),
        ExtractedFields(guest_count=10, companion_count=4),
    ]
    ctx = ComprehensiveChecker._build_context(
        ["a.md", "b.md"], fields
    )
    assert ctx.total_guest_count == 15
    assert ctx.total_companion_count == 7


def test_batch_context_skips_none_values():
    fields = [
        ExtractedFields(actual_amount=1000.0, guest_count=5),
        ExtractedFields(),  # all None
        ExtractedFields(invoice_amount=2000.0, companion_count=3),
    ]
    ctx = ComprehensiveChecker._build_context(
        ["a.md", "b.md", "c.md"], fields
    )
    assert ctx.total_amount == 3000.0
    assert ctx.total_guest_count == 5
    assert ctx.total_companion_count == 3


def test_batch_context_takes_first_non_empty_department():
    fields = [
        ExtractedFields(department=None),
        ExtractedFields(department="市场部"),
    ]
    ctx = ComprehensiveChecker._build_context(
        ["a.md", "b.md"], fields
    )
    assert ctx.department == "市场部"


def test_batch_context_earliest_dates():
    fields = [
        ExtractedFields(
            apply_date=datetime(2025, 10, 5),
            reception_date=datetime(2025, 10, 3),
        ),
        ExtractedFields(
            apply_date=datetime(2025, 10, 1),
            reception_date=datetime(2025, 10, 2),
        ),
    ]
    ctx = ComprehensiveChecker._build_context(
        ["a.md", "b.md"], fields
    )
    assert ctx.apply_date == datetime(2025, 10, 1)
    assert ctx.reception_date == datetime(2025, 10, 2)


# ---------- 2. check_batch_review() 返回结果 ----------


def test_check_batch_review_contains_per_document_findings():
    fields = [
        ExtractedFields(
            reimbursement_no=None,
            expense_detail_list_present=False,
            reception_date=datetime(2025, 10, 1),
        ),
    ]
    checker = ComprehensiveChecker()
    report = checker.check_batch_review(["doc1.md"], fields)
    assert len(report.all_findings) > 0
    # 单据完整性问题应标注来源文档
    integrity_findings = [
        f for f in report.all_findings
        if f.category == RuleCategory.DOCUMENT_INTEGRITY
    ]
    assert any(f.document == "doc1.md" for f in integrity_findings)


def test_check_batch_review_contains_cross_document_findings():
    fields = [
        ExtractedFields(
            handler="张三",
            reception_date=datetime(2025, 10, 1),
            actual_amount=1000.0,
        ),
        ExtractedFields(
            handler="张三",
            reception_date=datetime(2025, 10, 3),
            actual_amount=2000.0,
        ),
        ExtractedFields(
            handler="张三",
            reception_date=datetime(2025, 10, 5),
            actual_amount=3000.0,
        ),
    ]
    checker = ComprehensiveChecker()
    report = checker.check_batch_review(
        ["a.md", "b.md", "c.md"], fields
    )
    split_findings = [
        f for f in report.all_findings
        if f.rule == "拆分报销"
    ]
    assert len(split_findings) > 0


def test_check_batch_review_aggregated_amount_check():
    fields = [
        ExtractedFields(
            actual_amount=2000.0,
            guest_count=5,
            companion_count=3,
            reception_type="商务招待",
            personnel_level="其他人员",
        ),
        ExtractedFields(
            actual_amount=3000.0,
            guest_count=5,
            companion_count=3,
        ),
    ]
    checker = ComprehensiveChecker()
    report = checker.check_batch_review(["a.md", "b.md"], fields)
    # 总金额 5000, 总人数 16, 人均 312.5 > 250 (其他人员外事商务)
    amount_findings = [
        f for f in report.all_findings
        if f.category == RuleCategory.AMOUNT_STANDARD
    ]
    assert len(amount_findings) > 0


def test_check_batch_review_document_count():
    fields = [
        ExtractedFields(reimbursement_no="A"),
        ExtractedFields(reimbursement_no="B"),
        ExtractedFields(reimbursement_no="C"),
    ]
    checker = ComprehensiveChecker()
    report = checker.check_batch_review(["a.md", "b.md", "c.md"], fields)
    assert report.document_count == 3


def test_check_batch_review_has_high_risk():
    fields = [
        ExtractedFields(
            reception_date=datetime(2025, 10, 1),
            payment_voucher_present=False,
        ),
    ]
    checker = ComprehensiveChecker()
    report = checker.check_batch_review(["a.md"], fields)
    assert report.has_high_risk


# ---------- 3. 批次报告格式化输出 ----------


def test_batch_report_format_contains_batch_info():
    report = BatchReviewReport(
        batch_name="测试批次",
        document_count=5,
        department="市场部",
        reception_type="商务招待",
    )
    reporter = ComprehensiveReporter()
    text = reporter.format_batch_text(report)
    assert "测试批次" in text
    assert "文档数: 5" in text
    assert "市场部" in text
    assert "商务招待" in text


def test_batch_report_format_groups_by_category_and_document():
    findings = [
        BatchFinding(
            RuleCategory.DOCUMENT_INTEGRITY,
            "支付凭证", "第10条", "高",
            "缺少支付凭证", document="doc1.md",
        ),
        BatchFinding(
            RuleCategory.AMOUNT_STANDARD,
            "外部招待金额标准", "第15条", "高",
            "超标准", document="",
        ),
    ]
    report = BatchReviewReport(
        batch_name="测试",
        document_count=2,
        all_findings=findings,
    )
    report.category_reports = [
        CategoryBatchReport(
            category=RuleCategory.DOCUMENT_INTEGRITY,
            findings=[findings[0]],
        ),
        CategoryBatchReport(
            category=RuleCategory.AMOUNT_STANDARD,
            findings=[findings[1]],
        ),
    ]
    reporter = ComprehensiveReporter()
    text = reporter.format_batch_text(report)
    assert "单据完整性" in text
    assert "doc1.md" in text
    assert "(批次总计)" in text


def test_batch_report_summary():
    findings = [
        BatchFinding(RuleCategory.DOCUMENT_INTEGRITY, "支付凭证", "第10条", "高", "缺少"),
        BatchFinding(RuleCategory.AMOUNT_STANDARD, "外部招待", "第15条", "中", "略超"),
        BatchFinding(RuleCategory.CROSS_AUDIT, "企业状态", "风险点8", "提示", "人工确认"),
    ]
    report = BatchReviewReport(
        batch_name="测试批次",
        document_count=3,
        all_findings=findings,
    )
    reporter = ComprehensiveReporter()
    summary = reporter.format_batch_summary(report)
    assert "测试批次" in summary
    assert "高风险" in summary
    assert "3 条" in summary


def test_batch_report_no_findings():
    report = BatchReviewReport(
        batch_name="空批次",
        document_count=1,
    )
    assert not report.has_high_risk
    assert len(report.all_findings) == 0


def test_full_batch_review_pipeline():
    """集成测试：模拟多文档批次审核"""
    from src.expense_review_comprehensive import FieldExtractor

    texts = [
        "招待日期: 2025-10-01\n发票金额: 2000\n招待类型: 商务招待\n招待对象人数: 5\n陪同人数: 3\n省管中层",
        "招待日期: 2025-10-01\n发票金额: 1500\n招待对象人数: 3\n陪同人数: 2",
        "招待日期: 2025-10-01\n发票金额: 1000\n私人会所",
    ]
    extractor = FieldExtractor()
    fields = [extractor.extract(t) for t in texts]
    checker = ComprehensiveChecker()
    report = checker.check_batch_review(
        ["doc1.md", "doc2.md", "doc3.md"], fields
    )
    report.batch_name = "集成测试"
    reporter = ComprehensiveReporter()
    text = reporter.format_batch_text(report)
    assert "集成测试" in text
    assert report.document_count == 3
    assert len(report.all_findings) > 0

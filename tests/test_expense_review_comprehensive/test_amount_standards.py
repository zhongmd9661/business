"""10.3 金额标准规则测试"""
from src.expense_review_comprehensive import ComprehensiveChecker, FieldExtractor, RuleCategory


def test_external_amount_exceeded():
    checker = ComprehensiveChecker()
    text = (
        "招待日期: 2025-10-01\n"
        "招待类型: 商务招待\n"
        "人均: 500\n"
        "省管中层\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    amount_findings = [fi for fi in findings if fi.rule == "外部招待金额标准"]
    assert len(amount_findings) > 0
    assert amount_findings[0].level == "高"


def test_external_amount_within_limit():
    checker = ComprehensiveChecker()
    text = (
        "招待日期: 2025-10-01\n"
        "招待类型: 商务招待\n"
        "人均: 300\n"
        "省管中层\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    amount_findings = [fi for fi in findings if fi.rule == "外部招待金额标准"]
    assert len(amount_findings) == 0


def test_internal_amount_exceeded():
    checker = ComprehensiveChecker()
    text = (
        "招待日期: 2025-10-01\n"
        "招待类型: 内部业务招待\n"
        "人均: 200\n"
        "其他人员\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    amount_findings = [fi for fi in findings if fi.rule == "内部招待金额标准"]
    assert len(amount_findings) > 0


def test_work_meal_exceeded():
    checker = ComprehensiveChecker()
    text = (
        "招待日期: 2025-10-01\n"
        "工作餐\n"
        "人均: 100\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    meal_findings = [fi for fi in findings if fi.rule == "工作餐金额标准"]
    assert len(meal_findings) > 0


def test_work_meal_within_limit():
    checker = ComprehensiveChecker()
    text = (
        "招待日期: 2025-10-01\n"
        "工作餐\n"
        "人均: 50\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    meal_findings = [fi for fi in findings if fi.rule == "工作餐金额标准"]
    assert len(meal_findings) == 0


def test_alcohol_price_exceeded():
    checker = ComprehensiveChecker()
    text = (
        "招待日期: 2025-10-01\n"
        "酒水价格: 200\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    alcohol_findings = [fi for fi in findings if fi.rule == "酒水价格上限"]
    assert len(alcohol_findings) > 0


def test_souvenir_amount_exceeded():
    checker = ComprehensiveChecker()
    text = (
        "招待日期: 2025-10-01\n"
        "纪念品金额: 500\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    souvenir_findings = [fi for fi in findings if fi.rule == "纪念品金额标准"]
    assert len(souvenir_findings) > 0


def test_city_level_other_duty_limit():
    checker = ComprehensiveChecker()
    text = (
        "招待日期: 2025-10-01\n"
        "招待类型: 其他公务招待\n"
        "人均: 250\n"
        "市管中层\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    amount_findings = [fi for fi in findings if fi.rule == "外部招待金额标准"]
    assert len(amount_findings) > 0  # limit is 200 for 市管中层+其他公务

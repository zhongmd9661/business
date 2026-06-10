"""10.4 招待类型与陪同人数测试"""
from src.expense_review_comprehensive import ComprehensiveChecker, FieldExtractor, RuleCategory


def test_gov_must_be_other_duty():
    checker = ComprehensiveChecker()
    text = (
        "招待类型: 商务招待\n"
        "招待单位: 某市政府办公厅\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    type_findings = [fi for fi in findings if fi.rule == "招待类型匹配"]
    assert len(type_findings) > 0


def test_internal_unit_must_be_internal():
    checker = ComprehensiveChecker()
    text = (
        "招待类型: 商务招待\n"
        "招待单位: 省移动公司\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    type_findings = [fi for fi in findings if fi.rule == "招待类型匹配"]
    assert len(type_findings) > 0


def test_external_companion_exceeded_small():
    checker = ComprehensiveChecker()
    text = (
        "招待类型: 商务招待\n"
        "招待对象人数: 4\n"
        "陪同人数: 5\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    comp_findings = [fi for fi in findings if fi.rule == "外部招待陪同人数"]
    assert len(comp_findings) > 0  # limit = 4 for guest <= 5


def test_external_companion_exceeded_large():
    checker = ComprehensiveChecker()
    text = (
        "招待类型: 商务招待\n"
        "招待对象人数: 10\n"
        "陪同人数: 15\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    comp_findings = [fi for fi in findings if fi.rule == "外部招待陪同人数"]
    # limit = 10 + (10-5)//2 = 12, 15 > 12 -> exceeds
    assert len(comp_findings) > 0


def test_external_companion_ok():
    checker = ComprehensiveChecker()
    text = (
        "招待类型: 商务招待\n"
        "招待对象人数: 4\n"
        "陪同人数: 3\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    comp_findings = [fi for fi in findings if fi.rule == "外部招待陪同人数"]
    assert len(comp_findings) == 0


def test_internal_companion_exceeded_small():
    checker = ComprehensiveChecker()
    text = (
        "招待类型: 内部业务招待\n"
        "招待对象人数: 8\n"
        "陪同人数: 5\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    comp_findings = [fi for fi in findings if fi.rule == "内部招待陪同人数"]
    assert len(comp_findings) > 0  # limit = 3 for guest <= 10


def test_internal_companion_exceeded_large():
    checker = ComprehensiveChecker()
    text = (
        "招待类型: 内部业务招待\n"
        "招待对象人数: 15\n"
        "陪同人数: 8\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    comp_findings = [fi for fi in findings if fi.rule == "内部招待陪同人数"]
    assert len(comp_findings) > 0  # limit = 15//3 = 5


def test_internal_companion_ok():
    checker = ComprehensiveChecker()
    text = (
        "招待类型: 内部业务招待\n"
        "招待对象人数: 8\n"
        "陪同人数: 2\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    comp_findings = [fi for fi in findings if fi.rule == "内部招待陪同人数"]
    assert len(comp_findings) == 0

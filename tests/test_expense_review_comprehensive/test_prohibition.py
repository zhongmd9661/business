"""10.5 禁止性规定测试"""
from src.expense_review_comprehensive import ComprehensiveChecker, FieldExtractor, RuleCategory


def test_forbidden_places():
    checker = ComprehensiveChecker()
    text = "招待单位: 私人会所"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    place_findings = [fi for fi in findings if fi.rule == "高档场所"]
    assert len(place_findings) > 0


def test_forbidden_foods():
    checker = ComprehensiveChecker()
    text = "费用明细: 鱼翅 燕窝"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    food_findings = [fi for fi in findings if fi.rule == "高档菜品"]
    assert len(food_findings) > 0


def test_alcohol_in_work_meal():
    checker = ComprehensiveChecker()
    text = (
        "工作餐\n"
        "酒\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    alcohol_findings = [fi for fi in findings if fi.rule == "烟酒规定"]
    assert len(alcohol_findings) > 0


def test_alcohol_in_internal():
    checker = ComprehensiveChecker()
    text = (
        "内部业务招待\n"
        "白酒\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    alcohol_findings = [fi for fi in findings if fi.rule == "烟酒规定"]
    assert len(alcohol_findings) > 0


def test_alcohol_ok_in_external():
    checker = ComprehensiveChecker()
    text = (
        "商务招待\n"
        "红酒\n"
    )
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    alcohol_findings = [fi for fi in findings if fi.rule == "烟酒规定"]
    assert len(alcohol_findings) == 0  # External allows alcohol


def test_bulk_alcohol():
    checker = ComprehensiveChecker()
    text = "批量购买 白酒"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    bulk_findings = [fi for fi in findings if fi.rule == "批量购买酒水"]
    assert len(bulk_findings) > 0


def test_gift_suspected():
    checker = ComprehensiveChecker()
    text = "购物卡 预付卡"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    gift_findings = [fi for fi in findings if fi.rule == "公款送礼"]
    assert len(gift_findings) > 0


def test_tourism_suspected():
    checker = ComprehensiveChecker()
    text = "旅游景点 演出"
    f = FieldExtractor().extract(text)
    findings = checker.check_single(f)
    tour_findings = [fi for fi in findings if fi.rule == "变相旅游"]
    assert len(tour_findings) > 0

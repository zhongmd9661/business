"""10.1 字段提取器测试"""
from src.expense_review_comprehensive import FieldExtractor


def _make_text(**kw: str) -> str:
    return "\n".join(f"{k}: {v}" for k, v in kw.items())


def test_extract_dates():
    extractor = FieldExtractor()
    text = _make_text(
        招待日期="2025-10-01",
        发票日期="2025-10-01",
        申请日期="2025-09-28",
        支付日期="2025-10-02",
    )
    f = extractor.extract(text)
    assert f.reception_date is not None
    assert f.reception_date.year == 2025
    assert f.invoice_date is not None
    assert f.apply_date is not None
    assert f.payment_date is not None


def test_extract_amounts():
    extractor = FieldExtractor()
    text = _make_text(发票金额="3000", 实际金额="2800", 人均="280")
    f = extractor.extract(text)
    assert f.invoice_amount == 3000.0
    assert f.actual_amount == 2800.0
    assert f.per_person_amount == 280.0


def test_extract_people():
    extractor = FieldExtractor()
    text = _make_text(招待对象人数="5", 陪同人数="3", 经办人="张三", 收款人="李四")
    f = extractor.extract(text)
    assert f.guest_count == 5
    assert f.companion_count == 3
    assert f.handler == "张三"
    assert f.payee == "李四"


def test_extract_personnel_level():
    extractor = FieldExtractor()
    f1 = extractor.extract("省管中层人员")
    assert f1.personnel_level == "省管中层"
    f2 = extractor.extract("市管中层人员")
    assert f2.personnel_level == "市管中层"
    f3 = extractor.extract("其他一般人员")
    assert f3.personnel_level == "其他人员"


def test_extract_reception_type():
    extractor = FieldExtractor()
    assert extractor.extract("商务招待").reception_type == "商务招待"
    assert extractor.extract("外事招待").reception_type == "外事招待"
    assert extractor.extract("其他公务招待").reception_type == "其他公务招待"
    assert extractor.extract("内部业务招待").reception_type == "内部业务招待"
    assert extractor.extract("工作餐").reception_type == "工作餐"


def test_extract_supplier():
    extractor = FieldExtractor()
    text = _make_text(招待单位="某某酒店", 销售方="某某公司", 商户全称="某某商户")
    f = extractor.extract(text)
    assert f.host_unit == "某某酒店"
    assert f.seller_name == "某某公司"
    assert f.merchant_name == "某某商户"


def test_extract_document_ids():
    extractor = FieldExtractor()
    text = _make_text(报账单号="BZ20251001", 发票号码="FP20251001")
    f = extractor.extract(text)
    assert f.reimbursement_no == "BZ20251001"
    assert f.invoice_no == "FP20251001"


def test_extract_payment_voucher():
    extractor = FieldExtractor()
    f1 = extractor.extract("支付凭证: 有")
    assert f1.payment_voucher_present
    f2 = extractor.extract("刷卡单已上传")
    assert f2.payment_voucher_present


def test_extract_forbidden_keywords():
    extractor = FieldExtractor()
    text = "私人会所 鱼翅 燕窝 烟 酒 批量购买 旅游"
    f = extractor.extract(text)
    assert "私人会所" in f.forbidden_places
    assert "鱼翅" in f.forbidden_foods
    assert f.has_alcohol_tobacco
    assert f.bulk_alcohol
    assert f.tourism_suspected


def test_extract_cash_payment():
    extractor = FieldExtractor()
    f1 = extractor.extract("现金支付")
    assert f1.is_cash_payment
    f2 = extractor.extract("银行转账")
    assert not f2.is_cash_payment


def test_extract_empty():
    extractor = FieldExtractor()
    f = extractor.extract("")
    assert f.reception_date is None
    assert f.invoice_amount is None
    assert not f.payment_voucher_present

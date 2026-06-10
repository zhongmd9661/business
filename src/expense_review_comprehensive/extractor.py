"""从 OCR 解析的 Markdown 文本中提取审核所需结构化字段"""
from __future__ import annotations

from .models import (
    ExtractedFields,
    FORBIDDEN_PLACES,
    FORBIDDEN_FOODS,
    ALCOHOL_TOBACCO,
    BULK_PURCHASE,
    GIFT_KEYWORDS,
    TOURISM_KEYWORDS,
    _try_date,
    _try_float,
    _try_int,
    _try_str,
    _has,
)


class FieldExtractor:
    """从 Markdown 文本中提取业务招待费审核所需字段。"""

    def extract(self, text: str) -> ExtractedFields:
        f = ExtractedFields(raw_text=text)

        f.reception_date = _try_date(text, r"招待日期[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})")
        f.invoice_date = _try_date(text, r"发票日期[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})")
        f.apply_date = _try_date(text, r"申请日期[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})")
        f.payment_date = _try_date(text, r"支付日期[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})")

        f.invoice_amount = _try_float(text, r"发票[:\s]*金额[:\s]*(\d+\.?\d*)")
        if f.invoice_amount is None:
            f.invoice_amount = _try_float(text, r"金额[:\s]*(\d+\.?\d*)")
        f.actual_amount = _try_float(text, r"实际[:\s]*金额[:\s]*(\d+\.?\d*)")
        if f.actual_amount is None:
            f.actual_amount = _try_float(text, r"实付[:\s]*(\d+\.?\d*)")
        f.per_person_amount = _try_float(text, r"人均[:\s]*(\d+\.?\d*)")
        f.alcohol_price = _try_float(text, r"酒水[:\s]*价格[:\s]*(\d+\.?\d*)")
        f.souvenir_amount = _try_float(text, r"纪念品[:\s]*金额[:\s]*(\d+\.?\d*)")

        f.guest_count = _try_int(text, r"招待对象[:\s]*人数[:\s]*(\d+)")
        f.companion_count = _try_int(text, r"陪同[:\s]*人数[:\s]*(\d+)")
        f.handler = _try_str(text, r"经办人[:\s]*(.+?)(?:\n|$)")
        f.payee = _try_str(text, r"收款人[:\s]*(.+?)(?:\n|$)")
        f.department = _try_str(text, r"(?:部门|报销部门)[:\s]*(.+?)(?:\n|$)")

        # Personnel level
        if _has(text, r"省管中[层|级]", r"省管.*人员"):
            f.personnel_level = "省管中层"
        elif _has(text, r"市管中[层|级]", r"市管.*人员"):
            f.personnel_level = "市管中层"
        elif _has(text, r"其他.*人员", r"一般.*人员"):
            f.personnel_level = "其他人员"

        # Reception type
        f.reception_type = self._extract_type(text)

        # Supplier
        f.host_unit = _try_str(text, r"招待单位[:\s]*(.+?)(?:\n|$)")
        if not f.host_unit:
            f.host_unit = _try_str(text, r"来宾单位[:\s]*(.+?)(?:\n|$)")
        f.seller_name = _try_str(text, r"销售方[:\s]*(.+?)(?:\n|$)")
        f.merchant_name = _try_str(text, r"商户[:\s]*全称[:\s]*(.+?)(?:\n|$)")

        # Document IDs
        f.reimbursement_no = _try_str(text, r"报账[:\s]*单号[:\s]*(\S+)")
        f.invoice_no = _try_str(text, r"发票[:\s]*号码[:\s]*(\S+)")
        f.payment_voucher_present = _has(
            text, r"支付凭证[:\s]*有", r"刷卡单", r"电子消费凭证", r"POS机", r"互联网支付"
        )
        f.payment_statement_present = _has(
            text, r"支付流水", r"交易流水", r"银行流水", r"交易单号"
        )
        f.official_letter_present = _has(text, r"公函", r"往来公函")
        f.invoice_verified = _has(text, r"发票查验", r"发票验证", r"发票校验", r"系统校验")
        f.expense_detail_list_present = _has(text, r"费用明细", r"明细清单", r"招待明细")
        f.grid_allocation_signed = _has(text, r"网格分摊.*签章", r"分摊表.*签字")

        # Prohibition keywords
        for kw in FORBIDDEN_PLACES:
            if kw in text:
                f.forbidden_places.append(kw)
        for kw in FORBIDDEN_FOODS:
            if kw in text:
                f.forbidden_foods.append(kw)
        f.has_alcohol_tobacco = bool([kw for kw in ALCOHOL_TOBACCO if kw in text])
        f.bulk_alcohol = bool([kw for kw in BULK_PURCHASE if kw in text])
        f.gift_suspected = bool([kw for kw in GIFT_KEYWORDS if kw in text])
        f.tourism_suspected = bool([kw for kw in TOURISM_KEYWORDS if kw in text])

        # Payment method
        f.is_cash_payment = _has(text, r"现金[:\s]*支付", r"现金[:\s]*结算", r"现金支付", r"现金结算")
        f.has_prepaid = _has(text, r"预存", r"签单", r"后续签单")

        # Holiday report
        f.is_holiday_reported = _has(text, r"备案", r"报备", r"纪委报告", r"报备资料")

        return f

    @staticmethod
    def _extract_type(text: str) -> str | None:
        if _has(text, r"商务招[待|接]"):
            return "商务招待"
        if _has(text, r"外事招[待|接]"):
            return "外事招待"
        if _has(text, r"其他公务招[待|接]"):
            return "其他公务招待"
        if _has(text, r"内部.*招[待|接]", r"内部业务招待"):
            return "内部业务招待"
        if _has(text, r"工作餐"):
            return "工作餐"
        return None

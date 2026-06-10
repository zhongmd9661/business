"""全面审核规则检查器 — 按制度类别分组"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .models import (
    ExtractedFields,
    Finding,
    RuleCategory,
    INTERNAL_UNITS,
)

# ---------------------------------------------------------------------------
# 1. 单据完整性检查
# ---------------------------------------------------------------------------

class DocumentIntegrityChecker:
    """单据完整性规则：报账单号一致性、费用明细、支付凭证、支付流水、往来公函、发票查验、网格分摊表"""

    def check(self, f: ExtractedFields) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_reimbursement_no_consistency(f))
        findings.extend(self._check_expense_detail_list(f))
        findings.extend(self._check_payment_voucher(f))
        findings.extend(self._check_payment_statement(f))
        findings.extend(self._check_official_letter(f))
        findings.extend(self._check_invoice_verification(f))
        findings.extend(self._check_grid_allocation_signed(f))
        return findings

    def _check_reimbursement_no_consistency(self, f: ExtractedFields) -> list[Finding]:
        """3.1 报账单号一致性检查 — 发票、审批单、支付凭证上的报账单号应一致"""
        findings: list[Finding] = []
        if not f.reimbursement_no:
            findings.append(Finding(
                RuleCategory.DOCUMENT_INTEGRITY,
                "报账单号一致性",
                "管理办法 第8条",
                "提示",
                "未能提取到报账单号，请人工确认单据标识完整性",
            ))
        return findings

    def _check_expense_detail_list(self, f: ExtractedFields) -> list[Finding]:
        """3.2 费用明细清单检查"""
        findings: list[Finding] = []
        if not f.expense_detail_list_present:
            findings.append(Finding(
                RuleCategory.DOCUMENT_INTEGRITY,
                "费用明细清单",
                "管理办法 第9条",
                "中",
                "缺少费用明细清单",
            ))
        return findings

    def _check_payment_voucher(self, f: ExtractedFields) -> list[Finding]:
        """3.3 支付凭证检查 — 2024-04-01 后必须 100%"""
        findings: list[Finding] = []
        if f.reception_date and f.reception_date >= datetime(2024, 4, 1):
            if not f.payment_voucher_present:
                findings.append(Finding(
                    RuleCategory.DOCUMENT_INTEGRITY,
                    "支付凭证",
                    "管理办法 第10条",
                    "高",
                    "2024年4月1日后需提供支付凭证（刷卡单/电子消费凭证）",
                ))
        return findings

    def _check_payment_statement(self, f: ExtractedFields) -> list[Finding]:
        """3.4 支付流水证明检查 — 2025-09-01 后必须 100%"""
        findings: list[Finding] = []
        if f.reception_date and f.reception_date >= datetime(2025, 9, 1):
            if not f.payment_statement_present:
                findings.append(Finding(
                    RuleCategory.DOCUMENT_INTEGRITY,
                    "支付流水证明",
                    "管理办法 第10条",
                    "高",
                    "2025年9月1日后需提供支付流水证明",
                ))
        return findings

    def _check_official_letter(self, f: ExtractedFields) -> list[Finding]:
        """3.5 往来公函检查 — 2025-12-04 后外部招待必须 100%"""
        findings: list[Finding] = []
        is_external = f.reception_type in ("商务招待", "外事招待", "其他公务招待")
        if (f.reception_date
                and f.reception_date >= datetime(2025, 12, 4)
                and is_external):
            if not f.official_letter_present:
                findings.append(Finding(
                    RuleCategory.DOCUMENT_INTEGRITY,
                    "往来公函",
                    "管理办法 第11条",
                    "高",
                    "2025年12月4日后外部招待必需往来公函",
                ))
        return findings

    def _check_invoice_verification(self, f: ExtractedFields) -> list[Finding]:
        """3.6 发票查验检查 — 2025-06-01 前需要，之后系统校验即可"""
        findings: list[Finding] = []
        if f.reception_date and f.reception_date < datetime(2025, 6, 1):
            if not f.invoice_verified:
                findings.append(Finding(
                    RuleCategory.DOCUMENT_INTEGRITY,
                    "发票查验",
                    "管理办法 第12条",
                    "中",
                    "2025年6月1日前需提供发票查验证明",
                ))
        return findings

    def _check_grid_allocation_signed(self, f: ExtractedFields) -> list[Finding]:
        """3.7 网格分摊表签章检查"""
        findings: list[Finding] = []
        if not f.grid_allocation_signed:
            findings.append(Finding(
                RuleCategory.DOCUMENT_INTEGRITY,
                "网格分摊表签章",
                "管理办法 第13条",
                "低",
                "网格分摊表缺少签章",
            ))
        return findings


# ---------------------------------------------------------------------------
# 2. 金额标准检查
# ---------------------------------------------------------------------------

# 外部招待金额标准矩阵: (人员层级, 招待类型大类) -> 人均上限
EXTERNAL_AMOUNT_LIMITS: dict[tuple[str, str], float] = {
    # 外事/商务
    ("省管中层", "外事商务"): 400.0,
    ("市管中层", "外事商务"): 300.0,
    ("其他人员", "外事商务"): 250.0,
    # 其他公务
    ("省管中层", "其他公务"): 250.0,
    ("市管中层", "其他公务"): 200.0,
    ("其他人员", "其他公务"): 150.0,
}

INTERNAL_AMOUNT_LIMITS: dict[str, float] = {
    "省管中层": 150.0,
    "市管中层": 150.0,
    "其他人员": 100.0,
}

WORK_MEAL_LIMIT = 60.0
ALCOHOL_PRICE_LIMIT = 100.0  # 酒水单价上限
SOUVENIR_AMOUNT_LIMIT = 200.0  # 纪念品人均上限


class AmountStandardChecker:
    """金额标准规则：外部/内部/工作餐金额上限、酒水价格、纪念品"""

    def check(self, f: ExtractedFields) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_external_amount(f))
        findings.extend(self._check_internal_amount(f))
        findings.extend(self._check_work_meal_amount(f))
        findings.extend(self._check_alcohol_price(f))
        findings.extend(self._check_souvenir_amount(f))
        return findings

    def _check_external_amount(self, f: ExtractedFields) -> list[Finding]:
        """4.1 外部招待金额标准矩阵"""
        findings: list[Finding] = []
        if (not f.reception_type
                or f.reception_type not in ("商务招待", "外事招待", "其他公务招待")
                or f.personnel_level is None
                or f.per_person_amount is None):
            return findings

        category = "外事商务" if f.reception_type in ("商务招待", "外事招待") else "其他公务"
        limit = EXTERNAL_AMOUNT_LIMITS.get((f.personnel_level, category))
        if limit and f.per_person_amount > limit:
            findings.append(Finding(
                RuleCategory.AMOUNT_STANDARD,
                "外部招待金额标准",
                "管理办法 第15条",
                "高",
                f"人均费用({f.per_person_amount}元)超过{f.personnel_level}{category}标准({limit}元)",
            ))
        return findings

    def _check_internal_amount(self, f: ExtractedFields) -> list[Finding]:
        """4.2 内部招待金额标准"""
        findings: list[Finding] = []
        if (f.reception_type != "内部业务招待"
                or f.personnel_level is None
                or f.per_person_amount is None):
            return findings

        limit = INTERNAL_AMOUNT_LIMITS.get(f.personnel_level)
        if limit and f.per_person_amount > limit:
            findings.append(Finding(
                RuleCategory.AMOUNT_STANDARD,
                "内部招待金额标准",
                "管理办法 第16条",
                "高",
                f"人均费用({f.per_person_amount}元)超过{f.personnel_level}内部招待标准({limit}元)",
            ))
        return findings

    def _check_work_meal_amount(self, f: ExtractedFields) -> list[Finding]:
        """4.3 工作餐金额标准"""
        findings: list[Finding] = []
        if f.reception_type == "工作餐" and f.per_person_amount and f.per_person_amount > WORK_MEAL_LIMIT:
            findings.append(Finding(
                RuleCategory.AMOUNT_STANDARD,
                "工作餐金额标准",
                "管理办法 第17条",
                "高",
                f"人均费用({f.per_person_amount}元)超过工作餐标准({WORK_MEAL_LIMIT}元)",
            ))
        return findings

    def _check_alcohol_price(self, f: ExtractedFields) -> list[Finding]:
        """4.4 酒水价格上限检查"""
        findings: list[Finding] = []
        if f.alcohol_price and f.alcohol_price > ALCOHOL_PRICE_LIMIT:
            findings.append(Finding(
                RuleCategory.AMOUNT_STANDARD,
                "酒水价格上限",
                "管理办法 第18条",
                "中",
                f"酒水单价({f.alcohol_price}元)超过上限({ALCOHOL_PRICE_LIMIT}元)",
            ))
        return findings

    def _check_souvenir_amount(self, f: ExtractedFields) -> list[Finding]:
        """4.5 纪念品金额标准检查"""
        findings: list[Finding] = []
        if f.souvenir_amount and f.souvenir_amount > SOUVENIR_AMOUNT_LIMIT:
            findings.append(Finding(
                RuleCategory.AMOUNT_STANDARD,
                "纪念品金额标准",
                "管理办法 第19条",
                "中",
                f"纪念品金额({f.souvenir_amount}元)超过上限({SOUVENIR_AMOUNT_LIMIT}元)",
            ))
        return findings


# ---------------------------------------------------------------------------
# 3. 招待类型与陪同人数检查
# ---------------------------------------------------------------------------

class ReceptionTypeChecker:
    """招待类型匹配与陪同人数标准"""

    def check(self, f: ExtractedFields) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_type_match(f))
        findings.extend(self._check_external_companion(f))
        findings.extend(self._check_internal_companion(f))
        return findings

    def _check_type_match(self, f: ExtractedFields) -> list[Finding]:
        """5.1 招待类型与对象匹配 — 党政军→其他公务，内部单位→内部招待"""
        findings: list[Finding] = []
        if not f.reception_type or not f.host_unit:
            return findings

        host = f.host_unit
        # 党政军机关检测
        gov_keywords = ["党", "政", "军", "政府", "党委", "纪委", "人大", "政协", "公安局", "法院", "检察院"]
        is_gov = any(kw in host for kw in gov_keywords)

        if is_gov and f.reception_type == "商务招待":
            findings.append(Finding(
                RuleCategory.RECEPTION_TYPE,
                "招待类型匹配",
                "管理办法 第20条",
                "高",
                f"招待对象「{host}」为党政军机关，应选择其他公务招待而非商务招待",
            ))

        # 内部单位检测
        is_internal = self._is_internal_unit(host)
        if is_internal and f.reception_type in ("商务招待", "外事招待", "其他公务招待"):
            findings.append(Finding(
                RuleCategory.RECEPTION_TYPE,
                "招待类型匹配",
                "管理办法 第20条",
                "高",
                f"招待对象「{host}」为系统内部单位，应选择内部业务招待",
            ))

        return findings

    @staticmethod
    def _is_internal_unit(unit: str) -> bool:
        for name in INTERNAL_UNITS:
            if name in unit:
                return True
        return False

    def _check_external_companion(self, f: ExtractedFields) -> list[Finding]:
        """5.2 外部招待陪同人数 — ≤5对等，>5超出一半"""
        findings: list[Finding] = []
        if (not f.reception_type
                or f.reception_type == "内部业务招待"
                or f.guest_count is None
                or f.companion_count is None):
            return findings

        if f.guest_count <= 5:
            limit = f.guest_count
        else:
            limit = f.guest_count + (f.guest_count - 5) // 2

        if f.companion_count > limit:
            findings.append(Finding(
                RuleCategory.RECEPTION_TYPE,
                "外部招待陪同人数",
                "管理办法 第21条",
                "高",
                f"陪同人数({f.companion_count})超过标准({limit})，"
                f"招待对象{f.guest_count}人{'，对等' if f.guest_count <= 5 else '，超出部分一半'}",
            ))
        return findings

    def _check_internal_companion(self, f: ExtractedFields) -> list[Finding]:
        """5.3 内部招待陪同人数 — ≤10时3人，>10时1/3"""
        findings: list[Finding] = []
        if (f.reception_type != "内部业务招待"
                or f.guest_count is None
                or f.companion_count is None):
            return findings

        if f.guest_count <= 10:
            limit = 3
        else:
            limit = f.guest_count // 3

        if f.companion_count > limit:
            findings.append(Finding(
                RuleCategory.RECEPTION_TYPE,
                "内部招待陪同人数",
                "管理办法 第22条",
                "高",
                f"陪同人数({f.companion_count})超过标准({limit})，"
                f"招待对象{f.guest_count}人{'，上限3人' if f.guest_count <= 10 else '，上限1/3'}",
            ))
        return findings


# ---------------------------------------------------------------------------
# 4. 禁止性规定检查
# ---------------------------------------------------------------------------

class ProhibitionChecker:
    """禁止性规定：高档场所、高档菜品、烟酒、批量购买、送礼、旅游"""

    def check(self, f: ExtractedFields) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_forbidden_places(f))
        findings.extend(self._check_forbidden_foods(f))
        findings.extend(self._check_alcohol_tobacco(f))
        findings.extend(self._check_bulk_alcohol(f))
        findings.extend(self._check_gifts(f))
        findings.extend(self._check_tourism(f))
        return findings

    def _check_forbidden_places(self, f: ExtractedFields) -> list[Finding]:
        """6.1 高档场所检测"""
        findings: list[Finding] = []
        if f.forbidden_places:
            findings.append(Finding(
                RuleCategory.PROHIBITION,
                "高档场所",
                "风险点 第1条",
                "高",
                f"检测到禁止场所关键词: {', '.join(f.forbidden_places)}",
            ))
        return findings

    def _check_forbidden_foods(self, f: ExtractedFields) -> list[Finding]:
        """6.2 高档菜品检测"""
        findings: list[Finding] = []
        if f.forbidden_foods:
            findings.append(Finding(
                RuleCategory.PROHIBITION,
                "高档菜品",
                "风险点 第2条",
                "高",
                f"检测到禁止菜品关键词: {', '.join(f.forbidden_foods)}",
            ))
        return findings

    def _check_alcohol_tobacco(self, f: ExtractedFields) -> list[Finding]:
        """6.3 烟酒检测 — 工作餐和内部招待不上烟酒"""
        findings: list[Finding] = []
        if f.has_alcohol_tobacco and f.reception_type in ("工作餐", "内部业务招待"):
            findings.append(Finding(
                RuleCategory.PROHIBITION,
                "烟酒规定",
                "管理办法 第23条",
                "高",
                f"{f.reception_type}不应出现烟酒消费",
            ))
        return findings

    def _check_bulk_alcohol(self, f: ExtractedFields) -> list[Finding]:
        """6.4 批量购买酒水检测"""
        findings: list[Finding] = []
        if f.bulk_alcohol:
            findings.append(Finding(
                RuleCategory.PROHIBITION,
                "批量购买酒水",
                "风险点 第3条",
                "中",
                "检测到批量购买/采购酒水关键词，可能存在违规",
            ))
        return findings

    def _check_gifts(self, f: ExtractedFields) -> list[Finding]:
        """6.5 公款送礼检测"""
        findings: list[Finding] = []
        if f.gift_suspected:
            findings.append(Finding(
                RuleCategory.PROHIBITION,
                "公款送礼",
                "风险点 第4条",
                "高",
                "检测到疑似送礼关键词（现金/购物卡/会员卡/预付卡/有价证券/名贵土特产/珠宝/玉石）",
            ))
        return findings

    def _check_tourism(self, f: ExtractedFields) -> list[Finding]:
        """6.6 变相旅游检测"""
        findings: list[Finding] = []
        if f.tourism_suspected:
            findings.append(Finding(
                RuleCategory.PROHIBITION,
                "变相旅游",
                "风险点 第5条",
                "中",
                "检测到疑似旅游关键词（旅游/景点/演出/参观）",
            ))
        return findings


# ---------------------------------------------------------------------------
# 5. 报销合规检查
# ---------------------------------------------------------------------------

class ReimbursementComplianceChecker:
    """报销合规：事前审批、大额现金、拆分报销、混淆费用、发票类型、预存签单"""

    def check(self, f: ExtractedFields) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_prior_approval(f))
        findings.extend(self._check_large_cash(f))
        findings.extend(self._check_invoice_type(f))
        findings.extend(self._check_prepaid(f))
        return findings

    def _check_prior_approval(self, f: ExtractedFields) -> list[Finding]:
        """7.1 事前审批检查 — 申请日期应早于招待日期，否则需办公室会签"""
        findings: list[Finding] = []
        if f.apply_date and f.reception_date:
            if f.apply_date > f.reception_date:
                findings.append(Finding(
                    RuleCategory.REIMBURSEMENT,
                    "事前审批",
                    "管理办法 第24条",
                    "高",
                    f"申请日期({f.apply_date.date()})晚于招待日期({f.reception_date.date()})，需办公室会签",
                ))
        return findings

    def _check_large_cash(self, f: ExtractedFields) -> list[Finding]:
        """7.2 大额现金支付检查 — >5000元不得现金"""
        findings: list[Finding] = []
        amount = f.actual_amount or f.invoice_amount
        if f.is_cash_payment and amount and amount > 5000:
            findings.append(Finding(
                RuleCategory.REIMBURSEMENT,
                "大额现金支付",
                "管理办法 第25条",
                "高",
                f"金额({amount}元)超过5000元不得使用现金支付",
            ))
        return findings

    def _check_invoice_type(self, f: ExtractedFields) -> list[Finding]:
        """7.5 发票类型检查 — 应为电子普通发票+餐饮服务税目"""
        findings: list[Finding] = []
        text = f.raw_text
        if "增值税专用发票" in text:
            findings.append(Finding(
                RuleCategory.REIMBURSEMENT,
                "发票类型",
                "管理办法 第26条",
                "中",
                "业务招待费不应使用增值税专用发票",
            ))
        return findings

    def _check_prepaid(self, f: ExtractedFields) -> list[Finding]:
        """7.6 预存签单方式检查"""
        findings: list[Finding] = []
        if f.has_prepaid:
            findings.append(Finding(
                RuleCategory.REIMBURSEMENT,
                "预存签单",
                "管理办法 第27条",
                "低",
                "检测到预存/签单支付方式，建议确认是否符合规定",
            ))
        return findings

    def check_split_reimbursement(self, fields_list: list[ExtractedFields]) -> list[Finding]:
        """7.3 拆分报销检测 — 同一事项多笔小额（需批量模式）"""
        findings: list[Finding] = []
        # 按 handler + 日期月份 分组
        from collections import defaultdict
        groups: dict[tuple[str, str], list[ExtractedFields]] = defaultdict(list)
        for f in fields_list:
            if f.handler and f.reception_date:
                key = (f.handler, f.reception_date.strftime("%Y-%m"))
                groups[key].append(f)

        for (handler, month), group in groups.items():
            if len(group) >= 3:
                amounts = []
                for f in group:
                    amt = f.actual_amount or f.invoice_amount
                    if amt:
                        amounts.append(amt)
                if len(amounts) >= 3 and all(a < 5000 for a in amounts):
                    findings.append(Finding(
                        RuleCategory.REIMBURSEMENT,
                        "拆分报销",
                        "风险点 第6条",
                        "高",
                        f"「{handler}」在 {month} 有 {len(amounts)} 笔小额报销，"
                        f"金额分别为 {[round(a, 2) for a in amounts]}，疑似拆分报销",
                    ))
        return findings

    def check_mixed_expenses(self, fields_list: list[ExtractedFields]) -> list[Finding]:
        """7.4 混淆费用检测 — 招待费与市场营销费混淆（需批量模式）"""
        findings: list[Finding] = []
        market_keywords = ["市场营销", "市场推广", "营销费", "广告费", "宣传费"]
        for f in fields_list:
            if any(kw in f.raw_text for kw in market_keywords):
                if f.reception_type and "招待" in f.reception_type:
                    findings.append(Finding(
                        RuleCategory.REIMBURSEMENT,
                        "混淆费用",
                        "风险点 第7条",
                        "中",
                        f"单据同时包含招待费和市场营销相关词汇，可能混淆列支",
                    ))
        return findings


# ---------------------------------------------------------------------------
# 6. 交叉稽核检查
# ---------------------------------------------------------------------------

class CrossAuditChecker:
    """交叉稽核：企业经营状态、节日招待报备、重复招待、差旅期间非差旅地招待"""

    # 重大节日: (月, 日)
    HOLIDAYS = [
        (1, 1),   # 元旦
        (1, 22),  # 春节（示例，实际日期每年浮动）
        (5, 1),   # 劳动节
        (10, 1),  # 国庆节
    ]

    def check(self, f: ExtractedFields) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_holiday_reporting(f))
        return findings

    def _check_holiday_reporting(self, f: ExtractedFields) -> list[Finding]:
        """8.2 节日招待报备检查 — 重大节日前后3天"""
        findings: list[Finding] = []
        if not f.reception_date:
            return findings

        d = f.reception_date
        for month, day in self.HOLIDAYS:
            holiday = datetime(d.year, month, day)
            if abs((d - holiday).days) <= 3:
                if not f.is_holiday_reported:
                    findings.append(Finding(
                        RuleCategory.CROSS_AUDIT,
                        "节日招待报备",
                        "管理办法 第28条",
                        "中",
                        f"招待日期({d.date()})接近重大节日({holiday.date()})，需确认已报备",
                    ))
                break
        return findings

    def check_enterprise_status(self, fields_list: list[ExtractedFields]) -> list[Finding]:
        """8.1 企业经营状态检查 — 需要外部 API，此处仅做占位"""
        findings: list[Finding] = []
        # 实际需要调用工商 API 查询企业状态
        # 这里仅提示人工检查
        for f in fields_list:
            if f.host_unit:
                findings.append(Finding(
                    RuleCategory.CROSS_AUDIT,
                    "企业经营状态",
                    "风险点 第8条",
                    "提示",
                    f"请人工确认「{f.host_unit}」的经营状态是否正常",
                ))
        return findings

    def check_duplicate_reception(self, fields_list: list[ExtractedFields]) -> list[Finding]:
        """8.3 重复招待检测 — 同部门当月同一对象≥2次"""
        findings: list[Finding] = []
        from collections import defaultdict
        groups: dict[tuple[str, str, str], int] = defaultdict(int)
        for f in fields_list:
            if f.department and f.host_unit and f.reception_date:
                key = (f.department, f.host_unit, f.reception_date.strftime("%Y-%m"))
                groups[key] += 1

        for (dept, host, month), count in groups.items():
            if count >= 2:
                findings.append(Finding(
                    RuleCategory.CROSS_AUDIT,
                    "重复招待",
                    "风险点 第9条",
                    "中",
                    f"「{dept}」在 {month} 招待「{host}」达 {count} 次，建议核实",
                ))
        return findings

    def check_travel_mismatch(self, fields_list: list[ExtractedFields]) -> list[Finding]:
        """8.4 差旅期间非差旅地招待检测 — 需要差旅数据，此处提示"""
        findings: list[Finding] = []
        # 实际需要与差旅系统数据关联
        for f in fields_list:
            if f.host_unit and f.reception_date:
                findings.append(Finding(
                    RuleCategory.CROSS_AUDIT,
                    "差旅期间招待",
                    "风险点 第10条",
                    "提示",
                    f"请人工确认「{f.host_unit}」在 {f.reception_date.date()} 的招待是否发生在差旅期间",
                ))
        return findings


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------

class ComprehensiveChecker:
    """聚合所有检查器，统一执行审核"""

    def __init__(self):
        self._checkers = [
            DocumentIntegrityChecker(),
            AmountStandardChecker(),
            ReceptionTypeChecker(),
            ProhibitionChecker(),
            ReimbursementComplianceChecker(),
            CrossAuditChecker(),
        ]

    def check_single(self, f: ExtractedFields) -> list[Finding]:
        """对单张单据执行所有规则检查"""
        findings: list[Finding] = []
        for checker in self._checkers:
            findings.extend(checker.check(f))
        return findings

    def check_batch(self, fields_list: list[ExtractedFields]) -> list[Finding]:
        """对批量单据执行所有规则检查（含跨文档检测）"""
        findings: list[Finding] = []
        for f in fields_list:
            findings.extend(self.check_single(f))
        # 跨文档检查
        reimb_checker: ReimbursementComplianceChecker = self._checkers[4]  # type: ignore[assignment]
        cross_checker: CrossAuditChecker = self._checkers[5]  # type: ignore[assignment]
        findings.extend(reimb_checker.check_split_reimbursement(fields_list))
        findings.extend(reimb_checker.check_mixed_expenses(fields_list))
        findings.extend(cross_checker.check_enterprise_status(fields_list))
        findings.extend(cross_checker.check_duplicate_reception(fields_list))
        findings.extend(cross_checker.check_travel_mismatch(fields_list))
        return findings

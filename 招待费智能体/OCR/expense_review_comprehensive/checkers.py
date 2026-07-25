"""全面审核规则检查器 — 按制度类别分组"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional

from .models import (
    ExtractedFields,
    Finding,
    RuleCategory,
    INTERNAL_UNITS,
    BatchReviewContext,
    BatchFinding,
    BatchReviewReport,
    CategoryBatchReport,
)
from .proofreading_checker import ProofreadingChecker

# ---------------------------------------------------------------------------
# Helper: document type classification
# ---------------------------------------------------------------------------

def _classify_doc_type(filename: str) -> str:
    """根据文件名判断文档类型"""
    name = filename.lower()
    if '发票' in name:
        return '发票'
    if '审批单' in name:
        return '审批单'
    if '申请单' in name:
        return '申请单'
    if '报账单' in name:
        return '报账单'
    if '经营状态' in name or '认证' in name:
        return '经营状态'
    if '支付证明' in name:
        return '支付证明'
    if '支付凭证' in name:
        return '支付凭证'
    if '函件' in name:
        return '活动函件'
    return '其他'


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
    """聚合所有检查器，统一执行审核

    Args:
        llm_client: 可选的 Anthropic 客户端，供校对规则 LLM 提取使用
        dynamic_rules: 可选的动态规则列表（从数据库加载的 dict），支持热更新
    """

    def __init__(self, llm_client=None, dynamic_rules: list[dict] | None = None):
        self._checkers = [
            DocumentIntegrityChecker(),
            AmountStandardChecker(),
            ReceptionTypeChecker(),
            ProhibitionChecker(),
            ReimbursementComplianceChecker(),
            CrossAuditChecker(),
        ]
        self._proofreading_checker = ProofreadingChecker(client=llm_client)
        if llm_client is None:
            self._proofreading_checker.start()
        # Dynamic rules from database
        self._dynamic_rules: list[DynamicRule] = []
        if dynamic_rules:
            self._load_dynamic_rules(dynamic_rules)

    def _load_dynamic_rules(self, rules: list[dict]) -> None:
        """从数据库规则 dict 加载动态规则"""
        from .rule_engine import DynamicRule
        self._dynamic_rules = [DynamicRule(r) for r in rules]

    def reload_dynamic_rules(self, rules: list[dict]) -> None:
        """热更新动态规则 — 规则变更后调用，无需重启服务"""
        from .rule_engine import DynamicRule
        self._dynamic_rules = [DynamicRule(r) for r in rules]

    def check_single(self, f: ExtractedFields) -> list[Finding]:
        """对单张单据执行所有规则检查（含动态规则）"""
        findings: list[Finding] = []
        for checker in self._checkers:
            findings.extend(checker.check(f))
        # Dynamic rules from database
        for rule in self._dynamic_rules:
            finding = rule.evaluate(f)
            if finding:
                findings.append(finding)
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

    def check_batch_review(
        self, filenames: list[str], fields_list: list[ExtractedFields]
    ) -> BatchReviewReport:
        """以批次整体为单位审核，不逐文档检查。只运行聚合规则和跨文档规则。"""
        # 1. 构建批次上下文
        ctx = self._build_context(filenames, fields_list)

        # 2. 聚合规则（金额标准、陪同人数）
        agg_findings = self._check_aggregated(ctx)

        # 3. 跨文档规则（拆分报销、重复招待、差旅地校验）
        cross_findings = self._check_cross_document(fields_list)

        # 4. 校对规则（金额一致性、日期一致性、招待标准、单位经营状态、支付凭证一致性、活动函件日期）
        proofreading_findings, proofreading_data = self._proofreading_checker.check(
            list(zip(filenames, fields_list))
        )

        # 5. 组装报告
        return self._build_report(ctx, agg_findings, cross_findings + proofreading_findings, proofreading_data)

    @staticmethod
    def _build_context(
        filenames: list[str], fields_list: list[ExtractedFields]
    ) -> BatchReviewContext:
        """聚合各文档字段为批次级指标

        同一批次的文档属于同一笔招待事件，金额和人数不应重复计算：
        - 金额: 取第一个可靠来源的实际发生金额（发票 > 报账单 > 审批单）
        - 人数: 取第一个非空值（审批单/申请单记录，数值相同）
        """
        total_amount = None  # 取单笔代表值, 不累加
        total_guest = 0
        total_companion = 0
        department = None
        reception_type = None
        earliest_apply = None
        earliest_reception = None

        # 金额来源优先级: 发票 → 报账单 → 审批单/申请单
        for priority in ('发票', '报账单', '审批单', '申请单'):
            if total_amount is not None:
                break
            for fname, f in zip(filenames, fields_list):
                if _classify_doc_type(fname) == priority:
                    amt = f.actual_amount or f.invoice_amount
                    if amt:
                        total_amount = amt
                        break

        for fname, f in zip(filenames, fields_list):
            # 人数: 取第一个非空值即可, 不累加
            if total_guest == 0 and f.guest_count:
                total_guest = f.guest_count
            if total_companion == 0 and f.companion_count:
                total_companion = f.companion_count
            if not department and f.department:
                department = f.department
            if not reception_type and f.reception_type:
                reception_type = f.reception_type
            if f.apply_date and (earliest_apply is None or f.apply_date < earliest_apply):
                earliest_apply = f.apply_date
            if f.reception_date and (earliest_reception is None or f.reception_date < earliest_reception):
                earliest_reception = f.reception_date

        documents = list(zip(filenames, fields_list))
        return BatchReviewContext(
            documents=documents,
            total_amount=total_amount or 0.0,
            total_guest_count=total_guest,
            total_companion_count=total_companion,
            department=department,
            reception_type=reception_type,
            apply_date=earliest_apply,
            reception_date=earliest_reception,
        )

    def _check_per_document(
        self, filenames: list[str], fields_list: list[ExtractedFields]
    ) -> list[BatchFinding]:
        """逐文档运行单据完整性、禁止性规定、报销合规、交叉稽核检查（含动态规则）"""
        findings: list[BatchFinding] = []
        integrity_checker: DocumentIntegrityChecker = self._checkers[0]  # type: ignore
        prohibition_checker: ProhibitionChecker = self._checkers[3]  # type: ignore
        reimb_checker: ReimbursementComplianceChecker = self._checkers[4]  # type: ignore
        cross_checker: CrossAuditChecker = self._checkers[5]  # type: ignore

        for fname, f in zip(filenames, fields_list):
            for finding in integrity_checker.check(f):
                findings.append(self._to_batch_finding(finding, fname))
            for finding in prohibition_checker.check(f):
                findings.append(self._to_batch_finding(finding, fname))
            for finding in reimb_checker.check(f):
                findings.append(self._to_batch_finding(finding, fname))
            for finding in cross_checker.check(f):
                findings.append(self._to_batch_finding(finding, fname))
            # Dynamic rules from database
            for rule in self._dynamic_rules:
                bf = rule.to_batch_finding(f, fname)
                if bf:
                    findings.append(bf)
        return findings

    def _check_aggregated(self, ctx: BatchReviewContext) -> list[BatchFinding]:
        """基于批次上下文的聚合指标运行金额标准和陪同人数检查"""
        findings: list[BatchFinding] = []
        amount_checker: AmountStandardChecker = self._checkers[1]  # type: ignore
        type_checker: ReceptionTypeChecker = self._checkers[2]  # type: ignore

        # 构建一个虚拟字段用于聚合规则检查
        agg_fields = self._create_aggregated_fields(ctx)
        for finding in amount_checker.check(agg_fields):
            findings.append(self._to_batch_finding(finding, ""))
        for finding in type_checker.check(agg_fields):
            findings.append(self._to_batch_finding(finding, ""))
        return findings

    @staticmethod
    def _create_aggregated_fields(ctx: BatchReviewContext) -> ExtractedFields:
        """从批次上下文创建聚合字段，用于金额标准/陪同人数检查"""
        total_people = ctx.total_guest_count + ctx.total_companion_count
        per_person = ctx.total_amount / total_people if total_people > 0 else 0
        # 取第一个文档的人员层级
        level = None
        for _, f in ctx.documents:
            if f.personnel_level:
                level = f.personnel_level
                break
        return ExtractedFields(
            reception_date=ctx.reception_date,
            apply_date=ctx.apply_date,
            invoice_amount=ctx.total_amount,
            actual_amount=ctx.total_amount,
            per_person_amount=per_person,
            guest_count=ctx.total_guest_count,
            companion_count=ctx.total_companion_count,
            reception_type=ctx.reception_type,
            personnel_level=level,
        )

    def _check_cross_document(
        self, fields_list: list[ExtractedFields]
    ) -> list[BatchFinding]:
        """跨文档规则：拆分报销、重复招待、企业状态、差旅地校验"""
        findings: list[BatchFinding] = []
        reimb_checker: ReimbursementComplianceChecker = self._checkers[4]  # type: ignore
        cross_checker: CrossAuditChecker = self._checkers[5]  # type: ignore

        for finding in reimb_checker.check_split_reimbursement(fields_list):
            findings.append(self._to_batch_finding(finding, ""))
        for finding in reimb_checker.check_mixed_expenses(fields_list):
            findings.append(self._to_batch_finding(finding, ""))
        for finding in cross_checker.check_enterprise_status(fields_list):
            findings.append(self._to_batch_finding(finding, ""))
        for finding in cross_checker.check_duplicate_reception(fields_list):
            findings.append(self._to_batch_finding(finding, ""))
        for finding in cross_checker.check_travel_mismatch(fields_list):
            findings.append(self._to_batch_finding(finding, ""))
        return findings

    @staticmethod
    def _to_batch_finding(f: Finding, document: str) -> BatchFinding:
        return BatchFinding(
            category=f.category,
            rule=f.rule,
            clause=f.clause,
            level=f.level,
            message=f.message,
            document=document,
        )

    @staticmethod
    def _build_report(
        ctx: BatchReviewContext,
        agg_findings: list[BatchFinding],
        cross_findings: list[BatchFinding],
        proofreading_data: list[tuple[str, str, ExtractedFields, object]] | None = None,
    ) -> BatchReviewReport:
        all_findings = agg_findings + cross_findings
        report = BatchReviewReport(
            batch_name="",  # placeholder, set by caller
            document_count=len(ctx.documents),
            department=ctx.department,
            reception_type=ctx.reception_type,
            all_findings=all_findings,
        )

        # 按类别分组
        by_category: dict[RuleCategory, list[BatchFinding]] = defaultdict(list)
        for f in all_findings:
            by_category[f.category].append(f)

        for category in RuleCategory:
            cat_findings = by_category.get(category, [])
            if cat_findings:
                report.category_reports.append(
                    CategoryBatchReport(category=category, findings=cat_findings)
                )

        # 构建对比表数据
        if proofreading_data:
            comparison_rows: list[dict[str, str]] = []
            for fname, doc_type, _ef, pf in proofreading_data:
                row: dict[str, str] = {
                    'doc_type': doc_type,
                    'filename': fname,
                }
                # 金额类字段
                if pf.invoice_total_uppercase:
                    row['发票金额(大写)'] = pf.invoice_total_uppercase
                if pf.invoice_total_lowercase is not None:
                    row['发票金额(小写)'] = f'{pf.invoice_total_lowercase:.2f}'
                if pf.approval_amount is not None:
                    row['审批金额'] = f'{pf.approval_amount:.2f}'
                if pf.payment_amount is not None:
                    row['支付凭证金额'] = f'{pf.payment_amount:.2f}'
                if pf.statement_amount is not None:
                    row['支付证明金额'] = f'{pf.statement_amount:.2f}'
                if pf.reimbursement_invoice_amount is not None:
                    row['报账金额'] = f'{pf.reimbursement_invoice_amount:.2f}'
                # 日期类字段
                if pf.invoice_date:
                    row['开票日期'] = pf.invoice_date.strftime('%Y-%m-%d')
                if pf.reception_date:
                    row['招待日期'] = pf.reception_date.strftime('%Y-%m-%d')
                if pf.payment_date:
                    row['支付日期'] = pf.payment_date.strftime('%Y-%m-%d %H:%M:%S')
                if pf.transaction_date:
                    row['交易日期'] = pf.transaction_date.strftime('%Y-%m-%d %H:%M:%S')
                if pf.activity_date:
                    row['活动日期'] = pf.activity_date.strftime('%Y-%m-%d')
                # 招待标准字段
                if pf.guest_count is not None:
                    row['招待人数'] = str(pf.guest_count)
                if pf.companion_count is not None:
                    row['陪同人数'] = str(pf.companion_count)
                if pf.per_person_fee is not None:
                    row['人均费用'] = f'{pf.per_person_fee:.2f}'
                if pf.reception_type:
                    row['招待类型'] = pf.reception_type
                if pf.is_work_meal:
                    row['是否工作餐'] = pf.is_work_meal
                # 支付凭证一致性字段
                if pf.transaction_no:
                    row['交易单号'] = pf.transaction_no
                if pf.merchant_order_no:
                    row['商户单号'] = pf.merchant_order_no
                if pf.merchant_full_name:
                    row['商户全称'] = pf.merchant_full_name
                # 其他
                if pf.host_unit:
                    row['招待对象'] = pf.host_unit
                if row != {'doc_type': doc_type, 'filename': fname}:
                    comparison_rows.append(row)

            report.comparison_rows = comparison_rows

        return report

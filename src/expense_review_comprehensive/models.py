"""共享数据结构"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RuleCategory(str, Enum):
    DOCUMENT_INTEGRITY = "单据完整性"
    AMOUNT_STANDARD = "金额标准"
    RECEPTION_TYPE = "招待类型与陪同人数"
    PROHIBITION = "禁止性规定"
    REIMBURSEMENT = "报销合规"
    CROSS_AUDIT = "交叉稽核"


@dataclass
class Finding:
    category: RuleCategory
    rule: str
    clause: str  # 制度条款引用
    level: str  # "高", "中", "低", "提示"
    message: str
    detail: str = ""


# ---------- 从 OCR 文本中提取的结构化字段 ----------

INTERNAL_UNITS = {
    "集团公司", "省移动", "专业公司", "直属单位", "铁通公司", "设计院",
    "国际公司", "终端公司", "政企分公司", "财务公司", "中移物联网公司",
    "智慧家庭运营中心", "在线营销服务中心", "杭州研发中心", "苏州研发中心",
    "咪咕公司", "中移互联网公司", "研究院", "移动学院", "信息港中心",
    "信安中心", "采购共享中心", "信息技术中心", "卓望公司", "投资公司",
    "上海产业研究院", "成都产业研究院", "中移系统集成有限公司", "电商公司",
    "中移系统集成", "中移物联网", "信安", "卓望", "咪咕",
}

# 禁止性关键词分组
FORBIDDEN_PLACES = [
    "私人会所", "一桌餐", "一围餐", "高档娱乐", "高档小区", "写字楼",
    "烟酒专卖店", "农家乐", "宿舍", "保健", "健身",
]
FORBIDDEN_FOODS = ["鱼翅", "燕窝", "野生保护动物", "珍稀药材"]
ALCOHOL_TOBACCO = ["烟", "酒", "白酒", "红酒", "葡萄酒", "高档酒水"]
BULK_PURCHASE = ["批量购买", "批量采购", "成箱", "整箱"]
GIFT_KEYWORDS = ["现金", "购物卡", "会员卡", "预付卡", "有价证券", "名贵土特产", "珠宝", "玉石"]
TOURISM_KEYWORDS = ["旅游", "景点", "演出", "变相旅游", "参观"]


@dataclass
class ExtractedFields:
    # Dates
    reception_date: Optional[datetime] = None
    invoice_date: Optional[datetime] = None
    apply_date: Optional[datetime] = None
    payment_date: Optional[datetime] = None

    # Amounts
    invoice_amount: Optional[float] = None
    actual_amount: Optional[float] = None
    per_person_amount: Optional[float] = None
    alcohol_price: Optional[float] = None
    souvenir_amount: Optional[float] = None

    # People
    guest_count: Optional[int] = None
    companion_count: Optional[int] = None
    handler: Optional[str] = None
    payee: Optional[str] = None
    personnel_level: Optional[str] = None  # "省管中层", "市管中层", "其他人员"

    # Reception type
    reception_type: Optional[str] = None  # "商务招待", "外事招待", "其他公务招待", "内部业务招待", "工作餐"

    # Supplier
    host_unit: Optional[str] = None
    seller_name: Optional[str] = None
    merchant_name: Optional[str] = None

    # Document IDs
    reimbursement_no: Optional[str] = None
    invoice_no: Optional[str] = None
    payment_voucher_present: bool = False
    payment_statement_present: bool = False  # 支付流水证明
    official_letter_present: bool = False
    invoice_verified: bool = False
    expense_detail_list_present: bool = False
    grid_allocation_signed: bool = False

    # Prohibition flags
    forbidden_places: list[str] = field(default_factory=list)
    forbidden_foods: list[str] = field(default_factory=list)
    has_alcohol_tobacco: bool = False
    bulk_alcohol: bool = False
    gift_suspected: bool = False
    tourism_suspected: bool = False

    # Other
    is_cash_payment: bool = False
    has_prepaid: bool = False  # 预存签单
    is_holiday_reported: bool = False
    department: Optional[str] = None
    raw_text: str = ""


# ---------- 批次审核上下文 ----------

@dataclass
class BatchReviewContext:
    """聚合同批次所有文档的提取字段为批次级审核指标"""
    documents: list[tuple[str, ExtractedFields]]
    total_amount: float = 0.0
    total_guest_count: int = 0
    total_companion_count: int = 0
    department: Optional[str] = None
    reception_type: Optional[str] = None
    apply_date: Optional[datetime] = None
    reception_date: Optional[datetime] = None


@dataclass
class BatchFinding:
    """批次级别的审核发现，关联到具体文档或批次整体"""
    category: RuleCategory
    rule: str
    clause: str
    level: str
    message: str
    document: str = ""  # 来源文档文件名，空字符串表示批次级


@dataclass
class CategoryBatchReport:
    """单个规则类别的批次报告段"""
    category: RuleCategory
    findings: list[BatchFinding] = field(default_factory=list)


@dataclass
class BatchReviewReport:
    """批次审核报告：包含批次信息、总体判定、分类报告"""
    batch_name: str
    document_count: int = 0
    department: Optional[str] = None
    reception_type: Optional[str] = None
    category_reports: list[CategoryBatchReport] = field(default_factory=list)
    all_findings: list[BatchFinding] = field(default_factory=list)

    @property
    def has_high_risk(self) -> bool:
        return any(f.level == "高" for f in self.all_findings)


def _try_date(text: str, pattern: str) -> Optional[datetime]:
    m = re.search(pattern, text)
    if not m:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y-%m", "%Y/%m"):
        try:
            return datetime.strptime(m.group(1), fmt)
        except ValueError:
            continue
    return None


def _try_float(text: str, pattern: str) -> Optional[float]:
    m = re.search(pattern, text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _try_int(text: str, pattern: str) -> Optional[int]:
    m = re.search(pattern, text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _try_str(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text)
    return m.group(1) if m else None


def _has(text: str, *patterns: str) -> bool:
    for pat in patterns:
        if re.search(pat, text):
            return True
    return False

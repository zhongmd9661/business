"""接待标准数据 — 源自《清远分公司业务招待费管理办法（V9.0）》"""

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# 类型定义
# -------------------------------------------------------------------�-���

ReceptionType = Literal["商务招待", "外事招待", "其他公务招待", "内部业务招待", "工作餐"]
PersonnelLevel = Literal["省管中层", "市管中层", "其他人员"]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class MealStandard:
    """用餐标准"""
    per_person_limit: float  # 人均上限(元)
    name: str  # 标准名称


@dataclass
class SouvenirStandard:
    """纪念品标准"""
    per_person_limit: float | None  # 人均上限(元)，None表示不得赠送
    name: str


@dataclass
class AlcoholStandard:
    """酒水标准"""
    baijiu_limit: float  # 白酒 500ml 上限(元)
    red_wine_limit: float  # 红酒 750ml 上限(元)
    name: str


@dataclass
class CompanionRule:
    """陪同人数规则"""
    guest_limit: int  # 招待对象人数分界点
    rule_desc: str  # 规则描述
    companion_formula: str  # 计算公式


@dataclass
class ExternalReceptionStandard:
    """对外业务招待标准"""
    personnel_level: str
    reception_type: str  # "外事/商务" 或 "其他公务"

    meal: MealStandard
    souvenir: SouvenirStandard
    alcohol: AlcoholStandard

    def to_dict(self) -> dict:
        return {
            "人员层级": self.personnel_level,
            "招待类型": self.reception_type,
            "用餐标准": f"{self.meal.per_person_limit}元/人·次",
            "纪念品": (
                f"{self.souvenir.per_person_limit}元/人·次"
                if self.souvenir.per_person_limit is not None
                else "不得赠送"
            ),
            "酒水标准": (
                f"白酒≤{self.alcohol.baijiu_limit}元/500ml, 红酒≤{self.alcohol.red_wine_limit}元/750ml"
            ),
        }


@dataclass
class InternalReceptionStandard:
    """内部业务招待标准"""
    personnel_level: str
    meal: MealStandard
    souvenir: SouvenirStandard
    alcohol: AlcoholStandard

    def to_dict(self) -> dict:
        return {
            "人员层级": self.personnel_level,
            "用餐标准": f"{self.meal.per_person_limit}元/人·次",
            "纪念品": "不得赠送",
            "酒水": "不上烟酒",
        }


# ---------------------------------------------------------------------------
# 对外招待标准矩阵
# ---------------------------------------------------------------------------

EXTERNAL_STANDARDS: list[ExternalReceptionStandard] = [
    # 省管中层
    ExternalReceptionStandard(
        personnel_level="省管中层",
        reception_type="外事/商务",
        meal=MealStandard(400.0, "宴请标准"),
        souvenir=SouvenirStandard(400.0, "纪念品标准"),
        alcohol=AlcoholStandard(400.0, 400.0, "酒水标准"),
    ),
    ExternalReceptionStandard(
        personnel_level="省管中层",
        reception_type="其他公务",
        meal=MealStandard(200.0, "宴请标准"),
        souvenir=SouvenirStandard(None, "不得赠送纪念品"),
        alcohol=AlcoholStandard(400.0, 400.0, "酒水标准"),
    ),
    # 市管中层
    ExternalReceptionStandard(
        personnel_level="市管中层",
        reception_type="外事/商务",
        meal=MealStandard(300.0, "宴请标准"),
        souvenir=SouvenirStandard(300.0, "纪念品标准"),
        alcohol=AlcoholStandard(300.0, 300.0, "酒水标准"),
    ),
    ExternalReceptionStandard(
        personnel_level="市管中层",
        reception_type="其他公务",
        meal=MealStandard(200.0, "宴请标准"),
        souvenir=SouvenirStandard(None, "不得赠送纪念品"),
        alcohol=AlcoholStandard(300.0, 300.0, "酒水标准"),
    ),
    # 其他人员
    ExternalReceptionStandard(
        personnel_level="其他人员",
        reception_type="外事/商务",
        meal=MealStandard(200.0, "宴请标准"),
        souvenir=SouvenirStandard(200.0, "纪念品标准"),
        alcohol=AlcoholStandard(200.0, 200.0, "酒水标准"),
    ),
    ExternalReceptionStandard(
        personnel_level="其他人员",
        reception_type="其他公务",
        meal=MealStandard(150.0, "宴请标准"),
        souvenir=SouvenirStandard(None, "不得赠送纪念品"),
        alcohol=AlcoholStandard(200.0, 200.0, "酒水标准"),
    ),
]

# ---------------------------------------------------------------------------
# 内部招待标准
# ---------------------------------------------------------------------------

INTERNAL_STANDARDS: list[InternalReceptionStandard] = [
    InternalReceptionStandard(
        personnel_level="省管中层",
        meal=MealStandard(150.0, "用餐标准"),
        souvenir=SouvenirStandard(None, "不得赠送"),
        alcohol=AlcoholStandard(0, 0, "不上烟酒"),
    ),
    InternalReceptionStandard(
        personnel_level="市管中层",
        meal=MealStandard(150.0, "用餐标准"),
        souvenir=SouvenirStandard(None, "不得赠送"),
        alcohol=AlcoholStandard(0, 0, "不上烟酒"),
    ),
    InternalReceptionStandard(
        personnel_level="其他人员",
        meal=MealStandard(100.0, "用餐标准"),
        souvenir=SouvenirStandard(None, "不得赠送"),
        alcohol=AlcoholStandard(0, 0, "不上烟酒"),
    ),
]

# ---------------------------------------------------------------------------
# 陪同人数规则
# ---------------------------------------------------------------------------

COMPANION_RULES: list[CompanionRule] = [
    CompanionRule(
        guest_limit=5,
        rule_desc="招待对象≤5人时，陪餐人数可对等；>5人时，超过部分陪餐人数≤招待对象超过部分的1/2",
        companion_formula="guest≤5: companion≤guest; guest>5: companion≤5+(guest-5)//2",
    ),
    CompanionRule(
        guest_limit=10,
        rule_desc="内部招待：招待对象≤10人，陪同≤3人；>10人，陪同≤招待对象的1/3",
        companion_formula="guest≤10: companion≤3; guest>10: companion≤guest//3",
    ),
]

# ---------------------------------------------------------------------------
# 禁止性规定汇总
# ---------------------------------------------------------------------------

PROHIBITIONS: list[dict] = [
    {"条款": "第十四条", "规定": "不得安排私人会所及高档娱乐、休闲、健身、保健等高消费场所"},
    {"条款": "第十四条", "规定": "不得提供用野生保护动物制作的菜肴"},
    {"条款": "第十四条", "规定": "不得提供鱼翅、燕窝等高档菜肴"},
    {"条款": "第十四条", "规定": "严禁用公款购买香烟和高档酒水、珍稀药材、天价茶叶、名贵木材、珠宝玉石等"},
    {"条款": "第十五条", "规定": "不得批量购买业务招待用酒"},
    {"条款": "第十七条", "规定": "严禁用公款开展相互走访、送礼、宴请等拜年活动"},
    {"条款": "第十九条", "规定": "不得支付应由个人负担的招待费用；不得向下属单位摊派或转嫁费用"},
    {"条款": "第二十条", "规定": "严禁赠送现金、购物卡、会员卡、有价证券、贵重物品、名贵土特产等"},
    {"条款": "第二十五条", "规定": "不得采取预存费用后续签单消费方式"},
    {"条款": "第二十五条", "规定": "超过5000元不得以现金结算"},
]

# ---------------------------------------------------------------------------
# 招待类型说明
# ---------------------------------------------------------------------------

RECEPTION_TYPE_EXPLANATIONS: list[dict] = [
    {
        "类型": "商务招待",
        "说明": "在商业谈判或商业合作中招待客户、合资合作方、经贸联络考察团组的活动",
        "适用标准": "外事/商务标准（最高档）",
        "注意事项": "招待对象不包括党政军机关工作人员和国有企业集团总部工作人员",
    },
    {
        "类型": "外事招待",
        "说明": "招待外宾或其他外籍关系人员的活动",
        "适用标准": "外事/商务标准（最高档）",
        "注意事项": "应优先在社会公共场所安排，遵守外事工作规定和保密要求",
    },
    {
        "类型": "其他公务招待",
        "说明": "招待其他人员的公务活动",
        "适用标准": "其他公务标准",
        "注意事项": "招待党政军机关工作人员应参照《党政机关国内公务接待管理规定》执行",
    },
    {
        "类型": "内部业务招待",
        "说明": "集团公司内部上下级单位之间、平级单位之间的公务招待活动",
        "适用标准": "内部业务招待标准",
        "注意事项": "原则上不超过1次，不得进行商务宴请，不上烟酒，不得赠送纪念品",
    },
    {
        "类型": "工作餐",
        "说明": "内部公务活动期间的工作用餐",
        "适用标准": "参照所在单位食堂正常标准或差旅伙食补贴标准",
        "注意事项": "优先在单位食堂安排，优先自助形式，不上烟酒",
    },
]

# ---------------------------------------------------------------------------
# 审批流程
# ---------------------------------------------------------------------------

APPROVAL_FLOW: list[dict] = [
    {
        "步骤": 1,
        "动作": "事前审批",
        "说明": "所有业务招待活动均应履行事前审批程序，经相关领导审批同意后方可开展",
        "依据": "第二十二条",
    },
    {
        "步骤": 2,
        "动作": "填写招待清单",
        "说明": "如实反映招待人员、招待事由、招待费用等明细",
        "依据": "第二十二条",
    },
    {
        "步骤": 3,
        "动作": "开展招待活动",
        "说明": "如确因紧急事由无法事前审批，应请示有审批权限的领导同意后开展",
        "依据": "第二十二条",
    },
    {
        "步骤": 4,
        "动作": "事后及时补审批",
        "说明": "紧急情况下事后应及时补办审批手续",
        "依据": "第二十二条",
    },
    {
        "步骤": 5,
        "动作": "提交报销材料",
        "说明": "发票、审批单、支付凭证、费用明细清单等",
        "依据": "第二十六条",
    },
]

# ---------------------------------------------------------------------------
# 节假日报备
# ---------------------------------------------------------------------------

HOLIDAY_REPORTING: dict = {
    "触发条件": "重大节日前3个工作日、节日后3个工作日内，以及节日期间",
    "重大节日": ["元旦", "春节", "清明节", "劳动节", "端午节", "中秋节", "国庆节"],
    "报备要求": "招待发生部门应主动提前向办公室备案并向同级纪委报告",
    "报备材料": "报备邮件及报备附件（报备模板参见附件）",
    "报销时": "节假日业务招待报备资料将作为费用报销的支撑材料",
}

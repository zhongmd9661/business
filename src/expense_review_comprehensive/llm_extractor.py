"""从 OCR 解析的 Markdown 文本中使用本地大模型提取审核所需结构化字段"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from lmdeploy import GenerationConfig, Pipeline, TurbomindEngineConfig

from .models import ExtractedFields

SYSTEM_PROMPT = """\
你是一个专业的财务单据字段提取助手。你的任务是从 OCR 识别的文档文本中提取业务招待费审核所需的结构化字段。

文档来源包括：报销申请单、发票、支付凭证、银行流水、公函、确认单等。

请根据文档内容提取以下字段，以 JSON 格式返回。找不到的字段返回 null。

## 字段清单

### 日期字段（格式 YYYY-MM-DD，找不到则 null）
- reception_date: 招待/接待发生日期
- invoice_date: 发票开具日期
- apply_date: 报销申请日期
- payment_date: 实际支付日期

### 金额字段（浮点数，单位元，找不到则 null）
- invoice_amount: 发票总金额（价税合计）
- actual_amount: 实际报账金额/支付金额
- per_person_amount: 人均费用
- alcohol_price: 酒水价格
- souvenir_amount: 纪念品支出金额

### 数字字段（整数，找不到则 null）
- guest_count: 招待对象（来宾）人数
- companion_count: 陪同方人数

### 字符串字段（找不到则 null）
- handler: 经办人/使用人/提交人姓名
- payee: 收款对象/收款人户名
- personnel_level: 人员级别（"省管中层" / "市管中层" / "其他人员"）
- reception_type: 招待类型（"商务招待" / "外事招待" / "其他公务招待" / "内部业务招待" / "工作餐"）
- host_unit: 招待对象单位名称
- seller_name: 发票销售方名称
- merchant_name: 商户全称（支付凭证中的收款商户）
- department: 申请部门/使用部门
- reimbursement_no: 报账单号/来源系统单号/申请单号
- invoice_no: 发票号码

### 布尔标志（在文档中检测到相关关键词或内容为 true，否则 false）
- payment_voucher_present: 是否存在支付凭证（刷卡单、电子消费凭证、POS单）
- payment_statement_present: 是否存在支付流水证明（银行交易流水、交易单号）
- official_letter_present: 是否存在往来公函
- invoice_verified: 是否进行发票查验/验证
- expense_detail_list_present: 是否存在费用明细清单
- grid_allocation_signed: 是否有网格分摊表签章
- has_alcohol_tobacco: 是否涉及烟、酒相关消费
- bulk_alcohol: 是否批量购买酒水（成箱、整箱等）
- gift_suspected: 是否疑似礼品（购物卡、会员卡、预付卡、现金、名贵特产等）
- tourism_suspected: 是否疑似旅游消费（景点、旅游、演出等）
- is_cash_payment: 是否为现金支付
- has_prepaid: 是否预存签单
- is_holiday_reported: 是否有节假日报备记录

### 列表字段（从文本中匹配到的禁止性关键词，没有则返回空数组）
- forbidden_places: 禁止场所关键词列表（私人会所、一桌餐、高档娱乐、农家乐、烟酒专卖店等）
- forbidden_foods: 禁止食品关键词列表（鱼翅、燕窝、野生保护动物等）

## 重要规则
1. 只从给定的文档文本中提取信息，不编造、不推测
2. 日期统一转为 YYYY-MM-DD 格式
3. 金额去除逗号、货币符号后转为数字
4. 如果同一字段在文档中出现多次，取最合理的一个值
5. 布尔标志基于文档实际内容判断，不要因为没有明确写"是"就判 false——如果有相关消费项目就判 true
6. 返回纯 JSON，不要包裹在 markdown 代码块中，不要加任何额外说明
"""


def _parse_json_response(text: str) -> Optional[dict]:
    """从 LLM 响应中提取 JSON 对象。"""
    text = text.strip()
    # 尝试直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # 处理 markdown 代码块包裹的情况
    if text.startswith("```") and text.endswith("```"):
        inner = text[3:-3]
        if inner.startswith("json\n"):
            inner = inner[5:]
        elif inner.startswith("json"):
            inner = inner[4:]
        try:
            return json.loads(inner.strip())
        except (json.JSONDecodeError, TypeError):
            pass
    # 尝试找 JSON 对象边界
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def _to_datetime(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def _to_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _to_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _to_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.lower() in ("true", "1", "是", "有")
    return False


def _to_list(val) -> list:
    if isinstance(val, list):
        return val
    return []


class LlmFieldExtractor:
    """使用本地大模型从 OCR Markdown 文本中提取业务招待费审核字段。

    完全独立的提取模块，不依赖规则提取器。
    使用 lmdeploy Pipeline 进行本地推理。
    """

    def __init__(self, model_path: str = None):
        self.model_path = model_path or os.environ.get("LLM_MODEL_PATH")
        if not self.model_path:
            raise ValueError(
                "未指定模型路径。请设置 LLM_MODEL_PATH 环境变量或传入 model_path 参数。"
            )
        self._pipe: Optional[Pipeline] = None
        self._gen_config = GenerationConfig(top_p=0.99, top_k=40, temperature=0.1)

    def start(self):
        """启动推理引擎。"""
        tm_config = TurbomindEngineConfig(model_name="qwen2")
        self._pipe = Pipeline(self.model_path, backend_config=tm_config)

    def stop(self):
        """关闭推理引擎。"""
        self._pipe = None

    def extract(self, text: str) -> ExtractedFields:
        """从 OCR Markdown 文本中提取字段。

        Args:
            text: OCR 识别后的 Markdown 文本

        Returns:
            ExtractedFields: 提取结果
        """
        if self._pipe is None:
            raise RuntimeError("调用 extract() 前先调用 start() 启动模型")

        # 截断过长的输入以节省 token
        truncated = text[:15000] if len(text) > 15000 else text

        response = self._pipe(
            system=SYSTEM_PROMPT,
            prompt=truncated,
            gen_config=self._gen_config,
        )

        generated_text = ""
        if response:
            generated_text = response.text

        parsed = _parse_json_response(generated_text)
        if parsed is None:
            return ExtractedFields(raw_text=text)

        return _json_to_fields(parsed, text)


def _json_to_fields(data: dict, raw_text: str) -> ExtractedFields:
    """将 LLM 返回的 JSON 数据转换为 ExtractedFields。"""
    f = ExtractedFields(raw_text=raw_text)

    f.reception_date = _to_datetime(data.get("reception_date"))
    f.invoice_date = _to_datetime(data.get("invoice_date"))
    f.apply_date = _to_datetime(data.get("apply_date"))
    f.payment_date = _to_datetime(data.get("payment_date"))

    f.invoice_amount = _to_float(data.get("invoice_amount"))
    f.actual_amount = _to_float(data.get("actual_amount"))
    f.per_person_amount = _to_float(data.get("per_person_amount"))
    f.alcohol_price = _to_float(data.get("alcohol_price"))
    f.souvenir_amount = _to_float(data.get("souvenir_amount"))

    f.guest_count = _to_int(data.get("guest_count"))
    f.companion_count = _to_int(data.get("companion_count"))

    f.handler = data.get("handler")
    f.payee = data.get("payee")
    f.personnel_level = data.get("personnel_level")
    f.reception_type = data.get("reception_type")
    f.host_unit = data.get("host_unit")
    f.seller_name = data.get("seller_name")
    f.merchant_name = data.get("merchant_name")
    f.department = data.get("department")
    f.reimbursement_no = data.get("reimbursement_no")
    f.invoice_no = data.get("invoice_no")

    f.payment_voucher_present = _to_bool(data.get("payment_voucher_present", False))
    f.payment_statement_present = _to_bool(data.get("payment_statement_present", False))
    f.official_letter_present = _to_bool(data.get("official_letter_present", False))
    f.invoice_verified = _to_bool(data.get("invoice_verified", False))
    f.expense_detail_list_present = _to_bool(data.get("expense_detail_list_present", False))
    f.grid_allocation_signed = _to_bool(data.get("grid_allocation_signed", False))
    f.has_alcohol_tobacco = _to_bool(data.get("has_alcohol_tobacco", False))
    f.bulk_alcohol = _to_bool(data.get("bulk_alcohol", False))
    f.gift_suspected = _to_bool(data.get("gift_suspected", False))
    f.tourism_suspected = _to_bool(data.get("tourism_suspected", False))
    f.is_cash_payment = _to_bool(data.get("is_cash_payment", False))
    f.has_prepaid = _to_bool(data.get("has_prepaid", False))
    f.is_holiday_reported = _to_bool(data.get("is_holiday_reported", False))

    f.forbidden_places = _to_list(data.get("forbidden_places", []))
    f.forbidden_foods = _to_list(data.get("forbidden_foods", []))

    return f

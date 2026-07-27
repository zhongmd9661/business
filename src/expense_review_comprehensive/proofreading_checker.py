"""校对规则检查器 — LLM + 正则双引擎提取，跨文档一致性校验"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

from ..llm_client import LlmClient, extract_text_from_response, llm_messages_create_async

from .models import (
    ExtractedFields,
    BatchFinding,
    RuleCategory,
)

# ---------------------------------------------------------------------------
# 校对规则专用字段定义（LLM 提示词）
# ---------------------------------------------------------------------------

PROOFREADING_FIELD_DEFS = """\
### 日期字段（找不到则 null）
- reception_date: 招待日期（格式 YYYY-MM-DD）
- invoice_date: 开票日期（格式 YYYY-MM-DD）
- payment_date: 支付时间（格式 YYYY-MM-DD HH:MM:SS）
- transaction_date: 交易时间（格式 YYYY-MM-DD HH:MM:SS）
- activity_date: 活动函件交流时间（格式 YYYY-MM-DD）

### 金额字段（浮点数，单位元，找不到则 null）
- invoice_total_uppercase: 价税合计大写金额（提取中文大写，如 捌佰叁拾贰圆整）
- invoice_total_lowercase: 价税合计小写金额（数字）
- approval_amount: 审批单招待金额（数字）
- payment_amount: 支付凭证金额（数字）
- statement_amount: 支付证明交易金额（数字）
- reimbursement_invoice_amount: 报账单发票金额（数字）

### 数字字段（整数，找不到则 null）
- guest_count: 招待人数
- companion_count: 陪同人数

### 字符串字段（找不到则 null）
- per_person_fee: 人均费用
- reception_type: 招待类型
- is_work_meal: 是否工作餐
- host_unit: 招待对象单位名称
- transaction_no: 交易单号
- merchant_order_no: 商户单号
- merchant_full_name: 商户全称/交易对方
"""

PROOFREADING_SYSTEM_PROMPT = """\
你是一个专业的财务单据校对助手。你的任务是从 OCR 识别的文档文本中提取校对规则所需的字段。

请根据文档内容提取以下字段，以 JSON 格式返回。找不到的字段返回 null。

## 字段清单

""" + PROOFREADING_FIELD_DEFS + """

## 重要规则
1. 只从给定的文档文本中提取信息，不编造、不推测
2. 日期统一转为 YYYY-MM-DD 格式
3. 金额去除逗号、货币符号后转为数字
4. 大写金额保留原文（如 捌佰叁拾贰圆整）
5. 返回纯 JSON，不要包裹在 markdown 代码块中

## OCR 误差处理
源文本来自 OCR 识别，可能存在错字、漏字、多余空格等问题。
- "曰" 很可能是 "日" 的 OCR 误差
- "锐" 很可能是 "税" 的 OCR 误差
- "召待" 很可能是 "招待" 的 OCR 误差
- 表格单元格内容可能夹杂 HTML 标签残留，忽略标签只看内容
- 即使键名有 OCR 误差，也要根据上下文语义提取对应的值
- 对于数字和金额，OCR 通常较准确，优先信赖
"""


# ---------------------------------------------------------------------------
# 中文金额大写转数字
# ---------------------------------------------------------------------------

_CN_DIGITS = "零一二三四五六七八九"
_CN_BIG_DIGITS = "零壹贰叁肆伍陆柒捌玖"
_CN_UNITS = [
    ("十", 10), ("百", 100), ("千", 1000), ("万", 10000),
    ("拾", 10), ("佰", 100), ("仟", 1000),
]


def _cn_to_number(text: str) -> Optional[float]:
    """中文大写金额转数字，如 捌佰叁拾贰圆整 -> 832.0"""
    text = text.strip()
    if not text:
        return None

    result = 0.0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _CN_DIGITS or ch in _CN_BIG_DIGITS:
            digit = _CN_DIGITS.index(ch) if ch in _CN_DIGITS else _CN_BIG_DIGITS.index(ch)
            if i + 1 < len(text) and text[i + 1] in dict(_CN_UNITS):
                unit_val = dict(_CN_UNITS)[text[i + 1]]
                result += digit * unit_val
                i += 2
                continue
            result += digit
        elif ch in ("圆", "元", "整"):
            pass
        i += 1

    if result == 0:
        return None
    return result


# ---------------------------------------------------------------------------
# 正则提取辅助
# ---------------------------------------------------------------------------

def _parse_date(text: str) -> Optional[datetime]:
    """从文本中提取日期（含可选时间）"""
    if not text:
        return None
    m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[\sT]*(\d{1,2}):(\d{1,2}):(\d{1,2}))?', text)
    if m:
        try:
            return datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4) or 0), int(m.group(5) or 0), int(m.group(6) or 0),
            )
        except ValueError:
            pass
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日(?:[\s]*(\d{1,2}):(\d{1,2}):(\d{1,2}))?', text)
    if m:
        try:
            return datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4) or 0), int(m.group(5) or 0), int(m.group(6) or 0),
            )
        except ValueError:
            pass
    return None


def _extract_by_key(text: str, key: str) -> Optional[str]:
    """根据键名从 MD 文本中提取值（正则，容忍 OCR 误差）

    策略：
    1. 精确匹配（键名完整出现）
    2. 分词模糊匹配（键名拆成子串，允许中间有内容）
    3. 常见 OCR 错字替换后匹配
    """
    if not text or not key:
        return None

    # 1. 精确匹配
    m = re.search(re.escape(key) + r'[:：]?\s*([^\n\t<]+)', text)
    if m:
        val = _clean_value(m.group(1))
        if val:
            return val

    # 2. 常见 OCR 错字替换 — 尝试文本中可能出现的错字版本
    ocr_error_map = {"日": "曰", "税": "锐", "招": "召", "证": "政", "函": "涵", "凭": "凭"}
    for correct, erroneous in ocr_error_map.items():
        if correct in key:
            variant = key.replace(correct, erroneous)
            m = re.search(re.escape(variant) + r'[:：]?\s*([^\n\t<]+)', text)
            if m:
                val = _clean_value(m.group(1))
                if val:
                    return val

    # 3. 分词匹配：取键名的首尾字符，中间用 .{0,3} 桥接
    if len(key) >= 3:
        parts = [re.escape(key[0])] + [re.escape(c) for c in key[1:-1]] + [re.escape(key[-1])]
        pattern = r'.{0,3}'.join(parts) + r'[:：]?\s*([^\n\t<]+)'
        m = re.search(pattern, text)
        if m:
            val = _clean_value(m.group(1))
            if val:
                return val

    return None


def _clean_value(val: str) -> Optional[str]:
    """清理提取的值"""
    val = val.strip().rstrip(' \t\n\r')
    val = re.sub(r'<[^>]*>', '', val).strip()
    return val if val else None


def _extract_amount(text: str) -> Optional[float]:
    """从文本中提取金额数字"""
    if not text:
        return None
    m = re.search(r'[¥￥\-]?(\d+)\.?\d*', text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _parse_json_response(text: str) -> Optional[dict]:
    """从 LLM 响应中提取 JSON 对象"""
    text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    if text.startswith("```") and text.endswith("```"):
        inner = text[3:-3]
        if inner.startswith("json\n"):
            inner = inner[5:]
        try:
            return json.loads(inner.strip())
        except (json.JSONDecodeError, TypeError):
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except (json.JSONDecodeError, TypeError):
            pass
    return None


# ---------------------------------------------------------------------------
# 文档类型判断
# ---------------------------------------------------------------------------

def _get_doc_type(filename: str) -> str:
    """根据文件名判断文档类型

    文件名关键字：审批单、申请单、报账单、经营状态、支付、函件、发票
    """
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
# 双引擎字段提取（LLM 优先，正则兜底）
# ---------------------------------------------------------------------------

class _ProofreadingFields:
    """单文档的校对专用字段，LLM 和正则提取结果的统一载体"""
    __slots__ = (
        'reception_date', 'invoice_date', 'payment_date', 'transaction_date',
        'activity_date',
        'invoice_total_uppercase', 'invoice_total_lowercase',
        'approval_amount', 'payment_amount', 'statement_amount',
        'reimbursement_invoice_amount',
        'guest_count', 'companion_count',
        'per_person_fee', 'reception_type', 'is_work_meal',
        'host_unit',
        'transaction_no', 'merchant_order_no', 'merchant_full_name',
    )

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)


def _extract_proofreading_fields(
    text: str,
    doc_type: str,
    client: Optional[LlmClient] = None,
    model: str = "qwen/qwen3.6-27b",
) -> _ProofreadingFields:
    """LLM + 正则双引擎提取校对字段。

    策略：先 LLM 提取，LLM 返回 None 的字段由正则兜底。
    """
    pf = _ProofreadingFields()

    # -- 1. LLM 提取 --
    llm_data: dict = {}
    if client and text:
        truncated = text[:15000] if len(text) > 15000 else text
        try:
            response = client.messages_create(
                model=model,
                system=PROOFREADING_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": truncated}],
                temperature=0.1,
                max_tokens=2048,
            )
            generated = response.content[0].text if response.content else ""
            llm_data = _parse_json_response(generated) or {}
        except Exception:
            llm_data = {}

    # 辅助：安全取值
    def _str(key: str) -> Optional[str]:
        v = llm_data.get(key)
        return str(v) if v is not None else None

    def _float(key: str) -> Optional[float]:
        v = llm_data.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    def _int(key: str) -> Optional[int]:
        v = llm_data.get(key)
        if v is None:
            return None
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None

    # -- 2. 赋值（LLM -> 正则兜底）--

    # 日期
    pf.reception_date = _parse_date(_str("reception_date")) or _parse_date(_extract_by_key(text, "招待日期"))
    pf.invoice_date = _parse_date(_str("invoice_date")) or _parse_date(_extract_by_key(text, "开票日期"))
    pf.payment_date = _parse_date(_str("payment_date")) or _parse_date(_extract_by_key(text, "支付时间"))
    pf.transaction_date = _parse_date(_str("transaction_date")) or _parse_date(_extract_by_key(text, "交易时间")) or _parse_date(_extract_by_key(text, "支付时间"))
    pf.activity_date = _parse_date(_str("activity_date")) or _parse_date(_extract_by_key(text, "交流时间"))

    # 金额
    pf.invoice_total_uppercase = _str("invoice_total_uppercase") or _extract_by_key(text, "价税合计（大写)")
    pf.invoice_total_uppercase = pf.invoice_total_uppercase or _extract_by_key(text, "价税合计(大写)")
    pf.invoice_total_lowercase = _float("invoice_total_lowercase") or _extract_amount(_extract_by_key(text, "（小写）¥"))
    pf.approval_amount = _float("approval_amount") or _extract_amount(_extract_by_key(text, "招待金额"))
    pf.payment_amount = _float("payment_amount")
    if pf.payment_amount is None:
        m = re.search(r'#\s*(-?(\d+)\.?\d*)', text)
        pf.payment_amount = float(m.group(2)) if m else None
    pf.statement_amount = _float("statement_amount")
    if pf.statement_amount is None:
        m = re.search(r'金额\(元\).*?(\d+\.\d+)', text)
        pf.statement_amount = float(m.group(1)) if m else None
    pf.reimbursement_invoice_amount = _float("reimbursement_invoice_amount") or _extract_amount(_extract_by_key(text, "发票金额"))

    # 人数
    _gc = _int("guest_count")
    if _gc is None:
        _gc_str = _extract_by_key(text, "招待人数")
        _gc = int(_gc_str) if _gc_str else None
    pf.guest_count = _gc

    _cc = _int("companion_count")
    if _cc is None:
        _cc_str = _extract_by_key(text, "陪同人数")
        _cc = int(_cc_str) if _cc_str else None
    pf.companion_count = _cc

    # 字符串
    pf.per_person_fee = _float("per_person_fee") or _extract_amount(_extract_by_key(text, "人均费用"))
    pf.reception_type = _str("reception_type") or _extract_by_key(text, "招待类型")
    pf.is_work_meal = _str("is_work_meal") or _extract_by_key(text, "是否工作餐")
    pf.host_unit = _str("host_unit") or _extract_by_key(text, "招待对象") or _extract_by_key(text, "招待对象单位") or _extract_by_key(text, "来宾单位")

    # 支付凭证比对字段
    pf.transaction_no = _str("transaction_no") or _extract_by_key(text, "交易单号")
    pf.merchant_order_no = _str("merchant_order_no") or _extract_by_key(text, "商户单号")
    pf.merchant_full_name = _str("merchant_full_name") or _extract_by_key(text, "商户全称") or _extract_by_key(text, "交易对方")

    return pf


# ---------------------------------------------------------------------------
# 校对规则检查器
# ---------------------------------------------------------------------------

class ProofreadingChecker:
    """跨文档一致性校验：金额、日期、招待标准、单位经营状态、支付凭证、活动函件

    Args:
        base_url: LLM API 地址
        api_key: LLM API 密钥
        model: 模型名称
    """

    # 人均费用标准: (人员层级, 招待类型大类) -> 人均上限
    _AMOUNT_LIMITS = {
        ("省管中层", "外事商务"): 400.0,
        ("市管中层", "外事商务"): 300.0,
        ("其他人员", "外事商务"): 250.0,
        ("省管中层", "其他公务"): 250.0,
        ("市管中层", "其他公务"): 200.0,
        ("其他人员", "其他公务"): 150.0,
        ("省管中层", "内部招待"): 150.0,
        ("市管中层", "内部招待"): 150.0,
        ("其他人员", "内部招待"): 100.0,
    }
    _WORK_MEAL_LIMIT = 60.0

    def __init__(
        self,
        client: LlmClient = None,
        base_url: str = None,
        api_key: str = None,
        model: str = None,
    ):
        """
        Args:
            client: 共享的 LlmClient 客户端（推荐，避免重复建连）
            base_url: 不传 client 时的 API 地址
            api_key: 不传 client 时的 API 密钥
            model: 模型名称
        """
        import os
        self._external_client = client
        self._client = client
        self._base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL", "http://192.168.231.1:1235")
        self._api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "lmstudio")
        self._model = model or os.environ.get("LLM_MODEL", "qwen/qwen3.6-27b")

    def start(self):
        """如果没有传入外部客户端，则自建一个"""
        if self._external_client is None:
            self._client = LlmClient(base_url=self._base_url, api_key=self._api_key, model=self._model)
            self._client.start()

    def stop(self):
        """关闭自建的客户端（不关闭外部传入的）"""
        if self._external_client is None and self._client is not None:
            self._client.stop()
            self._client = None

    def check(self, documents: list[tuple[str, ExtractedFields]]) -> tuple[list[BatchFinding], list[tuple[str, str, ExtractedFields, _ProofreadingFields]]]:
        """对同批次所有文档执行校对规则校验

        Returns:
            (findings, extracted_fields) — extracted_fields 用于生成对比表
        """
        # 为每个文档提取校对字段
        extracted: list[tuple[str, str, ExtractedFields, _ProofreadingFields]] = []
        for fname, f in documents:
            doc_type = _get_doc_type(fname)
            pf = _extract_proofreading_fields(
                f.raw_text, doc_type, self._client, self._model
            )
            extracted.append((fname, doc_type, f, pf))

        findings: list[BatchFinding] = []
        findings.extend(self._check_amount_consistency(extracted))
        findings.extend(self._check_date_consistency(extracted))
        findings.extend(self._check_reception_standard(extracted))
        findings.extend(self._check_unit_business_status(extracted))
        findings.extend(self._check_payment_consistency(extracted))
        findings.extend(self._check_activity_letter_date(extracted))
        return findings, extracted

    # -----------------------------------------------------------------------
    # 规则1：金额一致性
    # -----------------------------------------------------------------------

    def _check_amount_consistency(
        self, docs: list[tuple[str, str, ExtractedFields, _ProofreadingFields]]
    ) -> list[BatchFinding]:
        """发票大写金额为标准，其他文档金额必须一致"""
        findings: list[BatchFinding] = []

        standard_amount = None
        for fname, doc_type, _, pf in docs:
            if doc_type == '发票':
                if pf.invoice_total_uppercase:
                    standard_amount = _cn_to_number(pf.invoice_total_uppercase)
                if standard_amount is None and pf.invoice_total_lowercase is not None:
                    standard_amount = pf.invoice_total_lowercase
                if standard_amount is not None:
                    break

        if standard_amount is None:
            return findings

        for fname, doc_type, _, pf in docs:
            if doc_type == '发票':
                continue

            compare_amount = None
            if doc_type == '审批单':
                compare_amount = pf.approval_amount
            elif doc_type == '支付凭证':
                compare_amount = pf.payment_amount
            elif doc_type == '支付证明':
                compare_amount = pf.statement_amount
            elif doc_type == '报账单':
                compare_amount = pf.reimbursement_invoice_amount

            if compare_amount is not None:
                if abs(compare_amount - standard_amount) > 0.01:
                    findings.append(BatchFinding(
                        RuleCategory.PROOFREADING,
                        "金额一致性",
                        "校对规则 规则1",
                        "高",
                        f"金额不一致: {fname} 金额 {compare_amount:.2f} 元与发票标准金额 {standard_amount:.2f} 元不符",
                        document=fname,
                    ))

        return findings

    # -----------------------------------------------------------------------
    # 规则2：日期一致性
    # -----------------------------------------------------------------------

    def _check_date_consistency(
        self, docs: list[tuple[str, str, ExtractedFields, _ProofreadingFields]]
    ) -> list[BatchFinding]:
        """审批单招待日期为基准，校验发票/支付日期逻辑"""
        findings: list[BatchFinding] = []

        reception_date = None
        for fname, doc_type, _, pf in docs:
            if doc_type in ('审批单', '申请单'):
                reception_date = pf.reception_date
                if reception_date:
                    break

        if reception_date is None:
            return findings

        for fname, doc_type, _, pf in docs:
            if doc_type in ('审批单', '申请单'):
                continue

            if doc_type == '发票':
                if pf.invoice_date and pf.invoice_date > reception_date:
                    findings.append(BatchFinding(
                        RuleCategory.PROOFREADING,
                        "日期一致性",
                        "校对规则 规则2",
                        "高",
                        f"发票开票日期({pf.invoice_date.date()})晚于招待日期({reception_date.date()})",
                        document=fname,
                    ))

            elif doc_type == '支付凭证':
                if pf.payment_date and pf.payment_date < reception_date.replace(hour=0, minute=0, second=0):
                    findings.append(BatchFinding(
                        RuleCategory.PROOFREADING,
                        "日期一致性",
                        "校对规则 规则2",
                        "高",
                        f"支付日期({pf.payment_date.date()})早于招待日期({reception_date.date()})",
                        document=fname,
                    ))

            elif doc_type == '支付证明':
                if pf.transaction_date and pf.transaction_date < reception_date.replace(hour=0, minute=0, second=0):
                    findings.append(BatchFinding(
                        RuleCategory.PROOFREADING,
                        "日期一致性",
                        "校对规则 规则2",
                        "高",
                        f"交易日期({pf.transaction_date.date()})早于招待日期({reception_date.date()})",
                        document=fname,
                    ))

        return findings

    # -----------------------------------------------------------------------
    # 规则3：招待标准合规性
    # -----------------------------------------------------------------------

    def _check_reception_standard(
        self, docs: list[tuple[str, str, ExtractedFields, _ProofreadingFields]]
    ) -> list[BatchFinding]:
        """从审批单提取招待人数、陪同人数、人均费用，对照标准表校验"""
        findings: list[BatchFinding] = []

        for fname, doc_type, _, pf in docs:
            if doc_type != '审批单':
                continue

            guest_count = pf.guest_count
            companion_count = pf.companion_count
            per_person = pf.per_person_fee
            reception_type = pf.reception_type
            is_work_meal = pf.is_work_meal

            if guest_count is None or companion_count is None or per_person is None:
                continue

            # 合理性校验 — 防止 LLM 误读（如 "2/5" 读成 25）
            if companion_count > guest_count * 10 or companion_count > 50:
                findings.append(BatchFinding(
                    RuleCategory.PROOFREADING,
                    "招待标准合规性",
                    "校对规则 规则3",
                    "提示",
                    f"陪同人数({companion_count})疑似提取错误，需人工核对",
                    document=fname,
                ))
                continue

            # 陪同人数校验
            if reception_type and '内部' in reception_type:
                limit = 3 if guest_count <= 10 else guest_count // 3
                if companion_count > limit:
                    findings.append(BatchFinding(
                        RuleCategory.PROOFREADING,
                        "招待标准合规性",
                        "校对规则 规则3",
                        "高",
                        f"内部招待陪同人数({companion_count})超过标准({limit})",
                        document=fname,
                    ))
            else:
                limit = guest_count if guest_count <= 5 else guest_count + (guest_count - 5) // 2
                if companion_count > limit:
                    findings.append(BatchFinding(
                        RuleCategory.PROOFREADING,
                        "招待标准合规性",
                        "校对规则 规则3",
                        "高",
                        f"外部招待陪同人数({companion_count})超过标准({limit})",
                        document=fname,
                    ))

            # 人均费用校验
            if reception_type:
                if is_work_meal and '是' in is_work_meal:
                    if per_person > self._WORK_MEAL_LIMIT:
                        findings.append(BatchFinding(
                            RuleCategory.PROOFREADING,
                            "招待标准合规性",
                            "校对规则 规则3",
                            "高",
                            f"工作餐人均费用({per_person}元)超过标准({self._WORK_MEAL_LIMIT}元)",
                            document=fname,
                        ))
                elif '内部' in reception_type:
                    limit = self._AMOUNT_LIMITS.get(("其他人员", "内部招待"), 100.0)
                    if per_person > limit:
                        findings.append(BatchFinding(
                            RuleCategory.PROOFREADING,
                            "招待标准合规性",
                            "校对规则 规则3",
                            "高",
                            f"内部招待人均费用({per_person}元)超过标准({limit}元)",
                            document=fname,
                        ))
                elif '商务' in reception_type or '外事' in reception_type:
                    limit = self._AMOUNT_LIMITS.get(("其他人员", "外事商务"), 250.0)
                    if per_person > limit:
                        findings.append(BatchFinding(
                            RuleCategory.PROOFREADING,
                            "招待标准合规性",
                            "校对规则 规则3",
                            "高",
                            f"外事商务招待人均费用({per_person}元)超过标准({limit}元)",
                            document=fname,
                        ))
                elif '公务' in reception_type:
                    limit = self._AMOUNT_LIMITS.get(("其他人员", "其他公务"), 150.0)
                    if per_person > limit:
                        findings.append(BatchFinding(
                            RuleCategory.PROOFREADING,
                            "招待标准合规性",
                            "校对规则 规则3",
                            "高",
                            f"其他公务招待人均费用({per_person}元)超过标准({limit}元)",
                            document=fname,
                        ))

        return findings

    # -----------------------------------------------------------------------
    # 规则4：招待单位经营状态
    # -----------------------------------------------------------------------

    def _check_unit_business_status(
        self, docs: list[tuple[str, str, ExtractedFields, _ProofreadingFields]]
    ) -> list[BatchFinding]:
        """从审批单提取招待对象，在经营状态文件中判断是否正常"""
        findings: list[BatchFinding] = []

        host_unit = None
        for fname, doc_type, _, pf in docs:
            if doc_type == '审批单':
                host_unit = pf.host_unit
                if host_unit:
                    break

        if not host_unit:
            findings.append(BatchFinding(
                RuleCategory.PROOFREADING,
                "单位经营状态",
                "校对规则 规则4",
                "提示",
                "未能从审批单中提取招待对象单位名称，需人工核对经营状态",
            ))
            return findings

        has_status_doc = False
        for fname, doc_type, ef, _pf in docs:
            if doc_type != '经营状态':
                continue

            has_status_doc = True
            text = ef.raw_text
            keywords = [host_unit]
            if len(host_unit) > 4:
                keywords.append(host_unit[:4])
                keywords.append(host_unit[-4:])

            found = False
            for kw in keywords:
                if kw in text:
                    found = True
                    match_pos = text.find(kw)
                    if match_pos >= 0:
                        after_text = text[match_pos:match_pos + len(kw) + 10]
                        if '正常' in after_text:
                            break
                        summary = after_text[len(kw):len(kw) + 5].strip()
                        findings.append(BatchFinding(
                            RuleCategory.PROOFREADING,
                            "单位经营状态",
                            "校对规则 规则4",
                            "提示",
                            f"招待单位「{host_unit}」经营状态异常: {summary or '未找到正常状态'}，需人工审核",
                            document=fname,
                        ))
                    break

            if not found:
                # 尝试在整个文档中搜索"正常"关键字作为兜底
                if '正常' not in (text or ''):
                    findings.append(BatchFinding(
                        RuleCategory.PROOFREADING,
                        "单位经营状态",
                        "校对规则 规则4",
                        "提示",
                        f"未在经营状态文件中找到「{host_unit}」的相关信息，需人工审核",
                        document=fname,
                    ))

        if not has_status_doc:
            findings.append(BatchFinding(
                RuleCategory.PROOFREADING,
                "单位经营状态",
                "校对规则 规则4",
                "提示",
                f"批次中未找到经营状态文档，无法校验招待单位「{host_unit}」经营状态",
            ))

        return findings

    # -----------------------------------------------------------------------
    # 规则5：支付凭证一致性
    # -----------------------------------------------------------------------

    def _check_payment_consistency(
        self, docs: list[tuple[str, str, ExtractedFields, _ProofreadingFields]]
    ) -> list[BatchFinding]:
        """支付凭证与支付证明的关键字段比对"""
        findings: list[BatchFinding] = []

        voucher_pf = None
        voucher_doc = None
        statement_pf = None
        statement_doc = None

        for fname, doc_type, _, pf in docs:
            if doc_type == '支付凭证' and voucher_pf is None:
                voucher_pf = pf
                voucher_doc = fname
            if doc_type == '支付证明' and statement_pf is None:
                statement_pf = pf
                statement_doc = fname

        if voucher_pf is None or statement_pf is None:
            return findings

        field_map = {
            '交易单号': (voucher_pf.transaction_no, statement_pf.transaction_no),
            '商户单号': (voucher_pf.merchant_order_no, statement_pf.merchant_order_no),
            '商户名称': (voucher_pf.merchant_full_name, statement_pf.merchant_full_name),
        }

        for label, (v_val, s_val) in field_map.items():
            if v_val is not None and s_val is not None:
                if str(v_val).strip() != str(s_val).strip():
                    findings.append(BatchFinding(
                        RuleCategory.PROOFREADING,
                        "支付凭证一致性",
                        "校对规则 规则5",
                        "高",
                        f"{label}不一致: 支付凭证「{v_val}」vs 支付证明「{s_val}」",
                        document=voucher_doc or '',
                    ))

        if voucher_pf.payment_date and statement_pf.transaction_date:
            if voucher_pf.payment_date.date() != statement_pf.transaction_date.date():
                findings.append(BatchFinding(
                    RuleCategory.PROOFREADING,
                    "支付凭证一致性",
                    "校对规则 规则5",
                    "高",
                    f"交易日期不一致: 支付凭证「{voucher_pf.payment_date.date()}」vs 支付证明「{statement_pf.transaction_date.date()}」",
                    document=voucher_doc or '',
                ))

        return findings

    # -----------------------------------------------------------------------
    # 规则6：活动函件日期一致性
    # -----------------------------------------------------------------------

    def _check_activity_letter_date(
        self, docs: list[tuple[str, str, ExtractedFields, _ProofreadingFields]]
    ) -> list[BatchFinding]:
        """活动函件日期与招待日期应在 ±7 天范围内"""
        findings: list[BatchFinding] = []

        reception_date = None
        for fname, doc_type, _, pf in docs:
            if doc_type == '审批单':
                reception_date = pf.reception_date
                if reception_date:
                    break

        if reception_date is None:
            return findings

        for fname, doc_type, _, pf in docs:
            if doc_type != '活动函件':
                continue

            if pf.activity_date:
                day_diff = abs((pf.activity_date - reception_date).days)
                if day_diff > 7:
                    findings.append(BatchFinding(
                        RuleCategory.PROOFREADING,
                        "活动函件日期",
                        "校对规则 规则6",
                        "中",
                        f"活动函件日期({pf.activity_date.date()})与招待日期({reception_date.date()})相差{day_diff}天，超出合理范围(±7天)",
                        document=fname,
                    ))

        return findings

"""从 OCR 解析的 Markdown 文本中提取审核所需结构化字段"""
from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Optional

from .models import (
    ExtractedFields,
    FORBIDDEN_PLACES,
    FORBIDDEN_FOODS,
    ALCOHOL_TOBACCO,
    BULK_PURCHASE,
    GIFT_KEYWORDS,
    TOURISM_KEYWORDS,
)


def _parse_table_kv(text: str) -> dict[str, str]:
    """从 HTML 表格中提取键值对。

    OCR 输出的 Markdown 包含两种 HTML 表格：
    1. KV 行：每个 <tr> 内按 标签1, 值1, 标签2, 值2, ... 排列 → 水平配对
    2. 标准表：第 1 行=列名，第 2 行=数据 → 垂直配对

    标题行（仅一个非空单元格）会被跳过。
    """
    result: dict[str, str] = {}
    tables = re.findall(r'<table>(.*?)</table>', text, re.DOTALL)
    for table in tables:
        rows = re.findall(r'<tr>(.*?)</tr>', table, re.DOTALL)
        cleaned_rows: list[list[str]] = []
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            cleaned: list[str] = []
            for cell in cells:
                plain = re.sub(r'<[^>]+>', '', cell)
                plain = html.unescape(plain).strip()
                if plain:
                    cleaned.append(plain)
            cleaned_rows.append(cleaned)

        i = 0
        while i < len(cleaned_rows):
            row = cleaned_rows[i]
            # 跳过全空行和标题行
            non_empty = [c for c in row if c]
            if len(non_empty) <= 1:
                i += 1
                continue

            # 检测标准表：当前行=纯文本列名，下一行=数值数据 → 垂直配对
            if (i + 1 < len(cleaned_rows)
                    and len([c for c in cleaned_rows[i + 1] if c]) >= 3
                    and len(row) >= 3
                    and _is_plain_text_row(non_empty)
                    and _is_data_row([c for c in cleaned_rows[i + 1] if c])):
                headers = row
                data = cleaned_rows[i + 1]
                for j in range(min(len(headers), len(data))):
                    if headers[j] and data[j]:
                        result[headers[j]] = data[j]
                i += 2
                continue

            # 默认：水平 KV 配对
            pair_count = len(row) // 2
            for j in range(0, pair_count * 2, 2):
                if row[j]:
                    result[row[j]] = row[j + 1] if j + 1 < len(row) else ""
            i += 1

    return result


def _parse_markdown_tables(text: str) -> dict[str, str]:
    """从 Markdown 表格（| 项目 | 内容 |）中提取键值对。

    OCR 输出的发票文档使用 Markdown 表格而非 HTML 表格：
    | 发票号码 | 26442000002098662676 |
    | 开票日期 | 2026-02-27 |
    """
    result: dict[str, str] = {}
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]  # remove empty from leading/trailing |
        if len(cells) >= 2:
            key = cells[0].strip()
            value = cells[1].strip()
            if key and value and not key.isdigit():
                result[key] = value
    return result


def _is_plain_text_row(cells: list[str]) -> bool:
    """判断一行是否主要是非数值文本（列名特征而非 KV 值特征）。"""
    numeric_pat = re.compile(r'^-?\d')
    numeric_count = sum(1 for c in cells if numeric_pat.match(c))
    total = len(cells)
    return (total > 0 and numeric_count / total < 0.3)


def _is_data_row(cells: list[str]) -> bool:
    """判断一行是否是数值/短文本数据行（标准表的数据特征）。

    要求：
    - 多数单元格匹配数据模式（数值、日期、短文本）
    - 至少有部分单元格是数值型的（排除纯文本 KV 行）
    """
    if not cells:
        return False
    numeric_pat = re.compile(r'^-?[\d,]+\.?\d*')
    short_text = re.compile(r'^.{1,3}$')
    date_pat = re.compile(r'^\d{4}[-/]')
    data_count = 0
    numeric_count = 0
    for c in cells:
        is_numeric = bool(numeric_pat.match(c))
        is_date = bool(date_pat.match(c))
        is_short = bool(short_text.match(c))
        if is_numeric or is_date or is_short:
            data_count += 1
        if is_numeric or is_date:
            numeric_count += 1
    total = len(cells)
    # 需要多数是数据，且至少有部分数值型单元格
    return (data_count / total > 0.5) and (numeric_count / total >= 0.15)


def _parse_int(s: str) -> Optional[int]:
    m = re.search(r'\d+', s)
    return int(m.group()) if m else None


def _parse_amount(s: str) -> Optional[float]:
    m = re.search(r'[\d,]+\.?\d*', s)
    if not m:
        return None
    try:
        return float(m.group().replace(',', ''))
    except ValueError:
        return None


def _parse_date(s: str) -> Optional[datetime]:
    s = s.strip()
    # 处理 OCR 输出中日期和时间之间缺少空格的情况: "2026-02-2720:52:04"
    m = re.match(r'(\d{4}-\d{2}-\d{2})(\d{2}:\d{2}:\d{2})', s)
    if m:
        s = f"{m.group(1)} {m.group(2)}"
    # 处理中文日期+时间: "2026年2月27日20:52:04"
    m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日(\d{1,2}):(\d{1,2}):(\d{1,2})', s)
    if m:
        s = f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:{m.group(6)}"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d", "%Y年%m月%d日", "%Y-%m", "%Y/%m"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


class FieldExtractor:
    """从 Markdown 文本中提取业务招待费审核所需字段。"""

    def extract(self, text: str) -> ExtractedFields:
        f = ExtractedFields(raw_text=text)
        raw_kv = _parse_table_kv(text)
        raw_kv.update(_parse_markdown_tables(text))
        # 规范化键名：去掉尾部中文/英文冒号，解决 OCR 输出不一致问题
        kv = {}
        for k, v in raw_kv.items():
            nk = k.rstrip("：:")
            if nk and nk not in kv:
                kv[nk] = v

        def get(*keys: str, fallback_pat: Optional[str] = None) -> Optional[str]:
            for k in keys:
                if k in kv and kv[k]:
                    return kv[k]
            # 如果表格中没找到或值为空，尝试从纯文本中匹配
            if fallback_pat:
                m = re.search(fallback_pat, text)
                if m:
                    return m.group(1).strip()
            return None

        # ---- 日期 ----
        d = get("接待日期", "招待日期",
                fallback_pat=r"(?:接待|招待)日期[：:]\s*([\d\-/年月日]+)")
        if d:
            f.reception_date = _parse_date(d)

        d = get("开票日期",
                fallback_pat=r"开票日期[：:]\s*([\d\-/年月日]+)")
        if d:
            f.invoice_date = _parse_date(d)

        d = get("申请日期",
                fallback_pat=r"申请日期[：:]\s*([\d\-/年月日]+)")
        if d:
            f.apply_date = _parse_date(d)

        d = get("支付日期",
                fallback_pat=r"支付日期[：:]\s*([\d\-/年月日]+)")
        if d:
            f.payment_date = _parse_date(d)

        # ---- 金额 ----
        a = get("发票总金额", "发票金额",
                fallback_pat=r"(?:发票总金额|发票金额|价税合计|[¥￥])\s*([\d,]+\.?\d*)")
        if a:
            f.invoice_amount = _parse_amount(a)

        a = get("报账总金额", "本次应支付金额", "预计支出金额", "宴请支出",
                "报账金额", "招待金额",
                fallback_pat=r"(?:报账总金额|报账金额|（小写）[¥￥])\s*([\d,]+\.?\d*)")
        if a:
            f.actual_amount = _parse_amount(a)

        a = get("人均", "人均费用",
                fallback_pat=r"人均[：:]\s*([\d,]+\.?\d*)")
        if a:
            f.per_person_amount = _parse_amount(a)

        a = get("酒水价格",
                fallback_pat=r"酒水价格[：:]\s*([\d,]+\.?\d*)")
        if a:
            f.alcohol_price = _parse_amount(a)

        a = get("纪念品支出", "纪念品金额",
                fallback_pat=r"纪念品支出[：:]\s*([\d,]+\.?\d*)")
        if a:
            f.souvenir_amount = _parse_amount(a)

        # ---- 人数 ----
        v = get("来宾人数", "招待对象人数", "招待人数",
                fallback_pat=r"(?:来宾|招待对象)人数[：:]\s*(\d+)")
        if v:
            f.guest_count = _parse_int(v)

        v = get("陪同人数",
                fallback_pat=r"陪同人数[：:]\s*(\d+)")
        if v:
            f.companion_count = _parse_int(v)

        # ---- 字符串字段 ----
        f.handler = get("使用人", "经办人", "创建人", "报账人", "提交人")
        f.payee = get("收款账号户名", "收款对象", "收款人")
        f.department = get("使用部门", "创建部门", "需求部门", "负责招待部门")
        f.host_unit = get("来宾单位", "招待单位", "招待对象")
        f.seller_name = get("销售方名称", "销售方信息", "发票销方", "名称")
        f.merchant_name = get("商户全称", "商户")
        f.reimbursement_no = get("来源系统单号", "结算单号", "申请单号",
                                 fallback_pat=r"来源系统单号[：:]\s*(\S+)")
        f.invoice_no = get("发票号码",
                           fallback_pat=r"发票号码[：:]\s*(\d+)")
        f.transaction_no = get("交易单号",
                               fallback_pat=r"交易单号[：:]\s*(\S+)")
        f.merchant_order_no = get("商户单号",
                                  fallback_pat=r"商户单号[：:]\s*(\S+)")

        # ---- 人员级别 ----
        level = get("职务")
        if level:
            if "省管" in level:
                f.personnel_level = "省管中层"
            elif "市管" in level:
                f.personnel_level = "市管中层"
            else:
                f.personnel_level = "其他人员"

        # ---- 招待类型 ----
        rtype = get("招待类型")
        if rtype:
            if "商务" in rtype:
                f.reception_type = "商务招待"
            elif "外事" in rtype:
                f.reception_type = "外事招待"
            elif "其他公务" in rtype:
                f.reception_type = "其他公务招待"
            elif "内部" in rtype:
                f.reception_type = "内部业务招待"
            elif "工作餐" in rtype:
                f.reception_type = "工作餐"

        # ---- 布尔标志：直接在原始文本中搜索关键词 ----
        f.payment_voucher_present = self._has(text, r"支付凭证", r"刷卡单", r"电子消费凭证", r"POS机", r"互联网支付")
        f.payment_statement_present = self._has(text, r"支付流水", r"交易流水", r"银行流水", r"交易单号")
        f.official_letter_present = self._has(text, r"公函", r"往来公函")
        f.invoice_verified = self._has(text, r"发票查验", r"发票验证", r"发票校验", r"系统校验")
        f.expense_detail_list_present = self._has(text, r"费用明细", r"明细清单", r"招待明细")
        f.grid_allocation_signed = self._has(text, r"网格分摊.*签章", r"分摊表.*签字")

        # ---- 禁止性关键词 ----
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

        # ---- 支付方式 ----
        f.is_cash_payment = self._has(text, r"现金支付", r"现金结算")
        f.has_prepaid = self._has(text, r"预存", r"签单", r"后续签单")

        # ---- 节假日报备 ----
        f.is_holiday_reported = self._has(text, r"备案", r"报备", r"纪委报告", r"报备资料")

        return f

    @staticmethod
    def _has(text: str, *patterns: str) -> bool:
        for pat in patterns:
            if re.search(pat, text):
                return True
        return False

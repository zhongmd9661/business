"""审核服务引擎 — 字段提取 + 审核规则校验 + 报告生成"""
import asyncio
import json
import os
import re
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from sqlalchemy.orm import Session

from .models_db import ExtractedField, ReviewResult, OCRRecord, ReceptionRecord, ExtractionRule, AuditRule

logger = logging.getLogger(__name__)

# ===================================================================
# 9个槽位定义
# ===================================================================

SLOTS = [
    {"index": 0, "name": "审批单", "label": "业务招待审批单", "rule": "approval_extraction"},
    {"index": 1, "name": "申请单", "label": "业务招待申请单", "rule": "application_extraction"},
    {"index": 2, "name": "报账单", "label": "业务招待费报账单", "rule": "reimbursement_extraction"},
    {"index": 3, "name": "发票XML", "label": "发票（XML格式）", "rule": "invoice_extraction"},
    {"index": 4, "name": "发票PDF", "label": "电子发票（PDF格式）", "rule": "invoice_extraction"},
    {"index": 5, "name": "经营状态", "label": "招待单位经营状态", "rule": "business_status_extraction"},
    {"index": 6, "name": "支付凭证", "label": "支付凭证", "rule": "payment_extraction"},
    {"index": 7, "name": "支付流水", "label": "支付流水证明", "rule": "payment_flow_extraction"},
    {"index": 8, "name": "活动函件", "label": "活动函件", "rule": "event_extraction"},
]

SLOT_NAMES = [s["name"] for s in SLOTS]

# ===================================================================
# 规则缓存：从数据库加载的提取规则，60 秒过期
# ===================================================================

_rule_cache: dict[str, tuple[list[dict], float]] = {}
_RULE_CACHE_TTL = 60  # 秒


def _load_rule_from_db(slot_name: str) -> Optional[list[dict]]:
    """从数据库加载提取规则，带缓存"""
    now = time.time()
    if slot_name in _rule_cache:
        fields, ts = _rule_cache[slot_name]
        if now - ts < _RULE_CACHE_TTL:
            return fields

    try:
        from .models_db import SessionLocal
        db = SessionLocal()
        try:
            rule = db.query(ExtractionRule).filter(
                ExtractionRule.slot_name == slot_name,
                ExtractionRule.enabled == True,
            ).first()
            if rule and rule.fields_json:
                fields = json.loads(rule.fields_json)
                _rule_cache[slot_name] = (fields, now)
                return fields
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to load extraction rule for {slot_name}: {e}")
    return None


def _clear_rule_cache():
    """清空规则缓存（规则修改后调用）"""
    _rule_cache.clear()


# ===================================================================
# 字段提取引擎
# ===================================================================

def extract_from_markdown(markdown: str, rule_name: str, slot_name: str = "", method: str = "rule") -> dict[str, Any]:
    """从 OCR markdown 文本中提取字段

    支持两种提取方式：
    - "rule": 基于关键词规则的提取（默认）
    - "llm": 使用大模型提取

    优先使用数据库中的规则配置，如找不到则回退到 Python 硬编码函数
    支持：键值对匹配、表格单元格匹配、正则表达式、模糊文本匹配
    """
    if not markdown or not markdown.strip():
        return {}

    if method == "llm":
        try:
            return extract_from_llm(markdown, slot_name)
        except Exception as e:
            logger.warning(f"LLM extraction failed for {slot_name}: {e}, falling back to rule-based")
            # LLM 失败时回退到规则提取
            pass

    md = markdown.strip()

    # 优先从数据库加载规则
    if slot_name:
        db_fields = _load_rule_from_db(slot_name)
        if db_fields:
            try:
                return _extract_from_json_rule(md, db_fields)
            except Exception as e:
                logger.warning(f"DB rule extraction failed for {slot_name}: {e}, falling back")

    # 回退到 Python 硬编码函数
    extractors = {
        "approval_extraction": _extract_approval,
        "application_extraction": _extract_application,
        "reimbursement_extraction": _extract_reimbursement,
        "invoice_extraction": _extract_invoice,
        "business_status_extraction": _extract_business_status,
        "payment_extraction": _extract_payment,
        "payment_flow_extraction": _extract_payment_flow,
        "event_extraction": _extract_event,
    }

    func = extractors.get(rule_name)
    if func is None:
        return {}

    try:
        return func(md)
    except Exception as e:
        logger.warning(f"Extraction failed for rule {rule_name}: {e}")
        return {}


def extract_from_llm(markdown: str, slot_name: str) -> dict[str, Any]:
    """使用大模型从 OCR markdown 文本中提取字段

    从数据库加载字段定义，构建提示词，调用 LLM API 进行提取。
    """
    if not markdown or not markdown.strip():
        return {}

    # 从数据库加载字段定义
    fields = _load_rule_from_db(slot_name)
    if not fields:
        logger.warning(f"No field definition found for slot {slot_name} in LLM extraction")
        return {}

    # 查找槽位标签
    slot_label = slot_name
    for s in SLOTS:
        if s["name"] == slot_name:
            slot_label = s["label"]
            break

    # 构建字段描述
    field_descs = []
    field_types = {}
    for field in fields:
        name = field.get("name", "")
        field_type = field.get("type", "text")
        if name:
            field_descs.append(f"- \"{name}\" (类型: {field_type})")
            field_types[name] = field_type

    # 构建示例 JSON 结构
    example_json = "{" + ", ".join(f'"{f.get("name", "")}": ""' for f in fields if f.get("name")) + "}"

    # 检查是否有自定义提示词模板
    rule = None
    try:
        from .models_db import SessionLocal as SL
        db_tmp = SL()
        try:
            rule = db_tmp.query(ExtractionRule).filter(
                ExtractionRule.slot_name == slot_name,
                ExtractionRule.enabled == True,
            ).first()
        finally:
            db_tmp.close()
    except Exception:
        pass

    if rule and rule.llm_prompt_template:
        # 使用自定义提示词模板，支持 {markdown} 占位符
        system_prompt = "你是一个文档信息提取助手。"
        user_prompt = rule.llm_prompt_template.replace("{markdown}", markdown.strip()).replace("{slot_name}", slot_name).replace("{slot_label}", slot_label)
    else:
        system_prompt = "你是一个文档信息提取助手。请从 OCR 识别的文本中提取指定字段，并以 JSON 格式返回结果。"
        user_prompt = f"""请从以下 OCR 识别文本中提取指定字段。

文档类型：{slot_label}（{slot_name}）
需要提取的字段：
{chr(10).join(field_descs)}

注意：
- 如果某个字段在文本中找不到，该字段值设为 null
- 日期格式统一为 YYYY-MM-DD
- 数字字段提取纯数值（不含千分位分隔符和货币符号）
- 请仅返回 JSON 格式的结果，不要包含任何其他文字说明
- JSON 格式示例：{example_json}

OCR 文本内容：
---
{markdown.strip()}
---"""

    # 读取 LLM 配置
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "http://192.168.231.1:1235")
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "lmstudio")
    model = os.environ.get("LLM_MODEL", "Qwen/Qwen3.6-27B")
    temperature = float(os.environ.get("LLM_LLM_EXTRACT_TEMPERATURE", "0.1"))
    max_tokens = int(os.environ.get("LLM_LLM_EXTRACT_MAX_TOKENS", "4096"))

    logger.info(f"LLM extraction: slot={slot_name}, base_url={base_url}, model={model}")

    try:
        # 在同步上下文中运行异步调用
        from src.llm_client import llm_messages_create_async, extract_text_from_response

        loop = asyncio.new_event_loop()
        try:
            response_data = loop.run_until_complete(
                llm_messages_create_async(
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=temperature,
                )
            )
        finally:
            loop.close()

        text = extract_text_from_response(response_data)
        if not text:
            logger.warning(f"LLM returned empty response for {slot_name}")
            return {}

        # 尝试从响应中提取 JSON（处理可能包含 ```json 标记的情况）
        import re as _re
        json_match = _re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, _re.DOTALL)
        if json_match:
            text = json_match.group(1)

        result = json.loads(text.strip())
        if not isinstance(result, dict):
            logger.warning(f"LLM returned non-dict JSON for {slot_name}")
            return {}

        # 对字段进行类型转换
        for name, ftype in field_types.items():
            val = result.get(name)
            if val is None:
                continue
            if ftype == "number":
                if isinstance(val, str):
                    result[name] = _extract_number(val)
                elif isinstance(val, (int, float)):
                    result[name] = float(val)
            elif ftype == "date":
                if isinstance(val, str):
                    result[name] = _parse_date(val)

        # 保存完整文本回复
        result["_llm_raw_text"] = text
        result["_llm_text"] = text
        logger.info(f"LLM extraction success for {slot_name}: {len(result)} fields")
        return result

    except Exception as e:
        logger.error(f"LLM extraction failed for {slot_name}: {e}")
        return {}


async def extract_from_llm_async(markdown: str, slot_name: str) -> dict[str, Any]:
    """异步版本：使用大模型从 OCR markdown 文本中提取字段"""
    if not markdown or not markdown.strip():
        return {}

    # 从数据库加载字段定义
    fields = _load_rule_from_db(slot_name)
    if not fields:
        logger.warning(f"No field definition found for slot {slot_name} in LLM extraction")
        return {}

    # 查找槽位标签
    slot_label = slot_name
    for s in SLOTS:
        if s["name"] == slot_name:
            slot_label = s["label"]
            break

    # 构建字段描述
    field_descs = []
    field_types = {}
    for field in fields:
        name = field.get("name", "")
        field_type = field.get("type", "text")
        if name:
            field_descs.append(f"- \"{name}\" (类型: {field_type})")
            field_types[name] = field_type

    # 构建示例 JSON 结构
    example_json = "{" + ", ".join(f'"{f.get("name", "")}": ""' for f in fields if f.get("name")) + "}"

    # 检查是否有自定义提示词模板
    rule = None
    try:
        from .models_db import SessionLocal as SL
        db_tmp = SL()
        try:
            rule = db_tmp.query(ExtractionRule).filter(
                ExtractionRule.slot_name == slot_name,
                ExtractionRule.enabled == True,
            ).first()
        finally:
            db_tmp.close()
    except Exception:
        pass

    if rule and rule.llm_prompt_template:
        # 使用自定义提示词模板，支持 {markdown} 占位符
        system_prompt = "你是一个文档信息提取助手。"
        user_prompt = rule.llm_prompt_template.replace("{markdown}", markdown.strip()).replace("{slot_name}", slot_name).replace("{slot_label}", slot_label)
    else:
        system_prompt = "你是一个文档信息提取助手。请从 OCR 识别的文本中提取指定字段，并以 JSON 格式返回结果。"
        user_prompt = f"""请从以下 OCR 识别文本中提取指定字段。

文档类型：{slot_label}（{slot_name}）
需要提取的字段：
{chr(10).join(field_descs)}

注意：
- 如果某个字段在文本中找不到，该字段值设为 null
- 日期格式统一为 YYYY-MM-DD
- 数字字段提取纯数值（不含千分位分隔符和货币符号）
- 请仅返回 JSON 格式的结果，不要包含任何其他文字说明
- JSON 格式示例：{example_json}

OCR 文本内容：
---
{markdown.strip()}
---"""

    # 读取 LLM 配置
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "http://192.168.231.1:1235")
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "lmstudio")
    model = os.environ.get("LLM_MODEL", "Qwen/Qwen3.6-27B")
    temperature = float(os.environ.get("LLM_LLM_EXTRACT_TEMPERATURE", "0.1"))
    max_tokens = int(os.environ.get("LLM_LLM_EXTRACT_MAX_TOKENS", "4096"))

    logger.info(f"LLM extraction (async): slot={slot_name}, base_url={base_url}, model={model}")

    try:
        from src.llm_client import llm_messages_create_async, extract_text_from_response

        response_data = await llm_messages_create_async(
            base_url=base_url,
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
        )

        text = extract_text_from_response(response_data)
        if not text:
            logger.warning(f"LLM returned empty response for {slot_name}")
            return {}

        # 尝试从响应中提取 JSON
        import re as _re
        json_match = _re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, _re.DOTALL)
        if json_match:
            text = json_match.group(1)

        result = json.loads(text.strip())
        if not isinstance(result, dict):
            logger.warning(f"LLM returned non-dict JSON for {slot_name}")
            return {}

        # 对字段进行类型转换
        for name, ftype in field_types.items():
            val = result.get(name)
            if val is None:
                continue
            if ftype == "number":
                if isinstance(val, str):
                    result[name] = _extract_number(val)
                elif isinstance(val, (int, float)):
                    result[name] = float(val)
            elif ftype == "date":
                if isinstance(val, str):
                    result[name] = _parse_date(val)

        # 保存完整文本回复
        result["_llm_raw_text"] = text
        result["_llm_text"] = text
        logger.info(f"LLM extraction (async) success for {slot_name}: {len(result)} fields")
        return result

    except Exception as e:
        logger.error(f"LLM extraction (async) failed for {slot_name}: {e}")
        return {}


# 异步提取任务管理
_extract_tasks: dict[str, dict] = {}


async def _run_async_extract(serial_number: str):
    """后台异步执行 LLM 提取"""
    from .models_db import SessionLocal
    db = SessionLocal()
    try:
        record = db.query(ReceptionRecord).filter(
            ReceptionRecord.serial_number == serial_number
        ).first()
        if not record:
            return

        # 更新状态为提取中
        record.ocr_status = "extracting"
        record.review_status = "pending"
        db.commit()

        results = []
        for slot in SLOTS:
            ocr = (
                db.query(OCRRecord)
                .filter(OCRRecord.serial_number == serial_number, OCRRecord.slot_name == slot["name"])
                .order_by(OCRRecord.created_at.desc())
                .first()
            )
            if not ocr or not ocr.markdown:
                results.append({"slot_name": slot["name"], "status": "skipped", "reason": "无 OCR 数据"})
                continue

            try:
                extracted = await extract_from_llm_async(ocr.markdown, slot["name"])
                # 过滤 _llm_raw_text 字段，单独保存完整文本
                raw_text = extracted.pop("_llm_raw_text", "")
                extracted_json = json.dumps(extracted, ensure_ascii=False)

                # 更新或创建提取记录
                existing_ef = (
                    db.query(ExtractedField)
                    .filter(ExtractedField.serial_number == serial_number, ExtractedField.slot_name == slot["name"])
                    .order_by(ExtractedField.created_at.desc())
                    .first()
                )
                if existing_ef:
                    existing_ef.extracted_json = extracted_json
                    existing_ef.status = "extracted"
                    existing_ef.extraction_rule = f"llm_{slot['rule']}"
                    existing_ef.updated_at = datetime.now().isoformat()
                else:
                    ef = ExtractedField(
                        serial_number=serial_number,
                        slot_name=slot["name"],
                        ocr_record_id=ocr.id,
                        extracted_json=extracted_json,
                        extraction_rule=f"llm_{slot['rule']}",
                        status="extracted",
                    )
                    db.add(ef)
                db.commit()
                results.append({"slot_name": slot["name"], "status": "success", "fields": extracted})
            except Exception as e:
                logger.error(f"Async extraction failed for {slot['name']}: {e}")
                results.append({"slot_name": slot["name"], "status": "error", "reason": str(e)})

        # 更新状态
        record.ocr_status = "completed"
        db.commit()
        _extract_tasks[serial_number] = {"status": "completed", "results": results}

    except Exception as e:
        logger.error(f"Async extraction failed for {serial_number}: {e}")
        _extract_tasks[serial_number] = {"status": "error", "error": str(e)}
    finally:
        db.close()


def _extract_from_json_rule(md: str, fields: list[dict]) -> dict[str, Any]:
    """从 JSON 规则定义执行字段提取"""
    result = {}
    for field in fields:
        name = field.get("name", "")
        keywords = field.get("keywords", [])
        field_type = field.get("type", "text")

        if not name or not keywords:
            continue

        value = _kv_extract(md, keywords)

        if field_type == "number":
            value = _extract_number(value)
        elif field_type == "date":
            value = _parse_date(value)

        result[name] = value
    return result


def _kv_extract(md: str, key_patterns: list[str]) -> Optional[str]:
    """从键值对格式提取值。支持 key: value, key = value, | key | value | 等格式"""
    for pattern in key_patterns:
        # 键值对: "key: value" or "key = value"
        regex_kv = re.compile(
            rf"(?:^|\||[\r\n])\s*{re.escape(pattern)}\s*[:\s=：]+\s*(.+?)(?:\s*$|\s*\|)",
            re.MULTILINE | re.IGNORECASE,
        )
        m = regex_kv.search(md)
        if m:
            val = m.group(1).strip().rstrip("|").strip()
            if val:
                return val
    return None


def _table_cell_extract(md: str, row_key: str, col_key: str = None) -> Optional[str]:
    """从 markdown 表格中提取单元格值"""
    lines = md.split("\n")
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if row_key in cells:
            idx = cells.index(row_key)
            # 同一行后面的值
            if idx + 1 < len(cells):
                return cells[idx + 1]
            # 下一行的对应列
            if col_key and i + 1 < len(lines):
                next_cells = [c.strip() for c in lines[i + 1].split("|") if c.strip()]
                if idx < len(next_cells):
                    return next_cells[idx]
    return None


def _extract_number(text: str) -> Optional[float]:
    """从文本中提取数字"""
    if not text:
        return None
    m = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
    if m:
        try:
            return float(m.group())
        except ValueError:
            pass
    return None


def _cn_amount_to_num(text: str) -> Optional[float]:
    """中文大写金额转数字"""
    if not text:
        return None
    cn_map = {
        "零": 0, "壹": 1, "壹": 1, "贰": 2, "贰": 2, "参": 3, "叁": 3,
        "肆": 4, "肆": 4, "伍": 5, "陆": 6, "陆": 6, "柒": 7, "柒": 7,
        "捌": 8, "捌": 8, "玖": 9, "玖": 9, "拾": 10, "佰": 100,
        "百": 100, "仟": 1000, "千": 1000, "万": 10000,
    }
    # 先尝试提取小写金额
    m = re.search(r"[¥￥]?\s*([\d,]+\.?\d*)", text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    # 中文大写金额简化处理
    nums = ""
    for ch in text:
        if ch in cn_map:
            nums += str(cn_map[ch])
        elif ch.isdigit():
            nums += ch
    if nums:
        try:
            return float(nums)
        except ValueError:
            pass
    return None


def _parse_date(text: str) -> Optional[str]:
    """解析日期文本，返回 YYYY-MM-DD 格式"""
    if not text:
        return None
    # 2026年02月27日
    m = re.search(r"(\d{4})[年.\/-](\d{1,2})[月.\/-](\d{1,2})日?", text)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    # 2026-02-27
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    return None


# ---- 各槽位提取器 ----

def _extract_approval(md: str) -> dict:
    """审批单提取"""
    return {
        "招待日期": _parse_date(_kv_extract(md, ["招待日期", "日期"])),
        "招待人数": _extract_number(_kv_extract(md, ["招待人数", "对象人数", "招待对象人数"])),
        "陪同人数": _extract_number(_kv_extract(md, ["陪同人数", "陪同"])),
        "人均费用": _extract_number(_kv_extract(md, ["人均费用", "人均", "人均消费"])),
        "招待金额": _extract_number(_kv_extract(md, ["招待金额", "金额", "预算金额"])),
        "招待类型": _kv_extract(md, ["招待类型", "类型", "业务类型"]),
        "招待对象": _kv_extract(md, ["招待对象", "对象单位", "招待单位", "对方单位"]),
        "陪同人员": _kv_extract(md, ["陪同人员", "陪同"]),
        "事由": _kv_extract(md, ["事由", "事由及内容"]),
    }


def _extract_application(md: str) -> dict:
    """申请单提取"""
    return {
        "申请日期": _parse_date(_kv_extract(md, ["申请日期", "日期"])),
        "事由": _kv_extract(md, ["事由", "申请事由", "申请内容"]),
        "预计费用": _extract_number(_kv_extract(md, ["预计费用", "预算", "金额"])),
        "参加人员": _kv_extract(md, ["参加人员", "人员"]),
    }


def _extract_reimbursement(md: str) -> dict:
    """报账单提取"""
    return {
        "发票金额": _extract_number(_kv_extract(md, ["发票金额", "金额"])),
        "税额": _extract_number(_kv_extract(md, ["税额"])),
        "合计金额": _extract_number(_kv_extract(md, ["合计", "合计金额", "报销金额"])),
        "报销日期": _parse_date(_kv_extract(md, ["报销日期", "日期"])),
    }


def _extract_invoice(md: str) -> dict:
    """发票提取(XML/PDF)"""
    return {
        "价税合计大写": _kv_extract(md, ["价税合计（大写)", "价税合计大写", "合计大写"]),
        "价税合计小写": _extract_number(_kv_extract(md, ["价税合计（小写)", "（小写）", "小写"])),
        "开票日期": _parse_date(_kv_extract(md, ["开票日期", "日期"])),
        "购买方": _kv_extract(md, ["购买方", "买方"]),
        "销售方": _kv_extract(md, ["销售方", "卖方"]),
        "发票号码": _kv_extract(md, ["发票号码", "号码"]),
    }


def _extract_business_status(md: str) -> dict:
    """经营状态提取"""
    # 查找包含"正常"的行
    status_text = ""
    company_name = ""
    for line in md.split("\n"):
        line_stripped = line.strip().lstrip("#").strip()
        if line_stripped:
            company_name = line_stripped
            if "正常" in line_stripped:
                status_text = "正常"
            else:
                # 提取末尾5-10个字符作为状态
                status_text = line_stripped[-10:] if len(line_stripped) > 10 else line_stripped
            break  # 只取第一条
    return {
        "单位名称": company_name,
        "经营状态": status_text,
        "是否异常": "正常" not in status_text,
    }


def _extract_payment(md: str) -> dict:
    """支付凭证提取"""
    return {
        "交易单号": _kv_extract(md, ["交易单号", "单号"]),
        "商户单号": _kv_extract(md, ["商户单号"]),
        "金额": _extract_number(_kv_extract(md, ["金额", "账单金额"])),
        "商户全称": _kv_extract(md, ["商户全称", "商户名称", "商户"]),
        "支付时间": _parse_date(_kv_extract(md, ["支付时间", "时间"])),
    }


def _extract_payment_flow(md: str) -> dict:
    """支付流水证明提取"""
    return {
        "交易单号": _kv_extract(md, ["交易单号", "单号"]),
        "交易对方": _kv_extract(md, ["交易对方", "对方", "收款方"]),
        "金额": _extract_number(_kv_extract(md, ["金额", "金额(元)"])),
        "交易时间": _parse_date(_kv_extract(md, ["交易时间", "时间"])),
    }


def _extract_event(md: str) -> dict:
    """活动函件提取"""
    return {
        "活动名称": _kv_extract(md, ["活动名称", "活动", "会议名称", "函件主题"]),
        "交流时间": _parse_date(_kv_extract(md, ["交流时间", "活动时间", "时间"])),
        "参加人员": _kv_extract(md, ["参加人员", "参会人员", "人员"]),
    }


# ===================================================================
# 审核规则引擎
# ===================================================================

# 从数据库加载启用的审核规则
def _load_active_rules(db):
    return db.query(AuditRule).filter(AuditRule.enabled == True).order_by(AuditRule.id).all()


# 初始化默认规则（首次调用时插入）
def _seed_default_rules(db):
    existing = db.query(AuditRule).filter(
        AuditRule.check_expression == "amount_consistency"
    ).first()
    if existing:
        return
    default_rules = [
        {"category": "一致性校验", "rule_name": "金额一致性", "clause": "以发票小写金额为准",
         "level": "高", "description": "核对发票金额与各单据金额是否一致",
         "check_expression": "amount_consistency", "source_document": "系统内置", "enabled": True},
        {"category": "一致性校验", "rule_name": "日期一致性", "clause": "以审批单招待日期为基准",
         "level": "高", "description": "核对审批单、发票、支付凭证的日期逻辑关系",
         "check_expression": "date_consistency", "source_document": "系统内置", "enabled": True},
        {"category": "合规性校验", "rule_name": "招待标准合规性", "clause": "人均费用和陪同人数应符合标准",
         "level": "高", "description": "工作餐≤60元，内部≤150元，其他公务≤200元，外事/商务≤400元",
         "check_expression": "standard_compliance", "source_document": "系统内置", "enabled": True},
        {"category": "经营风险", "rule_name": "单位经营状态", "clause": "招待单位应处于正常经营状态",
         "level": "提示", "description": "检查招待单位是否正常经营",
         "check_expression": "business_status", "source_document": "系统内置", "enabled": True},
        {"category": "一致性校验", "rule_name": "支付凭证一致性", "clause": "支付凭证和流水关键信息应一致",
         "level": "高", "description": "比对交易单号、金额、商户名称",
         "check_expression": "payment_consistency", "source_document": "系统内置", "enabled": True},
        {"category": "一致性校验", "rule_name": "活动函件日期", "clause": "函件日期与招待日期应相差在±7天内",
         "level": "中", "description": "核对活动函件时间与审批单日期",
         "check_expression": "event_date", "source_document": "系统内置", "enabled": True},
    ]
    for rd in default_rules:
        rule = AuditRule(**rd)
        db.add(rule)
    db.commit()
    logger.info("审核规则种子数据已初始化（6 条默认规则）")



def run_review(db: Session, serial_number: str) -> list[dict]:
    """执行全部审核规则，返回结果列表并写入数据库"""
    # 清除该流水号的旧审核结果
    db.query(ReviewResult).filter(ReviewResult.serial_number == serial_number).delete()

    # 获取提取字段
    extracted_records = (
        db.query(ExtractedField)
        .filter(ExtractedField.serial_number == serial_number, ExtractedField.status == "extracted")
        .all()
    )

    # 按槽位组织数据
    fields_by_slot = {}
    for ef in extracted_records:
        if ef.extracted_json:
            try:
                fields_by_slot[ef.slot_name] = json.loads(ef.extracted_json)
            except json.JSONDecodeError:
                pass

    # 从数据库加载启用的规则
    _seed_default_rules(db)
    active_rules = _load_active_rules(db)

    results = []
    for db_rule in active_rules:
        result = None

        # 双模式判断：JSON 表达式 or 硬编码函数名
        try:
            parsed_expr = json.loads(db_rule.check_expression)
            is_json_expr = isinstance(parsed_expr, dict) and "type" in parsed_expr
        except (json.JSONDecodeError, TypeError):
            is_json_expr = False

        if is_json_expr:
            # 模式 1: JSON 表达式 — 动态求值
            try:
                result = evaluate_expression(
                    parsed_expr, fields_by_slot,
                    rule_name=db_rule.rule_name,
                    severity=db_rule.level,
                )
            except Exception as e:
                logger.error(f"JSON 规则 '{db_rule.rule_name}' 执行异常: {e}")
                result = {
                    "rule_name": db_rule.rule_name,
                    "severity": db_rule.level,
                    "passed": False,
                    "detail": f"规则执行异常: {str(e)}",
                }
        else:
            # 模式 2: 硬编码函数名 — 向后兼容
            rule_func = RULE_REGISTRY.get(db_rule.check_expression)
            if rule_func is None:
                logger.warning(f"规则 '{db_rule.rule_name}' 的 check_expression 未注册，跳过")
                continue
            try:
                result = rule_func(fields_by_slot)
                result['rule_name'] = db_rule.rule_name
                result['severity'] = db_rule.level
            except Exception as e:
                logger.error(f"规则 '{db_rule.rule_name}' 执行异常: {e}")
                result = {
                    "rule_name": db_rule.rule_name,
                    "severity": db_rule.level,
                    "passed": False,
                    "detail": f"规则执行异常: {str(e)}",
                }

        if result:
            results.append(result)
            rr = ReviewResult(
                serial_number=serial_number,
                rule_name=db_rule.rule_name,
                severity=db_rule.level,
                passed=result["passed"],
                detail=result["detail"],
            )
            db.add(rr)

    db.commit()

    # 生成报告并保存
    report = generate_review_report(serial_number, results)
    record = db.query(ReceptionRecord).filter(
        ReceptionRecord.serial_number == serial_number
    ).first()
    if record:
        record.review_status = "completed"
        record.review_report = report
        db.commit()

    return results


def _rule_amount_consistency(fields: dict) -> dict:
    """规则1: 金额一致性 — 以发票小写金额为准"""
    detail_parts = []
    passed = True

    invoice_data = fields.get("发票XML") or fields.get("发票PDF")
    approval_data = fields.get("审批单")
    payment_data = fields.get("支付凭证")
    flow_data = fields.get("支付流水")
    reimb_data = fields.get("报账单")

    # 获取标准金额(发票小写)
    std_amount = None
    if invoice_data:
        std_amount = invoice_data.get("价税合计小写")
        detail_parts.append(f"发票金额: ¥{std_amount}")

    if not std_amount:
        return {"rule_name": "金额一致性", "severity": "高", "passed": True,
                "detail": "⚠️ 未找到发票数据，跳过校验"}

    # 比对审批单金额
    if approval_data and approval_data.get("招待金额"):
        amt = approval_data["招待金额"]
        diff = abs(float(amt) - float(std_amount))
        if diff > 0.01:
            passed = False
            detail_parts.append(f"❌ 审批单金额 ¥{amt} ≠ 发票 ¥{std_amount} (差¥{diff:.2f})")
        else:
            detail_parts.append(f"✅ 审批单金额 ¥{amt} ≈ 发票 ¥{std_amount}")

    # 比对支付凭证金额
    if payment_data and payment_data.get("金额"):
        amt = payment_data["金额"]
        diff = abs(float(amt) - float(std_amount))
        if diff > 0.01:
            passed = False
            detail_parts.append(f"❌ 支付凭证金额 ¥{amt} ≠ 发票 ¥{std_amount} (差¥{diff:.2f})")
        else:
            detail_parts.append(f"✅ 支付凭证金额 ¥{amt} ≈ 发票 ¥{std_amount}")

    # 比对支付流水金额
    if flow_data and flow_data.get("金额"):
        amt = flow_data["金额"]
        diff = abs(float(amt) - float(std_amount))
        if diff > 0.01:
            passed = False
            detail_parts.append(f"❌ 支付流水金额 ¥{amt} ≠ 发票 ¥{std_amount} (差¥{diff:.2f})")
        else:
            detail_parts.append(f"✅ 支付流水金额 ¥{amt} ≈ 发票 ¥{std_amount}")

    # 比对报账单金额
    if reimb_data and reimb_data.get("合计金额"):
        amt = reimb_data["合计金额"]
        diff = abs(float(amt) - float(std_amount))
        if diff > 0.01:
            passed = False
            detail_parts.append(f"❌ 报账单金额 ¥{amt} ≠ 发票 ¥{std_amount} (差¥{diff:.2f})")
        else:
            detail_parts.append(f"✅ 报账单金额 ¥{amt} ≈ 发票 ¥{std_amount}")

    return {"rule_name": "金额一致性", "severity": "高", "passed": passed,
            "detail": " | ".join(detail_parts) if detail_parts else "无数据可校验"}


def _rule_date_consistency(fields: dict) -> dict:
    """规则2: 日期一致性 — 以审批单招待日期为基准"""
    detail_parts = []
    passed = True

    approval_data = fields.get("审批单")
    std_date = None
    if approval_data and approval_data.get("招待日期"):
        std_date = approval_data["招待日期"]
        detail_parts.append(f"审批单招待日期: {std_date}")

    if not std_date:
        return {"rule_name": "日期一致性", "severity": "高", "passed": True,
                "detail": "⚠️ 未找到审批单日期，跳过校验"}

    # 发票日期应 ≤ 招待日期
    invoice_data = fields.get("发票XML") or fields.get("发票PDF")
    if invoice_data and invoice_data.get("开票日期"):
        inv_date = invoice_data["开票日期"]
        if inv_date > std_date:
            passed = False
            detail_parts.append(f"❌ 发票日期 {inv_date} > 招待日期 {std_date}")
        else:
            detail_parts.append(f"✅ 发票日期 {inv_date} ≤ 招待日期 {std_date}")

    # 支付时间应 ≥ 招待日期
    payment_data = fields.get("支付凭证")
    if payment_data and payment_data.get("支付时间"):
        pay_date = payment_data["支付时间"]
        if pay_date < std_date:
            passed = False
            detail_parts.append(f"❌ 支付时间 {pay_date} < 招待日期 {std_date}")
        else:
            detail_parts.append(f"✅ 支付时间 {pay_date} ≥ 招待日期 {std_date}")

    # 支付流水时间
    flow_data = fields.get("支付流水")
    if flow_data and flow_data.get("交易时间"):
        ft = flow_data["交易时间"]
        if ft < std_date:
            passed = False
            detail_parts.append(f"❌ 流水时间 {ft} < 招待日期 {std_date}")
        else:
            detail_parts.append(f"✅ 流水时间 {ft} ≥ 招待日期 {std_date}")

    return {"rule_name": "日期一致性", "severity": "高", "passed": passed,
            "detail": " | ".join(detail_parts) if detail_parts else "无数据可校验"}


def _rule_standard_compliance(fields: dict) -> dict:
    """规则3: 招待标准合规性"""
    detail_parts = []
    passed = True

    approval_data = fields.get("审批单")
    if not approval_data:
        return {"rule_name": "招待标准合规性", "severity": "高", "passed": True,
                "detail": "⚠️ 未找到审批单数据，跳过校验"}

    per_capita = approval_data.get("人均费用")
    guests = approval_data.get("招待人数") or 0
    accompany = approval_data.get("陪同人数") or 0
    reception_type = approval_data.get("招待类型", "")

    # 人均费用标准
    if per_capita is not None:
        per_capita = float(per_capita)
        limit = 400  # 默认宽松上限
        if "工作餐" in reception_type:
            limit = 60
        elif "内部" in reception_type:
            limit = 150
        elif "其他公务" in reception_type:
            limit = 200
        elif "外事" in reception_type or "商务" in reception_type:
            limit = 400

        if per_capita > limit:
            passed = False
            detail_parts.append(f"❌ 人均费用 ¥{per_capita} 超过标准 ¥{limit}")
        else:
            detail_parts.append(f"✅ 人均费用 ¥{per_capita} ≤ 标准 ¥{limit}")

    # 陪同人数标准
    if guests and accompany:
        guests = int(guests)
        accompany = int(accompany)
        if "内部" in reception_type:
            max_accompany = 3 if guests <= 10 else guests // 3
        else:
            max_accompany = guests if guests <= 5 else guests + (guests - 5) // 2

        if accompany > max_accompany:
            passed = False
            detail_parts.append(f"❌ 陪同人数 {accompany} 超过标准 {max_accompany}")
        else:
            detail_parts.append(f"✅ 陪同人数 {accompany} ≤ 标准 {max_accompany}")

    return {"rule_name": "招待标准合规性", "severity": "高", "passed": passed,
            "detail": " | ".join(detail_parts) if detail_parts else "无数据可校验"}


def _rule_business_status(fields: dict) -> dict:
    """规则4: 单位经营状态"""
    status_data = fields.get("经营状态")
    approval_data = fields.get("审批单")

    if not status_data:
        return {"rule_name": "单位经营状态", "severity": "提示", "passed": True,
                "detail": "⚠️ 未上传经营状态文件"}

    if not approval_data or not approval_data.get("招待对象"):
        return {"rule_name": "单位经营状态", "severity": "提示", "passed": True,
                "detail": "⚠️ 未找到招待对象名称，需人工核对"}

    org_name = approval_data["招待对象"]
    is_abnormal = status_data.get("是否异常", False)
    status_text = status_data.get("经营状态", "")

    if is_abnormal:
        return {"rule_name": "单位经营状态", "severity": "提示", "passed": False,
                "detail": f"⚠️ 招待单位'{org_name}'经营状态异常: {status_text}，需人工审核"}

    return {"rule_name": "单位经营状态", "severity": "提示", "passed": True,
            "detail": f"✅ 招待单位'{org_name}'经营状态: {status_text}"}


def _rule_payment_consistency(fields: dict) -> dict:
    """规则5: 支付凭证一致性"""
    detail_parts = []
    passed = True

    payment_data = fields.get("支付凭证")
    flow_data = fields.get("支付流水")

    if not payment_data or not flow_data:
        return {"rule_name": "支付凭证一致性", "severity": "高", "passed": True,
                "detail": "⚠️ 支付凭证或支付流水缺失，跳过校验"}

    # 比对关键字段
    compare_fields = [
        ("交易单号", "交易单号"),
        ("商户单号", None),  # 支付流水可能没有商户单号
        ("金额", "金额"),
        ("商户全称", "交易对方"),
    ]

    for pay_key, flow_key in compare_fields:
        pay_val = payment_data.get(pay_key)
        flw_val = flow_data.get(flow_key or pay_key)

        if pay_val and flw_val:
            if str(pay_val).strip() == str(flw_val).strip():
                detail_parts.append(f"✅ {pay_key} 一致")
            else:
                # 金额做数值比较
                if pay_key == "金额":
                    try:
                        diff = abs(float(pay_val) - float(flw_val))
                        if diff > 0.01:
                            passed = False
                            detail_parts.append(f"❌ {pay_key}: ¥{pay_val} ≠ ¥{flw_val}")
                        else:
                            detail_parts.append(f"✅ {pay_key} 一致")
                    except (ValueError, TypeError):
                        passed = False
                        detail_parts.append(f"❌ {pay_key}: {pay_val} ≠ {flw_val}")
                else:
                    # 商户名称做模糊比较
                    if pay_key == "商户全称":
                        if flw_val in str(pay_val) or pay_val in str(flw_val):
                            detail_parts.append(f"✅ 商户名称匹配")
                        else:
                            passed = False
                            detail_parts.append(f"❌ 商户名称: {pay_val} ≠ {flw_val}")
                    else:
                        passed = False
                        detail_parts.append(f"❌ {pay_key}: {pay_val} ≠ {flw_val}")

    return {"rule_name": "支付凭证一致性", "severity": "高", "passed": passed,
            "detail": " | ".join(detail_parts) if detail_parts else "无数据可校验"}


def _rule_event_date(fields: dict) -> dict:
    """规则6: 活动函件日期一致性"""
    approval_data = fields.get("审批单")
    event_data = fields.get("活动函件")

    if not event_data or not event_data.get("交流时间"):
        return {"rule_name": "活动函件日期", "severity": "中", "passed": True,
                "detail": "⚠️ 未找到活动函件日期，跳过校验"}

    if not approval_data or not approval_data.get("招待日期"):
        return {"rule_name": "活动函件日期", "severity": "中", "passed": True,
                "detail": "⚠️ 未找到审批单日期，跳过校验"}

    from datetime import timedelta
    try:
        std_date = datetime.strptime(approval_data["招待日期"], "%Y-%m-%d")
        event_date = datetime.strptime(event_data["交流时间"], "%Y-%m-%d")
        diff_days = abs((event_date - std_date).days)
        if diff_days > 7:
            return {"rule_name": "活动函件日期", "severity": "中", "passed": False,
                    "detail": f"❌ 函件日期 {event_data['交流时间']} 与招待日期 {approval_data['招待日期']} 相差 {diff_days} 天(超±7天)"}
        return {"rule_name": "活动函件日期", "severity": "中", "passed": True,
                "detail": f"✅ 函件日期 {event_data['交流时间']} 与招待日期 {approval_data['招待日期']} 相差 {diff_days} 天"}
    except ValueError as e:
        return {"rule_name": "活动函件日期", "severity": "中", "passed": False,
                "detail": f"❌ 日期解析失败: {e}"}


# 规则函数注册表（check_expression -> 函数）
RULE_REGISTRY = {
    "amount_consistency": _rule_amount_consistency,
    "date_consistency": _rule_date_consistency,
    "standard_compliance": _rule_standard_compliance,
    "business_status": _rule_business_status,
    "payment_consistency": _rule_payment_consistency,
    "event_date": _rule_event_date,
}



# ===================================================================
# JSON 表达式求值器 — 支持跨槽位字段比较、关键词匹配、金额阈值
# ===================================================================

def _parse_date_str(val):
    """解析日期字符串，统一返回 YYYY-MM-DD 格式"""
    import re
    if not isinstance(val, str):
        val = str(val)
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", val.strip())
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    m = re.match(r"(\d{4})[年.\/\-](\d{1,2})[月.\/\-](\d{1,2})", val.strip())
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    return val.strip() if val.strip() else None


def _eval_cross_field_compare(expr, fields_by_slot):
    """跨槽位字段比较表达式求值器

    {
        "type": "cross_field_compare",
        "field": "招待日期",
        "field_slot": "审批单",
        "field_type": "date",        // "date" or "number"
        "tolerance": 0.01,           // 数值比较容差
        "fallback_slot": "发票PDF",  // 基准字段备选槽位
        "comparisons": [
            {
                "other_slot": "申请单",
                "other_field": "申请日期",
                "operator": "<=",
                "message": "申请日期应早于招待日期",
                "fallback_slot": "发票PDF",
                "tolerance_days": 7   // 日期容差（天）
            }
        ]
    }

    运算符: <=, >=, ==, !=, >, <, ~ (近似, 需容差)
    """
    base_field = expr.get("field", "")
    base_slot = expr.get("field_slot", "")
    field_type = expr.get("field_type", "date")
    comparisons = expr.get("comparisons", [])
    default_tolerance = expr.get("tolerance", 0)

    # 获取基准值
    base_val = fields_by_slot.get(base_slot, {}).get(base_field)
    if base_val is None:
        fb = expr.get("fallback_slot")
        if fb and fb in fields_by_slot:
            base_val = fields_by_slot[fb].get(base_field)
    if base_val is None:
        return {
            "rule_name": expr.get("_rule_name", "跨字段比较"),
            "severity": expr.get("_severity", "高"),
            "passed": True,
            "detail": f"⚠️ 未找到槽位[{base_slot}]的字段[{base_field}]，跳过校验",
        }

    # 基准值标准化
    if field_type == "date":
        base_val = _parse_date_str(base_val)

    parts = []
    passed = True

    for comp in comparisons:
        other_slot = comp.get("other_slot", "")
        other_field = comp.get("other_field", "")
        operator = comp.get("operator", "==")
        msg = comp.get("message", "")
        tolerance = comp.get("tolerance_days", comp.get("tolerance", default_tolerance))
        fb = comp.get("fallback_slot")

        # 获取比较值
        other_val = fields_by_slot.get(other_slot, {}).get(other_field)
        if other_val is None and fb:
            other_val = fields_by_slot.get(fb, {}).get(other_field)

        if other_val is None:
            parts.append(f"⚠️ 跳过: 未找到槽位[{other_slot}]的字段[{other_field}]")
            continue

        if field_type == "date":
            other_val = _parse_date_str(other_val)
            if other_val is None:
                parts.append(f"⚠️ 跳过: 字段[{other_field}]日期解析失败")
                continue

        # 执行比较
        ok = _compare_values(base_val, other_val, operator, tolerance, field_type)
        if not ok:
            passed = False
            if msg:
                parts.append(f"❌ {msg}")
            else:
                parts.append(f"❌ {other_field}({other_val}) {operator} {base_field}({base_val})")
        else:
            if msg:
                parts.append(f"✅ {msg}")
            elif operator == "~":
                if field_type == "date":
                    d1 = datetime.strptime(base_val, "%Y-%m-%d")
                    d2 = datetime.strptime(other_val, "%Y-%m-%d")
                    diff = abs((d1 - d2).days)
                    parts.append(f"✅ {other_field}({other_val}) 与 {base_field}({base_val}) 相差 {diff} 天 (容差±{tolerance}天)")
                else:
                    parts.append(f"✅ {other_field}({other_val}) 与 {base_field}({base_val}) 相近")
            else:
                parts.append(f"✅ {other_field}({other_val}) {operator} {base_field}({base_val})")

    return {
        "rule_name": expr.get("_rule_name", "跨字段比较"),
        "severity": expr.get("_severity", "高"),
        "passed": passed,
        "detail": " | ".join(parts) if parts else "无数据可校验",
    }


def _compare_values(base_val, other_val, operator, tolerance, field_type):
    """执行两个值的比较"""
    if field_type == "date":
        b = str(base_val)
        o = str(other_val)
        if operator == "~":
            try:
                d1 = datetime.strptime(b, "%Y-%m-%d")
                d2 = datetime.strptime(o, "%Y-%m-%d")
                return abs((d1 - d2).days) <= tolerance
            except (ValueError, TypeError):
                return True
        elif operator == "<=":
            return o <= b
        elif operator == ">=":
            return o >= b
        elif operator == "==":
            return o == b
        elif operator == "!=":
            return o != b
        elif operator == ">":
            return o > b
        elif operator == "<":
            return o < b
    else:
        try:
            b = float(base_val)
            o = float(other_val)
        except (ValueError, TypeError):
            return True
        if operator == "==":
            return abs(b - o) <= tolerance
        elif operator == "!=":
            return abs(b - o) > tolerance
        elif operator == "<=":
            return o <= b + tolerance
        elif operator == ">=":
            return o >= b - tolerance
        elif operator == ">":
            return o > b + tolerance
        elif operator == "<":
            return o < b - tolerance
    return True


def _eval_keyword_match_expr(expr, fields_by_slot):
    """关键词匹配表达式求值器

    {
        "type": "keyword_match",
        "field": "商户全称",
        "field_slot": "支付凭证",
        "keywords": ["私人会所", "高档娱乐"],
        "mode": "any"
    }
    """
    target_field = expr.get("field", "")
    target_slot = expr.get("field_slot", "")
    keywords = expr.get("keywords", [])
    mode = expr.get("mode", "any")

    target_val = fields_by_slot.get(target_slot, {}).get(target_field, "")
    if not target_val:
        return {
            "rule_name": expr.get("_rule_name", "关键词匹配"),
            "severity": expr.get("_severity", "高"),
            "passed": True,
            "detail": f"⚠️ 未找到槽位[{target_slot}]的字段[{target_field}]，跳过",
        }

    matched = [kw for kw in keywords if kw in str(target_val)]
    if mode == "all":
        is_match = len(matched) == len(keywords)
    else:
        is_match = len(matched) > 0

    if is_match:
        return {
            "rule_name": expr.get("_rule_name", "关键词匹配"),
            "severity": expr.get("_severity", "高"),
            "passed": False,
            "detail": f"❌ [{target_slot}]{target_field} 命中关键词: {', '.join(matched)}",
        }

    return {
        "rule_name": expr.get("_rule_name", "关键词匹配"),
        "severity": expr.get("_severity", "高"),
        "passed": True,
        "detail": f"✅ [{target_slot}]{target_field} 未命中禁止关键词",
    }


def _eval_amount_threshold_expr(expr, fields_by_slot):
    """金额阈值表达式求值器

    {
        "type": "amount_threshold",
        "field": "人均费用",
        "field_slot": "审批单",
        "operator": ">",
        "threshold": 200,
        "message": "人均费用超标"
    }
    """
    target_field = expr.get("field", "")
    target_slot = expr.get("field_slot", "")
    operator = expr.get("operator", ">")
    threshold = expr.get("threshold", 0)
    msg = expr.get("message", "")

    target_val = fields_by_slot.get(target_slot, {}).get(target_field)
    if target_val is None:
        return {
            "rule_name": expr.get("_rule_name", "金额阈值"),
            "severity": expr.get("_severity", "高"),
            "passed": True,
            "detail": f"⚠️ 未找到槽位[{target_slot}]的字段[{target_field}]，跳过",
        }

    try:
        val = float(target_val)
    except (ValueError, TypeError):
        return {
            "rule_name": expr.get("_rule_name", "金额阈值"),
            "severity": expr.get("_severity", "高"),
            "passed": True,
            "detail": f"⚠️ 字段[{target_field}]值[{target_val}]无法转换为数字",
        }

    ops = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
           "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
           "==": lambda a, b: a == b, "!=": lambda a, b: a != b}
    cmp_fn = ops.get(operator)
    if cmp_fn is None:
        return {
            "rule_name": expr.get("_rule_name", "金额阈值"),
            "severity": expr.get("_severity", "高"),
            "passed": True,
            "detail": f"⚠️ 无效运算符: {operator}",
        }

    if cmp_fn(val, threshold):
        detail_msg = msg or f"[{target_slot}]{target_field}={val} {operator} {threshold}"
        return {
            "rule_name": expr.get("_rule_name", "金额阈值"),
            "severity": expr.get("_severity", "高"),
            "passed": False,
            "detail": f"❌ {detail_msg}",
        }

    detail_msg = msg or f"[{target_slot}]{target_field}={val} 符合标准"
    return {
        "rule_name": expr.get("_rule_name", "金额阈值"),
        "severity": expr.get("_severity", "高"),
        "passed": True,
        "detail": f"✅ {detail_msg}",
    }


# JSON 表达式求值器注册表
EXPRESSION_EVALUATORS = {
    "cross_field_compare": _eval_cross_field_compare,
    "keyword_match": _eval_keyword_match_expr,
    "amount_threshold": _eval_amount_threshold_expr,
}


def evaluate_expression(expr_dict, fields_by_slot, rule_name="", severity="高"):
    """通用表达式求值入口 — 根据 type 分派到对应求值器"""
    expr_type = expr_dict.get("type", "")
    evaluator = EXPRESSION_EVALUATORS.get(expr_type)
    if evaluator is None:
        return {
            "rule_name": rule_name or "未知规则",
            "severity": severity,
            "passed": True,
            "detail": f"⚠️ 未知表达式类型: {expr_type}，跳过",
        }

    expr_dict["_rule_name"] = rule_name or "动态规则"
    expr_dict["_severity"] = severity
    return evaluator(expr_dict, fields_by_slot)

# ===================================================================
# 审核报告生成
# ===================================================================

def generate_review_report(serial_number: str, results: list[dict]) -> str:
    """生成 Markdown 格式审核报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed"))
    failed_count = total - passed_count

    severity_order = {"高": 0, "中": 1, "低": 2, "提示": 3}
    sorted_results = sorted(results, key=lambda r: severity_order.get(r.get("severity", "低"), 99))

    lines = [
        f"# 审核报告",
        f"",
        f"- **流水号**: {serial_number}",
        f"- **审核时间**: {now}",
        f"- **规则总数**: {total}",
        f"- **通过**: {passed_count}",
        f"- **不通过**: {failed_count}",
        f"",
        "---",
        f"",
        "## 审核结果明细",
        f"",
    ]

    for r in sorted_results:
        icon = "✅" if r["passed"] else "❌"
        lines.append(f"### {icon} {r['rule_name']} ({r['severity']})")
        lines.append(f"")
        lines.append(f"**结果**: {'通过' if r['passed'] else '不通过'}")
        lines.append(f"")
        lines.append(f"**详情**: {r['detail']}")
        lines.append(f"")
        lines.append("---")
        lines.append(f"")

    # 总结
    lines.append("## 审核结论")
    lines.append(f"")
    if failed_count == 0:
        lines.append("✅ **全部通过** — 该笔招待费记录符合所有审核标准")
    else:
        failed_rules = [r["rule_name"] for r in results if not r["passed"]]
        lines.append(f"❌ **发现 {failed_count} 项不通过**，需人工审核处理")
        lines.append(f"")
        lines.append(f"不通过规则: {', '.join(failed_rules)}")

    lines.append(f"")
    lines.append("---")
    lines.append(f"*报告由系统自动生成*")

    return "\n".join(lines)

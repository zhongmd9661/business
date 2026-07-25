"""LLM 辅助解析 — 将制度条款文本转为结构化规则 JSON"""
from __future__ import annotations

import json
import os
from typing import Optional

from anthropic import Anthropic


SYSTEM_PROMPT = """\
你是一个专业的制度文档解析助手。你的任务是将业务招待费管理制度中的条款文本转换为结构化审核规则。

每个规则包含以下字段：

1. category: 规则分类，可选值
   - "单据完整性"
   - "金额标准"
   - "招待类型"
   - "陪同人数"
   - "禁止性规定"
   - "报销合规"
   - "审批管理"
   - "交叉稽核"

2. rule_name: 规则名称（简短描述，20字以内）

3. clause: 条款引用，如 "管理办法 第一条"

4. level: 风险等级，可选 "高"、"中"、"低"、"提示"

5. description: 规则详细描述（100字以内）

6. check_expression: JSON 对象，定义如何检查该规则。可选类型：
   - keyword_match: {"type": "keyword_match", "field": "merchant_name", "keywords": ["关键词1", "关键词2"], "mode": "any"}
   - amount_compare: {"type": "amount_compare", "field": "per_person_amount", "operator": ">", "threshold": 250}
   - date_range: {"type": "date_range", "field": "reception_date", "after": "2024-04-01"}
   - boolean_check: {"type": "boolean_check", "field": "payment_voucher_present", "expected": false}
   - count_compare: {"type": "count_compare", "field": "companion_count", "compare_field": "guest_count", "formula": "equal_if_le_5"}

如果条款不涉及具体检查逻辑，check_expression 返回 null。

返回纯 JSON 数组，不要包裹在 markdown 代码块中。
"""


def _parse_json_response(text: str) -> Optional[list]:
    """从 LLM 响应中提取 JSON 数组。"""
    text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # 处理 markdown 代码块
    if text.startswith("```") and text.endswith("```"):
        inner = text[3:-3]
        if inner.startswith("json\n"):
            inner = inner[5:]
        try:
            return json.loads(inner.strip())
        except (json.JSONDecodeError, TypeError):
            pass
    # 尝试找 JSON 数组边界
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except (json.JSONDecodeError, TypeError):
            pass
    return None


class LlmRuleParser:
    """使用 LLM 将制度条款文本解析为结构化规则 JSON。

    复用项目的 Anthropic 兼容 API 配置。
    """

    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        self.base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL", "http://192.168.231.1:1235")
        self.api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "lmstudio")
        self.model = model or os.environ.get("LLM_MODEL", "qwen/qwen3.6-27b")
        self._client: Optional[Anthropic] = None

    def start(self):
        self._client = Anthropic(base_url=self.base_url, api_key=self.api_key)

    def stop(self):
        self._client = None

    def parse_clauses(self, clauses: list[tuple[str, str]]) -> list[dict]:
        """解析多个条款文本为结构化规则。

        Args:
            clauses: [(source_document, clause_text), ...]

        Returns:
            结构化规则列表
        """
        if self._client is None:
            raise RuntimeError("调用 parse_clauses() 前先调用 start()")

        # 构建 prompt：每条条款标注来源
        parts = []
        for i, (source, text) in enumerate(clauses):
            truncated = text[:5000] if len(text) > 5000 else text
            parts.append(f"[{source}] 条款 {i+1}:\n{truncated}")

        prompt = f"请解析以下 {len(clauses)} 条制度条款：\n\n" + "\n\n".join(parts)

        response = self._client.messages.create(
            model=self.model,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            top_p=0.99,
            max_tokens=8192,
        )

        generated_text = response.content[0].text
        parsed = _parse_json_response(generated_text)
        if parsed is None:
            return []

        # 验证并补全必要字段
        rules = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            rule = self._normalize_rule(item)
            if rule:
                rules.append(rule)
        return rules

    @staticmethod
    def _normalize_rule(item: dict) -> Optional[dict]:
        """补全必要字段，确保规则格式正确。"""
        if not item.get("rule_name"):
            return None
        rule = {
            "category": item.get("category", "单据完整性"),
            "rule_name": str(item["rule_name"])[:50],
            "clause": item.get("clause", ""),
            "level": item.get("level", "中"),
            "description": item.get("description", "")[:500],
            "check_expression": "",
            "source_document": item.get("source_document", ""),
        }
        # check_expression 可能是嵌套 JSON 对象或字符串
        expr = item.get("check_expression")
        if isinstance(expr, dict):
            rule["check_expression"] = json.dumps(expr, ensure_ascii=False)
        elif isinstance(expr, str) and expr:
            rule["check_expression"] = expr
        return rule


# Convenience function — matches rule_parser.py interface
def parse_with_llm(clauses: list[tuple[str, str]], base_url: str = None) -> list[dict]:
    """便捷函数：使用 LLM 解析条款。

    Args:
        clauses: [(source_document, clause_text), ...]
        base_url: 可选的 API 地址

    Returns:
        结构化规则列表
    """
    parser = LlmRuleParser(base_url=base_url)
    try:
        parser.start()
        return parser.parse_clauses(clauses)
    finally:
        parser.stop()

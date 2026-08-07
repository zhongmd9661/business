"""
信息采集：从 QCC 搜索结果页提取结构化企业数据。
使用正确的 CSS 选择器匹配 Vue.js 动态渲染的页面结构。
"""
import logging
from typing import Dict, List

log = logging.getLogger(__name__)


def _safe_text(context, selector, default=""):
    """安全地获取元素文本。"""
    try:
        el = context.locator(selector)
        if el.count() > 0:
            text = el.first.inner_text(timeout=500).strip()
            return text or default
    except Exception:
        pass
    return default


class Collector:
    """从 QCC 搜索结果页采集企业信息。"""

    def __init__(self, page):
        self.page = page

    def extract_company_list(self) -> List[Dict[str, str]]:
        """遍历搜索结果并提取企业信息列表。"""
        log.info("开始采集企业信息...")
        companies = []

        # 查找所有企业行 (tr.frtrt 是第一个结果，tr:has(a.title.copy-value) 是其他结果)
        rows = self.page.locator("tr.frtrt, tr:has(a.title.copy-value)").all()
        log.info("找到 %d 个企业结果行", len(rows))

        for i, row in enumerate(rows):
            try:
                data = self._extract_from_row(row)
                if data.get("company_name") and len(data["company_name"]) >= 2:
                    companies.append(data)
            except Exception as e:
                log.debug("第 %d 行提取失败: %s", i, e)

        if not companies:
            log.warning("未能提取企业信息，保存调试快照")
            self.page.screenshot(path="debug_collector.png", full_page=True)
            with open("debug_page_source.html", "w", encoding="utf-8") as f:
                f.write(self.page.content())

        log.info("共采集到 %d 条企业信息", len(companies))
        return companies

    def _extract_from_row(self, row) -> Dict[str, str]:
        """从单个 tr 行提取企业字段。"""
        name = _safe_text(row, "a.title.copy-value")
        status = _safe_text(row, ".text-success.nstatus, .text-danger.nstatus")

        # 法定代表人
        legal = ""
        try:
            legal_span = row.locator("span.f:has-text('法定代表人')")
            if legal_span.count() > 0:
                legal_el = legal_span.locator(".val a")
                if legal_el.count() > 0:
                    legal = legal_el.first.inner_text(timeout=300).strip()
                else:
                    legal = legal_span.locator(".val").first.inner_text(timeout=300).strip()
        except Exception:
            pass

        # 注册资本
        capital = ""
        try:
            cap_span = row.locator("span.f:has-text('注册资本')")
            if cap_span.count() > 0:
                capital = cap_span.locator(".val").first.inner_text(timeout=300).strip()
        except Exception:
            pass

        # 成立日期
        date = ""
        try:
            date_span = row.locator("span.f:has-text('成立日期')")
            if date_span.count() > 0:
                date = date_span.locator(".val").first.inner_text(timeout=300).strip()
        except Exception:
            pass

        # 统一社会信用代码
        code = ""
        try:
            code_span = row.locator("span.f:has-text('统一社会信用代码')")
            if code_span.count() > 0:
                code_el = code_span.locator(".copy-value")
                if code_el.count() > 0:
                    code = code_el.first.inner_text(timeout=300).strip()
                else:
                    code = code_span.locator(".val").first.inner_text(timeout=300).strip()
        except Exception:
            pass

        # 地址
        addr = ""
        try:
            addr_span = row.locator("span.f:has-text('地址')")
            if addr_span.count() > 0:
                addr_el = addr_span.locator(".copy-value.address-map")
                if addr_el.count() > 0:
                    addr = addr_el.first.inner_text(timeout=300).strip()
                else:
                    addr = addr_span.locator(".val").first.inner_text(timeout=300).strip()
        except Exception:
            pass

        return {
            "company_name": name,
            "status": status,
            "legal_person": legal,
            "registered_capital": capital,
            "establish_date": date,
            "credit_code": code,
            "address": addr,
        }
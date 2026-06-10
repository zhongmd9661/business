# 业务招待费审核 Skill 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 OCR 批量解析完成后自动审核业务招待费报销单据，生成审核报告并通过 webhook 通知。

**Architecture:** 独立的 `src/expense_review/` 模块提供审核引擎和报告生成，`scripts/review_batch.py` 作为入口脚本在解析后调用，SKILL.md 定义 Claude Code 的审核提示词用于 LLM 辅助判断。

**Tech Stack:** Python, loguru, requests (webhook)

---

### Task 1: 创建 expense_review 包结构

**Files:**
- Create: `src/expense_review/__init__.py`
- Create: `src/expense_review/reviewer.py`
- Create: `src/expense_review/reporter.py`
- Create: `src/expense_review/notifier.py`

- [ ] **Step 1: 创建包结构**

```python
# src/expense_review/__init__.py
from .reviewer import ExpenseReviewer
from .reporter import ReportGenerator
from .notifier import WebhookNotifier

__all__ = ["ExpenseReviewer", "ReportGenerator", "WebhookNotifier"]
```

- [ ] **Step 2: 验证包可导入**

Run: `python -c "from src.expense_review import ExpenseReviewer, ReportGenerator, WebhookNotifier"`
Expected: 无错误（但类尚未实现，需要下一步）

- [ ] **Step 3: Commit**

```bash
git add src/expense_review/__init__.py
git commit -m "feat: 创建 expense_review 包结构"
```

---

### Task 2: 实现审核规则引擎

**Files:**
- Create: `src/expense_review/reviewer.py`
- Test: `tests/test_expense_review/test_reviewer.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_expense_review/test_reviewer.py
from src.expense_review.reviewer import ExpenseReviewer, ReviewRule

def test_review_empty_content():
    reviewer = ExpenseReviewer()
    findings = reviewer.review("")
    assert len(findings) > 0  # 应该有"文档为空"风险

def test_review_date_mismatch():
    reviewer = ExpenseReviewer()
    content = """招待日期: 2025-03-15
发票日期: 2025-03-20
招待对象人数: 3
陪同人数: 4
招待类型: 商务招待
申请日期: 2025-03-10
"""
    findings = reviewer.review(content)
    date_issues = [f for f in findings if "日期" in f.rule]
    assert len(date_issues) > 0

def test_review_compliant():
    reviewer = ExpenseReviewer()
    content = """招待日期: 2025-03-15
发票日期: 2025-03-15
招待对象人数: 3
陪同人数: 3
招待类型: 商务招待
申请日期: 2025-03-10
支付凭证: 有
"""
    findings = reviewer.review(content)
    high_risks = [f for f in findings if f.level == "高"]
    assert len(high_risks) == 0
```

- [ ] **Step 2: 实现审核引擎**

```python
# src/expense_review/reviewer.py
"""业务招待费审核规则引擎"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Finding:
    rule: str
    level: str  # "高", "中", "低", "提示"
    message: str
    detail: str = ""

@dataclass
class DocumentReview:
    filename: str
    findings: list[Finding] = field(default_factory=list)
    @property
    def has_high_risk(self) -> bool:
        return any(f.level == "高" for f in self.findings)

# 日期提取辅助
def _extract_dates(text: str) -> dict[str, datetime]:
    dates = {}
    patterns = {
        "招待日期": r"招待日期[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        "发票日期": r"发票日期[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        "申请日期": r"申请日期[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        "支付日期": r"支付日期[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
    }
    for name, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m"):
                try:
                    dates[name] = datetime.strptime(m.group(1), fmt)
                    break
                except ValueError:
                    continue
    return dates

# 数字提取辅助
def _extract_number(text: str, pattern: str) -> Optional[int]:
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None

class ExpenseReviewer:
    """逐文档审核业务招待费报销单据"""

    def review(self, content: str, filename: str = "") -> list[Finding]:
        findings = []
        if not content.strip():
            findings.append(Finding("文档完整性", "高", "文档内容为空，无法审核"))
            return findings

        findings.extend(self._check_dates(content))
        findings.extend(self._check_companion_count(content))
        findings.extend(self._check_payment_voucher(content))
        findings.extend(self._check_official_letter(content))
        findings.extend(self._check_invoice_verification(content))
        findings.extend(self._check_holiday_period(content))
        return findings

    def _check_dates(self, text: str) -> list[Finding]:
        findings = []
        dates = _extract_dates(text)

        if "招待日期" in dates and "发票日期" in dates:
            if dates["招待日期"] != dates["发票日期"]:
                findings.append(Finding(
                    "日期一致性", "高",
                    f"发票日期({dates['发票日期'].date()})与招待日期({dates['招待日期'].date()})不一致",
                ))

        if "招待日期" in dates and "申请日期" in dates:
            if dates["申请日期"] > dates["招待日期"]:
                findings.append(Finding(
                    "事前审批", "高",
                    f"申请日期({dates['申请日期'].date()})晚于招待日期({dates['招待日期'].date()})",
                ))

        return findings

    def _check_companion_count(self, text: str) -> list[Finding]:
        findings = []
        guest_count = _extract_number(text, r"招待对象人数[:\s]*(\d+)")
        companion_count = _extract_number(text, r"陪同人数[:\s]*(\d+)")

        if guest_count and companion_count:
            if guest_count <= 5:
                limit = guest_count  # 对等
            else:
                limit = guest_count + (guest_count - 5) // 2

            if companion_count > limit:
                findings.append(Finding(
                    "陪同人数", "高",
                    f"陪同人数({companion_count})超过标准({limit})",
                ))
        return findings

    def _check_payment_voucher(self, text: str) -> list[Finding]:
        findings = []
        dates = _extract_dates(text)

        if "招待日期" in dates and dates["招待日期"] >= datetime(2024, 4, 1):
            has_voucher = bool(re.search(r"支付凭证[:\s]*有|刷卡单|电子消费凭证", text))
            if not has_voucher:
                findings.append(Finding(
                    "支付凭证", "高",
                    "2024年4月1日后需提供支付凭证",
                ))
        return findings

    def _check_official_letter(self, text: str) -> list[Finding]:
        findings = []
        dates = _extract_dates(text)

        if "招待日期" in dates and dates["招待日期"] >= datetime(2025, 12, 4):
            is_external = bool(re.search(r"招待类型[:\s]*(商务|外事|其他公务)", text))
            has_letter = bool(re.search(r"公函|往来公函", text))

            if is_external and not has_letter:
                findings.append(Finding(
                    "往来公函", "高",
                    "2025年12月4日后外部招待必需往来公函",
                ))
        return findings

    def _check_invoice_verification(self, text: str) -> list[Finding]:
        findings = []
        dates = _extract_dates(text)

        if "招待日期" in dates and dates["招待日期"] < datetime(2025, 6, 1):
            has_verification = bool(re.search(r"发票查验|发票验证|发票校验", text))
            if not has_verification:
                findings.append(Finding(
                    "发票查验", "中",
                    "2025年6月1日前需提供发票查验",
                ))
        return findings

    def _check_holiday_period(self, text: str) -> list[Finding]:
        findings = []
        dates = _extract_dates(text)
        holidays = [
            (1, 1), (1, 2), (2, 4), (5, 1), (6, 7),
            (9, 10), (10, 1),
        ]

        if "招待日期" in dates:
            d = dates["招待日期"]
            for month, day in holidays:
                holiday_date = datetime(d.year, month, day)
                delta = abs((d - holiday_date).days)
                if delta <= 3:
                    has_report = bool(re.search(r"备案|报备|报告", text))
                    if not has_report:
                        findings.append(Finding(
                            "节日招待", "中",
                            f"招待日期接近重大节日，需确认是否已报备",
                        ))
                    break
        return findings
```

- [ ] **Step 3: 运行测试**

Run: `python -m pytest tests/test_expense_review/test_reviewer.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/expense_review/reviewer.py tests/test_expense_review/
git commit -m "feat: 实现审核规则引擎（日期、人数、支付凭证、公函、节日）"
```

---

### Task 3: 实现报告生成器

**Files:**
- Create: `src/expense_review/reporter.py`
- Test: `tests/test_expense_review/test_reporter.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_expense_review/test_reporter.py
from src.expense_review.reviewer import Finding, DocumentReview
from src.expense_review.reporter import ReportGenerator

def test_generate_report():
    reviews = [
        DocumentReview("001_test.md", [
            Finding("日期一致性", "高", "发票日期与招待日期不一致"),
            Finding("陪同人数", "低", "陪同人数接近上限"),
        ]),
        DocumentReview("002_test.md", []),
    ]
    report = ReportGenerator.generate(reviews, "测试批次", "2026-06-10")
    assert "# 业务招待费审核报告" in report
    assert "001_test.md" in report
    assert "002_test.md" in report
    assert "高" in report
    assert "通过" in report
```

- [ ] **Step 2: 实现报告生成器**

```python
# src/expense_review/reporter.py
"""审核报告生成器"""
from .reviewer import DocumentReview

class ReportGenerator:
    @staticmethod
    def generate(reviews: list[DocumentReview], batch_name: str, batch_date: str) -> str:
        total = len(reviews)
        passed = sum(1 for r in reviews if not r.findings)
        at_risk = total - passed

        sections = [
            "# 业务招待费审核报告",
            "",
            "## 批次信息",
            f"- 批次: {batch_name}",
            f"- 时间: {batch_date}",
            f"- 文档数: {total}",
            "",
            "## 审核结果总览",
            f"- 通过: {passed} | 风险: {at_risk}",
            "",
            "## 逐文档审核",
        ]

        for review in reviews:
            sections.append(f"\n### {review.filename}")
            if not review.findings:
                sections.append("- [通过] 未发现风险")
            else:
                for f in review.findings:
                    sections.append(f"- [{f.level}] {f.rule}: {f.message}")
                    if f.detail:
                        sections.append(f"  - {f.detail}")

        # 风险汇总
        high = sum(1 for r in reviews for f in r.findings if f.level == "高")
        mid = sum(1 for r in reviews for f in r.findings if f.level == "中")
        low = sum(1 for r in reviews for f in r.findings if f.level == "低")
        hint = sum(1 for r in reviews for f in r.findings if f.level == "提示")

        sections.extend([
            "",
            "## 风险汇总",
            "| 风险等级 | 数量 |",
            "|---------|------|",
            f"| 高 | {high} |",
            f"| 中 | {mid} |",
            f"| 低 | {low} |",
            f"| 提示 | {hint} |",
        ])

        return "\n".join(sections)
```

- [ ] **Step 3: 运行测试**

Run: `python -m pytest tests/test_expense_review/test_reporter.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/expense_review/reporter.py tests/test_expense_review/test_reporter.py
git commit -m "feat: 实现审核报告生成器"
```

---

### Task 4: 实现 Webhook 通知

**Files:**
- Create: `src/expense_review/notifier.py`
- Test: `tests/test_expense_review/test_notifier.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_expense_review/test_notifier.py
from src.expense_review.notifier import WebhookNotifier

def test_build_payload():
    notifier = WebhookNotifier("")
    payload = notifier.build_payload("测试批次", 5, 2, 1)
    assert "测试批次" in str(payload)
    assert "5" in str(payload)
    assert "2" in str(payload)
```

- [ ] **Step 2: 实现通知器**

```python
# src/expense_review/notifier.py
"""Webhook 通知器 - 支持企微/钉钉"""
import json
from loguru import logger

class WebhookNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def build_payload(self, batch_name: str, total: int, passed: int, at_risk: int) -> dict:
        return {
            "msgtype": "text",
            "text": {
                "content": f"【审核报告】批次: {batch_name}\n文档数: {total}\n通过: {passed} | 风险: {at_risk}"
            },
        }

    def send(self, batch_name: str, total: int, passed: int, at_risk: int) -> bool:
        if not self.webhook_url:
            logger.info("未配置 webhook URL，跳过通知")
            return True

        try:
            import requests
            payload = self.build_payload(batch_name, total, passed, at_risk)
            resp = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info("审核通知已发送")
                return True
            else:
                logger.warning(f"通知发送失败: {resp.status_code}")
                return False
        except Exception as e:
            logger.warning(f"通知发送异常: {e}")
            return False
```

- [ ] **Step 3: 运行测试**

Run: `python -m pytest tests/test_expense_review/test_notifier.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/expense_review/notifier.py tests/test_expense_review/test_notifier.py
git commit -m "feat: 实现 webhook 通知器"
```

---

### Task 5: 实现审核入口脚本

**Files:**
- Create: `scripts/review_batch.py`
- Modify: `scripts/batch_parse.py:127-128`

- [ ] **Step 1: 创建审核脚本**

```python
# scripts/review_batch.py
"""审核指定批次的业务招待费报销单据"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.expense_review import ExpenseReviewer, ReportGenerator, WebhookNotifier
from src.expense_review.reviewer import DocumentReview
from loguru import logger

def review_batch(results_dir: Path, batch_name: str, webhook_url: str = ""):
    reviewer = ExpenseReviewer()
    md_files = sorted(results_dir.glob("*.md"))

    if not md_files:
        logger.warning(f"未找到 Markdown 文件: {results_dir}")
        return

    reviews = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        findings = reviewer.review(content)
        reviews.append(DocumentReview(md_file.name, findings))

    report = ReportGenerator.generate(reviews, batch_name, datetime.now().strftime("%Y-%m-%d"))

    # 写入审核报告
    report_path = results_dir.parent / "审核报告.md"
    report_path.write_text(report, encoding="utf-8")
    logger.info(f"审核报告已生成: {report_path}")

    # 发送通知
    if webhook_url:
        notifier = WebhookNotifier(webhook_url)
        passed = sum(1 for r in reviews if not r.findings)
        notifier.send(batch_name, len(reviews), passed, len(reviews) - passed)

def main():
    parser = argparse.ArgumentParser(description="审核业务招待费报销单据")
    parser.add_argument("-d", "--dir", type=Path, help="识别结果目录")
    parser.add_argument("-n", "--name", type=str, default="", help="批次名称")
    parser.add_argument("-w", "--webhook", type=str, default="", help="Webhook URL")
    args = parser.parse_args()

    if args.dir:
        review_batch(args.dir, args.name or "手动审核", args.webhook)
    else:
        logger.info("用法: python scripts/review_batch.py -d <识别结果目录> -n <批次名>")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证脚本可运行**

Run: `python scripts/review_batch.py --help`
Expected: 显示帮助信息

- [ ] **Step 3: 在 batch_parse.py 中添加审核 hook**

在 `scripts/batch_parse.py` 的 `parse_all()` 函数末尾（`logger.info(f"Output: {output_dir}")` 之前）添加：

```python
    # 自动审核
    try:
        from src.expense_review import ExpenseReviewer, ReportGenerator
        from src.expense_review.reviewer import DocumentReview
        from datetime import datetime as dt

        results_dir = output_dir / "识别结果"
        if results_dir.exists():
            reviewer = ExpenseReviewer()
            reviews = []
            for md_file in sorted(results_dir.glob("*.md")):
                content = md_file.read_text(encoding="utf-8")
                findings = reviewer.review(content)
                reviews.append(DocumentReview(md_file.name, findings))

            report = ReportGenerator.generate(
                reviews, summary, dt.now().strftime("%Y-%m-%d")
            )
            (output_dir / "审核报告.md").write_text(report, encoding="utf-8")
            logger.info(f"审核报告已生成: {output_dir / '审核报告.md'}")
    except Exception as e:
        logger.warning(f"自动审核失败: {e}")
```

- [ ] **Step 4: Commit**

```bash
git add scripts/review_batch.py scripts/batch_parse.py
git commit -m "feat: 添加审核入口脚本，解析后自动生成审核报告"
```

---

### Task 6: 创建 Claude Code Skill 定义

**Files:**
- Create: `.claude/skills/generate-expense-review-skill/SKILL.md`

- [ ] **Step 1: 创建 Skill**

```markdown
---
name: generate-expense-review-skill
description: 基于 OCR 解析结果生成业务招待费审核报告。使用场景：解析完成后自动触发，或手动对历史批次进行审核。
---

对 OCR 解析后的 Markdown 文档进行业务招待费合规审核。

## 审核流程

1. 读取 `data/已识别/{批次}/识别结果/` 下的所有 Markdown 文件
2. 对每个文档运行规则检查（见下方规则列表）
3. 对模糊项进行 LLM 语义判断
4. 生成 `审核报告.md` 写入批次目录

## 审核规则

### 高风险规则
- 发票日期 ≠ 招待日期
- 申请日期 > 招待日期（事后审批且无办公室会签）
- 陪同人数超标（≤5人对等，>5人超1/2）
- 2024/4/1 后缺少支付凭证
- 2025/12/4 后外部招待缺少往来公函

### 中风险规则
- 重大节日前后3个工作日内安排招待且未报备
- 招待对象与招待类型不匹配
- 来宾单位经营状态异常
- 2025/6/1 前缺少发票查验

### LLM 判断项
- 招待事由是否合理（结合招待对象、事由描述判断）
- 是否存在虚假招待迹象（金额、频率、地点异常）
- 是否混淆费用（会议费、市场营销费混入招待费）

## 报告格式

输出到 `data/已识别/{批次}/审核报告.md`，格式：

```markdown
# 业务招待费审核报告

## 批次信息
- 批次: {name}
- 时间: {date}
- 文档数: {count}

## 审核结果总览
- 通过: {n} | 风险: {n}

## 逐文档审核
### {filename}
- [{level}] {rule}: {message}

## 风险汇总
| 风险等级 | 数量 |
|---------|------|
| 高 | {n} |
| 中 | {n} |
```

## 执行方式

```bash
python scripts/review_batch.py -d <识别结果目录> -n <批次名>
```

或在 `batch_parse.py` 解析完成后自动生成。
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/generate-expense-review-skill/SKILL.md
git commit -m "feat: 创建 expense review Claude Code skill"
```

---

### Task 7: 更新 OpenSpec 任务与集成测试

**Files:**
- Create: `openspec/changes/generate-expense-review-skill/tasks.md`
- Create: `openspec/changes/generate-expense-review-skill/design.md`
- Create: `openspec/changes/generate-expense-review-skill/specs/expense-review/spec.md`

- [ ] **Step 1: 创建 tasks.md**

```markdown
## 1. 包结构

- [x] 1.1 创建 src/expense_review/ 包
- [x] 1.2 导出 ExpenseReviewer, ReportGenerator, WebhookNotifier

## 2. 审核规则引擎

- [x] 2.1 实现日期一致性检查
- [x] 2.2 实现陪同人数检查
- [x] 2.3 实现支付凭证检查
- [x] 2.4 实现往来公函检查
- [x] 2.5 实现发票查验检查
- [x] 2.6 实现节日招待检查

## 3. 报告生成

- [x] 3.1 实现审核报告 Markdown 生成
- [x] 3.2 风险汇总统计

## 4. 通知

- [x] 4.1 实现 Webhook 通知器

## 5. 集成

- [x] 5.1 创建 review_batch.py 入口脚本
- [x] 5.2 在 batch_parse.py 中集成自动审核
- [x] 5.3 创建 Claude Code Skill 定义

## 6. 测试

- [x] 6.1 单元测试：审核规则
- [x] 6.2 单元测试：报告生成
- [x] 6.3 单元测试：通知器
```

- [ ] **Step 2: 创建 design.md**

引用 `docs/superpowers/specs/2026-06-10-expense-review-skill-design.md` 的内容。

- [ ] **Step 3: 创建 spec**

```markdown
# Expense Review Spec

## 需求

系统必须在 OCR 解析完成后自动对业务招待费报销单据进行审核，生成审核报告。

### 规则

- 日期一致性：发票日期必须等于招待日期
- 事前审批：申请日期不得晚于招待日期
- 陪同人数：不得超过招待标准的陪同人数限制
- 支付凭证：2024/4/1 后必须有支付凭证
- 往来公函：2025/12/4 后外部招待必须有往来公函
- 发票查验：2025/6/1 前需要发票查验
- 节日招待：重大节日前后 3 个工作日内需报备

### 输出

- 审核报告写入批次目录
- 支持 webhook 通知
```

- [ ] **Step 4: 运行完整测试**

Run: `python -m pytest tests/test_expense_review/ -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add openspec/changes/generate-expense-review-skill/
git commit -m "feat: 完成 expense review skill 的 openspec 文档"
```

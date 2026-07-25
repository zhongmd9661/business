"""全面审核报告生成器 — 按规则类别分组展示"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .models import Finding, RuleCategory, BatchFinding, BatchReviewReport


def _fmt_elapsed(seconds: float) -> str:
    """格式化运行时间为可读字符串"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}秒"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}分{secs:.1f}秒"


@dataclass
class CategoryReport:
    """单个规则类别的报告"""
    category: RuleCategory
    findings: list[Finding] = field(default_factory=list)
    rules_checked: int = 0
    rules_skipped: int = 0
    skip_reasons: list[str] = field(default_factory=list)

    @property
    def has_high(self) -> bool:
        return any(f.level == "高" for f in self.findings)

    @property
    def has_medium(self) -> bool:
        return any(f.level == "中" for f in self.findings)


@dataclass
class ComprehensiveReport:
    """完整审核报告"""
    filename: str
    category_reports: list[CategoryReport] = field(default_factory=list)
    all_findings: list[Finding] = field(default_factory=list)

    @property
    def has_high_risk(self) -> bool:
        return any(f.level == "高" for f in self.all_findings)

    @property
    def total_rules_checked(self) -> int:
        return sum(cr.rules_checked for cr in self.category_reports)

    @property
    def total_rules_skipped(self) -> int:
        return sum(cr.rules_skipped for cr in self.category_reports)


class ComprehensiveReporter:
    """生成按规则类别分组的审核报告"""

    def generate(self, findings: list[Finding], filename: str = "",
                 rules_checked: int = 0, rules_skipped: int = 0,
                 skip_reasons: list[str] | None = None) -> ComprehensiveReport:
        report = ComprehensiveReport(filename=filename)
        report.all_findings = findings

        # 按类别分组
        by_category: dict[RuleCategory, list[Finding]] = defaultdict(list)
        for f in findings:
            by_category[f.category].append(f)

        # 为每个类别创建报告段
        for category in RuleCategory:
            cat_findings = by_category.get(category, [])
            cr = CategoryReport(
                category=category,
                findings=cat_findings,
                rules_checked=rules_checked // len(RuleCategory) if rules_checked > 0 else 0,
                rules_skipped=rules_skipped // len(RuleCategory) if rules_skipped > 0 else 0,
                skip_reasons=skip_reasons or [],
            )
            report.category_reports.append(cr)

        return report

    def format_text(self, report: ComprehensiveReport) -> str:
        """生成可读的文本报告"""
        lines: list[str] = []
        lines.append("=" * 70)
        lines.append(f"全面业务招待费审核报告 — {report.filename or '未命名文档'}")
        lines.append("=" * 70)

        # 总体风险判定
        risk = "存在高风险" if report.has_high_risk else "无高风险"
        lines.append(f"\n【总体判定】{risk}")
        lines.append(f"发现问题: {len(report.all_findings)} 条")
        lines.append(f"规则覆盖率: {report.total_rules_checked} 已检查 / {report.total_rules_skipped} 已跳过")

        # 按类别展示
        for cr in report.category_reports:
            if not cr.findings:
                continue
            lines.append(f"\n--- [{cr.category.value}] {len(cr.findings)} 个问题 ---")
            for i, finding in enumerate(cr.findings, 1):
                lines.append(
                    f"  {i}. [{finding.level}] {finding.rule}: {finding.message}"
                )
                if finding.detail:
                    lines.append(f"     详情: {finding.detail}")
                lines.append(f"     依据: {finding.clause}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def format_summary(self, report: ComprehensiveReport) -> str:
        """生成简要摘要"""
        parts: list[str] = []
        parts.append(f"文档: {report.filename or '未命名'}")
        parts.append(f"风险: {'高风险' if report.has_high_risk else '无高风险'}")
        parts.append(f"问题: {len(report.all_findings)} 条")

        by_level = defaultdict(int)
        for f in report.all_findings:
            by_level[f.level] += 1
        level_parts = []
        for lvl in ("高", "中", "低", "提示"):
            if by_level[lvl]:
                level_parts.append(f"{lvl}: {by_level[lvl]}")
        if level_parts:
            parts.append(f"分级: {', '.join(level_parts)}")

        return " | ".join(parts)

    def generate_batch(self, report: BatchReviewReport) -> BatchReviewReport:
        """批次审核报告（报告已由 check_batch_review 组装，此方法仅做后处理）"""
        return report

    def format_batch_text(self, report: BatchReviewReport) -> str:
        """生成批次审核报告文本，按类别直接列出问题（不逐文档分组）"""
        lines: list[str] = []
        lines.append("=" * 70)
        lines.append(f"全面业务招待费审核报告 — 批次: {report.batch_name}")
        lines.append("=" * 70)

        # 批次信息
        lines.append(f"\n【批次信息】")
        lines.append(f"  文档数: {report.document_count}")
        if report.department:
            lines.append(f"  部门: {report.department}")
        if report.reception_type:
            lines.append(f"  招待类型: {report.reception_type}")

        # 总体风险判定
        risk = "存在高风险" if report.has_high_risk else "无高风险"
        lines.append(f"\n【总体判定】{risk}")
        lines.append(f"发现问题: {len(report.all_findings)} 条")

        by_level = defaultdict(int)
        for f in report.all_findings:
            by_level[f.level] += 1
        level_parts = []
        for lvl in ("高", "中", "低", "提示"):
            if by_level[lvl]:
                level_parts.append(f"{lvl}: {by_level[lvl]}")
        if level_parts:
            lines.append(f"分级: {', '.join(level_parts)}")

        # 按类别展示
        for cr in report.category_reports:
            if not cr.findings:
                continue
            lines.append(f"\n--- [{cr.category.value}] {len(cr.findings)} 个问题 ---")
            for finding in cr.findings:
                lines.append(f"  [{finding.level}] {finding.rule}: {finding.message}")
                lines.append(f"   依据: {finding.clause}")

        # 对比表
        if report.comparison_rows:
            lines.append(self._format_comparison_text_table(report.comparison_rows))

        # 运行时间
        if report.elapsed_seconds is not None:
            lines.append(f"\n【运行时间】{_fmt_elapsed(report.elapsed_seconds)}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def _format_comparison_text_table(self, rows: list[dict[str, str]]) -> str:
        """生成本地审核字段对比表（文本格式，按文档分组）"""
        lines: list[str] = []
        lines.append("\n【字段对比表】")

        display_names = {
            'doc_type': '文档类型',
            'filename': '文件名',
        }

        for row in rows:
            doc_type = row.get('doc_type', '')
            filename = row.get('filename', '')
            lines.append(f"\n  ┌─ [{doc_type}] {filename}")
            lines.append(f"  │")
            for key, val in row.items():
                if key in ('doc_type', 'filename'):
                    continue
                if not val:
                    continue
                label = display_names.get(key, key)
                lines.append(f"  │ {label}: {val}")
            lines.append(f"  └─")

        return "\n".join(lines)

    def format_batch_md(self, report: BatchReviewReport) -> str:
        """生成批次审核报告的 Markdown 格式，按类别直接列出问题"""
        lines: list[str] = []
        lines.append(f"# 全面业务招待费审核报告")
        lines.append(f"\n> 批次: {report.batch_name}\n")

        # 批次信息
        lines.append("## 批次信息")
        lines.append(f"- **文档数**: {report.document_count}")
        if report.department:
            lines.append(f"- **部门**: {report.department}")
        if report.reception_type:
            lines.append(f"- **招待类型**: {report.reception_type}")

        # 总体风险判定
        risk_label = "存在高风险" if report.has_high_risk else "无高风险"
        lines.append(f"\n## 总体判定\n\n**{risk_label}**\n")
        lines.append(f"- 发现问题: {len(report.all_findings)} 条")
        by_level = defaultdict(int)
        for f in report.all_findings:
            by_level[f.level] += 1
        level_parts = []
        for lvl in ("高", "中", "低", "提示"):
            if by_level[lvl]:
                level_parts.append(f"**{lvl}**: {by_level[lvl]}")
        if level_parts:
            lines.append(f"- 分级: {', '.join(level_parts)}")

        # 按类别展示
        lines.append("\n---\n")
        for cr in report.category_reports:
            if not cr.findings:
                continue
            lines.append(f"## [{cr.category.value}] ({len(cr.findings)} 个问题)\n")
            for finding in cr.findings:
                lines.append(f"- **[{finding.level}] {finding.rule}**: {finding.message}")
                lines.append(f"  - 依据: {finding.clause}")
            lines.append("")

        # 对比表
        if report.comparison_rows:
            lines.append(self._format_comparison_md_table(report.comparison_rows))

        # 运行时间
        if report.elapsed_seconds is not None:
            lines.append(f"\n> 运行时间: {_fmt_elapsed(report.elapsed_seconds)}\n")

        return "\n".join(lines)

    def _format_comparison_md_table(self, rows: list[dict[str, str]]) -> str:
        """生成本地审核字段对比表（Markdown 格式）"""
        lines: list[str] = []
        lines.append("---\n")
        lines.append("## 字段对比表\n")

        # 定义列顺序
        columns = [
            'doc_type', 'filename',
            '发票金额(大写)', '发票金额(小写)', '审批金额', '支付凭证金额',
            '支付证明金额', '报账金额',
            '开票日期', '招待日期', '支付日期', '交易日期', '活动日期',
            '招待人数', '陪同人数', '人均费用', '招待类型', '是否工作餐',
            '交易单号', '商户单号', '商户全称', '招待对象',
        ]

        display_names = {
            'doc_type': '文档类型',
            'filename': '文件名',
        }

        # 收集所有字段并过滤
        all_keys = list(columns)
        for row in rows:
            for k in row:
                if k not in all_keys:
                    all_keys.append(k)
        visible_cols = [c for c in all_keys if any(c in r for r in rows)]

        # 表头
        header_parts = [display_names.get(c, c) for c in visible_cols]
        lines.append("| " + " | ".join(header_parts) + " |")
        lines.append("| " + " | ".join("---" for _ in visible_cols) + " |")

        # 数据行
        for row in rows:
            cell_parts = [row.get(c, '') or '' for c in visible_cols]
            lines.append("| " + " | ".join(cell_parts) + " |")

        lines.append("")
        return "\n".join(lines)

    def format_batch_summary(self, report: BatchReviewReport) -> str:
        """生成批次审核简要摘要"""
        parts: list[str] = []
        parts.append(f"批次: {report.batch_name}")
        parts.append(f"文档: {report.document_count}")
        parts.append(f"风险: {'高风险' if report.has_high_risk else '无高风险'}")
        parts.append(f"问题: {len(report.all_findings)} 条")

        by_level = defaultdict(int)
        for f in report.all_findings:
            by_level[f.level] += 1
        level_parts = []
        for lvl in ("高", "中", "低", "提示"):
            if by_level[lvl]:
                level_parts.append(f"{lvl}: {by_level[lvl]}")
        if level_parts:
            parts.append(f"分级: {', '.join(level_parts)}")

        return " | ".join(parts)

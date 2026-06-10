## Why

现有 `ExpenseReviewer` 仅覆盖 6 条基础审核规则（日期一致性、陪同人数、支付凭证、往来公函、发票查验、节日招待），但 `00规则制度` 中的《业务招待费审查风险点》和《业务招待费管理办法（V9.0）》包含约 40 条审查要点。大量规则缺失导致审核不完整，高风险问题可能被遗漏。

## What Changes

- 在 `src/expense_review_comprehensive/` 下创建独立代码包，不修改现有 `expense_review` 代码
- 实现覆盖制度全部审查要点的规则引擎，包括：金额标准校验、招待类型匹配、禁止性规定、报销资料完整性、企业经营状态、拆分报销检测、重复招待检测等
- 从 OCR 解析结果中结构化提取审核所需字段（金额、招待类型、人员层级、供应商信息等）
- 生成覆盖全部规则的审核报告

## Capabilities

### New Capabilities

- `comprehensive-rule-engine`: 覆盖制度全部审查要点的规则引擎，按类别组织（单据完整性、金额标准、招待类型、禁止性规定、报销合规、交叉稽核）
- `ocr-field-extraction`: 从 OCR 解析的 Markdown 文本中提取审核所需结构化字段（金额、日期、人员、供应商、招待类型等）
- `comprehensive-review-report`: 按规则类别分组的审核报告，支持逐条规则命中情况展示

### Modified Capabilities

无 — 新代码包独立于现有模块，不修改已有代码。

## Impact

- **新增代码包**: `src/expense_review_comprehensive/`（独立于 `src/expense_review/`）
- **新增测试**: `tests/test_expense_review_comprehensive/`
- **规则来源**: `00规则制度/` 目录下的两份制度文档
- **不修改**: 现有 `expense_review` 模块、`batch_parse.py`、MinerU 引擎代码

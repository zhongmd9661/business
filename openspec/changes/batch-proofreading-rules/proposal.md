## Why

当前批次审核流程已有 6 个 checker 类别（文档完整性、金额标准、招待类型、禁止项、报销合规、交叉稽核），但缺少**跨文档一致性校验**。同一笔报销的多个文档之间可能存在金额不一致、日期矛盾、支付信息不匹配等问题，这些问题无法通过逐文档审核发现。

具体缺失：
- 发票金额与其他单据金额是否一致无法校验
- 各文档日期之间的逻辑关系（发票日期应在招待日期前、支付日期应在招待日期后）无法校验
- 支付凭证与支付证明之间的交易信息一致性无法校验
- 招待单位经营状态的文本匹配与人工审核标记缺失
- 活动函件日期与其他文档日期的关联无法校验

## What Changes

- 新增 `ProofreadingChecker` 类，实现 6 条校对规则
- 规则定义在 `校对规则/校对规则.md` 中，代码与之对应
- 在 `ComprehensiveChecker` 中集成 `ProofreadingChecker`
- 扩展 `RuleCategory` 枚举，新增 `PROOFREADING` 类别
- 校对规则结果纳入批次审核报告

## Capabilities

### New Capabilities

- `proofreading-checker`: 跨文档一致性校验，包括金额、日期、支付信息、单位经营状态、活动函件日期
- `proofreading-report`: 校对规则发现纳入批次审核报告，按 PROOFREADING 分类展示

### Modified Capabilities

- `ComprehensiveChecker`: 集成 ProofreadingChecker 到批次审核流程
- `RuleCategory`: 新增 PROOFREADING 枚举值

## Impact

- **新增**: `src/expense_review_comprehensive/proofreading_checker.py`（6 条校对规则实现）
- **修改**: `src/expense_review_comprehensive/checkers.py`（集成 ProofreadingChecker）
- **修改**: `src/expense_review_comprehensive/models.py`（新增 RuleCategory.PROOFREADING）
- **新增**: `校对规则/校对规则.md`（规则定义文档）
- **不修改**: `extractor.py`、`llm_extractor.py`、`reporter.py`（字段提取与报告格式不变）

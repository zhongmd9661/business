## Why

原项目分 5 个独立 change 逐步建设业务招待费审核系统，各 change 已完成开发。现整合为单一 change，便于编写项目汇总材料。

**原始 5 个 change：**
1. `batch-expense-review` — 批次统一审核（取代逐文档审核）
2. `llm-field-extraction` — LLM 字段提取（替代正则提取）
3. `batch-proofreading-rules` — 跨文档校对规则
4. `convert-rules-to-md` — 规则制度 docx → Markdown
5. `generate-rules-skill` — 规则文档 → Claude Code skill

**整合原因：**
- 5 个 change 共同构成完整系统，存在交叉依赖（如 LLM 提取依赖 skill 规则、批次审核依赖校对规则）
- 汇总材料需要统一的视角，而非分散的变更记录
- 所有任务已完成，整合为归档状态便于追溯

## What Changes

整合后的 change 覆盖完整系统：

| 模块 | 变更 |
|------|------|
| **规则制度数字化** | docx → Markdown → Claude Code skill，建立规则与批次的自动关联 |
| **OCR 解析** | MinerU 引擎解析 PDF/图片/Office/XML，输出 Markdown + JSON + 图片 |
| **字段提取** | 规则提取（正则）+ LLM 提取（Anthropic API），通过环境变量切换 |
| **批次审核** | 7 类 checker（完整性/金额/招待/禁止/合规/交叉/校对），批次级统一判定 |
| **报告输出** | 审核报告.txt + 审核报告.md，含字段对比表与分类问题 |
| **告警通知** | Webhook 推送高风险发现 |

## Capabilities

### New Capabilities

- `rule-digitalization`: 规则制度 docx → Markdown → skill 的完整数字化链路
- `llm-field-extraction`: 基于本地大模型的语义字段提取
- `batch-review`: 批次级统一审核上下文与聚合指标计算
- `proofreading-checker`: 跨文档一致性校验（金额/日期/支付/单位/函件）
- `batch-reporting`: 批次审核报告（txt + md），含字段对比表
- `webhook-alerting`: 高风险发现自动推送

### Modified Capabilities

- `batch_parse.py`: 完整流程串联（OCR → 提取 → 审核 → 报告 → 告警）
- `ComprehensiveChecker`: 集成 7 类 checker，含批次聚合逻辑
- `OutputOrganizer`: 目录扁平化，JSON/图片分离

## Impact

### 新增文件
- `src/expense_review_comprehensive/llm_extractor.py`
- `src/expense_review_comprehensive/proofreading_checker.py`
- `skill/expense-review-rules/SKILL.md`
- `skill/00综合部业务招待费/SKILL.md`
- `校对规则/校对规则.md`
- `scripts/convert_rules.py`

### 修改文件
- `src/expense_review_comprehensive/__init__.py`
- `src/expense_review_comprehensive/models.py`
- `src/expense_review_comprehensive/checkers.py`
- `src/expense_review_comprehensive/reporter.py`
- `scripts/batch_parse.py`
- `src/output_visualization/organizer.py`
- `src/document_parsing_pipeline/engine.py`

### 不修改文件
- `src/expense_review_comprehensive/extractor.py`（规则提取保留）
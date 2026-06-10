## Why

`expense_review` 模块的审核规则引擎已完成，但报告生成（`ReportGenerator`）和通知（`WebhookNotifier`）两个核心组件仍为空存根，审核结果无法输出为可读报告，也无法在发现高风险问题时及时告警，整个审核流程不完整。

## What Changes

- 实现 `ReportGenerator` — 汇总多文档审核结果，生成 Markdown 格式的审核报告（含风险统计、逐文档明细、高风险清单）
- 实现 `WebhookNotifier` — 发现高风险问题时通过 Webhook 发送告警通知
- 将审核流程接入批量处理管道，实现"解析 → 审核 → 报告 → 通知"的完整链路
- 为 `ReportGenerator` 和 `WebhookNotifier` 补充单元测试

## Capabilities

### New Capabilities

- `expense-report-generation`: 审核报告生成功能，汇总所有文档的审核发现并输出 Markdown 报告，包含风险等级统计、逐文档明细、高风险问题清单
- `expense-webhook-notification`: Webhook 告警通知功能，在发现高风险问题时自动发送通知到配置的目标地址

### Modified Capabilities

无 — 当前项目无现有规范。

## Impact

- **代码**: `src/expense_review/reporter.py`、`src/expense_review/notifier.py` 从空存根变为完整实现
- **集成**: 批量处理脚本 `scripts/batch_parse.py` 需支持审核后自动触发报告生成和通知
- **测试**: 新增 `tests/test_expense_review/test_reporter.py`、`tests/test_expense_review/test_notifier.py`
- **依赖**: 需 `requests` 库用于 Webhook 调用（如尚未安装）

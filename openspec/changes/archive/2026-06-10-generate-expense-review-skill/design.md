## Context

当前 `expense_review` 模块有完整的规则引擎（`ExpenseReviewer`），能对单文档进行合规性检查。但 `ReportGenerator` 和 `WebhookNotifier` 为空存根，审核结果无法输出为报告或发送告警。本项目需要补全这两个组件，使审核流程闭环。

## Goals / Non-Goals

**Goals:**
- 实现 `ReportGenerator`，支持汇总多文档审核结果并生成 Markdown 报告
- 实现 `WebhookNotifier`，发现高风险问题时发送 Webhook 告警
- 报告应包含风险统计、逐文档明细、高风险问题清单

**Non-Goals:**
- 不实现审核规则引擎本身（已完成）
- 不提供 Web UI 或数据库存储
- 不处理审核结果的审批工作流

## Decisions

- **报告格式选 Markdown**: 与项目已有的输出格式一致，便于直接查看和归档
- **Webhook _notifier_ 只负责发送**: 不管理 webhook 配置持久化，配置通过参数传入。保持职责单一
- **报告生成器接收 `list[Finding]` 列表**: 不直接依赖文档内容，只处理审核发现。与 reviewer 解耦
- **Webhook 使用 `requests` 库**: 轻量 HTTP 客户端，Python 生态标准选择

## Risks / Trade-offs

- [Webhook 目标不可达] → 发送失败记录到报告，不中断审核流程
- [网络超时] → Webhook 调用设 10 秒超时，失败不阻塞批量处理

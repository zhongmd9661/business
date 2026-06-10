## 1. 实现 ReportGenerator

- [x] 1.1 实现 `ReportGenerator.generate()` 方法，接收 `list[tuple[str, list[Finding]]]`（文档名-发现对）生成 Markdown 报告
- [x] 1.2 添加报告头部元数据（生成时间、文档总数、总体风险判定）
- [x] 1.3 添加风险等级统计区（高、中、低、提示各级数量）
- [x] 1.4 添加逐文档明细区，无问题的文档标记为"通过"
- [x] 1.5 添加高风险问题汇总清单，注明来源文档

## 2. 实现 WebhookNotifier

- [x] 2.1 实现 `WebhookNotifier.__init__(url)` 接收目标地址
- [x] 2.2 实现 `WebhookNotifier.notify(findings, filename)` 方法，仅对高风险问题发送 POST 请求
- [x] 2.3 添加 10 秒超时和异常捕获，发送失败不中断流程
- [x] 2.4 告警载荷包含文档名、风险规则、问题描述、发现时间

## 3. 单元测试

- [x] 3.1 创建 `tests/test_expense_review/test_reporter.py` — 测试报告生成的统计、明细、清单、元数据
- [x] 3.2 创建 `tests/test_expense_review/test_notifier.py` — 测试通知发送、无高风险不发送、失败不中断（Mock HTTP）

## 4. 集成到批量处理管道

- [x] 4.1 在批量处理流程中接入审核步骤，解析后对每个文档运行 `ExpenseReviewer`
- [x] 4.2 审核完成后调用 `ReportGenerator` 生成报告，有高风险时触发 `WebhookNotifier`

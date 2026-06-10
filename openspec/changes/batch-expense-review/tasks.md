## 1. 定义批次审核数据结构

- [x] 1.1 在 `models.py` 新增 `BatchReviewContext` dataclass（文档列表、聚合指标：总费用、总人数、部门、招待类型等）
- [x] 1.2 在 `models.py` 新增 `BatchReviewReport` dataclass（批次总体判定、分类报告、跨文档发现）

## 2. 实现批次审核方法

- [x] 2.1 在 `ComprehensiveChecker` 新增 `check_batch_review()` 方法，接收 `list[ExtractedFields]` 和文件名列表
- [x] 2.2 构建 `BatchReviewContext`，聚合各文档字段为批次级指标
- [x] 2.3 单文档规则（单据完整性、禁止性规定）逐文档运行，结果标注来源文档
- [x] 2.4 聚合规则（金额标准、陪同人数）基于批次上下文运行
- [x] 2.5 跨文档规则（拆分报销、重复招待、差旅地校验）纳入报告

## 3. 实现批次报告生成

- [ ] 3.1 在 `ComprehensiveReporter` 新增 `generate_batch()` 方法
- [ ] 3.2 在 `ComprehensiveReporter` 新增 `format_batch_text()` 方法，按类别 + 文档分组展示
- [ ] 3.3 批次报告包含批次信息头（文档数、部门、招待类型）+ 总体判定 + 分类问题

## 4. 修改 batch_parse.py 审核流程

- [x] 4.1 将逐文档 `check_single()` 调用替换为 `check_batch_review()`
- [x] 4.2 移除逐文档报告生成，改为生成单份批次报告
- [x] 4.3 批次报告输出到 `审核报告.txt`，同时保留逐文档简要摘要日志
- [x] 4.4 Webhook 通知应在批次审核完成后，基于总体判定触发

## 5. 单元测试

- [x] 5.1 测试 `BatchReviewContext` 聚合指标计算
- [x] 5.2 测试 `check_batch_review()` 返回结果包含单文档 + 跨文档发现
- [x] 5.3 测试批次报告格式化输出

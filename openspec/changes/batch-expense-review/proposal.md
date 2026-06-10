## Why

当前审核流程对每个 OCR 识别文件独立运行 `check_single()`，生成逐文档的审核报告。但实际业务中，同一批次的所有页属于**同一笔业务招待费报销**，应当作为整体审核。逐文档审核导致：

- 费用总额、陪同人数等跨文档聚合指标无法计算
- 拆分报销检测仅在 `check_batch` 的跨文档部分运行，结果只写入日志不进入报告
- 审核结论分散在多个文件中，缺乏批次级别的总体判定

## What Changes

- 在 `ComprehensiveChecker` 新增 `check_batch_review()` 方法，将同批次所有文档的提取字段作为整体审核上下文
- 新增 `BatchReviewReport` 数据结构，支持批次级别总体判定 + 逐文档问题明细
- `ComprehensiveReporter` 新增批次报告生成与格式化方法
- 修改 `batch_parse.py` 的审核流程：调用 `check_batch_review()` 替代逐文档 `check_single()`，生成一份批次审核报告

## Capabilities

### New Capabilities

- `batch-review`: 将同批次所有文档作为整体审核上下文，计算跨文档聚合指标（总费用、总陪同人数等），统一生成批次审核报告
- `batch-review-report`: 批次级别审核报告，包含总体判定、逐文档问题明细、跨文档检测结果

### Modified Capabilities

- `batch_parse.py`: 审核部分从逐文档循环改为调用 `check_batch_review()`，输出改为单份批次报告

## Impact

- **新增**: `src/expense_review_comprehensive/batch_review.py`（批次审核上下文、报告结构）
- **修改**: `src/expense_review_comprehensive/checkers.py`（新增 `check_batch_review` 方法，含聚合指标计算）
- **修改**: `src/expense_review_comprehensive/reporter.py`（新增批次报告格式化）
- **修改**: `scripts/batch_parse.py`（审核流程改为批次统一审核）
- **不修改**: `extractor.py`、`models.py`（字段提取与数据结构不变）

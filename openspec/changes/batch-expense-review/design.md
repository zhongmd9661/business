## Context

当前 `batch_parse.py` 的审核流程是逐文档调用 `check_single()`，然后单独调用 `check_batch()` 仅做跨文档检测。同一批次的所有页属于同一笔报销，需要整体审核。

## Goals / Non-Goals

**Goals:**
- 将同批次所有文档的提取字段整合为批次审核上下文
- 计算跨文档聚合指标（总费用、总陪同人数、总招待人数等）
- 基于聚合指标重新校验金额标准、陪同人数等规则
- 生成一份批次级别审核报告，包含总体判定 + 逐文档问题明细
- 跨文档检测结果（拆分报销、重复招待）纳入正式报告

**Non-Goals:**
- 不修改字段提取逻辑（`extractor.py` 不变）
- 不修改单文档规则定义（`checkers.py` 的 checker 类不变）
- 不影响 Webhook 通知机制

## Decisions

### 批次审核上下文 `BatchReviewContext`

新增 dataclass，聚合同批次所有文档的字段：

```python
@dataclass
class BatchReviewContext:
    documents: list[tuple[str, ExtractedFields]]  # (文件名, 字段)
    total_amount: float  # 所有文档金额合计
    total_guest_count: int  # 所有文档招待人数合计
    total_companion_count: int  # 所有文档陪同人数合计
    department: str  # 统一部门（取第一个非空值）
    reception_type: str  # 统一招待类型
    apply_date: datetime  # 最早申请日期
    reception_date: datetime  # 最早招待日期
```

### 审核流程变更

1. **单文档规则**（单据完整性、禁止性规定）仍逐文档运行，但结果归集到批次报告
2. **聚合规则**（金额标准、陪同人数）基于 `BatchReviewContext` 的聚合指标运行
3. **跨文档规则**（拆分报销、重复招待）同现有 `check_batch` 逻辑
4. 所有结果统一归入 `BatchReviewReport`

### 报告结构

```
全面业务招待费审核报告 — 批次: 测试

【批次信息】
  文档数: 5
  部门: xxx
  招待类型: xxx

【总体判定】存在高风险 / 无高风险

--- [单据完整性] ---
  [文档 1_302138C55260305001-0001.md]
    [中] 费用明细清单: 缺少费用明细清单
  [文档 2_302138C55260305001-0002.md]
    ...

--- [金额标准] ---
  [批次总计]
    [高] 总招待金额 4200 元超出标准 3000 元

--- [禁止性规定] ---
  [文档 5_302138C55260305001-0005.md]
    [高] 公款送礼: ...
```

### 影响范围

| 文件 | 变更 |
|------|------|
| `models.py` | 新增 `BatchReviewContext`, `BatchReviewReport` |
| `checkers.py` | 新增 `check_batch_review()` 方法 |
| `reporter.py` | 新增 `generate_batch()`, `format_batch_text()` |
| `batch_parse.py` | 审核流程改为批次统一审核 |

## Risks / Trade-offs

- [聚合指标可能因 OCR 误差偏大] → 金额/人数聚合时跳过 `None` 值，仅汇总有效数据
- [批次报告可能过长] → 按类别 + 文档分组，无问题的文档不展示
- [向后兼容] → 保留 `check_single()` 和 `check_batch()` 接口不变

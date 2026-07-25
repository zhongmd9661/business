## Context

现有 `ComprehensiveChecker` 包含 6 个 checker 子类，覆盖文档完整性、金额标准、招待类型、禁止项、报销合规、交叉稽核。但所有规则都是单文档级别的，缺少跨文档一致性校验。

校对规则（`校对规则/校对规则.md`）定义了 6 条跨文档校验规则，需要在批次审核阶段执行。

## Goals / Non-Goals

**Goals:**
- 实现 6 条校对规则，覆盖金额一致性、日期一致性、招待标准、单位经营状态、支付凭证一致性、活动函件日期
- 规则与 `校对规则/校对规则.md` 中的定义一一对应
- 集成到 `ComprehensiveChecker` 的批次审核流程
- 校对规则发现纳入批次审核报告

**Non-Goals:**
- 不修改字段提取逻辑
- 不修改现有 6 个 checker 类别的规则
- 不影响 Webhook 通知机制

## Decisions

### ProofreadingChecker 设计

独立类，接收同批次所有文档的 `ExtractedFields` 列表，执行跨文档校验：

```python
class ProofreadingChecker:
    def check(self, fields_list: list[tuple[str, ExtractedFields]]) -> list[BatchFinding]:
        findings = []
        findings.extend(self._check_amount_consistency(fields_list))
        findings.extend(self._check_date_consistency(fields_list))
        findings.extend(self._check_reception_standard(fields_list))
        findings.extend(self._check_unit_business_status(fields_list))
        findings.extend(self._check_payment_consistency(fields_list))
        findings.extend(self._check_activity_letter_date(fields_list))
        return findings
```

### 规则实现细节

#### 规则1: AMOUNT_CONSISTENCY
- 从发票文档提取大写金额（`invoice_amount`）作为标准
- 遍历其他文档的 `invoice_amount`、`actual_amount`，与标准值比对
- 浮点比较用 `abs(a - b) < 0.01` 容差

#### 规则2: DATE_CONSISTENCY
- 从审批单提取 `reception_date` 作为基准
- 发票日期应 ≤ 招待日期，支付日期应 ≥ 招待日期
- 超出合理范围的判定为异常

#### 规则3: RECEPTION_STANDARD
- 从审批单提取招待人数、陪同人数、人均费用
- 对照 `校对规则/校对规则.md` 中的标准表校验
- 使用现有 `EXTERNAL_AMOUNT_LIMITS` 等常量

#### 规则4: UNIT_BUSINESS_STATUS
- 从审批单提取 `host_unit`
- 在经营状态文档中搜索单位名称，提取后 10 字符
- 判断是否含 "正常"，不含则提取 5 字符摘要标记人工审核

#### 规则5: PAYMENT_CONSISTENCY
- 找到支付凭证与支付证明文档
- 比对 `transaction_no`、`merchant_order_no`、`invoice_amount`、`merchant_name`、`payment_date`
- 任一字段不匹配判定为违规

#### 规则6: ACTIVITY_LETTER_DATE
- 从活动函件提取日期
- 与招待日期比对，应在 ±7 天合理范围内

### 集成方式

在 `ComprehensiveChecker` 的 `check_batch_review()` 中，在现有 checker 之后调用 `ProofreadingChecker`，结果归入 `BatchReviewReport` 的 `PROOFREADING` 分类。

### 影响范围

| 文件 | 变更 |
|------|------|
| `proofreading_checker.py` | 新增，6 条校对规则 |
| `checkers.py` | 集成 ProofreadingChecker + 修复 _build_context 聚合逻辑 |
| `models.py` | 新增 RuleCategory.PROOFREADING |
| `校对规则/校对规则.md` | 规则定义文档 |

### _build_context 聚合逻辑修复

同一批次的文档属于同一笔招待事件，金额和人数不应重复计算：

- **金额**: 取第一个可靠来源的实际发生金额，优先级：发票 → 报账单 → 审批单 → 申请单
- **人数**: 取第一个非空值（审批单/申请单记录，数值相同）
- **辅助函数**: `_classify_doc_type(filename)` 根据文件名关键字判断文档类型

## Risks / Trade-offs

- [OCR 识别的日期格式可能不一致] → 用 `dateutil.parser.parse` 容错解析
- [大写金额提取可能含特殊字符] → 正则清洗后转为数字
- [经营状态文本匹配依赖 OCR 准确度] → 提供 5 字符摘要供人工确认
- [支付凭证/证明可能在同一文档中] → 通过文件名关键词区分

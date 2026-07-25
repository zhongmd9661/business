## 1. 扩展 RuleCategory 枚举

- [x] 1.1 在 `models.py` 的 `RuleCategory` 枚举中新增 `PROOFREADING = "校对规则"` 值

## 2. 实现 ProofreadingChecker

- [x] 2.1 创建 `src/expense_review_comprehensive/proofreading_checker.py`
- [x] 2.2 实现 `_check_amount_consistency` — 发票大写金额与其他文档金额比对
- [x] 2.3 实现 `_check_date_consistency` — 审批单招待日期为基准，校验发票/支付日期逻辑
- [x] 2.4 实现 `_check_reception_standard` — 提取招待人数、陪同人数、人均费用，对照标准表
- [x] 2.5 实现 `_check_unit_business_status` — 提取单位名称后 10 字符，判断"正常"，否则 5 字符摘要
- [x] 2.6 实现 `_check_payment_consistency` — 支付凭证与支付证明的交易信息比对
- [x] 2.7 实现 `_check_activity_letter_date` — 活动函件日期与招待日期 ±7 天比对

## 3. 集成到 ComprehensiveChecker

- [x] 3.1 在 `ComprehensiveChecker.__init__` 中实例化 `ProofreadingChecker`
- [x] 3.2 在 `check_batch_review()` 中调用 `ProofreadingChecker.check()`，结果归入 PROOFREADING 分类
- [x] 3.3 在 `__init__.py` 中导出 `ProofreadingChecker`

## 4. 验证

- [x] 4.1 用案例数据运行批次审核，验证 6 条规则都能正常触发
- [x] 4.2 确认校对规则发现正确出现在批次审核报告中

## 5. 修复 _build_context 聚合逻辑

- [x] 5.1 金额不再跨文档累加 — 取第一个可靠来源（发票 > 报账单 > 审批单/申请单）
- [x] 5.2 人数不再跨文档累加 — 取第一个非空值
- [x] 5.3 添加 _classify_doc_type 辅助函数供 _build_context 使用
- [x] 5.4 用实际案例数据验证修复 — 人均从 268.86 → 118.86，不再误报金额标准

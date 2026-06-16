## 1. 创建 LLM 提取模块

- [x] 1.1 创建 `src/expense_review_comprehensive/llm_extractor.py`
- [x] 1.2 实现 `LlmFieldExtractor` 类（`start()`, `stop()`, `extract(text)` 方法）
- [x] 1.3 编写系统提示词，定义 35+ 个字段的类型、格式规范
- [x] 1.4 实现 JSON 响应解析 → `ExtractedFields`
- [x] 1.5 处理模型加载（lmdeploy Pipeline + TurboMind）

## 2. 集成到批量解析流程

- [ ] 2.1 修改 `__init__.py` 导出 `LlmFieldExtractor`
- [ ] 2.2 修改 `batch_parse.py` 添加 `USE_LLM_EXTRACTOR` 环境变量开关
- [ ] 2.3 LLM 模式使用 `start()` / `stop()` 管理模型生命周期

## 3. 测试验证

- [ ] 3.1 用现有识别结果测试 LLM 提取效果
- [ ] 3.2 对比 LLM 与规则提取结果，确认问题文件改善
- [ ] 3.3 验证 `batch_parse.py` 在两种模式下都能正常运行

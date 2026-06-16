## Why

当前规则提取器（`FieldExtractor`）使用正则表达式 + HTML 表格解析来提取字段，在以下场景效果差：

- **标准多行数据表**：列名行 + 数据行的表格被误识别为 KV 配对，导致字段错位（如 `发票号码="8"`, `销售方="是"`）
- **纯文本格式**：微信支付凭证等非表格文档，正则无法匹配结构化数据
- **非结构化文档**：公函、企业资料等文档中没有标准表格，正则提取率为 0

规则提取器的维护成本也越来越高——每增加一个字段需要写多个 fallback 正则，且 OCR 输出格式变化时正则容易失效。

## What Changes

- 新增 `LlmFieldExtractor` 类，使用本地大模型（lmdeploy + TurboMind）理解文档语义并提取结构化字段
- `batch_parse.py` 添加 `USE_LLM_EXTRACTOR` 环境变量开关，可选切换 LLM 提取
- 规则提取器保留作为备选，不删除

## Capabilities

### New Capabilities

- `llm-field-extraction`: 利用本地大模型理解文档语义，从任意格式的 OCR 输出中提取结构化字段

### Modified Capabilities

- `batch_parse.py`: 审核部分根据环境变量选择使用 LLM 或规则提取器

## Impact

- **新增**: `src/expense_review_comprehensive/llm_extractor.py`（独立 LLM 提取模块）
- **修改**: `src/expense_review_comprehensive/__init__.py`（导出 `LlmFieldExtractor`）
- **修改**: `scripts/batch_parse.py`（添加 LLM 提取开关）
- **不修改**: `extractor.py`、`models.py`（规则提取与数据结构不变）

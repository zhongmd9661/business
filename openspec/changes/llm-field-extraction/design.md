## Context

当前 `batch_parse.py` 的字段提取流程使用 `FieldExtractor` 对每个 OCR 识别后的 Markdown 文件运行正则匹配。对于复杂表格结构和纯文本文档，提取准确率不足 50%。

环境：RTX PRO 6000 Blackwell (68GB 空闲)，`lmdeploy 0.11.1` + `openai 2.40.0` 已安装。

## Goals / Non-Goals

**Goals:**
- 实现独立的 LLM 字段提取模块，不依赖规则提取器
- 相同接口 `extract(text) -> ExtractedFields` 可与规则提取器互换
- 支持通过环境变量切换提取方式
- 7B 级别模型在本地 GPU 上推理，无需外部 API

**Non-Goals:**
- 不修改 `ExtractedFields` 数据结构
- 不删除规则提取器（保留作为 fallback）
- 不改变审核逻辑和报告格式

## Decisions

### 独立模块设计

`llm_extractor.py` 完全独立：
- 不依赖 `extractor.py` 的任何函数
- 只依赖 `models.py` 的 `ExtractedFields`
- 自行管理模型加载、提示词构建、响应解析

### 模型加载

```python
from lmdeploy import pipeline, TurbomindEngineConfig

pipe = pipeline(model_path, backend_config=TurbomindEngineConfig(model_name="qwen2"))
response = pipe(system=SYSTEM_PROMPT, prompt=text, gen_config=gen_config)
```

### 提示词设计

系统提示词定义提取任务和 35+ 个字段的类型、格式规范，要求 LLM 以 JSON 返回。找不到的字段返回 `null`。

### JSON 响应解析

LLM 返回 JSON → 解析为 `ExtractedFields`。处理 markdown 代码块包裹、日期/数字/布尔类型转换。解析失败返回空 `ExtractedFields`。

### 影响范围

| 文件 | 变更 |
|------|------|
| `llm_extractor.py` | 新增：独立 LLM 提取模块 |
| `__init__.py` | 新增 `LlmFieldExtractor` 导出 |
| `batch_parse.py` | 添加 `USE_LLM_EXTRACTOR` 环境变量开关 |

## Risks / Trade-offs

- [LLM 推理速度慢于正则] → 单次提取约 2-5 秒，批处理场景可接受
- [模型加载需要时间] → 首次启动加载模型约 30-60 秒，之后复用
- [7B 模型需要 ~16GB 显存] → RTX PRO 6000 有 68GB 空闲，完全满足
- [LLM 可能产生幻觉] → 提示词明确要求不编造，找不到的字段返回 null

## Why

项目需要处理 PDF、图片等文档格式，并将其转换为机器可读格式（Markdown），以便后续检索、抽取与二次处理。当前环境已安装 MinerU，具备完整的文档解析能力，需要建立系统化的批量处理流程。

## What Changes

- 新增 MinerU 文档解析管道，支持 PDF、图片格式输入
- 自动检测扫描版 PDF 并启用 OCR 功能
- 输出 Markdown 格式文本，保留原文档结构（标题、段落、列表、表格、公式）
- 支持批量处理多个文档文件
- 输入文件带序号前缀，输出目录带时间戳
- 集成 ModelScope 模型源以加速模型下载（国内网络环境）

## Capabilities

### New Capabilities

- `document-parsing-pipeline`: MinerU 文档解析管道，支持多格式输入（PDF、图片），输出 Markdown 格式，包含版面分析、OCR 识别、表格/公式转换
- `batch-processing`: 批量文档处理能力，支持输入目录扫描、序号排序、进度显示、时间戳输出
- `output-visualization`: 解析结果输出（Markdown、图像提取），便于质检和效果确认

### Modified Capabilities

无 — 当前项目无现有规范。

## Impact

- **依赖**: MinerU (mineru[all]) 及其模型依赖（DocLayout-YOLO, PP-DocLayoutV2, UniMERNet, PaddleOCR, TableMaster 等）
- **模型源**: 使用 ModelScope 替代 HuggingFace（国内网络环境）
- **输出**: 生成 Markdown、图像等文件
- **硬件**: 支持 CPU 运行，GPU/MPS 加速可选
- **平台**: Windows 兼容

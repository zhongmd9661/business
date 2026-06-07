## Why

本项目需要一套完整的文档解析能力，将 PDF、图片、DOCX、PPTX、XLSX 等格式转化为机器可读格式（Markdown、JSON）。MinerU 作为成熟的开源文档解析工具，能提供版面分析、OCR、公式/表格识别等核心能力，是构建 OCR 文档处理管道的理想基础。

## What Changes

- 引入 MinerU 作为核心文档解析引擎
- 支持 PDF、图片、DOCX、PPTX、XLSX 输入格式
- 支持 Markdown、JSON 等输出格式
- 集成自动 OCR 检测（扫描版/乱码 PDF）
- 支持公式（LaTeX）和表格（HTML）自动识别转换
- 提供命令行接口和 API 接口用于文档解析
- 支持纯 CPU 运行以及 GPU/MPS 加速

## Capabilities

### New Capabilities
- `document-parsing`: 核心文档解析能力，支持多格式输入输出，包含版面分析、阅读顺序还原、结构保留
- `ocr-recognition`: OCR 文字识别能力，支持 109 种语言，自动检测扫描版/乱码 PDF
- `formula-table-extraction`: 公式（LaTeX）和表格（HTML）的自动识别与转换
- `cli-interface`: 命令行接口，支持本地批量解析和单文件处理
- `api-interface`: FastAPI 接口，支持多服务部署和远程调用

### Modified Capabilities
- 无（新项目，无已有能力需要修改）

## Impact

- 新增 Python 依赖：MinerU 及其相关包
- 需要配置 GPU/CPU 运行环境
- 项目从空仓库变为完整的文档解析应用
- 兼容 Windows、Linux、Mac 平台

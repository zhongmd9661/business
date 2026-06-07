## Context

项目需要处理多种格式的文档（PDF、图片、DOCX、PPTX、XLSX），将其转换为 Markdown 格式以便后续处理。MinerU 已安装并验证可用，模型通过 ModelScope 下载。

**当前状态**:
- MinerU 已安装于虚拟环境
- 模型源配置为 ModelScope（`MINERU_MODEL_SOURCE=modelscope`）
- 批量解析脚本 `scripts/batch_parse.py` 已实现并验证可用
- 解析引擎封装在 `src/engine/mineru_engine.py`
- 输入文件带序号前缀（`001_`、`002_`...）
- 输出目录带时间戳（`data/output/20260606_163000/`）

**约束**:
- 国内网络环境，HuggingFace 不可用，需使用 ModelScope
- Windows 11 平台
- 首次运行需下载约 1GB 模型数据

## Goals / Non-Goals

**Goals:**
- 批量解析 `data/input/` 下的文档，输出 Markdown 和图像
- 自动检测扫描版 PDF 并启用 OCR
- 输出带时间戳的目录，方便对比多次运行结果
- 输入文件带序号前缀，便于追踪和排序
- 解析过程显示进度、耗时、汇总

**Non-Goals:**
- 修改 MinerU 核心代码
- 实现在线 API 服务部署
- 支持实时流式处理

## Decisions

### 1. 实现方式: Python 脚本调用 MinerU LocalAPIServer
- **决策**: 使用 Python 脚本直接调用 MinerU 的 `LocalAPIServer` 而非 CLI 子进程
- **理由**: 环境变量（`MINERU_MODEL_SOURCE`）在子进程中丢失，直接调用可保证配置传递
- **替代方案**: PowerShell 调用 `mineru parse` CLI

### 2. 输出目录: 时间戳子目录
- **决策**: 每次运行在 `data/output/` 下创建 `{YYYYMMDD_HHMMSS}` 子目录
- **理由**: 多次运行结果可对比，不会被覆盖
- **替代方案**: 固定 output 目录，每次覆盖

### 3. 输入文件: 序号前缀
- **决策**: 输入文件名加 `NNN_` 前缀（如 `001_xxx.pdf`）
- **理由**: 确保处理顺序可控，日志和输出目录可追溯
- **替代方案**: 按文件名自然排序

### 4. 并发控制: MinerU 默认并发 3
- **决策**: 使用 MinerU 内置并发控制（processing-window）
- **理由**: 避免 GPU/内存溢出
- **替代方案**: 自定义并发数

## Risks / Trade-offs

[首次模型下载时间长] → 约 1GB 模型数据，首次运行需 10-15 分钟。

[CPU 处理速度慢] → 单页约 5-10 秒，大文档处理时间较长。

[解析精度因文档类型而异] → 复杂版面、扫描件、手写体可能不尽如人意。

[输出目录累积] → 多次运行会产生多个时间戳目录，需定期清理。

## Project Structure

```
src/
  engine/
    mineru_engine.py     # MinerU 解析引擎封装（ModelScope 配置）
  core/
    parser.py            # 核心解析逻辑
  cli/
    main.py              # CLI 入口
  api/
    app.py               # API 服务
scripts/
  batch_parse.py         # 批量解析脚本（主入口）
  download_models.py     # 模型预下载
data/
  input/                 # 输入文件（带序号前缀）
  output/                # 输出目录（时间戳子目录）
```

## Context

本项目是一个从零开始的 OCR 文档解析应用。MinerU 作为核心解析引擎，提供多格式文档到机器可读格式的转换能力。项目运行在 Windows 11 环境，需要支持 CPU 和 GPU 两种运行模式。

## Goals / Non-Goals

**Goals:**
- 集成 MinerU 作为文档解析的核心引擎
- 提供命令行接口用于单文件和批量解析
- 提供 FastAPI 接口用于远程调用
- 支持 GPU 加速和纯 CPU  fallback
- 输出 Markdown 和 JSON 格式

**Non-Goals:**
- 不修改 MinerU 核心源码
- 不提供 Gradio WebUI（仅 CLI + API）
- 不涉及文档编辑功能

## Decisions

- **MinerU 作为解析引擎**: 选择了 MinerU 而非 Tesseract、PaddleOCR 独立方案，因为 MinerU 已经整合了版面分析、OCR、公式/表格识别等多重能力，减少集成复杂度。
- **Python 作为主要开发语言**: MinerU 基于 Python 生态，直接使用 Python 构建 CLI 和 API 层，避免跨语言调用的开销。
- **FastAPI 作为 API 框架**: 轻量、高性能，原生支持异步，适合文件上传和长时间处理的场景。
- **分层架构**: 解析引擎层（MinerU）→ 业务逻辑层 → 接口层（CLI/API），便于后续替换或扩展解析引擎。

## Risks / Trade-offs

- [MinerU 模型下载体积较大] → 首次运行需要下载预训练模型，建议在安装脚本中提示用户并提供进度反馈
- [GPU 内存需求较高] → 复杂文档解析可能消耗 4-8GB 显存，提供 CPU fallback 和批处理控制
- [OCR 处理耗时] → 扫描版 PDF 的 OCR 识别较慢，API 端需要支持异步任务队列或长轮询
- [Windows 兼容性] → MinerU 部分依赖在 Windows 上可能存在兼容问题，需要验证测试

## Migration Plan

不适用（新项目，无现有系统迁移）。

## Open Questions

- 是否需要支持异步任务队列（Celery/RQ）处理大文件？
- 输出文件的存储策略：内存返回 vs 临时文件 vs 持久化存储

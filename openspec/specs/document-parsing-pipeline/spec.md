## Purpose

定义文档解析管道的输入输出规范，包括多格式支持、自动 OCR 检测、模型管理与输出目录结构。

## Requirements

### Requirement: 支持多格式文档输入
系统 SHALL 接受 PDF、图片（JPG、PNG）、Office 文档（docx、xlsx、pptx）格式的文档作为输入。

#### Scenario: PDF 文档解析
- **WHEN** 用户提供 PDF 文件
- **THEN** 系统解析 PDF 并输出 Markdown 格式结果

#### Scenario: 图片文档解析
- **WHEN** 用户提供 JPG/PNG 图片文件
- **THEN** 系统通过 OCR 识别图片内容并输出 Markdown 格式结果

#### Scenario: Word 文档解析
- **WHEN** 用户提供 docx 文件
- **THEN** 系统解析 docx 并输出 Markdown 格式结果，保留标题、段落、表格、列表等结构

#### Scenario: Excel 文档解析
- **WHEN** 用户提供 xlsx 文件
- **THEN** 系统解析 xlsx 并输出 Markdown 格式结果，每个工作表转换为 Markdown 表格

### Requirement: 自动检测扫描版文档
系统 SHALL 使用 `auto` 模式自动检测扫描版 PDF 并启用 OCR。

#### Scenario: 扫描版 PDF 检测
- **WHEN** 输入为扫描版 PDF（图片型 PDF）
- **THEN** 系统自动启用 OCR 模式进行解析

#### Scenario: 数字版 PDF 检测
- **WHEN** 输入为数字版 PDF（文本型 PDF）
- **THEN** 系统使用直接解析模式

### Requirement: 保留文档结构
系统 SHALL 保留原文档的结构，包括标题、段落、表格、公式。

#### Scenario: 标题层级保留
- **WHEN** 原文档包含多级标题
- **THEN** 输出 Markdown 保留标题层级（#、##、###）

#### Scenario: 表格转换
- **WHEN** 原文档包含表格
- **THEN** 输出 HTML 格式的表格，保留行列结构

#### Scenario: 公式转换
- **WHEN** 原文档包含数学公式
- **THEN** 输出 LaTeX 格式的公式

### Requirement: 输出格式
系统 SHALL 输出 Markdown 格式的结果，源文件与识别结果分目录存放。

#### Scenario: Markdown 输出
- **WHEN** 解析完成
- **THEN** 在 `识别结果/` 目录下生成 Markdown 文件，包含文本、表格、公式等内容

#### Scenario: 源文件归档
- **WHEN** 解析成功
- **THEN** 源文件移至 `源文件/` 目录，文件名带序号前缀，与识别结果文件名对应

#### Scenario: 不输出图像文件
- **WHEN** 原文档包含图像
- **THEN** 不提取图像文件，仅保留 Markdown 文本

### Requirement: 模型源配置
系统 SHALL 使用 ModelScope 作为模型源，确保国内网络环境可用。

#### Scenario: 模型下载
- **WHEN** 首次运行需下载模型
- **THEN** 系统从 ModelScope 下载模型，不尝试 HuggingFace

### Requirement: 模型本地缓存管理
系统 SHALL 使用本地模型缓存，避免每次解析都联网下载模型。

#### Scenario: 本地模型优先
- **WHEN** 本地已存在模型文件
- **THEN** 系统直接使用本地模型，不发起网络请求

#### Scenario: 模型缺失检测
- **WHEN** 启动时检测到模型文件缺失
- **THEN** 系统给出明确提示，引导用户运行 `mineru-models-download` 命令下载

#### Scenario: 必需模型完整性
- **WHEN** 检查模型可用性
- **THEN** 系统验证 Layout、MFR、OCR、TabRec、TabCls 模型文件是否齐全

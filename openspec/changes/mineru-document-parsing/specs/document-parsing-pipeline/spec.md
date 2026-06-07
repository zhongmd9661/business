## ADDED Requirements

### Requirement: 支持多格式文档输入
系统 SHALL 接受 PDF、图片（JPG、PNG）格式的文档作为输入。

#### Scenario: PDF 文档解析
- **WHEN** 用户提供 PDF 文件
- **THEN** 系统解析 PDF 并输出 Markdown 格式结果

#### Scenario: 图片文档解析
- **WHEN** 用户提供 JPG/PNG 图片文件
- **THEN** 系统通过 OCR 识别图片内容并输出 Markdown 格式结果

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
系统 SHALL 输出 Markdown 格式的结果，并提取图像文件。

#### Scenario: Markdown 输出
- **WHEN** 解析完成
- **THEN** 生成 Markdown 文件，包含文本、表格、公式等内容

#### Scenario: 图像提取
- **WHEN** 原文档包含图像
- **THEN** 图像文件提取到输出目录的 `images/` 子目录

### Requirement: 模型源配置
系统 SHALL 使用 ModelScope 作为模型源，确保国内网络环境可用。

#### Scenario: 模型下载
- **WHEN** 首次运行需下载模型
- **THEN** 系统从 ModelScope 下载模型，不尝试 HuggingFace

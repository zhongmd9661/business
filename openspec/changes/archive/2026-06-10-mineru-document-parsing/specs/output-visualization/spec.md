## ADDED Requirements

### Requirement: Markdown 输出
系统 SHALL 生成 Markdown 格式的解析结果。

#### Scenario: Markdown 文件生成
- **WHEN** 解析完成
- **THEN** 系统生成 Markdown 文件，包含文档文本、表格、公式等内容

### Requirement: 文档摘要
系统 SHALL 为每个解析结果生成文档摘要，便于快速了解文档内容。

#### Scenario: 摘要生成
- **WHEN** 解析完成
- **THEN** Markdown 文件头部包含文档摘要，概括文档类型、关键信息（如单据编号、日期、金额等）

#### Scenario: 摘要格式
- **WHEN** 用户查看 Markdown 输出
- **THEN** 摘要位于文档顶部，以 `## 摘要` 标题呈现，包含 1-3 句概述

### Requirement: 图像文件提取
系统 SHALL 提取文档中的图像文件。

#### Scenario: 图像提取
- **WHEN** 原文档包含图像
- **THEN** 图像文件保存到输出目录的 `images/` 子目录

### Requirement: 输出目录扁平化
系统 SHALL 控制输出目录深度，子文件夹不超过 2 层。

#### Scenario: 目录层级限制
- **WHEN** 解析完成
- **THEN** 输出结构为 `data/output/{timestamp}/{seq}_{filename}/`，其中 `seq` 为输入文件序号
- **AND** Markdown 文件和 `images/` 目录直接位于 `{seq}_{filename}/` 下，不再嵌套 `auto/` 等中间目录

### Requirement: 序号对应
系统 SHALL 在输出目录和文件名中保留输入序号，确保输入输出可一一对应。

#### Scenario: 输出带序号
- **WHEN** 输入文件为 `001_xxx.pdf`
- **THEN** 输出目录为 `data/output/{timestamp}/001_xxx/`，输出 Markdown 为 `001_xxx.md`
- **AND** 无序号的输入文件使用自动分配的序号（如 `008_xxx.pdf` → `008_xxx/`）

### Requirement: 输出目录隔离
系统 SHALL 每次运行使用独立的输出目录，避免覆盖历史结果。

#### Scenario: 时间戳目录
- **WHEN** 多次运行批量解析
- **THEN** 每次结果保存于不同的 `{YYYYMMDD_HHMMSS}` 目录，互不干扰

### Requirement: 质检支持
系统 SHALL 提供输出结果，便于确认解析效果。

#### Scenario: Markdown 内容查看
- **WHEN** 用户查看 Markdown 输出
- **THEN** 用户可以确认文本、表格、公式等内容是否正确解析

#### Scenario: 图像对比
- **WHEN** 用户查看提取的图像
- **THEN** 用户可以对比原始文档中的图像与提取结果

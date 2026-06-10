## Purpose

支持批量处理输入目录下的多个文档，提供进度显示、序号管理、zip 自动解压与容错机制。

## Requirements

### Requirement: 输入目录扫描
系统 SHALL 扫描 `data/input/` 目录，查找所有支持的文档文件。

#### Scenario: 扫描输入目录
- **WHEN** 启动批量解析
- **THEN** 系统扫描 `data/input/` 目录并识别所有支持的文档格式（PDF、JPG、PNG）

### Requirement: 序号前缀排序
系统 SHALL 按序号前缀（`NNN_`）对输入文件排序。

#### Scenario: 带序号的文件排序
- **WHEN** 输入文件名为 `001_xxx.pdf`、`002_yyy.jpg` 格式
- **THEN** 系统按序号 001、002... 顺序处理

#### Scenario: 无序号的文件
- **WHEN** 部分文件没有序号前缀
- **THEN** 系统将其排在序号文件之后

### Requirement: 批量处理
系统 SHALL 支持批量处理多个文档文件。

#### Scenario: 多文档处理
- **WHEN** 扫描结果包含多个文档文件
- **THEN** 系统逐个处理文档，生成对应的输出文件

#### Scenario: 处理进度显示
- **WHEN** 批量处理进行中
- **THEN** 系统显示当前进度（`[i/N] pct%`）、序号、文件名、耗时

#### Scenario: 汇总报告
- **WHEN** 批量处理完成
- **THEN** 系统显示总耗时、处理文件数、每个文件的耗时明细

### Requirement: 输出目录结构
系统 SHALL 按时间戳组织输出文件，目录深度不超过 2 层子文件夹。

#### Scenario: 时间戳目录创建
- **WHEN** 启动批量解析
- **THEN** 系统在 `data/output/` 下创建 `{YYYYMMDD_HHMMSS}` 子目录

#### Scenario: 输出文件组织
- **WHEN** 处理文档 `001_xxx.pdf`
- **THEN** 输出目录为 `data/output/{timestamp}/001_xxx/`，Markdown 文件为 `001_xxx.md`，图像在 `001_xxx/images/`
- **AND** 不再存在 `auto/` 等中间目录层

#### Scenario: 序号对应
- **WHEN** 输入文件带有序号前缀 `NNN_`
- **THEN** 输出目录名和 Markdown 文件名均保留该序号，输入 `001_xxx.pdf` 对应输出 `001_xxx/001_xxx.md`
- **AND** 无序号文件按处理顺序自动分配序号（接在已有序号之后）

### Requirement: Zip 文件自动解压
系统 SHALL 在扫描输入目录时自动解压 zip 文件，统一使用 UTF-8 编码处理文件名。

#### Scenario: 扫描到 zip 文件
- **WHEN** `data/input/` 目录中存在 zip 文件
- **THEN** 系统自动解压到 `data/input/` 根目录，使用 UTF-8 编码处理文件名

#### Scenario: 非 zip 文件
- **WHEN** 输入目录中没有 zip 文件
- **THEN** 系统正常扫描已有的文档文件

### Requirement: 批次摘要输入
系统 SHALL 在启动批量解析前 prompt 用户输入批次摘要。

#### Scenario: 输入批次摘要
- **WHEN** 启动批量解析
- **THEN** 系统提示用户输入本次批次的简要描述（如：差旅报销、业务招待等）

#### Scenario: 未输入摘要
- **WHEN** 用户直接回车未输入摘要
- **THEN** 系统使用 `batch` 作为默认摘要

### Requirement: 已处理文件归档
系统 SHALL 在 OCR 完成后，将已处理的文件移至 `data/已识别/` 目录。

#### Scenario: 成功处理的文件
- **WHEN** 某个文件解析成功
- **THEN** 该文件从 `data/input/` 移至 `data/已识别/<摘要>_{YYYYMMDD_HHMMSS}/`

#### Scenario: 处理失败的文件
- **WHEN** 某个文件解析失败
- **THEN** 该文件保留在 `data/input/` 中，不移动

### Requirement: 错误处理
系统 SHALL 处理单个文档失败的情况，继续处理其他文档。

#### Scenario: 单个文档失败
- **WHEN** 处理某个文档时发生错误
- **THEN** 系统记录错误并继续处理下一个文档

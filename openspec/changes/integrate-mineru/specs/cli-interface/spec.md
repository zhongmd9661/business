## ADDED Requirements

### Requirement: 单文件解析命令
系统 SHALL 提供命令行接口用于解析单个文件。

#### Scenario: 解析单个文件
- **WHEN** 用户通过命令行指定输入文件和输出格式
- **THEN** 系统解析文件并将结果输出到指定位置

#### Scenario: 查看帮助信息
- **WHEN** 用户请求帮助信息
- **THEN** 系统显示可用的命令和参数说明

### Requirement: 批量解析
系统 SHALL 支持批量解析目录下的多个文件。

#### Scenario: 目录批量解析
- **WHEN** 用户指定输入目录和输出目录
- **THEN** 系统解析目录下所有支持的文档文件

### Requirement: 运行模式选择
系统 SHALL 支持选择 CPU 或 GPU 运行模式。

#### Scenario: GPU 加速模式
- **WHEN** 用户指定使用 GPU 模式且系统有可用 GPU
- **THEN** 系统使用 GPU 加速解析

#### Scenario: CPU 模式
- **WHEN** 用户指定使用 CPU 模式或系统无可用 GPU
- **THEN** 系统在纯 CPU 环境下运行解析

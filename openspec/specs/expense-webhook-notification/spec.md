## Purpose

发现高风险问题时通过 Webhook 发送告警通知，支持参数化配置与失败容错。

## Requirements

### Requirement: 高风险告警触发

系统 SHALL 在发现高风险问题时发送 Webhook 告警通知。

#### Scenario: 发现高风险触发通知
- **WHEN** 审核结果包含高风险发现
- **THEN** 系统向配置的 Webhook 地址发送 POST 请求，载荷包含问题摘要

#### Scenario: 无高风险不触发
- **WHEN** 审核结果无高风险发现
- **THEN** 系统不发送任何通知

### Requirement: 告警载荷内容

系统 SHALL 在告警请求中包含足够的上下文信息。

#### Scenario: 告警包含必要字段
- **WHEN** 发送告警通知
- **THEN** 请求体包含来源文档名、风险规则、问题描述、发现时间

### Requirement: 发送失败不中断流程

系统 SHALL 在 Webhook 发送失败时记录错误但不中断审核流程。

#### Scenario: 网络不可达
- **WHEN** Webhook 目标地址不可达
- **THEN** 错误被记录，审核流程继续执行后续文档

#### Scenario: 超时处理
- **WHEN** Webhook 请求超过 10 秒未响应
- **THEN** 请求被取消，错误被记录，流程继续

### Requirement: Webhook 配置参数化

系统 SHALL 通过构造函数参数接收 Webhook 目标地址。

#### Scenario: 配置目标地址
- **WHEN** 创建 WebhookNotifier 实例
- **THEN** 传入的 URL 被用于后续通知发送

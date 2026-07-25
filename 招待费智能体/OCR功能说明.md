# 招待费智能体 OCR 功能

## 概述

本目录包含从 `D:\00_项目\02_ocr` 复制的 OCR 功能代码，用于实现招待费智能审核系统的 OCR 识别功能。

## 目录结构

```
招待费智能体/
├── web_service/              # FastAPI Web 服务
│   ├── app.py               # 应用入口
│   ├── router.py            # 任务管理路由
│   ├── service.py           # 业务逻辑服务
│   ├── models_db.py         # 数据库模型
│   ├── auth.py              # 认证模块
│   ├── config.py            # 配置文件
│   ├── schemas.py           # 数据模型
│   ├── rule_*.py            # 规则相关模块
│   ├── static/              # 静态文件
│   └── templates/           # HTML 模板
├── document_parsing_pipeline/  # OCR 解析引擎
│   ├── engine.py            # 解析引擎
│   ├── llm_vision_engine.py # LLM 视觉引擎
│   └── splicing_engine.py   # 拼接引擎
├── expense_review_comprehensive/  # 费用审核模块
│   ├── extractor.py         # 字段提取器
│   ├── llm_extractor.py     # LLM 字段提取
│   ├── checker.py           # 审核检查器
│   ├── reporter.py          # 报告生成器
│   └── models.py            # 数据模型
├── batch_processing/        # 批量处理
│   ├── collector.py         # 文件收集器
│   ├── runner.py            # 批量运行器
│   └── xml_to_md.py         # XML 转 Markdown
├── output_visualization/    # 输出可视化
│   └── organizer.py         # 输出组织器
├── standards_query/         # 标准查询
│   └── query.py             # 查询模块
└── index.html               # 前端页面
```

## 核心功能

### 1. OCR 识别
- 使用 MinerU 引擎进行 OCR 识别
- 支持多种文档格式
- 自动提取字段信息

### 2. 字段提取
- 支持规则提取和 LLM 提取两种方式
- 提取字段包括：招待日期、发票日期、金额、人数等

### 3. 审核检查
- 基于规则引擎进行审核
- 支持动态规则加载
- 生成审核报告

### 4. Web 服务
- FastAPI 提供的 RESTful API
- 支持文件上传、任务管理
- 实时状态查询

## 使用方法

### 启动 Web 服务

```bash
cd web_service
python app.py
```

### API 端点

- `POST /api/tasks/upload` - 上传文件进行 OCR 识别
- `GET /api/tasks` - 查询任务列表
- `GET /api/tasks/{task_id}` - 查询任务详情
- `GET /api/tasks/{task_id}/report` - 获取审核报告
- `GET /api/tasks/{task_id}/fields` - 获取字段提取结果
- `DELETE /api/tasks/{task_id}` - 删除任务

## 依赖安装

确保已安装以下依赖：

```bash
pip install fastapi uvicorn sqlalchemy loguru
pip install python-multipart
```

## 注意事项

1. 确保 `requirements.txt` 中的依赖已安装
2. 配置文件 `config.py` 中的路径需要根据实际情况调整
3. 数据库初始化在应用启动时自动完成

## 相关文档

- 原始项目文档：`D:\00_项目\02_ocr\README.md`
- 使用说明：`D:\00_项目\02_ocr\USAGE.md`
- 审核规则查看/编辑：`ui/card7-audit.html`（在线可编辑审核规则页面，每条规则标注标准来源）
- 审核标准目录：`审核标准/`（政策法规、业务规范、审核规则、参考案例）

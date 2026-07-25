## Why

当前系统为命令行批处理模式，用户需手动将文件放入 `data/input/` 目录，然后执行 `batch_parse.py` 脚本。对于非技术人员来说，操作门槛高，且无法实时查看审核进度和结果。

需要建设一个 Web 后端服务，让用户通过浏览器完成文件上传、自动识别、规则审核、结果查看的全流程。

审核规则的权威来源是项目 `00规则制度/00综合部业务招待费/` 目录下的两份制度文件——《业务招待费管理办法（V9.0）》（40 条，7 章）与《业务招待费审查风险点》。系统首次启动时从这两份文档导出初始规则库，管理员可在系统中增删改规则，每条规则保留制度条款引用以便追溯。

**制度文件变更同步**：当 `00规则制度/` 目录下的制度文件发生更新（如 V9.0 → V10.0），系统定时扫描目录，通过文件最新修改时间（mtime）检测变更，重新解析文档对比新旧规则差异，生成同步报告供管理员确认后更新数据库中的审核规则。确保线上规则始终与最新制度保持一致。扫描间隔通过环境变量 `RULE_SYNC_INTERVAL_MIN` 配置，测试期间默认 2 分钟。

## What Changes

- 新增 FastAPI 后端服务，提供 RESTful API
- 实现用户认证（JWT Token），支持登录/注册，区分普通用户与管理员角色
- 文件上传接口，支持多文件批量上传（PDF、图片、XML、Office）
- 异步任务队列，上传后立即返回任务 ID，后台执行 OCR 识别与规则审核
- 任务状态查询与审核报告下载接口
- **审核规则管理**：用户可查阅当前审核规则，管理员可增加/修改/删除规则
- 复用现有的 OCR 引擎、字段提取器、审核规则模块
- 数据库存储用户信息、任务记录、审核结果、审核规则

## Capabilities

### New Capabilities

- `web-api`: FastAPI 后端服务，提供文件上传、任务管理、报告下载的 RESTful API
- `user-auth`: 基于 JWT 的用户认证与授权，区分普通用户与管理员角色
- `async-task-queue`: 异步任务处理，支持大文件 OCR 识别的后台执行
- `task-tracking`: 任务状态查询、进度反馈、结果持久化
- `rule-management`: 审核规则的增删改查，管理员可修改规则，普通用户仅可查阅
- `rule-sync`: 定时扫描 `00规则制度/` 目录，通过文件修改时间（mtime）检测制度文件更新，对比新旧规则差异，管理员确认后同步到数据库。扫描间隔可配置（`RULE_SYNC_INTERVAL_MIN`，测试默认 2 分钟）

### Modified Capabilities

- `batch_parse.py`: 核心处理逻辑抽取为可独立调用的服务模块，被 Web 服务复用
- `MinerUEngine`: 引擎生命周期由 Web 服务统一管理，启动时初始化，持续运行
- `ComprehensiveChecker`: 审核规则从数据库动态加载，而非硬编码在代码中

## Impact

- **新增**: `src/web_service/app.py`（FastAPI 应用入口）
- **新增**: `src/web_service/auth.py`（用户认证与权限校验）
- **新增**: `src/web_service/router.py`（API 路由）
- **新增**: `src/web_service/service.py`（业务逻辑：任务创建、OCR、审核）
- **新增**: `src/web_service/models_db.py`（SQLAlchemy 数据模型）
- **新增**: `src/web_service/schemas.py`（Pydantic 请求/响应模型）
- **新增**: `src/web_service/config.py`（服务配置）
- **新增**: `src/web_service/router_rule.py`（审核规则管理路由）
- **新增**: `src/web_service/rule_service.py`（审核规则业务逻辑）
- **新增**: `src/web_service/rule_sync.py`（制度文件监控与规则同步）
- **新增**: `src/web_service/rule_parser.py`（从 .docx 制度文档解析规则到结构化数据）
- **修改**: `scripts/batch_parse.py`（核心逻辑抽取，CLI 模式保留为兼容）
- **修改**: `src/expense_review_comprehensive/checkers.py`（审核规则从数据库动态加载）
- **新增**: `requirements-web.txt`（Web 服务额外依赖）

## 技术选型

- **Web 框架**: FastAPI（项目已有依赖，异步支持，自动生成 OpenAPI 文档）
- **认证**: JWT Token + Passlib 密码哈希
- **数据库**: SQLite（开发）/ PostgreSQL（生产），SQLAlchemy ORM
- **任务队列**: asyncio 异步任务（轻量级，无需 Celery/Redis）
- **文件存储**: 本地文件系统，上传文件存于 `data/uploads/`

## 运行指令

```powershell
# 启动 Web 服务
.venv\Scripts\python.exe -m uvicorn src.web_service.app:app --host 0.0.0.0 --port 8000

# API 文档
# http://localhost:8000/docs
```

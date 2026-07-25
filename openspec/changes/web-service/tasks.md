## 1. 创建 Web 服务基础架构

- [x] 1.1 创建 `src/web_service/` 目录结构
  - [x] 1.1.1 `__init__.py`
  - [x] 1.1.2 `app.py` — FastAPI 应用入口，配置中间件、CORS、静态文件
  - [x] 1.1.3 `config.py` — 服务配置（数据库路径、JWT 密钥、文件上传限制、`RULE_SYNC_INTERVAL_MIN`）
- [x] 1.2 添加 Web 服务依赖到 `requirements-web.txt`
  - [x] fastapi（已有）
  - [x] uvicorn（已有）
  - [x] python-jose[cryptography]（JWT）
  - [x] passlib[bcrypt]（密码哈希）
  - [x] python-multipart（文件上传）
  - [x] sqlalchemy（ORM）
  - [x] aiosqlite（异步 SQLite）
  - [x] python-docx（读取 .docx 制度文档）

## 2. 实现用户认证与角色权限

- [x] 2.1 实现 `models_db.py` — SQLAlchemy 用户模型（增加 `role` 字段：`user` / `admin`）
- [x] 2.2 实现 `auth.py` — 密码哈希、JWT 生成/验证（Token 携带角色信息）
- [x] 2.3 实现 `schemas.py` — RegisterRequest, LoginRequest, TokenResponse
- [x] 2.4 实现注册接口 `POST /api/auth/register` — 默认注册为普通用户
- [x] 2.5 实现登录接口 `POST /api/auth/login` — 返回 JWT，Token 中包含用户角色
- [x] 2.6 实现依赖注入 `get_current_user` — 从 Header 提取 JWT 并验证
- [x] 2.7 实现依赖注入 `get_admin_user` — 校验管理员角色，非管理员返回 403

## 3. 实现数据库模型

- [x] 3.1 定义 `User` 模型（id, username, hashed_password, role, created_at）
- [x] 3.2 定义 `Task` 模型（id, user_id, batch_name, status, file_count, output_dir, error_message, timestamps）
- [x] 3.3 定义 `TaskFile` 模型（id, task_id, filename, file_type, parsed, md_path）
- [x] 3.4 定义 `AuditRule` 模型（id, category, rule_name, clause, level, description, check_expression, source_document, enabled, created_by, timestamps）
- [x] 3.5 定义 `AuditRuleHistory` 模型（id, rule_id, action, old_value, new_value, changed_by, changed_at）
- [x] 3.6 定义 `DocumentVersion` 模型（id, document_name, file_path, last_mtime, version_tag, sync_status, sync_diff, timestamps）
- [x] 3.7 定义 `SyncHistory` 模型（id, trigger_type, document_name, rules_added/modified/deleted, diff_report, status, operated_by, timestamps）
- [x] 3.8 实现数据库初始化函数 `init_db()` — 建表 + 初始化默认规则
- [x] 3.9 实现数据库会话管理 `get_db` 依赖注入

## 4. 实现文件上传与任务管理

- [x] 4.1 实现 `POST /api/tasks/upload` — 接收多文件上传，保存到 `data/uploads/`
- [x] 4.2 实现文件类型白名单校验与大小限制
- [x] 4.3 实现 `service.py` — `ReviewPipeline` 类
- [x] 4.4 实现异步任务处理 `process_review_task(task_id)` — 编排 OCR → 提取 → 审核
- [x] 4.5 实现 asyncio.Semaphore 限制并发 OCR 任务数

## 5. 复用现有审核管线

- [x] 5.1 抽取 `batch_parse.py` 中 `process_batch()` 的核心逻辑到 `service.py`
- [x] 5.2 实现 MinerU 引擎单例管理（启动初始化，关闭停止）
- [x] 5.3 集成 FieldExtractor / LlmFieldExtractor
- [x] 5.4 集成 ComprehensiveChecker + ComprehensiveReporter
- [x] 5.5 确保审核报告同时写入数据库和文件系统

## 6. 实现任务查询与报告下载

- [x] 6.1 实现 `GET /api/tasks/{task_id}` — 任务状态查询
- [x] 6.2 实现 `GET /api/tasks` — 用户任务列表（分页）
- [x] 6.3 实现 `GET /api/tasks/{task_id}/report` — 下载审核报告
- [x] 6.4 实现 `GET /api/tasks/{task_id}/fields` — 查看字段提取详情
- [x] 6.5 实现 `DELETE /api/tasks/{task_id}` — 删除任务及关联文件
- [x] 6.6 所有接口校验用户权限（只能访问自己的任务）

## 7. 实现审核规则管理

- [x] 7.1 创建 `src/web_service/router_rule.py` — 规则管理路由
- [x] 7.2 创建 `src/web_service/rule_service.py` — 规则业务逻辑
- [x] 7.3 实现 `GET /api/rules` — 查阅审核规则列表（所有用户可访问）
- [x] 7.4 实现 `GET /api/rules/{rule_id}` — 查阅单条规则详情
- [x] 7.5 实现 `POST /api/rules` — 新增审核规则（管理员）
- [x] 7.6 实现 `PUT /api/rules/{rule_id}` — 修改审核规则（管理员）
- [x] 7.7 实现 `DELETE /api/rules/{rule_id}` — 删除审核规则（管理员）
- [x] 7.8 实现 `GET /api/rules/categories` — 列出规则分类
- [x] 7.9 规则变更日志记录到 `audit_rule_history` 表
- [x] 7.10 初始化默认规则 — 首次启动从 `00规则制度/00综合部业务招待费/` 目录下的制度文档导出规则到数据库
  - [x] 从《业务招待费管理办法（V9.0）》导出开支标准、陪同人数、禁止性规定、审批管理等条款
  - [x] 从《业务招待费审查风险点》导出单据审查要点、典型违规问题、潜在风险问题

## 8. 审核规则动态加载

- [x] 8.1 修改 `ComprehensiveChecker` — 从数据库加载启用规则
- [x] 8.2 实现规则表达式解析器 — 支持 `keyword_match`, `amount_compare`, `date_range` 等检查类型
- [x] 8.3 规则变更后即时生效，无需重启服务（CRUD 操作后调用 `reload_rules()`）
- [x] 8.4 实现规则缓存机制 — 减少数据库查询开销

## 9. 实现制度文档解析器

- [x] 9.1 创建 `src/web_service/rule_parser.py`
- [x] 9.2 实现 `parse_docx(file_path) -> List[AuditRule]` — 读取 .docx 文本，按条款分段
- [x] 9.3 实现 LLM 辅助解析 — 将制度条款转为结构化规则 JSON（category, rule_name, clause, level, description, check_expression）
- [x] 9.4 实现 `parse_management_measures()` — 解析管理办法，提取开支标准、陪同人数、禁止性规定等
- [x] 9.5 实现 `parse_risk_points()` — 解析审查风险点，提取单据审查要点、典型违规问题等
- [x] 9.6 解析结果标注 `source_document` 字段，追溯来源

## 10. 实现制度文件同步机制

- [x] 10.1 创建 `src/web_service/rule_sync.py`
- [x] 10.2 实现 `scan_rules_directory()` — 定时扫描 `00规则制度/` 目录
- [x] 10.3 实现 `detect_document_changes()` — 通过 `os.path.getmtime()` 获取文件最新修改时间，与 `document_versions.last_mtime` 对比，检测文件是否被修改
- [x] 10.4 实现 `diff_rules(old_rules, new_rules) -> DiffReport` — 按 clause + rule_name 匹配，识别新增/修改/删除，确定修改了什么实际内容
- [x] 10.5 实现 `POST /api/rules/sync` — 手动触发同步（管理员）
- [x] 10.6 实现 `GET /api/rules/sync/status` — 查询同步状态与差异报告
- [x] 10.7 实现 `POST /api/rules/sync/apply` — 确认应用同步变更，更新 `audit_rules` + `sync_history`
- [x] 10.8 实现 `GET /api/rules/sync/history` — 查询历史同步记录
- [x] 10.9 实现定时扫描 — 间隔通过环境变量 `RULE_SYNC_INTERVAL_MIN` 配置（测试默认 2 分钟，生产可调整）
- [x] 10.10 实现冲突检测 — 管理员手动修改的规则与制度原文冲突时标记，需人工介入
- [x] 10.11 同步完成后通知 — 通过 Webhook 通知管理员有新规则待确认

## 11. 服务生命周期管理

- [x] 11.1 实现 `on_event("startup")` — 初始化数据库、启动 MinerU 引擎、加载审核规则、启动定时扫描
- [x] 11.2 实现 `on_event("shutdown")` — 优雅关闭 MinerU 引擎、停止定时扫描
- [x] 11.3 实现健康检查接口 `GET /api/health`

## 12. 集成测试

- [x] 12.1 注册/登录流程测试
- [x] 12.2 上传文件并等待审核完成（已验证：9 个文件，耗时 96 秒）
- [x] 12.3 查询任务状态变更（已验证：parsing → completed）
- [x] 12.4 下载审核报告验证内容正确（已验证：报告包含 6 条发现，2 条高风险）
- [ ] 12.5 并发上传测试（验证 Semaphore 生效）
- [x] 12.6 权限隔离测试（用户 A 无法访问用户 B 的任务）
- [x] 12.7 规则管理权限测试（普通用户无法修改规则，管理员可正常操作）
- [x] 12.8 规则变更即时生效测试（修改规则后新任务使用新规则）
- [x] 12.9 制度文件变更同步测试 — 验证手动触发同步、状态查询、历史记录
- [x] 12.10 同步间隔配置测试 — 验证 `RULE_SYNC_INTERVAL_MIN` 环境变量生效（默认 2 分钟）

## 13. 文档与部署

- [x] 13.1 更新 USAGE.md，添加 Web 服务使用说明
- [x] 13.2 添加环境变量配置说明（含 `RULE_SYNC_INTERVAL_MIN`）
- [x] 13.3 保留 `batch_parse.py` CLI 模式作为向后兼容
- [x] 13.4 添加管理员初始化说明（创建首个管理员账户）


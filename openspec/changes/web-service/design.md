## Context

当前 `batch_parse.py` 是命令行批处理脚本，用户需手动管理文件目录。核心处理链路为：

```
FileCollector -> MinerUEngine -> FieldExtractor/LlmFieldExtractor -> ComprehensiveChecker -> ComprehensiveReporter
```

这些模块位于 `src/` 下，逻辑清晰，可被 Web 服务直接复用。

环境：Windows 11，RTX PRO 6000 (68GB GPU)，MinerU LocalAPIServer 需 GPU 支持。

### 基础规则制度来源

项目 `00规则制度/00综合部业务招待费/` 目录存放审核规则的原始制度文件，是审核规则的权威来源：

1. **《业务招待费管理办法（V9.0）》** — 40 条制度，7 章，涵盖总则、分工职责、范围及标准、审批管理、费用报销、信息公开与监督检查、附则。定义了招待类型（商务/外事/其他公务/内部）、各级人员开支标准、陪同人数限制、禁止性规定等。
2. **《业务招待费审查风险点》** — 梳理了报账单封面、付款确认单、结算单、审批表、发票、支付凭证等单据的审查要点；典型违规问题（12 类）；潜在风险问题（虚假招待、超标准招待、混淆费用等）。

审核规则管理功能的初始规则库由这两份文档导出，管理员可在系统中增删改规则，系统同时保留规则来源的制度条款引用。

**制度文件变更同步**：`00规则制度/` 目录是审核规则的单一事实来源。当制度文件更新（如 V9.0 → V10.0），系统自动检测变更，重新解析文档，对比新旧规则差异，生成同步报告。管理员确认后将变更应用到数据库，确保线上规则始终与最新制度保持一致。

## Goals / Non-Goals

**Goals:**
- 提供 RESTful API，用户通过浏览器/HTTP 客户端完成文件上传到审核报告下载的全流程
- 用户认证基于 JWT，支持登录/注册，区分普通用户与管理员角色
- OCR 识别与规则审核作为异步任务执行，支持进度查询
- 审核结果持久化到数据库，支持历史记录查询
- **审核规则管理**：用户可查阅规则，管理员可增加/修改/删除规则
- 复用现有的 OCR 引擎、字段提取器、审核规则模块

**Non-Goals:**
- 不提供前端页面（前端由其他团队负责），仅提供 API
- 不改变 MinerU 引擎的配置与部署方式
- 不支持多租户（第一阶段）

## Decisions

### 架构设计

```
┌─────────────────────────────────────────────────────────┐
│  Client (Browser / HTTP)                                │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP
                       ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI App (src/web_service/)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ auth.py  │  │ router.py│  │ service.py│              │
│  │ JWT 认证 │  │ API 路由 │  │ 业务编排  │              │
│  └──────────┘  └──────────┘  └─────┬────┘              │
│                                    │                    │
│  ┌──────────┐  ┌──────────────────┐ │                  │
│  │ config.py│  │ models_db.py     │ │                  │
│  │ 配置管理 │  │ SQLAlchemy ORM   │ │                  │
│  └──────────┘  └──────────────────┘ │                  │
│                                     │                  │
└─────────────────────────────────────┼──────────────────┘
                                      │ 复用
                                      ▼
┌─────────────────────────────────────────────────────────┐
│  Existing Pipeline (src/)                                │
│  FileCollector -> MinerUEngine -> Extractor -> Checker  │
│                                   -> Reporter           │
└─────────────────────────────────────────────────────────┘
```

### API 设计

```
POST   /api/auth/register       # 用户注册
POST   /api/auth/login          # 用户登录，返回 JWT
POST   /api/tasks/upload        # 上传文件，创建审核任务
GET    /api/tasks/{task_id}     # 查询任务状态
GET    /api/tasks               # 列出当前用户的任务列表
GET    /api/tasks/{task_id}/report  # 下载审核报告 (Markdown/文本)
GET    /api/tasks/{task_id}/fields  # 查看提取的字段详情
DELETE /api/tasks/{task_id}     # 删除任务

# 审核规则管理
GET    /api/rules               # 查阅审核规则（所有用户）
POST   /api/rules               # 新增审核规则（管理员）
PUT    /api/rules/{rule_id}     # 修改审核规则（管理员）
DELETE /api/rules/{rule_id}     # 删除审核规则（管理员）
GET    /api/rules/categories    # 列出规则分类（所有用户）

# 制度文件同步
POST   /api/rules/sync          # 手动触发制度文件同步（管理员）
GET    /api/rules/sync/status   # 查询同步状态与差异报告（管理员）
POST   /api/rules/sync/apply    # 确认应用同步变更（管理员）
GET    /api/rules/sync/history  # 查询历史同步记录
```

### 异步任务处理

OCR 识别耗时较长（单文件 10-30 秒），采用 asyncio 异步任务：

1. 用户上传文件 → 立即返回 `task_id`
2. FastAPI 后台创建 asyncio.Task 执行 OCR → 提取 → 审核
3. 用户轮询 `/api/tasks/{task_id}` 获取状态
4. 任务完成后报告文件持久化，用户可下载

**不使用 Celery/Redis 的原因**: 当前为单机 GPU 服务，asyncio 足够处理并发。后续如需水平扩展再引入消息队列。

### 数据库设计

SQLite（开发环境）/ PostgreSQL（生产环境），通过 SQLAlchemy ORM 抽象：

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT DEFAULT 'user',  -- 'user' 或 'admin'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 任务表
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    batch_name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, parsing, reviewing, completed, failed
    file_count INTEGER DEFAULT 0,
    output_dir TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 文件表（关联到任务）
CREATE TABLE task_files (
    id INTEGER PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id),
    filename TEXT NOT NULL,
    file_type TEXT,  -- pdf, image, xml, office
    parsed BOOLEAN DEFAULT FALSE,
    md_path TEXT
);

-- 审核规则表
CREATE TABLE audit_rules (
    id INTEGER PRIMARY KEY,
    category TEXT NOT NULL,         -- 单据完整性, 金额标准, 禁止性规定, 招待类型, 报销合规, 交叉稽核, 校对规则
    rule_name TEXT NOT NULL,        -- 规则名称
    clause TEXT NOT NULL,           -- 制度条款引用，如 "管理办法 V9.0 第十二条"
    level TEXT NOT NULL,            -- 高, 中, 低, 提示
    description TEXT,               -- 规则详细描述
    check_expression TEXT,          -- 检查逻辑 (JSON 表达式)
    source_document TEXT,           -- 来源文档，如 "业务招待费管理办法（V9.0）", "业务招待费审查风险点"
    enabled BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 规则变更历史
CREATE TABLE audit_rule_history (
    id INTEGER PRIMARY KEY,
    rule_id INTEGER REFERENCES audit_rules(id),
    action TEXT NOT NULL,       -- 'create', 'update', 'delete'
    old_value TEXT,             -- JSON 快照
    new_value TEXT,             -- JSON 快照
    changed_by INTEGER REFERENCES users(id),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 制度文档版本追踪
CREATE TABLE document_versions (
    id INTEGER PRIMARY KEY,
    document_name TEXT NOT NULL,       -- 文档名称，如 "业务招待费管理办法（V9.0）"
    file_path TEXT NOT NULL,           -- 文件路径，相对项目根目录
    last_mtime REAL,                   -- 上次检测时文件的修改时间 (timestamp float)
    version_tag TEXT,                  -- 版本标签，如 "V9.0", 由管理员手动设置
    parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'synced', -- 'synced', 'pending', 'applied', 'conflict'
    sync_diff TEXT,                    -- JSON: 上次同步的差异报告
    applied_by INTEGER REFERENCES users(id),
    applied_at TIMESTAMP
);

-- 同步历史
CREATE TABLE sync_history (
    id INTEGER PRIMARY KEY,
    trigger_type TEXT NOT NULL,        -- 'auto', 'manual'
    document_name TEXT NOT NULL,
    rules_added INTEGER DEFAULT 0,
    rules_modified INTEGER DEFAULT 0,
    rules_deleted INTEGER DEFAULT 0,
    diff_report TEXT,                  -- JSON: 完整差异报告
    status TEXT DEFAULT 'pending',     -- 'pending', 'applied', 'rejected'
    operated_by INTEGER REFERENCES users(id),
    operated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### MinerU 引擎生命周期

Web 服务启动时初始化 MinerU LocalAPIServer，服务关闭时优雅停止。引擎作为单例被所有任务共享。

### 文件存储

- 上传文件存于 `data/uploads/<user_id>/<task_id>/`
- 识别结果存于 `data/已识别/<batch_name>_<timestamp>/`（复用现有路径）
- 审核报告同时持久化到数据库（方便查询）和文件系统（方便下载）

### 安全考虑

- 密码使用 Passlib (bcrypt) 哈希存储
- JWT Token 有效期 24 小时，Token 中携带用户角色信息
- 文件上传大小限制 100MB
- 文件类型白名单校验（PDF, JPG, PNG, XML, DOCX, XLSX）
- 用户只能访问自己的任务数据
- 审核规则修改接口校验管理员角色，非管理员返回 403

### 角色权限

| 操作 | 普通用户 | 管理员 |
|------|---------|--------|
| 注册/登录 | ✓ | ✓ |
| 上传文件审核 | ✓ | ✓ |
| 查阅审核规则 | ✓ | ✓ |
| 新增/修改/删除规则 | ✗ | ✓ |

### 审核规则动态加载

`ComprehensiveChecker` 启动时从数据库加载启用的规则，替代硬编码的规则列表。规则变更即时生效，无需重启服务。

规则分类依据《业务招待费管理办法（V9.0）》7 章结构与《审查风险点》文档，映射为以下类别：

| 规则分类 | 来源 | 说明 |
|---------|------|------|
| 单据完整性 | 审查风险点 | 报账单封面、付款确认单、结算单、审批表、发票、支付凭证等 |
| 金额标准 | 管理办法 第九条、第十一条 | 各级人员开支标准（省管中层/市管中层/其他人员） |
| 招待类型 | 管理办法 第三条、第十条 | 商务/外事/其他公务/内部业务招待/工作餐 |
| 陪同人数 | 管理办法 第十二条、第十三条 | 对外/内部陪同比例限制 |
| 禁止性规定 | 管理办法 第十四～二十一条 | 私人会所、高档菜肴、烟酒、送礼、旅游等 |
| 报销合规 | 管理办法 第二十五～三十一条 | 支付凭证、预存签单、现金支付、拆分报销等 |
| 交叉稽核 | 审查风险点 | 差旅交叉、重复招待、超标准拆分等 |
| 审批管理 | 管理办法 第二十二条～二十四条 | 事前审批、节假日报备等 |

规则格式示例：

```json
{
  "category": "禁止性规定",
  "rule_name": "高档场所禁止",
  "clause": "管理办法 V9.0 第十四条",
  "level": "高",
  "description": "不得安排私人会所及高档娱乐、休闲、健身、保健等高消费场所",
  "source_document": "业务招待费管理办法（V9.0）",
  "check_expression": {
    "type": "keyword_match",
    "field": "merchant_name",
    "keywords": ["私人会所", "高档娱乐", "一桌餐", "一围餐", "农家乐"]
  }
}
```

### 制度文件变更同步机制

```
┌───────────────────────────────────────────────────────────┐
│  00规则制度/00综合部业务招待费/                              │
│  ├── 业务招待费管理办法（V9.0）.docx                         │
│  └── 业务招待费审查风险点.docx                               │
│                                                             │
│  ← 定时扫描: os.path.getmtime() 对比 last_mtime             │
│     扫描间隔: RULE_SYNC_INTERVAL_MIN (环境变量, 默认 2 分钟)  │
└────────────────────┬──────────────────────────────────────┘
                     │ mtime 变化 → 文件被修改
                     ▼
┌───────────────────────────────────────────────────────────┐
│  rule_parser.py — 制度文档解析器                             │
│  ├── python-docx 读取 .docx 文本                            │
│  ├── LLM 辅助解析：将制度条款转为结构化规则 JSON              │
│  └── 输出: List[AuditRule]                                 │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────┐
│  rule_sync.py — 规则对比引擎                                │
│  ├── 新旧规则按 clause + rule_name 匹配                     │
│  ├── 识别: 新增 / 修改 / 删除 / 无变化                       │
│  ├── 生成差异报告 (diff_report JSON)                        │
│  └── 更新 document_versions 表为 'pending'                   │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────┐
│  管理员通过 API 确认                                        │
│  ├── GET /api/rules/sync/status → 查看差异报告              │
│  ├── POST /api/rules/sync/apply → 确认应用                 │
│  └── 应用后: 更新 audit_rules + sync_history                │
└───────────────────────────────────────────────────────────┘
```

**变更检测**: 定时扫描 `00规则制度/` 目录，通过 `os.path.getmtime()` 获取文件最新修改时间，与 `document_versions.last_mtime` 对比。mtime 发生变化说明文件内容被修改，触发后续解析与对比流程。

**扫描间隔**: 通过环境变量 `RULE_SYNC_INTERVAL_MIN` 配置（分钟），测试期间默认 2 分钟，生产环境可调整为 30 分钟。

**同步流程**:

1. **检测**: 定时器按配置的间隔扫描 `00规则制度/` 目录，对比文件 mtime 与 `document_versions.last_mtime`
2. **解析**: mtime 变化时，调用 `rule_parser.py` 重新解析文档，使用 LLM 将制度条款转为结构化规则
3. **对比**: 按 `clause` + `rule_name` 作为规则唯一键，对比新旧规则集，确定修改了什么实际内容
4. **报告**: 生成差异报告，列出新增、修改、删除的规则详情
5. **确认**: 管理员通过 API 查看报告，确认后应用变更
6. **记录**: 所有同步操作记录到 `sync_history` 表，更新 `document_versions.last_mtime`

**冲突处理**: 若管理员手动修改了某条源自制度文件的规则，同步时标记为冲突，需人工介入解决（保留手动修改 / 覆盖为制度原文）。

## Risks / Trade-offs

- [MinerU 启动耗时] → 服务启动需等待模型加载，约 30-60 秒。启动期间 API 返回 503，就绪后正常服务
- [asyncio 并发限制] → GPU 显存有限，并发 OCR 任务数需控制（通过 asyncio.Semaphore 限制为 3）
- [SQLite 并发写入] → 开发环境够用，生产环境需切换 PostgreSQL
- [文件上传大体积] → 单个批次可能超过 100MB，需配置 uvicorn `--limit-max-request` 参数
- [LLM 解析制度文档可能不准确] → 制度条款的结构化转换依赖 LLM，需人工确认差异报告后再应用
- [管理员手动修改与制度同步的冲突] → 标记为冲突，需人工介入，优先保留制度原文
- [mtime 被手动篡改] → 极少见场景，正常文件编辑会更新 mtime；管理员可通过手动触发同步兜底

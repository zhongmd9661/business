# 业务招待费智能审核系统


基于 MinerU OCR 引擎的文档解析与费用审核自动化系统，面向企业财务报销场景。支持批量 OCR 识别、双引擎字段提取、多维度规则审核和报告生成。

## 工作流程

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐      ┌────────────┐      ┌────────────┐
│  ① 扫描文档  │ ──→  │ ② OCR 识别  │ ──→  │ ③ 字段提取  │ ──→  │ ④ 规则审核  │ ──→  │ ⑤ 审核报告  │
│  (PDF/图片)  │      │ (MinerU 引擎) │      │ (正则/LLM)  │      │ (34+条规则)  │      │ (文本+Markdown)│
└─────────────┘      └──────────────┘      └──────────────┘      └────────────┘      └────────────┘
```

## 快速开始

```powershell
# 1. 准备材料 — 将一批单据放入 input 的子文件夹
Copy-Item "01业务招待费材料案例\某批次" "data\input\" -Recurse

# 2. 运行审核（处理完退出）
.venv\Scripts\python.exe -m scripts.batch_parse --once

# 3. 查看结果 — data/已识别/<批次名>_<时间戳>/审核报告.md
```

## 系统架构

```
┌───────────────────────────────────────────────────────────────────────────────   ┐
│  输入: data/input/<批次>/                                                        │
│  ├── 1_发票.pdf                                                                  │
│  ├── 2_审批单.jpg                                                                │
│  ├── 3_支付凭证.png                                                              │
│  └── 4_发票.xml                                                                  │
└───────────────────────────┬───────────────────────────────────────────────────   ┘
                                                                                   │
                            ▼
┌───────────────────────────────────────────────────────────────────────────────   ┐
│  FileCollector                                                                   │
│  ───────────────                                                                 │
│  ZIP 解压 · 按 ###_ 序号排序 · 支持 PDF / 图片 / Office / XML                    │
└───────────────────────────┬───────────────────────────────────────────────────   ┘
                                                                                   │
                            ▼
┌───────────────────────────────────────────────────────────────────────────────   ┐
│  MinerUEngine / xml_to_md                                                        │
│  ────────────────────────────                                                    │
│  PDF / 图片 / Office ─→ MinerU LocalAPIServer ─→ Markdown                        │
│  XML ─→ xml_to_md (全电发票直接转 Markdown)                                      │
└───────────────────────────┬───────────────────────────────────────────────────   ┘
                                                                                   │
                            ▼
┌───────────────────────────────────────────────────────────────────────────────   ┐
│  OutputOrganizer                                                                 │
│  ───────────────────                                                             │
│  目录扁平化 · 摘要注入 · JSON / 图片分离                                         │
│                                                                                  │
│  输出: data/已识别/<批次>/识别结果/                                              │
│  ├── 1_发票.md                                                                   │
│  ├── 2_审批单.md                                                                 │
│  ├── 3_支付凭证.md                                                               │
│  ├── _json/                                                                      │
│  └── images/                                                                     │
└───────────────────────────┬───────────────────────────────────────────────────   ┘
                                                                                   │
            ┌───────────────┴───────────────                                       ┐
            ▼                               ▼
┌───────────────────────────┐  ┌────────────────────────────────────────────────   ┐
│  FieldExtractor           │  │  LlmFieldExtractor                                │
│  ──────────────────────── │  │  ─────────────────────                            │
│  正则表达式 + 表格解析    │  │  Anthropic 兼容 API                               │
│  (默认引擎)              │  │  通过 skill/ 动态加载规则                          │
│                          │  │  通过 USE_LLM_EXTRACTOR 切换                       │
└──────────┬───────────────┘  └──────────────┬──────────────────────────────────   ┘
           │                                                                       │
           └──────────┬──────────────────────                                      ┘
                      ▼
┌───────────────────────────────────────────────────────────────────────────────   ┐
│  ExtractedFields (结构化数据)                                                    │
└───────────────────────────┬───────────────────────────────────────────────────   ┘
                                                                                   │
                            ▼
┌───────────────────────────────────────────────────────────────────────────────   ┐
│  ComprehensiveChecker                                                            │
│  ──────────────────────────                                                      │
│  ├── DocumentIntegrityChecker     ─── 单据完整性 (7 条)                          │
│  ├── AmountStandardChecker        ─── 金额标准 (5 条)                            │
│  ├── ReceptionTypeChecker         ─── 招待类型与陪同人数 (3 条)                  │
│  ├── ProhibitionChecker           ─── 禁止性规定 (6 条)                          │
│  ├── ReimbursementComplianceCheck ─── 报销合规 (6 条)                            │
│  ├── CrossAuditChecker            ─── 交叉稽核 (4 条)                            │
│  └── ProofreadingChecker          ─── 跨文档校对 (6 条)                          │
│                                                                                  │
│  批次聚合: 金额取发票→报账单→审批单  ·  人数取第一个非空值                       │
└───────────────────────────┬───────────────────────────────────────────────────   ┘
                                                                                   │
                            ▼
┌───────────────────────────────────────────────────────────────────────────────   ┐
│  ComprehensiveReporter                                                           │
│  ───────────────────────────                                                     │
│  ├── 审核报告.txt    ─── 文本格式                                                │
│  ├── 审核报告.md     ─── Markdown 格式 (含字段对比表)                            │
└───────────────────────────┬───────────────────────────────────────────────────   ┘
                                                                                   │
              ┌─────────────┴─────────────                                         ┐
              │                                                                    │
    (仅高风险) │                           │ 正常结束
              ▼                                                                    │
┌───────────────────────────┐                                                      │
│  WebhookNotifier          │                                                      │
│  ──────────────────────── │                                                      │
│  POST http://localhost:   │                                                      │
│  9999/hook                │                                                      │
│  高风险发现列表            │                                                     │
└───────────────────────────┘                                                      │
                                                                                   │
                                        ▼
                              清理已处理的源文件夹
```

## 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| **批次处理** | `src/batch_processing/` | 文件收集、ZIP 解压、序号排序、进度显示 |
| **文档解析** | `src/document_parsing_pipeline/` | MinerU 引擎管理、PDF/图片/Office → Markdown |
| **费用审核** | `src/expense_review_comprehensive/` | 字段提取、规则检查、报告生成、告警通知 |
| **输出可视化** | `src/output_visualization/` | 目录扁平化、摘要注入、JSON/图片分离 |
| **标准查询** | `src/standards_query/` | 报销标准查询 |
| **Web 服务** | `src/web_service/` | FastAPI Web 服务：文件上传、任务管理、规则管理、标准设置、认证 |
| **申请表单** | `src/application_form/` | 审批单/申请单/报账单表单生成 |

### 费用审核模块

| 文件                        | 类                                                                                       | 职责                                   |
| ------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------ |
| `models.py`               | `RuleCategory`, `Finding`, `ExtractedFields`, `BatchReviewContext`, `BatchReviewReport` | 数据模型和常量定义                            |
| `extractor.py`            | `FieldExtractor`                                                                        | 正则规则字段提取器（默认）                        |
| `llm_extractor.py`        | `LlmFieldExtractor`                                                                     | LLM 字段提取器（通过 `USE_LLM_EXTRACTOR` 切换） |
| `checkers.py`             | `ComprehensiveChecker` + 6 个子 Checker                                                   | 单文档审核 + 批次聚合 + 跨文档检测                 |
| `proofreading_checker.py` | `ProofreadingChecker`                                                                   | 6 条跨文档校对规则                           |
| `reporter.py`             | `ComprehensiveReporter`                                                                 | 报告生成器（文本 + Markdown 双格式）             |
| `notifier.py`             | `WebhookNotifier`                                                                       | 高风险 Webhook 告警通知                     |

## Web 服务

系统提供 FastAPI Web 服务，支持在线文件上传、智能审核、标准设置等功能。

### 启动服务

```powershell
# 在项目根目录执行
.venv\Scripts\python.exe -m uvicorn src.web_service.app:app --host 0.0.0.0 --port 8006
```

### 访问地址

| 页面 | 地址 | 说明 |
|------|------|------|
| 招待费智能体主页 | `http://localhost:8006/ui-index` | 首页入口 |
| 文件上传页 | `http://localhost:8006/upload` | 上传单据文件 |
| 智能审核页 | `http://localhost:8006/audit` | 在线审核 |
| 提交记录页 | `http://localhost:8006/records` | 查看历史记录 |
| 参考资料页 | `http://localhost:8006/reference` | 制度文档参考 |
| API 文档 | `http://localhost:8006/docs` | Swagger UI |
| 健康检查 | `http://localhost:8006/api/health` | 服务状态 |

### Web 服务模块

| 文件 | 职责 |
|------|------|
| `app.py` | FastAPI 应用入口、静态文件挂载、UI 路由 |
| `service.py` | MinerU 引擎生命周期管理 |
| `models_db.py` | SQLAlchemy 数据模型 |
| `router.py` | 任务管理、认证路由 |
| `router_rule.py` | 规则管理路由 |
| `router_standards.py` | 标准查询路由 |
| `router_standards_admin.py` | 标准设置路由（密码保护） |
| `router_application_form.py` | 申请表单生成路由 |
| `rule_sync.py` | 规则同步扫描器 |

### UI 界面

`招待费智能体/ui/` 目录下的 HTML 页面已集成到 Web 服务中，通过 `/ui/` 路径提供静态资源，快捷路由方便直接访问各页面。

## 审核规则体系

覆盖 **7 个规则类别**，约 **34 条具体规则**：

| 规则类别 | 规则数 | 关键规则 |
|----------|--------|----------|
| **单据完整性** | 7 | 报账单号一致性、费用明细、支付凭证(2024-04后强制)、支付流水(2025-09后强制)、往来公函(2025-12后外部强制)、发票查验、网格分摊表签章 |
| **金额标准** | 5 | 外部招待矩阵(人员层级×招待类型)、内部招待(150/100元)、工作餐(60元)、酒水单价(100元)、纪念品(200元) |
| **招待类型与陪同人数** | 3 | 类型-对象匹配、外部陪同(≤5对等, >5超一半)、内部陪同(≤10时3人, >10时1/3) |
| **禁止性规定** | 6 | 高档场所、高档菜品、烟酒、批量购买、公款送礼、变相旅游 |
| **报销合规** | 6 | 事前审批、大额现金(>5000)、拆分报销、混淆费用、发票类型、预存签单 |
| **交叉稽核** | 4 | 企业经营状态、节日招待报备、重复招待、差旅期间招待 |
| **校对规则** | 6 | 金额一致性、日期一致性、招待标准、单位状态、支付凭证一致性、活动函件日期 |

### 严重级别

四级：`高` → `中` → `低` → `提示`

### 批次聚合逻辑

同一批次文档属于同一笔招待事件，金额和人数不重复计算：

- **金额**：取第一个可靠来源（优先级：发票 → 报账单 → 审批单 → 申请单）
- **人数**：取第一个非空值

## 目录结构

```
D:\00_项目\招待费智能体\
├── src/                              # 核心源码
│   ├── batch_processing/             # 批次处理
│   │   ├── collector.py              # 文件收集、ZIP 解压、序号分配
│   │   ├── runner.py                 # 进度显示、耗时统计、汇总报告
│   │   └── xml_to_md.py              # 全电发票 XML → Markdown
│   ├── document_parsing_pipeline/    # 文档解析管道
│   │   └── engine.py                 # MinerU LocalAPIServer 生命周期管理
│   ├── expense_review_comprehensive/ # 费用审核
│   │   ├── models.py                 # 数据模型
│   │   ├── extractor.py              # 正则规则字段提取器
│   │   ├── llm_extractor.py          # LLM 字段提取器
│   │   ├── checkers.py               # 6 个单文档 Checker
│   │   ├── proofreading_checker.py   # 跨文档校对 Checker
│   │   ├── reporter.py               # 报告生成器
│   │   └── notifier.py               # Webhook 告警通知
│   └── output_visualization/         # 输出可视化
│       └── organizer.py              # 目录扁平化、摘要注入
├── scripts/                          # 入口脚本
│   ├── batch_parse.py                # 主入口：OCR + 字段提取 + 审核
│   ├── download_models.py            # 下载 MinerU 模型
│   ├── cleanup_outputs.py            # 清理旧输出目录
│   └── convert_rules.py              # 规则文档转 Markdown
├── data/                             # 数据目录
│   ├── input/                        # 输入（批次文件夹放在这里）
│   └── 已识别/                       # 输出（识别结果 + 审核报告）
├── skill/                            # 审核规则 Skill（动态加载到 LLM 提示词）
│   ├── expense-review-rules/         # 审核规则（制度条款 + 风险点）
│   └── 00综合部业务招待费/            # 批次审核标准
├── 00规则制度/                       # 原始制度文档 (.docx)
├── 00规则制度_md/                    # 制度 Markdown 转换版
├── 校对规则/                         # 跨文档校对规则定义
├── 01业务招待费材料案例/              # 测试案例数据
├── openspec/                         # OpenSpec 规范文档
├── tests/                            # 测试用例
├── pyproject.toml                    # 项目配置
├── .env                              # 环境变量
└── requirements.txt                  # 依赖清单
```

## 使用方式

### 运行模式

| 模式 | 命令 | 说明 |
|------|------|------|
| **单次运行** | `python -m scripts.batch_parse --once` | 处理完现有批次后退出 |
| **监听模式** | `python -m scripts.batch_parse` | 常驻运行，每 5 秒检测新批次 |

### 输入要求

- 将一批单据放在 `data/input/<批次名>/` 目录下
- 文件名以 `###_` 开头（3 位数字 + 下划线），系统按序号排序
- 支持格式：PDF、JPG、PNG、XML、Office 文档
- XML 文件（全电发票）直接转 Markdown，不经过 OCR 引擎

### 输出结构

```
data/已识别/<批次名>_<时间戳>/
├── 源文件/              # 原始文件归档
├── 识别结果/            # OCR 识别结果
│   ├── 1_发票.md
│   ├── 2_审批单.md
│   ├── 字段提取结果.json # 结构化字段
│   ├── 字段提取结果.md   # 可读汇总
│   ├── _json/           # 中间 JSON
│   └── images/          # 解析图片
├── 审核报告.txt          # 文本格式报告
└── 审核报告.md           # Markdown 格式报告
```

### 字段提取器切换

通过环境变量切换正则规则提取器和 LLM 提取器：

```powershell
# 使用 LLM 提取器（默认使用正则规则提取器）
$env:USE_LLM_EXTRACTOR = "1"
```

LLM 提取器需要配置 Anthropic 兼容 API：

```powershell
$env:ANTHROPIC_BASE_URL = "http://localhost:1234"
$env:ANTHROPIC_AUTH_TOKEN = "lmstudio"
```

### Skill 审核

除了自动化脚本审核，也支持通过 Claude Code Skill 进行人工辅助审核：

```powershell
# 在项目中启动 Claude Code，加载审核规则上下文
/expense-review-rules
# 或
/00综合部业务招待费
```

## 配置

### 环境变量 (.env)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MINERU_MODEL_SOURCE` | `modelscope` | 模型来源：`modelscope`（国内镜像）/ `huggingface` |
| `MINERU_DEVICE` | `cuda` | GPU 设备：`cuda` / `mps` / `cpu` |
| `USE_LLM_EXTRACTOR` | 未设置 | 设置为 `1`/`true`/`yes` 启用 LLM 字段提取 |
| `ANTHROPIC_BASE_URL` | - | LLM API 地址（使用 LLM 提取器时必需） |
| `ANTHROPIC_AUTH_TOKEN` | - | LLM API 密钥 |

### 系统要求

- **操作系统**：Windows 11
- **Python**：3.11+
- **GPU**：NVIDIA CUDA 11.8 + cuDNN 8.9.7
- **模型**：MinerU 模型通过 ModelScope 下载（约数 GB）

## 辅助脚本

| 脚本 | 用途 |
|------|------|
| `scripts/download_models.py` | 下载 MinerU OCR 模型 |
| `scripts/cleanup_outputs.py` | 清理 `data/已识别/` 下旧输出，支持 `--keep N` / `--days N` / `--dry-run` |
| `scripts/convert_rules.py` | 将 `00规则制度/` 下的 .docx 转为 Markdown |

## 开发

### 安装依赖

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 运行测试

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

### 下载模型

```powershell
.venv\Scripts\python.exe scripts/download_models.py
```

## 技术细节

### 双引擎字段提取

系统支持两种字段提取方式，接口完全一致：

- **规则提取器** (`extractor.py`)：基于正则表达式 + HTML/Markdown 表格解析
- **LLM 提取器** (`llm_extractor.py`)：通过 Anthropic 兼容 API 调用本地大模型

### 动态规则加载

LLM 系统提示词从 `skill/` 目录动态读取审核规则文档，非硬编码，便于制度更新时无需修改代码。

### 时间线规则

审核规则根据招待日期自动切换。例如：

- 2024-04-01 后：必须附带支付凭证
- 2025-09-01 后：必须附带支付流水
- 2025-12-04 后：外部招待必须附带往来公函

### 异步架构

整个管线基于 `asyncio`，MinerU LocalAPIServer 通过 HTTP 异步调用，支持并发处理。

## 审核规则依据

基于《中国移动广东公司清远分公司业务招待费管理办法（V9.0）》及审查风险点清单，所有规则均标注对应制度条款。

## 规范文档

项目使用 **OpenSpec** 进行规范驱动开发，所有功能变更均有对应的提案、设计、规范和任务跟踪：

- `openspec/specs/` — 10 个已发布规范
- `openspec/changes/` — 进行中的变更提案
- `openspec/changes/archive/` — 已归档的变更

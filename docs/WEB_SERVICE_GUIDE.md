# 业务招待费智能审核系统 — Web 服务使用指南

> 基于 FastAPI 的 Web 应用，提供完整的前端界面，支持文件上传、OCR 识别、规则审核、报告下载的全流程能力。
> 同时提供 RESTful API 供第三方系统集成。

## 目录

- [快速开始](#快速开始)
- [环境准备](#环境准备)
- [启动服务](#启动服务)
- [Web 界面使用](#web-界面使用)
- [API 使用指南](#api-使用指南)
- [审核标准管理](#审核标准管理)
- [制度文件同步](#制度文件同步)
- [配置说明](#配置说明)
- [常见问题](#常见问题)

---

## 快速开始

```powershell
# 1. 进入项目目录
cd "D:\00_项目\招待费智能体"

# 2. 设置环境变量
$env:PYTHONPATH = "D:\00_项目\招待费智能体"

# 3. 启动服务
& .venv\Scripts\python.exe -m uvicorn src.web_service.app:app --host 0.0.0.0 --port 8006
```

启动成功后访问：
- **Web 界面**：`http://localhost:8006/`
- API 文档：`http://localhost:8006/docs`
- 健康检查：`http://localhost:8006/api/health`

---

## 环境准备

### 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 11 / Linux |
| Python 版本 | >= 3.11 |
| GPU | NVIDIA GPU（推荐 RTX 6000 及以上） |
| 显存 | >= 16GB |

### 虚拟环境

```powershell
# 创建虚拟环境（首次）
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-web.txt
```

### LLM 配置（可选）

如需使用 LLM 字段提取，需配置 Anthropic 兼容 API：

```powershell
$env:ANTHROPIC_BASE_URL = "http://192.168.231.1:1235"
$env:ANTHROPIC_AUTH_TOKEN = "lmstudio"
$env:LLM_MODEL = "qwen/qwen3.6-27b"
$env:USE_LLM_EXTRACTOR = "true"
```

---

## 启动服务

### 方式一：命令行启动

```powershell
cd "D:\00_项目\招待费智能体"
$env:PYTHONPATH = "D:\00_项目\招待费智能体"
& .venv\Scripts\python.exe -m uvicorn src.web_service.app:app --host 0.0.0.0 --port 8006
```

### 方式二：带配置启动

```powershell
cd "D:\00_项目\招待费智能体"
$env:PYTHONPATH = "D:\00_项目\招待费智能体"
$env:RULE_SYNC_INTERVAL_MIN = "5"
$env:MAX_CONCURRENT_OCR = "3"
& .venv\Scripts\python.exe -m uvicorn src.web_service.app:app --host 0.0.0.0 --port 8006
```

### 启动日志示例

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
2026-07-07 14:49:45.524 | INFO    | Started local mineru-api: http://127.0.0.1:65128
2026-07-07 14:49:52.070 | INFO    | Loaded 43 audit rules from database
2026-07-07 14:49:52.071 | INFO    | MinerU engine started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8006
```

---

## Web 界面使用

### 1. 登录/注册

访问 `http://localhost:8006/`，首次使用需要注册账号：
- 点击"注册"标签页
- 输入用户名和密码
- 注册成功后切换到"登录"标签页登录

### 2. 任务管理

登录后默认进入任务管理页面：
- 查看所有历史任务及其状态
- 点击任务卡片查看详情
- 对已完成的任务可以查看报告、字段提取结果或删除任务

**任务状态说明：**

| 状态 | 说明 |
|------|------|
| `等待处理` | 任务已创建，等待 OCR 识别 |
| `识别中` | 正在进行 OCR 识别和字段提取 |
| `已完成` | 审核完成，可以下载报告 |
| `失败` | 处理失败，可查看错误信息 |

### 3. 文件上传

点击左侧菜单"文件上传"：
- 拖拽文件到上传区域，或点击选择文件
- 支持 PDF、JPG、PNG、XML、DOCX、XLSX 格式
- 选择文件后点击"开始上传"
- 上传成功后自动跳转到任务管理页面

### 4. 审核报告

- 在任务管理中点击已完成的任务
- 点击"查看报告"按钮
- 报告以 Markdown 格式展示，支持直接查看或下载

### 5. 审核标准管理（管理员）

点击左侧菜单"规则管理"：
- 查看所有审核规则及其分类
- 按分类筛选规则
- 点击规则查看详情（包括检查表达式）
- 管理员可以：
  - 新增审核规则
  - 编辑现有规则
  - 启用/禁用规则
  - 删除规则

### 6. 制度文件同步（管理员）

点击左侧菜单"制度同步"：
- 查看制度文档的同步状态
- 手动触发同步
- 查看同步历史记录

---

## API 使用指南

> 除了 Web 界面，系统还提供完整的 RESTful API 供第三方系统集成。

### 1. 用户注册

```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8006/api/auth/register" `
  -ContentType "application/json" `
  -Body '{"username": "zhangsan", "password": "mysecurepass"}'
```

**响应：**
```json
{
  "id": 1,
  "username": "zhangsan",
  "role": "user",
  "created_at": "2026-07-07T14:50:00"
}
```

### 2. 用户登录

```powershell
$loginResponse = Invoke-RestMethod -Method POST -Uri "http://localhost:8006/api/auth/login" `
  -ContentType "application/json" `
  -Body '{"username": "zhangsan", "password": "mysecurepass"}'

# 保存 Token
$token = $loginResponse.access_token
$headers = @{ Authorization = "Bearer $token" }
```

**响应：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "role": "user"
}
```

### 3. 上传文件并审核

```powershell
& .venv\Scripts\python.exe -X utf8 -c @'
import requests

BASE_URL = "http://localhost:8006"
TOKEN = "YOUR_TOKEN_HERE"
headers = {"Authorization": f"Bearer {TOKEN}"}

files_to_upload = [
    "D:/00_项目/招待费智能体/01业务招待费材料案例/案例3/【发票】26442000002098662676.pdf",
    "D:/00_项目/招待费智能体/01业务招待费材料案例/案例3/业务审批单.jpg",
    "D:/00_项目/招待费智能体/01业务招待费材料案例/案例3/业务接待报账单.pdf",
    "D:/00_项目/招待费智能体/01业务招待费材料案例/案例3/支付凭证.jpg",
]

file_data = []
for fpath in files_to_upload:
    with open(fpath, "rb") as f:
        file_data.append(("files", (fpath.split("/")[-1], f.read(), "application/octet-stream")))

resp = requests.post(f"{BASE_URL}/api/tasks/upload", files=file_data, headers=headers)
print(f"任务 ID: {resp.json()['task_id']}")
print(f"状态: {resp.json()['status']}")
'@
```

**响应：**
```json
{
  "task_id": 1,
  "status": "pending"
}
```

### 4. 查询任务状态

```powershell
# 查询单个任务
Invoke-RestMethod -Method GET -Uri "http://localhost:8006/api/tasks/1" `
  -Headers $headers

# 查询任务列表
Invoke-RestMethod -Method GET -Uri "http://localhost:8006/api/tasks?skip=0&limit=50" `
  -Headers $headers
```

### 5. 下载审核报告

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8006/api/tasks/1/report" `
  -Headers $headers | Out-File -Encoding utf8 "审核报告.md"
```

### 6. 查看字段提取结果

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8006/api/tasks/1/fields" `
  -Headers $headers
```

### 7. 删除任务

```powershell
Invoke-RestMethod -Method DELETE -Uri "http://localhost:8006/api/tasks/1" `
  -Headers $headers
```

---

## 审核标准管理

> 以下接口需要管理员权限。

### 查看规则列表

```powershell
# 查看所有规则
Invoke-RestMethod -Method GET -Uri "http://localhost:8006/api/rules" `
  -Headers $adminHeaders

# 按分类筛选
Invoke-RestMethod -Method GET -Uri "http://localhost:8006/api/rules?category=金额标准" `
  -Headers $adminHeaders
```

### 查看规则分类

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8006/api/rules/categories" `
  -Headers $adminHeaders
```

**响应：**
```json
[
  "单据完整性",
  "金额标准",
  "招待类型与陪同人数",
  "禁止性规定",
  "报销合规",
  "交叉稽核",
  "校对规则"
]
```

### 新增审核规则

```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8006/api/rules" `
  -ContentType "application/json" `
  -Headers $adminHeaders `
  -Body @'
{
  "category": "金额标准",
  "rule_name": "人均费用上限",
  "clause": "管理办法 第九条",
  "level": "高",
  "description": "人均费用不得超过规定标准",
  "check_expression": "{\"type\": \"amount_compare\", \"field\": \"per_person_amount\", \"operator\": \">\", \"threshold\": 250}"
}
'@
```

### 修改审核规则

```powershell
Invoke-RestMethod -Method PUT -Uri "http://localhost:8006/api/rules/1" `
  -ContentType "application/json" `
  -Headers $adminHeaders `
  -Body '{"level": "中", "enabled": false}'
```

### 删除审核规则

```powershell
Invoke-RestMethod -Method DELETE -Uri "http://localhost:8006/api/rules/1" `
  -Headers $adminHeaders
```

---

## 制度文件同步

### 手动触发同步

```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8006/api/rules/sync" `
  -Headers $adminHeaders
```

### 查看同步状态

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8006/api/rules/sync/status" `
  -Headers $adminHeaders
```

### 应用同步变更

```powershell
# 确认应用
Invoke-RestMethod -Method POST -Uri "http://localhost:8006/api/rules/sync/apply" `
  -ContentType "application/json" `
  -Headers $adminHeaders `
  -Body '{"apply": true}'

# 拒绝变更
Invoke-RestMethod -Method POST -Uri "http://localhost:8006/api/rules/sync/apply" `
  -ContentType "application/json" `
  -Headers $adminHeaders `
  -Body '{"apply": false}'
```

### 查看同步历史

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8006/api/rules/sync/history?limit=20" `
  -Headers $adminHeaders
```

---

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | `sqlite:///data/web_service.db` | 数据库连接字符串 |
| `JWT_SECRET_KEY` | `dev-secret-key-change-in-production` | JWT 签名密钥 |
| `JWT_EXPIRE_MINUTES` | `1440` | Token 有效期（分钟） |
| `MAX_UPLOAD_SIZE_MB` | `100` | 单文件上传大小限制（MB） |
| `RULE_SYNC_INTERVAL_MIN` | `2` | 制度文件扫描间隔（分钟） |
| `MAX_CONCURRENT_OCR` | `3` | 并发 OCR 任务数 |
| `USE_LLM_EXTRACTOR` | `false` | 是否使用 LLM 字段提取 |
| `RULE_SYNC_WEBHOOK_URL` | *(空)* | 规则同步 Webhook 通知地址 |
| `ANTHROPIC_BASE_URL` | `http://192.168.231.1:1235` | LLM API 地址 |
| `ANTHROPIC_AUTH_TOKEN` | `lmstudio` | LLM API 密钥 |
| `LLM_MODEL` | `qwen/qwen3.6-27b` | LLM 模型名称 |

### 支持的文件类型

| 类型 | 扩展名 |
|------|--------|
| PDF | `.pdf` |
| 图片 | `.jpg`, `.jpeg`, `.png` |
| XML | `.xml` |
| Office | `.docx`, `.xlsx` |

### 用户角色

| 角色 | 权限 |
|------|------|
| `user` | 上传文件、查看任务、下载报告、查阅规则 |
| `admin` | 所有权限 + 规则管理 + 制度文件同步 |

### 创建管理员账户

```powershell
& .venv\Scripts\python.exe -X utf8 -c @'
from src.web_service.models_db import SessionLocal, User
db = SessionLocal()
user = db.query(User).filter(User.username == "你的用户名").first()
user.role = "admin"
db.commit()
db.close()
print("管理员角色已设置")
'@
```

---

## 常见问题

### Q1: 服务启动慢怎么办？

服务启动时需要加载 MinerU OCR 引擎，首次启动约需 30-60 秒。启动期间 API 会返回 503，就绪后正常服务。

### Q2: 如何增加并发 OCR 任务数？

设置环境变量 `MAX_CONCURRENT_OCR`，注意 GPU 显存限制：

```powershell
$env:MAX_CONCURRENT_OCR = "5"
```

### Q3: 审核规则如何即时生效？

规则通过 Web 界面或 API 修改后，系统会自动重载规则，无需重启服务。

### Q4: 如何使用测试案例？

项目 `01业务招待费材料案例/` 目录包含 3 组测试材料：
- `案例1/` - 基础测试
- `案例3/` - 完整测试（9 个文件）
- `案例标准测试材料/` - 标准测试集

### Q5: 如何切换到 PostgreSQL 数据库？

```powershell
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/expense_review"
```

### Q6: 前端页面无法访问？

确保服务正常启动，访问 `http://localhost:8006/`。如果仍然无法访问，检查：
1. 端口 8006 是否被占用
2. 防火墙设置是否阻止访问
3. 静态文件目录是否存在：`src/web_service/static/`

---

## 完整示例脚本

```powershell
# ============================================
# 业务招待费智能审核系统 - 完整使用示例
# ============================================

# 1. 启动服务（在另一个终端窗口运行）
# cd "D:\00_项目\招待费智能体"
# $env:PYTHONPATH = "D:\00_项目\招待费智能体"
# & .venv\Scripts\python.exe -m uvicorn src.web_service.app:app --host 0.0.0.0 --port 8006

# 2. 注册并登录
$BASE_URL = "http://localhost:8006"

# 注册
RegisterResponse = Invoke-RestMethod -Method POST -Uri "$BASE_URL/api/auth/register" `
  -ContentType "application/json" `
  -Body '{"username": "demo_user", "password": "demo123456"}'

# 登录
$LoginResponse = Invoke-RestMethod -Method POST -Uri "$BASE_URL/api/auth/login" `
  -ContentType "application/json" `
  -Body '{"username": "demo_user", "password": "demo123456"}'

$Token = $LoginResponse.access_token
$Headers = @{ Authorization = "Bearer $Token" }

# 3. 上传文件并等待完成
& .venv\Scripts\python.exe -X utf8 -c @'
import requests, time

BASE_URL = "http://localhost:8006"
TOKEN = "YOUR_TOKEN_HERE"
headers = {"Authorization": f"Bearer {TOKEN}"}

# 上传文件
files = [
    ("files", ("invoice.pdf", open("01业务招待费材料案例/案例3/【发票】26442000002098662676.pdf", "rb").read(), "application/pdf")),
    ("files", ("approval.jpg", open("01业务招待费材料案例/案例3/业务审批单.jpg", "rb").read(), "image/jpeg")),
]
resp = requests.post(f"{BASE_URL}/api/tasks/upload", files=files, headers=headers)
task_id = resp.json()["task_id"]
print(f"任务 ID: {task_id}")

# 等待完成
while True:
    status = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=headers).json()
    print(f"状态: {status['status']}")
    if status["status"] in ("completed", "failed"):
        break
    time.sleep(10)

# 下载报告
report = requests.get(f"{BASE_URL}/api/tasks/{task_id}/report", headers=headers).text
with open("审核报告.md", "w", encoding="utf-8") as f:
    f.write(report)
print("报告已保存到 审核报告.md")
'@
```

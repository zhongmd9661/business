# 提交失败问题调试记录

> **日期**: 2026-07-24
> **问题**: 前端 `card7-fill.html` 录入页面点击"提交"后提示"提交失败"
> **状态**: ✅ 已修复

---

## 一、问题描述

用户在 `/ui-index` 主页进入"录入招待费"页面 (`/ui/card7-fill.html`)，填写完表单后点击"提交记录"按钮，前端提示 `❌ 提交失败`。

## 二、排查过程

### 2.1 查看服务日志

服务日志 (`uvicorn` 输出) 显示：

```
INFO:     127.0.0.1:62270 - "POST /api/reception-records HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:62427 - "GET /api/reception-records?limit=500 HTTP/1.1" 404 Not Found
```

**关键发现**: `POST /api/reception-records` 和 `GET /api/reception-records` 均返回 **404 Not Found**。

### 2.2 定位前端调用

在 `招待费智能体/ui/card7-fill.html` 第 2063 行：

```javascript
const response = await fetch('/api/reception-records', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
});
```

前端提交的 JSON 数据字段（camelCase）：

| 前端字段名 | 含义 |
|---|---|
| `scenario` | 场景编码 (A/B/C/D/E/F) |
| `scenario_name` | 场景名称 |
| `submitter` | 提交人 |
| `date` | 招待日期 |
| `location` | 地点 |
| `org` | 招待对象单位 |
| `guests` | 招待对象人数 |
| `accompanyPeople` | 陪同人员 |
| `accompanyCount` | 陪同人数 |
| `perCapita` | 人均消费 |
| `baijiuPrice` | 白酒单价 |
| `winePrice` | 葡萄酒单价 |
| `giftPer` | 礼品单价 |
| `rooms` | 房间数 |
| `roomPrice` | 房价 |
| `reason` | 事由 |
| `nationality` | 国籍（仅场景B） |
| `fee` | 费用（仅场景E） |

### 2.3 检查后端路由

grep 搜索 `src/web_service/` 下所有路由注册，确认**不存在** `/api/reception-records` 相关路由。

同时检查 `models_db.py` 数据库模型，发现缺少 `ReceptionRecord` 模型。

## 三、根本原因

后端缺少招待费提交记录功能的完整实现：

1. **无数据模型**: `models_db.py` 中没有 `ReceptionRecord` 表模型
2. **无 API 路由**: 没有处理 `POST/GET/DELETE /api/reception-records` 的路由器
3. **未注册路由**: `app.py` 中未引入相关路由模块

## 四、修复方案

### 4.1 新增数据模型

在 `src/web_service/models_db.py` 中添加 `ReceptionRecord` 模型（位于 `ReceptionTemplate` 之后、Engine & Session 之前）：

```python
class ReceptionRecord(Base):
    __tablename__ = "reception_records"

    id = Column(Integer, primary_key=True)
    scenario = Column(String, nullable=False)
    scenario_name = Column(String, nullable=False)
    submitter = Column(String, default="匿名")
    date = Column(String)
    location = Column(String)
    org = Column(String)
    guests = Column(Integer)
    accompany_people = Column(String)
    accompany_count = Column(Integer)
    per_capita = Column(Float)
    total_amount = Column(Float)
    baijiu_price = Column(String)
    wine_price = Column(String)
    gift_per = Column(String)
    rooms = Column(String)
    room_price = Column(String)
    reason = Column(Text)
    nationality = Column(String)
    fee = Column(String)
    status = Column(String, default="pending")
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())
```

> **注意**: SQLAlchemy 的 `Base.metadata.create_all()` 在服务启动时自动建表，新增模型后重启服务即可创建新表。

### 4.2 新增路由文件

创建 `src/web_service/router_reception_records.py`，包含三个端点：

| 方法 | 路径 | 功能 |
|---|---|---|
| `POST` | `/api/reception-records` | 提交一条招待费记录 |
| `GET` | `/api/reception-records?scenario=&status=&limit=` | 查询记录列表（支持筛选） |
| `DELETE` | `/api/reception-records/{record_id}` | 删除记录 |

**关键细节**:
- 使用 `Request` 对象接收 body，而非 `dict` 参数（避免 FastAPI body 解析问题）
- 内置 `_camel_to_snake()` 转换函数，兼容前端 `camelCase` 字段名
- 自动计算 `total_amount = per_capita * (guests + accompany_count)`（当前端未传入时）
- 编码兼容：先尝试 UTF-8 解码，失败则回退 GBK

### 4.3 注册路由

在 `src/web_service/app.py` 的 `on_startup` 中添加路由注册：

```python
from . import router_reception_records
app.include_router(router_reception_records.router, prefix="/api", tags=["reception-records"])
```

## 五、修改文件清单

| 文件 | 改动 |
|---|---|
| `src/web_service/models_db.py` | 新增 `ReceptionRecord` 模型类 |
| `src/web_service/router_reception_records.py` | **新建** — 提交记录 API 路由 |
| `src/web_service/app.py` | 新增 `router_reception_records` 导入和注册 |

## 六、如何启动服务

### 6.1 启动步骤

```powershell
# 1. 进入项目目录
cd "D:\00_项目\02_ocr"

# 2. 启动服务（PowerShell）
& "$PWD\.venv\Scripts\python.exe" -m uvicorn src.web_service.app:app --host 0.0.0.0 --port 8006
```

### 6.2 启动成功标志

启动日志中出现以下输出即表示成功：

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8006 (Press CTRL+C to quit)
```

### 6.3 验证

| 检查项 | 命令/操作 | 预期结果 |
|---|---|---|
| 健康检查 | `curl http://127.0.0.1:8006/api/health` | `{"status":"ok","version":"0.1.0"}` |
| 提交记录 API | `GET http://127.0.0.1:8006/api/reception-records` | 返回 `[]`（空数组） |
| Swagger 文档 | 浏览器打开 `http://127.0.0.1:8006/docs` | 能看到 `reception-records` 分组 |
| 前端主页 | 浏览器打开 `http://127.0.0.1:8006/ui-index` | 正常显示招待费管理页面 |
| 提交测试 | 进入录入页，填写表单并提交 | 提示 ✅ 记录已提交 |

### 6.4 常见启动问题

| 问题 | 解决方法 |
|---|---|
| 端口 8006 被占用 | `netstat -ano \| findstr ":8006"` 查找占用进程，`taskkill /PID <pid> /F` 终止 |
| Python 环境找不到 | 确认 `.venv` 目录存在；使用完整路径 `& "$PWD\.venv\Scripts\python.exe"` |
| 数据库文件缺失 | 服务启动时 `init_db()` 会自动创建 SQLite 数据库，无需手动操作 |
| 服务启动后页面无响应 | 等待 10-15 秒（MinerU 引擎启动需要时间） |

### 6.5 停止服务

- **终端内**: 按 `Ctrl+C`
- **命令行**: `taskkill /F /FI "WINDOWTITLE eq *uvicorn*"`

## 七、相关前端文件

| 文件 | 功能 | 调用的 API |
|---|---|---|
| `招待费智能体/ui/card7-fill.html` | 录入页面 | `POST /api/reception-records` |
| `招待费智能体/ui/records.html` | 提交记录列表页 | `GET /api/reception-records`, `DELETE /api/reception-records/{id}` |
| `招待费智能体/ui/index.html` | 主页入口 | 无 API 调用 |

## 八、数据库说明

- **类型**: SQLite（文件位于项目根目录，由 `config.py` 中 `DATABASE_URL` 配置）
- **建表**: 服务启动时自动执行 `Base.metadata.create_all()`，新增模型自动建表
- **数据路径**: 见 `src/web_service/config.py` 中 `DATABASE_URL` 变量

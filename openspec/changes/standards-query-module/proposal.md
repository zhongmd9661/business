## Why

经办人在填写业务招待费申请单前，需要快速了解当前适用的招待标准（用餐标准、纪念品标准、酒水标准、陪同人数限制等），但现有系统仅有审核模块，缺乏面向经办人的标准查询与场景模板功能。

本模块提供：
1. **招待标准查询** — 按人员层级和招待类型快速查询金额标准
2. **场景接待模板** — 6 个常见场景的填写示例，经办人点击即可对照填写
3. **管理员标准管理** — 管理员可在线修改标准、模板、禁止性规定，所有变更保留审计历史

## What Changes

- 新增 `src/standards_query/` 模块，包含标准数据、查询函数、场景模板
- 新增 `src/standards_query/reference.html` — 标准参考页（Web 界面）
- 新增 `src/web_service/router_standards.py` — 面向经办人的标准查询 API
- 新增 `src/web_service/router_standards_admin.py` — 面向管理员的标准管理 API
- 新增数据库表：`reception_standards`、`reception_standard_history`、`reception_templates`
- 标准数据首次启动时自动注入默认值

## Capabilities

### New Capabilities

- `standards-query`: 招待标准快速查询，按人员层级 + 招待类型返回完整标准
- `standards-template`: 场景接待模板，6 个常见场景的填写示例
- `standards-admin`: 管理员标准管理，支持标准/模板/禁止性规定的增删改查
- `standards-audit`: 标准变更审计历史，记录所有修改操作

### Modified Capabilities

- `web-api`: 新增 `/api/standards/*`（查询）和 `/api/admin/standards/*`（管理）端点
- `user-auth`: 管理员端点复用 `get_admin_user` 权限校验
- `rule-sync`: 制度文件同步机制可扩展至招待标准管理

## Impact

- **新增**: `src/standards_query/__init__.py` — 模块入口
- **新增**: `src/standards_query/standards.py` — 标准数据（对外 6 档 + 内部 3 档 + 陪同人数规则 + 禁止性规定 + 类型说明 + 审批流程 + 节假日报备）
- **新增**: `src/standards_query/query.py` — 查询函数（快速查询、陪同人数计算、一键查询）
- **新增**: `src/standards_query/templates.py` — 场景模板数据（6 个模板）
- **新增**: `src/standards_query/reference.html` — 标准参考页（含快速查询表单 + 场景模板卡片）
- **新增**: `src/web_service/router_standards.py` — 标准查询 API（12 端点）
- **新增**: `src/web_service/router_standards_admin.py` — 标准管理 API（21 端点）
- **修改**: `src/web_service/models_db.py` — 新增 3 个 DB 表 + 种子数据
- **修改**: `src/web_service/app.py` — 注册新路由
- **修改**: `openspec/changes/web-service/proposal.md` — 补充标准管理说明
- **修改**: `openspec/changes/web-service/design.md` — 补充数据库表设计

## 运行指令

```powershell
# 标准参考页
# http://localhost:8006/api/standards/reference

# 管理员管理页面（需 admin 角色）
# http://localhost:8006/api/admin/standards/all
```

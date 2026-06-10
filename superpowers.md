不是的，这里需要澄清一个非常关键的误区。

在 OpenSpec + Superpowers 的融合工作流中，**并不是** `/opsx:apply` 自动调用 Superpowers，恰恰相反，**我们需要主动禁用 OpenSpec 自带的 `/opsx:apply` 命令**，然后由开发者手动触发 Superpowers 来接管执行。

这两个工具本身是相互独立的，并没有内置的 API 集成或自动调用机制。所谓的“联动”，完全是靠架构师（也就是你）在同一个会话中手动“桥接”的。

具体的操作逻辑如下：

**1. 禁用 OpenSpec 的 apply**  
因为 OpenSpec 自己的 `/opsx:apply` 缺乏严格的 TDD（测试驱动开发）纪律，所以我们需要通过配置（如执行 `openspec config profile`）取消选中 `Apply tasks`，彻底干掉它。

**2. 手动触发 Superpowers 接管**  
当 OpenSpec 生成好 `tasks.md`（任务清单）后，你需要手动输入 Superpowers 的命令来启动执行流程：

- 首先执行 `/superpowers:writing-plans`：让 Superpowers 读取 OpenSpec 产出的 tasks，将其拆解为 2-5 分钟可完成的详细计划。
- 然后执行 `/superpowers:subagent-driven-development`：让 Superpowers 启动子代理，严格按照 TDD 铁律和双重审查机制去实现代码。

**3. 回到 OpenSpec 验证归档**  
等 Superpowers 把代码写完并审查通过后，你再回到 OpenSpec 的流程，执行 `/opsx:verify` 验证需求，最后执行 `/opsx:archive` 归档变更。





这是一个非常专业且切中要害的问题。在实际的复杂项目中，同时存在多个 `change`（例如：`add-user-auth`、`refactor-database`、`fix-payment-bug`）是常态。

Superpowers 本身并不会“自动”去猜你想要执行哪个 change。要确定 `tasks.md`，**核心在于“上下文切换”和“工作目录的隔离”**。

具体来说，Superpowers 是通过以下机制来确定并读取正确的 `tasks.md` 的：

### 1. 物理路径隔离（最核心的机制）

在 OpenSpec 的设计规范中，每一个 `change` 都是一个独立的文件夹。

- 例如：`.openspec/changes/add-user-auth/tasks.md`
- 例如：`.openspec/changes/refactor-database/tasks.md`

当你准备让 Superpowers 接管某个特定 change 时，你需要**明确指定该 change 的路径或名称**作为上下文。

### 2. 手动指定上下文（桥接操作）

在执行 `/superpowers:writing-plans` 之前，你需要通过自然语言或参数，告诉 Superpowers 当前要处理的是哪一个 change。

**实际操作示例：**

- **错误做法**：直接输入 `/superpowers:writing-plans`（如果当前目录下有多个 tasks.md，AI 可能会混淆或报错）。
- **正确做法**：输入 `/superpowers:writing-plans .openspec/changes/add-user-auth/tasks.md`，或者在提示词中明确说明：“请读取 `add-user-auth` 这个 change 下的 tasks.md，并生成执行计划”。

### 3. 工作区状态锁定（Session Context）

Superpowers 在执行 `/superpowers:writing-plans` 时，会将你指定的这个 `tasks.md` 解析为当前的**唯一执行蓝图（Active Context）**。

- 在这个会话（Session）中，Superpowers 的所有 TDD 测试编写、代码生成、审查机制，都会**严格且仅**围绕这一个 `tasks.md` 展开。
- 其他 change 的 `tasks.md` 会被完全忽略，直到当前 change 完成并归档（Archive）。

### 4. 最佳实践建议：一次只处理一个 Change

为了保证 Superpowers 的 TDD 纪律和代码审查质量，**强烈建议不要试图让 Superpowers 一次性读取多个 change 的 tasks**。

**标准的高阶工作流应该是：**

1. 处理 Change A：`/superpowers:writing-plans [Change A 的路径]` -> `/superpowers:subagent-driven-development` -> `/opsx:verify [Change A]` -> `/opsx:archive [Change A]`。
2. 处理 Change B：`/superpowers:writing-plans [Change B 的路径]` -> ...

**总结：**  
Superpowers 确定 `tasks.md` 的方式不是“智能猜测”，而是**“精准投喂”**。作为架构师，你需要通过**指定文件路径**或**明确 Change 名称**，将特定的 `tasks.md` 作为上下文传递给 Superpowers，从而锁定当前的执行范围。
# 容错 (Fault tolerance)

> 这是 LangGraph 中**容错机制**的胖索引，覆盖节点级重试、超时和错误处理的组合策略，包括策略参数、进度信号、补偿路由及功能 API 支持。
> 阅读本文档可一次性掌握容错体系的全部概念及其关联，为构建健壮、自恢复的图执行流程提供决策支撑。

---

## 概念全景

LangGraph 为每个节点提供了三种可组合的容错机制，按固定顺序生效：**重试** → **超时** → **错误处理**。当节点执行失败（包括超时引发的 `NodeTimeoutError`），重试策略决定是否重新执行；只有在重试耗尽后，错误处理器才会运行，允许通过 `Command` 更新状态或跳转到补偿节点。

| 机制           | 作用                                                         | 关键配置                                   |
| -------------- | ------------------------------------------------------------ | ------------------------------------------ |
| **重试**       | 基于异常类型和退避算法自动重新运行失败尝试                   | `retry_policy`（最大尝试次数、退避参数、自定义 `retry_on`） |
| **超时**       | 限制单次尝试的运行时间或空闲时间                             | `timeout`（秒）、`TimeoutPolicy`（运行/空闲超时、进度刷新方式） |
| **错误处理**   | 重试耗尽后执行恢复或补偿函数                                 | `error_handler`（接收 `NodeError`，可返回 `Command`） |

三者协同：超时触发 `NodeTimeoutError`（默认可重试），重试策略决定是否重试，最终错误处理器处理剩余的失败。该设计支持优雅降级与 Saga 补偿模式。

核心决策点：**哪些异常应重试、重试多少次/间隔多长、何时使用运行超时 vs 空闲超时、空闲进度信号来源（自动或心跳）、如何处理最终失败（跳转到补偿节点还是向上冒泡）**。

---

## 1. 重试

通过 `add_node(retry_policy=RetryPolicy(...))` 为节点配置自动重试。

- **默认行为**：`default_retry_on` 重试大多数异常，但排除 `ValueError`、`TypeError`、`OSError` 等；对 HTTP 库仅重试 5xx 状态码；`NodeTimeoutError` 默认可重试。
- **关键参数**：`max_attempts`（默认 3）、`initial_interval`（0.5s）、`backoff_factor`（2.0）、`max_interval`（128s）、`jitter`（默认开启）。
- **自定义重试条件**：传入异常类型元组或可调用对象；可组合 `default_retry_on`。
- **运行时感知**：在节点内通过 `runtime.execution_info.node_attempt` 获取当前尝试次数（从 1 开始），可根据尝试次数切换到备用逻辑。

---

## 2. 超时

需要 `langgraph>=1.2`（alpha）。仅限异步节点。通过 `add_node(timeout=...)` 设置。

- **运行超时**：硬性墙上时钟限制；超时引发 `NodeTimeoutError`，清除失败尝试的写入。
- **空闲超时**：进度重置的限制；节点在指定时间内无进度信号时触发；每当产生进度信号时钟重置。
- **进度信号**：默认 `refresh_on="auto"` 下，状态写入、流输出、子任务调度、流写入器调用、LangChain 回调事件均可重置空闲时钟。
- **心跳模式**：`refresh_on="heartbeat"` 仅承认显式的 `runtime.heartbeat()` 调用。
- **NodeTimeoutError** 携带 `node`、`elapsed`、`kind`（`"idle"` / `"run"`）、`idle_timeout`、`run_timeout` 等上下文。
- **动态超时**：使用 `Send` 分发节点时，可传递 `timeout=` 覆盖该次调用的静态超时。

---

## 3. 错误处理

需要 `langgraph>=1.2`（alpha）。通过 `add_node(error_handler=...)` 设置，在重试耗尽后执行。

- **处理器签名**：可接收 `state`，可选注入 `error: NodeError` 和 `runtime: Runtime`。
- **NodeError** 数据类包含 `node`（失败节点名）和 `error`（引发的异常）。
- **路由与补偿**：处理器返回 `Command(update=..., goto=...)` 可修改状态并跳转到补偿节点，实现 Saga 模式。
- **可恢复性**：失败源被检查点记录；若处理器执行前图中断，恢复后会看到相同的 `NodeError` 上下文。
- **与中断的交互**：`interrupt()` 不被视为错误，不会触发错误处理器；图正常暂停。
- **子图失败**：子图未处理异常会向上传播，父节点的 `error_handler` 可通过 `error.error` 获取子图异常。

---

## 4. 功能 API 支持

`@task` 和 `@entrypoint` 装饰器同样接受 `timeout` 和 `retry_policy` 参数，行为与 `add_node` 一致。

---

## 5. 限制

- **仅限 Python**：超时和错误处理器暂不支持 JavaScript/TypeScript SDK；重试策略两者均可用。
- **超时仅限异步节点**：同步节点不能设置 `timeout`。
- **每个节点至多一个 `error_handler`**。
- **处理器自身失败会向上冒泡**。

---

## 6. 与全局概念的关联

- **中断 (Interrupts)**：`interrupt()` 绕过重试和错误处理，直接暂停图执行，用于人机协同而非错误恢复。
- **持久化 (Persistence)**：重试和错误处理依赖检查点记录状态；失败尝试的写入在重试/超时时被清除，错误处理器的更新可被持久化；恢复时可继续处理未完成的错误上下文。
- **Runtime**：通过 `runtime.execution_info` 暴露尝试次数，支持节点内自适应逻辑；`runtime.heartbeat()` 用于手动心跳。
- **人机协同 (Human-in-the-loop)**：与容错机制解耦；中断用于审批流程，容错用于处理异常，互不干扰。
- **流式传输 (Streaming)**：超时的进度信号与流输出、回调事件联动；错误处理器的状态变更可通过流观察。
- **子图**：子图异常可被父节点错误处理器捕获，便于集中补偿。

---

## 链接原文

### 语义检索（聚焦查询）

- `RetryPolicy max_attempts backoff_factor default_retry_on` → 重试策略
- `node_attempt execution_info 切换后备` → 运行时重试状态
- `TimeoutPolicy run_timeout idle_timeout refresh_on` → 超时配置
- `heartbeat idle_timeout refresh_on="heartbeat"` → 手动心跳
- `NodeTimeoutError kind elapsed` → 超时异常结构
- `error_handler NodeError Command goto` → 错误处理与补偿路由
- `Send 动态超时 timeout=` → 动态超时覆盖
- `@task @entrypoint timeout retry_policy` → 功能 API 容错

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 重试`、`### 自定义重试逻辑`、`### 超时`、`### 错误处理`），可用 `read_file` 精确定位对应章节。
# API 模块技术文档

> 本文档为 `backend/api/` 模块的详细技术说明，涵盖路由端点、数据模型、服务层、工具模块和错误处理体系。

---

## 概述

API 模块是 Index RAG 项目的 FastAPI 后端 API 层，采用**分层架构**：

```
Router（路由层）  →  参数校验、端点暴露
    ↓
Service（服务层）  →  业务编排、数据加工
    ↓
Utils / SQL（工具/数据层）  →  流式处理、文件提取、数据库操作
```

核心职责：
- **路由分发**：7 组路由模块，覆盖对话、线程、检查点、文件、RAG、设置、记忆与技能
- **数据校验**：基于 Pydantic Schema 的请求/响应模型
- **SSE 流式响应**：支持 9 种事件类型的实时推送
- **统一错误处理**：装饰器模式 + 全局异常处理器

---

## 模块结构

```
backend/api/
├── __init__.py
├── routers/                          # 路由层（7 个模块）
│   ├── chat.py                       # 对话端点（非流式/流式/恢复/带文件）
│   ├── threads.py                    # 线程管理（历史/删除/列表）
│   ├── checkpoints.py                # 检查点导航（列表/重放/分叉）
│   ├── files.py                      # 文件管理（浏览/上传/修改/删除）
│   ├── rag_pipeline.py               # RAG 入库管道（处理/删除/健康/配置）
│   ├── settings.py                   # 设置管理（配置读写/Skills/Graph重建）
│   └── memory_and_skill.py           # 记忆与技能文件管理
├── schemas/                          # Pydantic 数据模型（9 个模块）
│   ├── request.py                    # 对话请求模型
│   ├── response.py                   # 对话响应模型（含 SSE 流式事件）
│   ├── checkpoint.py                 # 检查点相关模型
│   ├── interrupt.py                  # 中断恢复模型
│   ├── error.py                      # 统一错误响应
│   ├── files.py                      # 文件管理模型
│   ├── rag_pipeline.py               # RAG 管道模型
│   └── settings.py                   # 设置模型
├── services/                         # 业务服务层（9 个模块）
│   ├── chat_service.py               # 对话服务
│   ├── thread_service.py             # 线程服务
│   ├── checkpoint_service.py         # 检查点服务
│   ├── file_service.py               # 文件服务
│   ├── rag_service.py                # RAG 服务
│   ├── settings_service.py           # 设置服务
│   ├── memory_and_skill_service.py   # 记忆与技能服务
│   └── graph.py                      # Graph 实例管理
├── utils/                            # 工具模块
│   ├── stream.py                     # SSE 流处理器
│   ├── error_handlers.py             # 全局异常处理器 & 端点装饰器
│   ├── exceptions.py                 # 错误码枚举 & 自定义异常类
│   ├── file_handler.py               # PDF/DOCX 文本提取
│   ├── message2json.py               # 消息序列化
│   └── dict2json.py                  # 字典/消息转换
└── sql/                              # SQL 操作
    ├── list_threads.py               # 线程列表查询
    └── dele_sql.py                   # 线程数据删除
```

---


## 设计要点

### 1. 分层架构与职责分离

- **Router** 层只负责端点暴露、参数校验、调用 Service
- **Service** 层负责业务编排，与 LangGraph / SQLite / 文件系统交互
- **Utils** 层提供通用工具，被 Router 和 Service 层复用

### 2. SSE 多模式流式处理

使用 LangGraph `astream` 的 `version="v2"` 多模式流式：

```
graph.astream(input_data, config, version="v2",
    stream_mode=["messages", "checkpoints", "updates", "custom"],
    subgraphs=True)
```

同一流中处理 4 种事件类型，前端按 `type` 字段分发渲染。子图（subgraphs）场景通过 `ns` 元组标识事件来源。

### 3. 统一错误处理装饰器模式

所有端点使用 `@handle_endpoint_errors` 装饰器替代手动 try/except，减少样板代码：

```python
@router.post("/{thread_id}")
@handle_endpoint_errors(
    ErrorCode.CHAT_INVOKE_FAILED,
    log_msg="非流式聊天异常 | thread_id={thread_id}",
    detail_msg="非流式聊天失败: thread_id={thread_id}",
)
async def chat_endpoint(...):
    ...
```

模板变量自动从函数参数中提取（`{thread_id}` → `kwargs["thread_id"]`）。

### 4. 检查点时间旅行

- **input 检查点**：每次用户发送消息时 LangGraph 自动生成，标记为 `source=input`
- **叶子检查点**：`next` 为空的检查点，表示分支末端
- **Replay**：从检查点重新执行（不修改历史，结果可能变化）
- **Fork**：创建新分支（原始链完整保留，新分支独立发展）

### 5. Files ↔ Memory & Skill 镜像设计

Files 路由和 Memory & Skill 路由共享相同的操作模式，区别仅在于：
- Files 操作项目文件空间（`WORKSPACE_DIR`）
- Memory & Skill 按 `type` 参数操作记忆库（`MEMORY_DIR`）或技能库（`SKILLS_DIR`）

### 6. RAG 入库「预览 → 确认」两步流程

通过 `preview_only=True` 参数控制：
- `preview_only=true`：只执行分块，不写入向量库，返回逐文件分块详情（含标题路径、内容预览、长度、切分类型）
- `preview_only=false`：分块后写入 Chroma 向量库

## 路由端点详解

### 1. Chat 路由（`/chat`）

对话核心路由，前缀 `/chat`，标签 `chat`。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/chat/{thread_id}` | 非流式聊天，返回完整响应 |
| `POST` | `/chat/{thread_id}/stream` | 流式聊天（SSE），支持 `checkpoint_id` / `checkpoint_ns` 恢复和 `rubric` 条件驱动循环 |
| `POST` | `/chat/{thread_id}/resume` | 恢复中断的对话，传入用户审批决策后以 SSE 流式返回 |
| `POST` | `/chat/{thread_id}/with-files` | 非流式聊天（支持上传 PDF / DOCX 附件） |
| `POST` | `/chat/{thread_id}/with-files/stream` | 流式聊天（支持上传 PDF / DOCX 附件） |

**ChatRequest 请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `messages` | `list[Message]` | ✅ | 对话消息列表，每条含 `role`（user/assistant/system）和 `content`（>=1字符） |
| `checkpoint_id` | `str` | ❌ | 检查点 ID，用于从指定检查点恢复/重放 |
| `checkpoint_ns` | `str` | ❌ | 检查点命名空间（子图场景） |
| `rubric` | `str` | ❌ | 完成条件，Agent 自然停止时由独立评估器判断是否满足，未满足则自动注入反馈循环 |

**ResumeRequest 请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `decisions` | `list[Decision]` | ✅ | 用户决策列表，每条含 `type`（approve/reject/edit）和可选的 `edited_action` |

**带文件附件端点**使用 `multipart/form-data`：
- `messages`：JSON 字符串，格式 `{"messages": [{"role":"user","content":"..."}]}`
- `files`：PDF / DOCX 文件列表

---

### 2. Threads 路由

线程管理路由，标签 `threads`。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/chat/{thread_id}/get-messages-history` | 获取会话历史消息，支持 `checkpoint_id` 查询参数获取指定分支 |
| `DELETE` | `/chat/{thread_id}/delete-messages-history` | 删除会话历史（从 SQLite checkpoints/writes 两张表中删除） |
| `GET` | `/threads` | 列出所有对话线程（ID + 消息数） |

**GET /threads 响应**：

```json
[
  {"thread_id": "abc123", "message_count": 15},
  {"thread_id": "def456", "message_count": 3}
]
```

---

### 3. Checkpoints 路由（`/checkpoints`）

检查点分支导航，前缀 `/checkpoints`，标签 `checkpoints`。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/checkpoints/{thread_id}/inputs` | 获取 input 检查点列表（分页），每次用户发送消息时自动生成 |
| `POST` | `/checkpoints/{thread_id}/replay` | 从指定检查点重放执行（SSE 流式），可注入新消息触发重新生成 |
| `POST` | `/checkpoints/{thread_id}/fork` | 从指定检查点分叉执行（SSE 流式），可传入新 state values 创建独立分支 |

**GET /inputs 查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | `int` | 50 | 每页数量（1-200） |
| `offset` | `int` | 0 | 偏移量 |

**CheckpointSummary 响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `config` | `dict` | 完整 LangGraph config，可直接用于 replay/fork |
| `next_nodes` | `list[str]` | 待执行节点列表（为空表示已完成） |
| `input_preview` | `str` | 用户输入前 80 字预览 |
| `parent_checkpoint_id` | `str` | 父检查点 ID（根节点为 None） |
| `source` | `str` | 检查点来源：input / loop / fork |
| `leaf_checkpoint_id` | `str` | 该 input 所在分支的叶子检查点 ID |

**Replay 语义**：
- 检查点之前的节点不重新执行（结果已缓存）
- 检查点之后的节点重新执行（LLM / API / 中断会再次触发）
- 提供 `messages` 时注入用户输入触发模型重新生成

**Fork 语义**：
- 通过 `graph.update_state` 创建新分支检查点，原始执行链完整保留
- `values` 可传入任意 state 字段，通过对应 reducer 应用
- 新分支独立发展，前端展示为对话树

---

### 4. Files 路由（`/api/files`）

文件管理路由，前缀 `/api/files`，标签 `files`。

#### 读取类

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/files/list` | 目录列表（`path` 查询参数，空字符串=根目录），文件夹优先、按名称排序 |
| `GET` | `/api/files/file` | 读取文件，直接返回文件（支持浏览器预览/下载） |
| `GET` | `/api/files/read` | 读取文件内容，返回 JSON（含内容、类型、是否可编辑） |
| `GET` | `/api/files/search` | 递归搜索匹配名称的文件和目录（`q` 查询参数，>=1 字符） |

#### 创建/上传类

| 方法 | 路径 | 请求体/参数 | 说明 |
|------|------|------|------|
| `POST` | `/api/files/create-file` | `CreateFileRequest` | 创建新文件（可指定初始内容） |
| `POST` | `/api/files/create-directory` | `CreateDirectoryRequest` | 创建新目录 |
| `POST` | `/api/files/upload` | Query `path` + form `file` | 上传文件到指定路径 |

#### 修改类

| 方法 | 路径 | 请求体 | 说明 |
|------|------|------|------|
| `PUT` | `/api/files/rename` | `RenameRequest` | 重命名文件或目录 |
| `PUT` | `/api/files/move` | `MoveRequest` | 移动文件或目录到目标目录 |
| `PUT` | `/api/files/modify` | `ModifyFileRequest` | 修改文件内容（覆盖写入） |

#### 删除类

| 方法 | 路径 | 请求体 | 说明 |
|------|------|------|------|
| `DELETE` | `/api/files/delete` | `DeleteRequest` | 删除文件或目录（递归删除） |

**核心 Schema**：

| Schema | 字段 |
|--------|------|
| `FileItem` | `name`, `type`（dir/file）, `size`, `modified` |
| `CreateFileRequest` | `path`, `content`（默认空） |
| `CreateDirectoryRequest` | `path` |
| `RenameRequest` | `path`, `new_name` |
| `ModifyFileRequest` | `path`, `content` |
| `MoveRequest` | `path`, `target_dir` |
| `DeleteRequest` | `path` |
| `OperationResult` | `success`, `message`, `path` |

---

### 5. RAG Pipeline 路由（`/api/rag`）

RAG 入库管道路由，前缀 `/api/rag`，标签 `rag-pipeline`。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rag/process` | 通过文件路径处理 .md 文档（JSON body 模式），支持 `preview_only` |
| `POST` | `/api/rag/process/upload` | 上传 .md 文件，完成分切 +（可选）入库（multipart 模式） |
| `POST` | `/api/rag/delete` | 按 ID 从向量库中删除文档 |
| `GET` | `/api/rag/health` | 向量库健康检查 |
| `GET` | `/api/rag/config` | 读取 `rag_config.yaml` 完整配置 |
| `PUT` | `/api/rag/config` | 覆写 `rag_config.yaml`，自动重载运行时配置 |

**RAGProcessRequest**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `files` | `list[str]` | ✅ | .md 文件绝对路径列表（>=1） |
| `preview_dir` | `str` | ❌ | 分块预览输出目录 |
| `preview_only` | `bool` | ❌ | 仅预览分块而不入库（默认 false） |

**RAGProcessResponse**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_files` | `int` | 总文件数 |
| `success_count` | `int` | 成功数 |
| `failed_count` | `int` | 失败数 |
| `total_chunks` | `int` | 总入库分块数 |
| `collection_count` | `int` | 向量库当前文档块总数 |
| `split_config` | `SplitConfig` | 本次处理使用的分割配置 |
| `results` | `list[RAGProcessResult]` | 每个文件的处理详情 |

**RAGDeleteResponse**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `deleted_count` | `int` | 成功删除的文档数 |
| `collection_count` | `int` | 向量库当前文档块总数 |
| `message` | `str` | 操作描述 |

**RAGHealthResponse**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `str` | 集合名称 |
| `collection_count` | `int` | 当前文档块总数 |
| `persist_directory` | `str` | 持久化目录 |
| `embedding_model` | `str` | 嵌入模型名称 |
| `embedding_base_url` | `str` | 嵌入模型服务地址 |

---

### 6. Settings 路由（`/settings`）

设置管理路由，前缀 `/settings`，标签 `settings`。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/settings/model-config/read` | 读取指定配置文件内容（`path` 查询参数） |
| `PUT` | `/settings/model-config/write` | 覆写指定配置文件内容 |
| `GET` | `/settings/skills` | 获取所有 skill 及其启用状态 |
| `PUT` | `/settings/skills` | 更新启用的 skill 列表并重建 Graph |
| `POST` | `/settings/rebuild` | 重新编译 LangGraph，使配置生效 |

**SkillsUpdateRequest**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `enabled` | `list[str]` | 启用的 skill 名称列表 |

---

### 7. Memory & Skill 路由（`/settings/memory-and-skill`）

记忆库与技能库文件管理，前缀 `/settings/memory-and-skill`，标签 `memory-and-skill`。

与 Files 路由功能镜像，但通过 `type` 查询参数区分操作目标：
- `type=memory`：操作记忆库目录
- `type=skills`：操作技能库目录

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/settings/memory-and-skill/list` | 目录列表 |
| `GET` | `/settings/memory-and-skill/file` | 读取文件（直接返回） |
| `GET` | `/settings/memory-and-skill/read` | 读取文件内容（JSON 返回） |
| `GET` | `/settings/memory-and-skill/search` | 递归搜索文件/目录 |
| `POST` | `/settings/memory-and-skill/create-file` | 创建新文件 |
| `POST` | `/settings/memory-and-skill/create-directory` | 创建新目录 |
| `POST` | `/settings/memory-and-skill/upload` | 上传文件 |
| `PUT` | `/settings/memory-and-skill/rename` | 重命名 |
| `PUT` | `/settings/memory-and-skill/move` | 移动 |
| `PUT` | `/settings/memory-and-skill/modify` | 修改文件内容 |
| `DELETE` | `/settings/memory-and-skill/delete` | 删除文件或目录 |

---

## Schema 数据模型

### 请求模型

#### ChatRequest
```
messages: list[Message]        # 对话消息（role="user"|"assistant"|"system", content:>=1）
checkpoint_id: str?            # 检查点 ID
checkpoint_ns: str?            # 检查点命名空间
rubric: str?                   # 完成条件
```

#### ResumeRequest
```
decisions: list[Decision]      # 决策列表（type="approve"|"reject"|"edit", edited_action?:dict）
```

### 响应模型

#### ChatResponse
```
messages: list[MessageResponse]   # role + content + reason_content?
```

#### StreamResponse（SSE 流式）

核心流式事件模型，支持 9 种事件类型：

| 事件类型 | 触发条件 | 额外字段 |
|----------|----------|----------|
| `text` | 普通文本增量 | — |
| `reasoning` | 推理内容（思维链） | — |
| `tool_call` | 工具调用增量 | `tool_call_id`, `tool_call_name`, `tool_call_args` |
| `tool_result` | 工具执行结果 | `tool_call_id` |
| `interrupt` | HITL 中断 | `content` 为中断数据的 JSON |
| `checkpoint` | 检查点生成（input 或 leaf） | `content` 含 `checkpoint_id`, `parent_checkpoint_id`, `kind` |
| `rubric` | Rubric 评估事件 | `content` 含评估详情 JSON |
| `error` | 错误 | `error_code` |
| `done` | 流结束 | `done=true` |

### 错误模型

```json
{
  "error_code": "THREAD_NOT_FOUND",
  "detail": "线程 'abc' 不存在"
}
```

---

## 服务层概览

9 个 Service 模块对应各路由的业务逻辑：

| 服务模块 | 职责 |
|----------|------|
| `chat_service` | 非流式对话（`graph.ainvoke`）、SSE 流式对话、对话恢复、文件提取拼接 |
| `thread_service` | 从 SQLite 获取/删除会话历史，列出线程 |
| `checkpoint_service` | 获取 input 检查点列表、重放执行、分支创建 |
| `file_service` | 文件系统 CRUD：目录浏览、文件读写、创建、上传、重命名、移动、删除、搜索 |
| `rag_service` | RAG 文档分块、向量入库、文档删除、健康检查、配置读写 |
| `settings_service` | 配置文件读写、Skills 状态管理 |
| `memory_and_skill_service` | 记忆库/技能库文件管理（与 file_service 镜像） |
| `graph` | LangGraph 图实例的单例管理和重建 |

服务层通过 `backend/core/` 模块获取 `main_agent` 图实例。

---

## 工具模块详解

### SSE 流处理器（`utils/stream.py`）

核心类 `StreamProcessor` 和生成器 `_sse_stream`：

**StreamProcessor 职责**：

| 方法 | 功能 |
|------|------|
| `_handle_message_chunk` | 解析 astream 消息事件：区分推理内容、工具调用、文本内容、工具结果 |
| `_handle_checkpoint_chunk` | 提取检查点事件：区分 `input` 检查点（用户消息绑定）和 `leaf` 叶子节点（分支导航） |

**`_sse_stream` 流生成器流程**：

1. 构建 LangGraph config（`thread_id` + 可选 `checkpoint_id`、`checkpoint_ns`、Langfuse 配置）
2. 异步遍历 `graph.astream`，stream_mode 同时监听 4 种模式：
   - `messages` → 消息增量（text / reasoning / tool_call / tool_result）
   - `checkpoints` → 检查点信息（input / leaf）
   - `updates` → 中断检测（`__interrupt__`）
   - `custom` → Rubric 评估事件
3. 每种事件序列化为 SSE 格式：`data: {json}\n\n`
4. 流正常结束推送 `type=done`，异常推送 `type=error`

**Langfuse 集成**：当 `LANGFUSE_TRACING_ENABLED` 启用时，自动注入 `callbacks` 和 `metadata` 到 LangGraph config。

---

### 异常处理体系（`utils/exceptions.py` + `utils/error_handlers.py`）

#### 异常层次

```
HTTPException
  └── AppException              # 携带业务 error_code
        ├── NotFoundException   # 404
        ├── InternalErrorException  # 500
        └── UnavailableException    # 503
```

#### ErrorCode 枚举（30+ 错误码）

| 分类 | 错误码 |
|------|--------|
| 通用 | `INTERNAL_ERROR`, `VALIDATION_ERROR`, `NOT_FOUND` |
| Graph | `GRAPH_NOT_INITIALIZED` |
| Thread | `THREAD_NOT_FOUND`, `THREAD_DELETE_FAILED`, `THREAD_HISTORY_FAILED` |
| Checkpoint | `CHECKPOINT_NOT_FOUND`, `CHECKPOINT_LIST_FAILED`, `CHECKPOINT_REPLAY_FAILED`, `CHECKPOINT_FORK_FAILED` |
| Chat | `CHAT_INVOKE_FAILED`, `CHAT_STREAM_FAILED`, `CHAT_RESUME_FAILED` |
| Stream | `STREAM_INTERNAL_ERROR` |
| RAG | `RAG_PROCESS_FAILED`, `RAG_DELETE_FAILED`, `RAG_FILE_NOT_FOUND`, `RAG_UNSUPPORTED_FORMAT`, `RAG_VECTORSTORE_ERROR` |
| File/Dir | `PATH_NOT_FOUND`, `NOT_A_DIRECTORY`, `PERMISSION_DENIED`, `FILE_NOT_FOUND`, `FORBIDDEN_PATH`, `FILE_ALREADY_EXISTS`, `DIR_ALREADY_EXISTS`, `FILE_CREATE_FAILED`, `DIR_CREATE_FAILED`, `FILE_UPLOAD_FAILED`, `FILE_MODIFY_FAILED`, `FILE_DELETE_FAILED`, `DIR_DELETE_FAILED`, `INVALID_OPERATION` |

#### 全局异常处理器（3 层）

| 优先级 | 处理器 | 行为 |
|--------|--------|------|
| 1 | `AppException` | 按 error_code + detail 返回结构化 JSON |
| 2 | `RequestValidationError` | 422 + `VALIDATION_ERROR` |
| 3 | `Exception`（兜底） | 500 + `INTERNAL_ERROR` |

#### `handle_endpoint_errors` 装饰器

统一处理端点 try/except 样板代码：

```python
@handle_endpoint_errors(
    ErrorCode.CHAT_INVOKE_FAILED,
    log_msg="非流式聊天异常 | thread_id={thread_id}",
    detail_msg="非流式聊天失败: thread_id={thread_id}",
)
```

特性：
- `AppException` 及其子类 → 直接透传（不包装）
- 其他 `Exception` → 记录日志并包装为 `AppException(500, error_code)`
- 模板支持 `{param_name}` 和 `{param.attr}` 运行时填充

---

### 文件处理（`utils/file_handler.py`）

| 函数 | 功能 |
|------|------|
| `pdf_to_text` | 使用 pdfplumber 提取 PDF 文本 |
| `docx_to_text` | 使用 MarkItDown 提取 DOCX 文本 |
| `save_extracted_text` | 将提取的文本保存为 `.md` 文件到 `UPLOADS_DIR` |

模块级单例 `_markitdown = MarkItDown()` 避免重复初始化。

**支持格式**（`SUPPORTED_EXTENSIONS`）：

| 扩展名 | 提取器 |
|--------|--------|
| `.pdf` | `pdf_to_text` |
| `.docx` | `docx_to_text` |

---

### 消息序列化（`utils/message2json.py` + `utils/dict2json.py`）

| 函数 | 功能 |
|------|------|
| `message_to_response` | 将 LangChain 消息对象转为 `MessageResponse`，处理附件消息的 text 块提取，用户消息只取第一个文本块 |
| `dump_messages` | `list[Message]` → `list[dict]` |
| `langchain_result_to_response` | `graph.ainvoke` 结果 → `ChatResponse`，提取推理内容 |

---

## SQL 层

直接操作 SQLite `checkpoints` 数据库（路径由 `CHECKPOINT_DB` 环境变量指定）。

| 文件 | 功能 | 涉及表 |
|------|------|--------|
| `list_threads.py` | 查询所有线程 ID 及消息数 | `checkpoints` |
| `dele_sql.py` | 按 thread_id 删除历史数据 | `checkpoints`, `writes` |

---



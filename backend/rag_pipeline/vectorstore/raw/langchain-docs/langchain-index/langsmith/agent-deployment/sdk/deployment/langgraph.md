# LangGraph CLI

**LangGraph CLI** 是一个用于在本地构建和运行 Agent Server 的命令行工具。生成的服务器暴露了用于运行、线程、助手等的所有 API 端点，并包含支持服务，例如用于检查点和存储的托管数据库。

## 安装

1. 确保已安装 Docker（例如 `docker --version`）。

2. 安装 CLI：

```bash
pip install langgraph-cli
```

3. 验证安装

```bash
langgraph --help
```

### 快速命令

| 命令               | 功能描述                                                             |
| ----------------------------- | -------------------------------------------------------------------- |
| `langgraph dev`            | 启动轻量级本地开发服务器（无需 Docker），适合快速测试。                      |
| `langgraph build`           | 为部署构建 LangGraph API 服务器的 Docker 镜像。                             |
| `langgraph deploy`         | 一步构建 LangGraph 镜像并直接部署到 LangSmith Deployments。                             |
| `langgraph dockerfile`      | 从配置生成 Dockerfile，用于自定义构建。                             | 
| `langgraph up`                 | 在 Docker 中本地启动 LangGraph API 服务器。需要 Docker 运行；本地开发需要 LangSmith API 密钥；生产需要许可证。 |


## 配置文件

为了构建和运行有效的应用程序，LangGraph CLI 需要一个遵循此模式的 JSON 配置文件。它包含以下属性：

LangGraph CLI 默认使用当前目录中名为 `langgraph.json` 的配置文件。

| 键                  | 描述                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dependencies`     | **必需**。LangSmith API 服务器的依赖项数组。依赖项可以是以下之一：一个句点（`"."`），将查找本地 Python 包。包含 `pyproject.toml`、`setup.py` 或 `requirements.txt` 的目录路径。例如，如果 `requirements.txt` 位于项目根目录，则指定 `"./"`。如果位于名为 `local_package` 的子目录中，则指定 `"./local_package"`。不要指定 `"requirements.txt"` 字符串本身。一个 Python 包名称。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `graphs`           | **必需**。从 graph ID 到定义已编译 graph 或返回 graph 的函数的路径的映射。示例：`./your_package/your_file.py:variable`，其中 `variable` 是 `langgraph.graph.state.CompiledStateGraph` 的实例。`./your_package/your_file.py:make_graph`，其中 `make_graph` 是一个接受配置字典（`langchain_core.runnables.RunnableConfig`）并返回 `langgraph.graph.state.StateGraph` 或 `langgraph.graph.state.CompiledStateGraph` 实例的函数。有关更多详细信息，请参阅如何在运行时重建 graph。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `auth`             | *（在 v0.0.11 中添加）* 认证配置，包含指向认证处理程序的路径。示例：`./your_package/auth.py:auth`，其中 `auth` 是 `langgraph_sdk.Auth` 的实例。有关详细信息，请参阅认证指南。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `base_image`       | 可选。用于 LangGraph API 服务器的基础镜像。默认为 `langchain/langgraph-api` 或 `langchain/langgraphjs-api`。使用此选项可将构建固定到特定版本的 langgraph API，例如 `"langchain/langgraph-server:0.2"`。有关更多标签，请参阅 https://hub.docker.com/r/langchain/langgraph-server/tags。（在 `langgraph-cli==0.2.8` 中添加）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `image_distro`     | 可选。基础镜像的 Linux 发行版。必须是 `"debian"`、`"wolfi"`、`"bookworm"` 或 `"bullseye"` 之一。如果省略，默认为 `"debian"`。在 `langgraph-cli>=0.2.11` 中可用。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `env`              | 指向 `.env` 文件的路径或环境变量到其值的映射。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `store`            | 为 BaseStore 添加语义搜索和/或生存时间（TTL）的配置。包含以下字段：`index`（可选）：语义搜索索引配置，包含字段 `embed`、`dims` 和可选的 `fields`。`ttl`（可选）：项目过期配置。一个对象，包含可选字段：`refresh_on_read`（布尔值，默认为 `true`）、`default_ttl`（浮点数，生命周期以**分钟**为单位；仅适用于新创建的项目；现有项目不变；默认无过期）和 `sweep_interval_minutes`（整数，检查过期项目的频率，默认不扫描）。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `ui`               | 可选。代理发出的 UI 组件的命名定义，每个指向一个 JS/TS 文件。（在 `langgraph-cli==0.1.84` 中添加）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `python_version`   | `3.11`、`3.12` 或 `3.13`。默认为 `3.11`。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `node_version`     | 指定 `node_version: 20` 以使用 LangGraph.js。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `pip_config_file`  | `pip` 配置文件的路径。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `pip_installer`    | *（在 v0.3 中添加）* 可选。Python 包安装程序选择器。可以设置为 `"auto"`、`"pip"` 或 `"uv"`。从 0.3 版本开始，默认策略是运行 `uv pip`，通常提供更快的构建，同时保持即插即用的替代。在不常见的情况下，如果 `uv` 无法处理您的依赖图或 `pyproject.toml` 的结构，请在此处指定 `"pip"` 以恢复到以前的行为。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `keep_pkg_tools`   | *（在 v0.3.4 中添加）* 可选。控制是否在最终镜像中保留 Python 打包工具（`pip`、`setuptools`、`wheel`）。接受的值：true：保留所有三个工具（跳过卸载）。false / 省略：卸载所有三个工具（默认行为）。list[str]：要保留的工具名称。每个值必须是 "pip"、"setuptools"、"wheel" 之一。默认情况下，所有三个工具都会被卸载。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `dockerfile_lines` | 在从父镜像导入之后要添加到 Dockerfile 的附加行数组。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `checkpointer`     | 检查点的配置。支持：`backend`（可选）：`"default"`、`"mongo"` 或 `"custom"`。默认为 `"default"`（PostgreSQL）。请参阅配置检查点后端。`path`（可选）：自定义检查点工厂的路径（当 `backend` 为 `"custom"` 时）。请参阅自定义检查点。`ttl`（可选）：包含 `strategy`、`sweep_interval_minutes`、`default_ttl` 的对象，用于控制检查点过期。`serde`（可选，0.5+）：包含 `allowed_json_modules` 和 `pickle_fallback` 的对象，用于调整反序列化行为。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `http`             | HTTP 服务器配置，包含以下字段： `app`：指向自定义 Starlette/FastAPI 应用的路径（例如 `"./src/agent/webapp.py:app"`）。请参阅自定义路由指南。 `cors`：CORS 配置，包含诸如 `allow_origins`、`allow_methods`、`allow_headers`、`allow_credentials`、`allow_origin_regex`、`expose_headers` 和 `max_age` 等字段。 `configurable_headers`：通过 `includes` / `excludes` 模式定义哪些请求头作为可配置值暴露。 `logging_headers`：用于从日志中排除敏感头的 `configurable_headers` 的镜像。 `middleware_order`：选择自定义中间件和认证的交互方式。`auth_first` 在自定义中间件之前运行认证钩子，而 `middleware_first`（默认）首先运行您的中间件。 `enable_custom_route_auth`：将认证检查应用于通过 `app` 添加的路由。 路由禁用标志——选择性地关闭内置端点组： `disable_meta`：禁用 `/`（根）、`/info`、`/metrics`、`/docs` 和 `/openapi.json` 系统路由。`/ok` 健康检查仍然可用。 `disable_assistants`：禁用所有 `/assistants/*` 路由。 `disable_runs`：禁用所有 `/runs/*` 路由。 `disable_threads`：禁用所有 `/threads/*` 路由。 `disable_store`：禁用所有 `/store/*` 路由。 `disable_ui`：禁用所有 `/ui/*` 路由。 `disable_mcp`：禁用 `/mcp` 端点。请参阅禁用 MCP。 `disable_a2a`：禁用 `/a2a/*` 端点。请参阅禁用 A2A。 `disable_webhooks`：禁用运行完成时的 webhook 传递（不是路由切换）。请参阅禁用 webhooks。 `mount_prefix`：挂载路由的前缀（例如 "/my-deployment/api"）。 |
| `webhooks`         | *（在 v0.5.36 中添加）* 出站 webhook 传递的配置。包含：`env_prefix`：头模板中引用的环境变量的必需前缀（默认为 `LG_WEBHOOK_`）。`headers`：包含在 webhook 请求中的静态头。值可以包含模板，如 `${{ env.VAR }}`。`url`：URL 验证策略，包含 `allowed_domains`、`allowed_ports`、`require_https`、`disable_loopback` 和 `max_url_length`。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `api_version`      | *（在 v0.3.7 中添加）* 要使用的 LangGraph API 服务器的语义版本（例如 `"0.3"`）。默认为最新版本。请查看服务器变更日志以了解每个版本的详细信息。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

### 示例

#### 基本配置

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "chat": "chat.graph:graph"
  }
}
```

#### 使用 Wolfi 基础镜像

您可以使用 `image_distro` 字段指定基础镜像的 Linux 发行版。有效选项为 `debian`、`wolfi`、`bookworm` 或 `bullseye`。Wolfi 是推荐选项，因为它提供更小、更安全的镜像。此选项在 `langgraph-cli>=0.2.11` 中可用。

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "chat": "chat.graph:graph"
  },
  "image_distro": "wolfi"
}
```

#### 为存储添加语义搜索

所有部署都附带一个由数据库支持的 BaseStore。在您的 `langgraph.json` 中添加 `index` 配置将为部署中的 BaseStore 启用语义搜索。

`index.fields` 配置决定文档的哪些部分被嵌入：

* 如果省略或设置为 `["$"]`，整个文档将被嵌入。
* 要嵌入特定字段，请使用 JSON 路径表示法：`["metadata.title", "content.text"]`。
* 缺少指定字段的文档仍将被存储，但不会为这些字段生成嵌入。
* 您仍然可以在 `put` 时使用 `index` 参数覆盖每个特定项目要嵌入的字段。

```json
{
  "dependencies": ["."],
  "graphs": {
    "memory_agent": "./agent/graph.py:graph"
  },
  "store": {
    "index": {
      "embed": "openai:text-embedding-3-small",
      "dims": 1536,
      "fields": ["$"]
    }
  }
}
```

**常见模型维度**

  * `openai:text-embedding-3-large`: 3072
  * `openai:text-embedding-3-small`: 1536
  * `openai:text-embedding-ada-002`: 1536
  * `cohere:embed-english-v3.0`: 1024
  * `cohere:embed-english-light-v3.0`: 384
  * `cohere:embed-multilingual-v3.0`: 1024
  * `cohere:embed-multilingual-light-v3.0`: 384

#### 使用自定义嵌入函数的语义搜索

如果您希望使用自定义嵌入函数进行语义搜索，可以传递指向自定义嵌入函数的路径：

```json
{
  "dependencies": ["."],
  "graphs": {
    "memory_agent": "./agent/graph.py:graph"
  },
  "store": {
    "index": {
      "embed": "./embeddings.py:embed_texts",
      "dims": 768,
      "fields": ["text", "summary"]
    }
  }
}
```

`store` 配置中的 `embed` 字段可以引用一个自定义函数，该函数接受一个字符串列表并返回一个嵌入列表。示例实现：

```python
# embeddings.py
def embed_texts(texts: list[str]) -> list[list[float]]:
    """Custom embedding function for semantic search."""
    # Implementation using your preferred embedding model
    return [[0.1, 0.2, ...] for _ in texts]  # dims-dimensional vectors
```

#### 添加自定义认证

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "chat": "chat.graph:graph"
  },
  "auth": {
    "path": "./auth.py:auth",
    "openapi": {
      "securitySchemes": {
        "apiKeyAuth": {
          "type": "apiKey",
          "in": "header",
          "name": "X-API-Key"
        }
      },
      "security": [{ "apiKeyAuth": [] }]
    },
    "disable_studio_auth": false
  }
}
```

有关详细信息，请参阅认证概念指南，以及设置自定义认证指南以实际操作该过程。

#### 配置存储项目生存时间

您可以使用 `store.ttl` 键为 BaseStore 中的项目/记忆配置默认数据过期时间。这决定了项目在最后一次访问后保留多长时间（根据 `refresh_on_read`，读取可能会重置计时器）。请注意，这些默认值可以通过修改 `get`、`search` 等中的相应参数在每个调用上覆盖。

`ttl` 配置是一个包含可选字段的对象：

* `refresh_on_read`：如果为 `true`（默认），通过 `get` 或 `search` 访问项目会重置其过期计时器。设置为 `false` 则仅在写入（`put`）时刷新 TTL。
* `default_ttl`：项目的默认生命周期，以**分钟**为单位。仅适用于新创建的项目；现有项目不会被修改。如果未设置，项目默认不会过期。
* `sweep_interval_minutes`：系统运行后台进程删除过期项目的频率（以分钟为单位）。如果未设置，不会自动扫描。

以下是一个启用 7 天 TTL（10080 分钟）、在读取时刷新并每小时扫描一次的示例：

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "memory_agent": "./agent/graph.py:graph"
  },
  "store": {
    "ttl": {
      "refresh_on_read": true,
      "sweep_interval_minutes": 60,
      "default_ttl": 10080
    }
  }
}
```

#### 配置检查点生存时间

您可以使用 `checkpointer` 键配置检查点的生存时间（TTL）。这决定了检查点数据在被根据指定策略（例如删除）自动处理之前保留多长时间。支持两个可选子对象：

* `ttl`：包含 `strategy`、`sweep_interval_minutes` 和 `default_ttl`，它们共同设置检查点如何过期。
* `serde` *（Agent server 0.5+）*：允许您控制检查点负载的反序列化行为。

以下是一个设置默认 TTL 为 30 天（43200 分钟）的示例：

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "chat": "chat.graph:graph"
  },
  "checkpointer": {
    "ttl": {
      "strategy": "delete",
      "sweep_interval_minutes": 10,
      "default_ttl": 43200
    }
  }
}
```

在此示例中，超过 30 天的检查点将被删除，并且每 10 分钟运行一次检查。

#### 配置检查点 serde

`checkpointer.serde` 对象塑造反序列化：

* `allowed_json_modules` 定义了一个允许列表，用于服务器能够从以 "json" 模式保存的负载中反序列化的自定义 Python 对象。这是一个 `[path, to, module, file, symbol]` 序列列表。如果省略，仅允许 LangChain 安全的默认值。您可以不安全地设置为 `true` 以允许反序列化任何模块。
* `pickle_fallback`：是否在 JSON 解码失败时回退到 pickle 反序列化。

```json
{
  "checkpointer": {
    "serde": {
      "allowed_json_modules": [
        ["my_agent", "auth", "SessionState"]
      ]
    }
  }
}
```

#### 自定义 HTTP 中间件和头

`http` 块允许您微调请求处理：

* `middleware_order`：选择 `"auth_first"` 在中间件之前运行认证，或 `"middleware_first"`（默认）反转该顺序。
* `enable_custom_route_auth`：将认证扩展到您通过 `http.app` 挂载的路由。
* `configurable_headers` / `logging_headers`：每个接受一个包含可选 `includes` 和 `excludes` 数组的对象；支持通配符，排除在包含之前执行。
* `cors`：自定义服务器的 CORS（跨源资源共享）配置。用于配置 CORS 的 `langgraph.json` 示例文件：

```json
{
  ...
  "http": {
    "cors": {
      "allow_origins": ["https://example.com", "https://app.example.com"],
      "allow_methods": ["GET", "POST"],
      "allow_headers": ["Authorization", "Content-Type"],
      "allow_credentials": true,
      "allow_origin_regex": "^https://.*\\.example\\.com$",
      "expose_headers": ["x-pagination-total", "x-pagination-next", "x-request-id"],
      "max_age": 600
    }
  },
  ...
}
```

自定义服务器的 CORS 配置将覆盖设置 `CORS_ALLOW_ORIGINS` 环境变量的功能。

#### 配置 webhooks

您可以为出站 webhook 请求配置自定义头和 URL 限制：

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "chat": "chat.graph:graph"
  },
  "webhooks": {
    "headers": {
      "Authorization": "Bearer ${{ env.LG_WEBHOOK_TOKEN }}"
    },
    "url": {
      "allowed_domains": ["*.mycompany.com"],
      "require_https": true
    }
  }
}
```

有关头配置、环境变量模板化和 URL 限制的详细信息，请参阅使用 webhooks。

#### 固定 API 版本

*（在 v0.3.7 中添加）*

您可以使用 `api_version` 键固定 Agent Server 的 API 版本。如果您希望确保服务器使用特定版本的 API，这将非常有用。
默认情况下，云部署中的构建使用服务器的最新稳定版本。可以通过将 `api_version` 键设置为特定版本来固定。

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "chat": "chat.graph:graph"
  },
  "api_version": "0.2"
}
```

#### 禁用内置路由

您可以使用 `http` 配置块中的布尔标志有选择地禁用内置路由组。这对于希望最小化服务器暴露面积的生产部署非常有用。

例如，要禁用系统信息和文档路由：

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "chat": "chat.graph:graph"
  },
  "http": {
    "disable_meta": true
  }
}
```

将 `disable_meta` 设置为 `true` 将禁用以下路由：

* `/` — 根健康检查
* `/info` — 服务器版本和配置信息
* `/metrics` — Prometheus 和 JSON 指标
* `/docs` — API 文档 UI
* `/openapi.json` — OpenAPI 规范

即使设置了 `disable_meta`，`/ok` 健康检查端点仍然可用，因此像 Kubernetes 这样的编排器仍然可以执行存活和就绪探针。

其他路由禁用标志包括 `disable_assistants`、`disable_runs`、`disable_threads`、`disable_store` 和 `disable_ui`。对于 MCP、A2A 和 webhooks，请参阅各自的指南：禁用 MCP、禁用 A2A、禁用 webhooks。

#### 基本配置

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "graphs": {
    "chat": "./src/graph.ts:graph"
  }
}
```

#### 固定 API 版本

*（在 v0.3.7 中添加）*

您可以使用 `api_version` 键固定 Agent Server 的 API 版本。如果您希望确保服务器使用特定版本的 API，这将非常有用。
默认情况下，云部署中的构建使用服务器的最新稳定版本。可以通过将 `api_version` 键设置为特定版本来固定。

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "chat": "./src/chat/graph.ts:graph"
  },
  "api_version": "0.2"
}
```

#### 禁用内置路由

您可以使用 `http` 配置块中的布尔标志有选择地禁用内置路由组。这对于希望最小化服务器暴露面积的生产部署非常有用。

例如，要禁用系统信息和文档路由：

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "graphs": {
    "chat": "./src/chat/graph.ts:graph"
  },
  "http": {
    "disable_meta": true
  }
}
```

将 `disable_meta` 设置为 `true` 将禁用以下路由：

* `/` — 根健康检查
* `/info` — 服务器版本和配置信息
* `/metrics` — Prometheus 和 JSON 指标
* `/docs` — API 文档 UI
* `/openapi.json` — OpenAPI 规范

即使设置了 `disable_meta`，`/ok` 健康检查端点仍然可用，因此像 Kubernetes 这样的编排器仍然可以执行存活和就绪探针。

其他路由禁用标志包括 `disable_assistants`、`disable_runs`、`disable_threads`、`disable_store` 和 `disable_ui`。对于 MCP、A2A 和 webhooks，请参阅各自的指南：禁用 MCP、禁用 A2A、禁用 webhooks。

## 命令

**用法**

LangGraph CLI 的基本命令是 `langgraph`。

```
langgraph [OPTIONS] COMMAND [ARGS]
```

### `dev`

在开发模式下运行 LangGraph API 服务器，具有热重载和调试功能。这个轻量级服务器不需要安装 Docker，适用于开发和测试。状态持久化到本地目录。

目前，CLI 仅支持 Python >= 3.11。

如果您需要有关何时使用 `langgraph dev` 与 `langgraph up` 的更多信息，请参阅本地开发与测试指南以进行详细比较。

**安装**

此命令需要安装 "inmem" 扩展：

```bash
pip install -U "langgraph-cli[inmem]"
```

**用法**

```
langgraph dev [OPTIONS]
```

**选项**

| 选项           | 默认              | 描述              |
| ---------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `-c, --config FILE`           | `langgraph.json` | 声明依赖项、graph 和环境变量的配置文件路径            |
| `--host TEXT`                 | `127.0.0.1`      | 绑定服务器的主机|
| `--port INTEGER`              | `2024`           | 绑定服务器的端口       |
| `--no-reload`                 |                  | 禁用自动重载           |
| `--n-jobs-per-worker INTEGER` |                  | 每个工作进程的作业数。默认为 10       |
| `--debug-port INTEGER`        |                  | 调试器监听的端口           |
| `--wait-for-client`           | `False`          | 在启动服务器之前等待调试器客户端连接到调试端口             |
| `--no-browser`                |                  | 服务器启动时跳过自动打开浏览器              |
| `--studio-url TEXT`           |                  | 要连接的 Studio 实例的 URL。默认为 https://smith.langchain.com|
| `--allow-blocking`            | `False`          | 不对代码中的同步 I/O 阻塞操作引发错误（在 `0.2.6` 中添加）  |
| `--tunnel`                    | `False`          | 通过公共隧道（Cloudflare）暴露本地服务器以供远程前端访问。这避免了浏览器（如 Safari）或网络阻止 localhost 连接的问题 |
| `--help`                      |                  | 显示命令文档   |

### `build`

构建 LangSmith API 服务器 Docker 镜像。

**用法**

```
langgraph build [OPTIONS]
```

**选项**

| 选项                                | 默认              | 描述          |
| ------------------- | ---------------- | ------------- |
| `--platform TEXT`                     |                  | 构建 Docker 镜像的目标平台。示例：`langgraph build --platform linux/amd64,linux/arm64`       |
| `-t, --tag TEXT`                      |                  | **必需**。Docker 镜像的标签。示例：`langgraph build -t my-image`              |
| `--pull / --no-pull`                  | `--pull`         | 使用最新的远程 Docker 镜像构建。使用 `--no-pull` 以使用本地构建的镜像运行 LangSmith API 服务器。                                  |
| `-c, --config FILE`                   | `langgraph.json` | 声明依赖项、graph 和环境变量的配置文件路径。      |
| `--build-command TEXT`\*   |                  | 要运行的构建命令。从 `langgraph.json` 文件所在的目录运行。示例：`langgraph build --build-command "yarn run turbo build"` |
| `--install-command TEXT`\* |                  | 要运行的安装命令。从您调用 `langgraph build` 的目录运行。示例：`langgraph build --install-command "yarn install"`      |
| `--help`                              |                  | 显示命令文档。 |

### `deploy`

此命令处于测试阶段，正在积极开发中。预计会有频繁的更新和改进。

一步构建 LangGraph 镜像并直接部署到 LangSmith Deployments。此命令在本地构建 Docker 镜像，将其推送到托管注册表，并创建或更新部署——全部在一个步骤中完成。如果未安装 Docker，则会触发远程构建。

**前提条件**

* 具有 Deployments 访问权限的 **LangSmith API 密钥**。
*（可选）**Docker** 必须已安装且 Docker 守护进程必须正在运行以进行本地构建。远程构建不需要。安装 Docker Desktop。

仅适用于 LangSmith Cloud。

**用法**

```
langgraph deploy [OPTIONS] [DOCKER_BUILD_ARGS]
```

此命令也接受所有 `langgraph build` 标志（`--platform`、`-t`、`--pull`、`--no-pull`、`-c`）。有关详细信息，请参阅 `langgraph build --help`。

**选项**

| 选项                       | 默认                    | 描述      |
| ------------------------ | ---------------------- | ------------------------- |
| `--api-key TEXT`         |                        | LangSmith Deployments 的 API 密钥。也可以通过 `LANGGRAPH_HOST_API_KEY`、`LANGSMITH_API_KEY` 或 `LANGCHAIN_API_KEY` 环境变量或 `.env` 文件设置。 |
| `--name TEXT`            | 当前目录名称 | 部署名称。也可以通过 `LANGSMITH_DEPLOYMENT_NAME` 环境变量或 `.env` 文件设置。                                                             |
| `--deployment-id TEXT`   |                        | 要更新的现有部署的 ID。如果省略，则使用 `--name` 查找或创建部署。                                                            |
| `--deployment-type TEXT` | `dev`                  | 部署类型（`dev` 或 `prod`）。在创建新部署时使用。       |
| `--remote / --no-remote` |                        | 强制远程或本地构建。默认情况下，如果本地没有可用的 Docker，则远程构建。    |
| `--no-wait`              | `False`                | 推送后跳过等待部署状态。   |
| `--verbose`              | `False`                | 显示详细输出，包括 Docker 构建和推送日志。      |
| `--help`                 |                        | 显示命令文档。   |

**示例**

```bash
# 使用 .env 文件中的 API 密钥部署
langgraph deploy

# 使用内联 API 密钥部署
LANGSMITH_API_KEY=lsv2_... langgraph deploy

# 更新现有部署
langgraph deploy --deployment-id abc123

# 使用内联部署名称部署
LANGSMITH_DEPLOYMENT_NAME=my-agent langgraph deploy

# 部署到 EU 区域
LANGGRAPH_HOST_URL=https://eu.api.host.langchain.com langgraph deploy
```

通过其他方法（例如 LangSmith UI 或 GitHub 集成）创建的部署也可以使用 `langgraph deploy` 命令进行更新。

#### `deploy list`

列出 LangSmith Deployments。

**用法**

```bash
langgraph deploy list [OPTIONS]
```

**选项**

| 选项       | 默认 | 描述      |
| ---------------------- | ------- | ------------------------- |
| `--name-contains TEXT` |         | 仅显示名称包含此值的部署。           |
| `--api-key TEXT`       |         | API 密钥。也可以通过 `LANGGRAPH_HOST_API_KEY`、`LANGSMITH_API_KEY` 或 `LANGCHAIN_API_KEY` 环境变量或 `.env` 文件设置。 |
| `--help`               |         | 显示此消息并退出。           |

#### `deploy revisions`

[Beta] 管理部署修订版本。

**用法**

```bash
langgraph deploy revisions [OPTIONS] COMMAND [ARGS]...
```

**选项**

| 选项   | 默认 | 描述                 |
| -------- | ------- | --------------------------- |
| `--help` |         | 显示此消息并退出。 |

**命令**

| 命令 | 描述                                        |
| ------- | -------------------------------------------------- |
| `list`  | [Beta] 列出 LangSmith Deployment 的修订版本。 |

#### `deploy revisions list`

[Beta] 列出 LangSmith Deployment 的修订版本。

使用 `deploy list` 列出部署 ID。

**用法**

```bash
langgraph deploy revisions list [OPTIONS] DEPLOYMENT_ID
```

**选项**

| 选项                | 默认 | 描述      |
| ----------------- | ------- | ------------------------- |
| `--limit INTEGER` | `10`    | 要返回的最大修订版本数。           |
| `--api-key TEXT`  |         | API 密钥。也可以通过 `LANGGRAPH_HOST_API_KEY`、`LANGSMITH_API_KEY` 或 `LANGCHAIN_API_KEY` 环境变量或 `.env` 文件设置。 |
| `--help`          |         | 显示此消息并退出。           |

#### `deploy delete`

删除 LangSmith Deployment。

使用 `deploy list` 查找要删除的部署 ID。

**用法**

```bash
langgraph deploy delete [OPTIONS] DEPLOYMENT_ID
```

**选项**

| 选项               | 默认 | 描述      |
| ---------------- | ------- | ------------------------- |
| `--force`        |         | 删除时不提示确认。           |
| `--api-key TEXT` |         | API 密钥。也可以通过 `LANGGRAPH_HOST_API_KEY`、`LANGSMITH_API_KEY` 或 `LANGCHAIN_API_KEY` 环境变量或 `.env` 文件设置。 |
| `--help`         |         | 显示此消息并退出。           |

#### `deploy logs`

获取 LangSmith Deployment 日志。使用 `deploy` 获取代理运行时日志，或使用 `build` 获取远程构建日志。

**用法**

```bash
langgraph deploy logs [OPTIONS]
```

**选项**

| 选项                                                | 默认                    | 描述      |
| ------------------------------------------------- | ---------------------- | ------------------------- |
| `-f, --follow`                                    | `False`                | 持续轮询新日志。           |
| `--end-time TEXT`                                 |                        | ISO8601 结束时间。示例：`2026-03-08T00:00:00Z`。           |
| `--start-time TEXT`                               |                        | ISO8601 开始时间。示例：`2026-03-08T00:00:00Z`。           |
| `-q, --query TEXT`                                |                        | 搜索字符串过滤器。           |
| `--limit INTEGER`                                 | `100`                  | 要获取的最大日志条目数。           |
| `--level [DEBUG\|INFO\|WARNING\|ERROR\|CRITICAL]` |                        | 按日志级别过滤。           |
| `--revision-id TEXT`                              |                        | 特定的修订版本 ID。对于构建日志，默认为最新修订版本。           |
| `--type [deploy\|build]`                          | `deploy`               | 要获取的日志流。`deploy` 显示代理服务器运行时日志。`build` 显示远程构建日志。           |
| `--deployment-id TEXT`                            |                        | 部署 ID。如果省略，则使用 `--name` 查找部署。           |
| `--name TEXT`                                     | 当前目录名称 | 部署名称。也可以通过 `LANGSMITH_DEPLOYMENT_NAME` 环境变量或 `.env` 文件设置。当未提供 `--deployment-id` 时使用。           |
| `--api-key TEXT`                                  |                        | API 密钥。也可以通过 `LANGGRAPH_HOST_API_KEY`、`LANGSMITH_API_KEY` 或 `LANGCHAIN_API_KEY` 环境变量或 `.env` 文件设置。           |
| `--help`                                          |                        | 显示此消息并退出。           |

### `up`

启动 LangGraph API 服务器。对于本地测试，需要具有 LangSmith 访问权限的 LangSmith API 密钥。生产使用需要许可证密钥。

如果您需要有关何时使用 `langgraph dev` 与 `langgraph up` 的更多信息，请参阅本地开发与测试指南以进行详细比较。

**用法**

```
langgraph up [OPTIONS]
```

**选项**

| 选项                           | 默认                        | 描述                                                                |     |
| ---------------------------- | ------------------------- | ----------------------------------------------------------------- | --- |
| `--wait`                     |                           | 等待服务启动后再返回。隐含 `--detach`。                                         |     |
| `--base-image TEXT`          | `langchain/langgraph-api` | 用于 LangGraph API 服务器的基础镜像。使用版本标签固定到特定版本。                          |     |
| `--image TEXT`               |                           | 用于 langgraph-api 服务的 Docker 镜像。如果指定，则跳过构建并直接使用此镜像。                |     |
| `--postgres-uri TEXT`        | 本地数据库                     | 用于数据库的 Postgres URI。                                              |     |
| `--watch`                    |                           | 文件更改时重启。                                                          |     |
| `--debugger-base-url TEXT`   | `http://127.0.0.1:[PORT]` | 调试器用于访问 LangGraph API 的 URL。                                      |     |
| `--debugger-port INTEGER`    |                           | 在本地拉取调试器镜像并在指定端口上提供 UI。                                           |     |
| `--verbose`                  |                           | 显示更多服务器日志输出。                                                      |     |
| `-c, --config FILE`          | `langgraph.json`          | 声明依赖项、graph 和环境变量的配置文件路径。                                         |     |
| `-d, --docker-compose FILE`  |                           | 包含要启动的附加服务的 docker-compose.yml 文件路径。                              |     |
| `-p, --port INTEGER`         | `8123`                    | 要暴露的端口。示例：`langgraph up --port 8000`                              |     |
| `--pull / --no-pull`         | `pull`                    | 拉取最新镜像。使用 `--no-pull` 以使用本地构建的镜像运行服务器。示例：`langgraph up --no-pull` |     |
| `--recreate / --no-recreate` | `no-recreate`             | 即使容器的配置和镜像未更改也重新创建容器。                                             |     |
| `--help`                     |                           | 显示命令文档。                                                           |     |

### `dockerfile`

生成用于构建 LangSmith API 服务器 Docker 镜像的 Dockerfile。

**用法**

```
langgraph dockerfile [OPTIONS] SAVE_PATH
```

**选项**

| 选项              | 默认              | 描述      |
| ------------------- | ---------------- | ------------------------- |
| `-c, --config FILE` | `langgraph.json` | 声明依赖项、graph 和环境变量的配置文件路径。           |
| `--help`            |                  | 显示此消息并退出。           |

示例：

```bash
langgraph dockerfile -c langgraph.json Dockerfile
```

这将生成一个类似于以下的 Dockerfile：

```dockerfile
FROM langchain/langgraph-api:3.11

ADD ./pipconf.txt /pipconfig.txt

RUN PIP_CONFIG_FILE=/pipconfig.txt PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -c /api/constraints.txt langchain_anthropic langchain_openai wikipedia scikit-learn

ADD ./graphs /deps/__outer_graphs/src
RUN set -ex && \
    for line in '[project]' \
                'name = "graphs"' \
                'version = "0.1"' \
                '[tool.setuptools.package-data]' \
                '"*" = ["**/*"]'; do \
        echo "$line" >> /deps/__outer_graphs/pyproject.toml; \
    done

RUN PIP_CONFIG_FILE=/pipconfig.txt PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -c /api/constraints.txt -e /deps/*

ENV LANGSERVE_GRAPHS='{"agent": "/deps/__outer_graphs/src/agent.py:graph", "storm": "/deps/__outer_graphs/src/storm.py:graph"}'
```

`langgraph dockerfile` 命令将 `langgraph.json` 文件中的所有配置转换为 Dockerfile 命令。使用此命令时，每当更新 `langgraph.json` 文件时，都必须重新运行它。否则，您的更改将不会在构建或运行 dockerfile 时反映出来。
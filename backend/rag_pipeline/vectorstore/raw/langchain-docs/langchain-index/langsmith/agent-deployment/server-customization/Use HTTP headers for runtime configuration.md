# 使用 HTTP headers 进行运行时配置

LangGraph 允许运行时配置以动态修改 agent 行为和权限。当使用 LangSmith Deployment 时，您可以在请求体（`config`）或特定的请求 headers 中传递此配置。这支持基于用户身份或其他请求进行调整。

出于隐私考虑，可通过 `langgraph.json` 文件中的 `http.configurable_headers` 部分控制哪些 headers 被传递到运行时配置。

以下是如何自定义包含和排除的 headers：

```json
{
  "http": {
    "configurable_headers": {
      "includes": ["x-user-id", "x-organization-id", "my-prefix-*"],
      "excludes": ["authorization", "x-api-key"]
    }
  }
}
```

`includes` 和 `excludes` 列表接受精确的 header 名称或使用 `*` 匹配任意数量字符的模式。出于安全考虑，不支持其他正则表达式模式。

## 在 graph 内部使用

您可以在任何 **node** 中使用 `config` 参数访问被包含的 headers。

```python
def my_node(state, config):
  organization_id = config["configurable"].get("x-organization-id")
  ...
```

或者通过从上下文中获取（在 tools 或其他嵌套函数中很有用）。

```python
from langgraph.config import get_config

def search_everything(query: str):
  organization_id = get_config()["configurable"].get("x-organization-id")
  ...
```

您甚至可以使用它来动态编译 graph。

```python
# my_graph.py.
import contextlib

@contextlib.asynccontextmanager
async def generate_agent(config):
  organization_id = config["configurable"].get("x-organization-id")
  if organization_id == "org1":
    graph = ...
    yield graph
  else:
    graph = ...
    yield graph

```

```json
{
  "graphs": {"agent": "my_grph.py:generate_agent"}
}
```

### 退出可配置 headers

如果您想退出可配置 headers，只需在 `s` 列表中设置通配符模式：

```json
{
  "http": {
    "configurable_headers": {
      "excludes": ["*"]
    }
  }
}
```

这将阻止所有 headers 被添加到您的运行配置中。

请注意，排除项优先于包含项。
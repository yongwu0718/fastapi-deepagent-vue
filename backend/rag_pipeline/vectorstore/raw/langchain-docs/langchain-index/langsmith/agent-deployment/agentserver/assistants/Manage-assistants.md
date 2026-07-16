# 管理 assistants

本页介绍如何创建、配置和管理 assistants。Assistants 允许您通过配置（例如模型选择、提示词和工具可用性）来定制已部署 Graph 的行为，而无需修改底层 Graph 代码。

您可以使用 SDK 或在 LangSmith UI 中进行操作。

## 理解 assistant 配置

Assistants 存储 **context** 值，用于在运行时定制 Graph 行为。您在 Graph 代码中定义一个 context schema，然后在创建 assistant 时通过 `context` 参数提供具体的 context 值。

考虑这个 `call_model` 节点的示例，它从 context 中读取 `model_name`：

```python
class ContextSchema(TypedDict):
    model_name: str

builder = StateGraph(AgentState, context_schema=ContextSchema)

def call_model(state, runtime: Runtime[ContextSchema]):
    messages = state["messages"]
    model = _get_model(runtime.context.get("model_name", "anthropic"))
    response = model.invoke(messages)
    return {"messages": [response]}
```
当您创建一个 assistant 时，您需要为这些配置字段提供具体的值。assistant 会存储此配置，并在 Graph 运行时应用它。

有关 LangGraph 中配置的更多信息，请参阅 runtime context 文档。

**为工作流选择 SDK 或 UI：**

## 创建 assistant

使用 `AssistantsClient.create` 方法创建一个新的 assistant。该方法需要：

* **Graph ID**：此 assistant 将使用的已部署 Graph 的名称（例如 `"agent"`）。
* **Context**：与您 Graph 的 context schema 匹配的配置值。
* **Name**：assistant 的描述性名称。

以下示例创建了一个将 `model_name` 设置为 `openai` 的 assistant：

```python
from langgraph_sdk import get_client

# Initialize the client with your deployment URL
client = get_client(url=)

# Create an assistant for the "agent" graph
# The first parameter is the graph ID (also called graph name)
openai_assistant = await client.assistants.create(
    "agent",  # Graph ID of the deployed graph
    context={"model_name": "openai"},
    name="Open AI Assistant"
)

print(openai_assistant)
# Output includes the assistant_id (UUID) that uniquely identifies this assistant
```

**响应：**

API 返回一个 assistant 对象，包含：

* `assistant_id`：唯一标识此 assistant 的 UUID
* `graph_id`：此 assistant 为其配置的 Graph
* `context`：您提供的配置值
* `name`、`metadata`、时间戳和其他字段

```json
{
    "assistant_id": "62e209ca-9154-432a-b9e9-2d75c7a9219b",
    "graph_id": "agent",
    "name": "Open AI Assistant",
    "context": {
        "model_name": "openai"
    },
    "metadata": {},
    "created_at": "2024-08-31T03:09:10.230718+00:00",
    "updated_at": "2024-08-31T03:09:10.230718+00:00"
}
```

`assistant_id`（类似 `"62e209ca-9154-432a-b9e9-2d75c7a9219b"` 的 UUID）唯一标识此 assistant 配置。在运行 Graph 时，您将使用此 ID 来指定要应用的配置。

**Graph ID vs Assistant ID**

创建 assistant 时，您需要指定一个 **graph ID**（图名称，如 `"agent"`）。这将返回一个 **assistant ID**（UUID，如 `"62e209ca..."`）。在运行 Graph 时，您可以使用其中任意一种：

* **Graph ID**（例如 `"agent"`）：使用该 Graph 的默认 assistant
* **Assistant ID**（UUID）：使用特定的 assistant 配置

请参阅下面的“使用 assistant”示例。

## 使用 assistant

要使用 assistant，请在创建 run 时传入其 `assistant_id`。下面的示例使用了我们上面创建的 assistant：

```python
# Create a thread for the conversation
thread = await client.threads.create()

# Prepare the input
input = {"messages": [{"role": "user", "content": "who made you?"}]}

# Run the graph using the assistant's configuration
# Pass the assistant_id (UUID) as the second parameter
async for event in client.runs.stream(
    thread["thread_id"],
    openai_assistant["assistant_id"],  # Assistant ID (UUID)
    input=input,
    stream_mode="updates",
):
    print(f"Receiving event of type: {event.event}")
    print(event.data)
    print("\n\n")
```

**响应：**

流返回 Graph 使用您的 assistant 配置执行时的事件：

```
Receiving event of type: metadata
{'run_id': '1ef6746e-5893-67b1-978a-0f1cd4060e16'}

Receiving event of type: updates
{'agent': {'messages': [{'content': 'I was created by OpenAI...', ...}]}}
```

**使用 graph ID 与 assistant ID 的对比**

在运行 Graph 时，您可以传入 **graph ID** 或 **assistant ID**：

```python
# Option 1: Use graph ID to get the default assistant
client.runs.stream(thread_id, "agent", input=input)

# Option 2: Use assistant ID (UUID) for a specific configuration
client.runs.stream(thread_id, "62e209ca-9154-432a-b9e9-2d75c7a9219b", input=input)
```

## 为您的 assistant 创建新版本

使用 `AssistantsClient.update` 方法为 assistant 创建新版本。

**更新需要完整的配置**

更新时，您必须提供 **完整** 的配置。update 端点会从头创建新版本，不会与先前版本合并。请包含您希望保留的所有配置字段。

例如，为 assistant 添加一个系统提示词：

```python
# Update the assistant with a new configuration
# IMPORTANT: Include ALL configuration fields, not just the ones you're changing
openai_assistant_v2 = await client.assistants.update(
    openai_assistant["assistant_id"],  # Assistant ID (UUID)
    context={
        "model_name": "openai",  # Must include existing fields
        "system_prompt": "You are a mindful assistant!",  # New field
    },
)

# This creates version 2 and sets it as the active version
# Future runs using this assistant_id will use version 2
```

更新操作会创建一个新版本并自动将其设置为 **active** 版本。将来使用此 assistant ID 的所有 runs 都将使用新的配置。

## 使用之前的 assistant 版本

使用 `setLatest` 方法更改哪个版本是 active：

```python
# Roll back to version 1 of the assistant
await client.assistants.set_latest(
    openai_assistant['assistant_id'],  # Assistant ID (UUID)
    1  # Version number
)

# All future runs using this assistant_id will now use version 1
```

更改 active 版本后，所有使用此 assistant ID 的 runs 都将使用指定版本的配置。

## 创建 assistant（UI）

您可以从 LangSmith UI 创建 assistants：

1. 导航到您的部署，选择 **Assistants** 选项卡。
2. 点击 **+ New assistant**。
3. 在打开的表单中：
    * 选择此 assistant 所对应的 Graph。
    * 提供名称和描述。
    * 使用该 Graph 的配置 schema 来配置 assistant。
4. 点击 **Create assistant**。

这将带您进入 Studio，您可以在其中测试 assistant。返回 **Assistants** 选项卡，即可在表格中看到您新创建的 assistant。

## 使用 assistant（UI）

要在 LangSmith UI 中使用 assistant：

1. 导航到您的部署，选择 **Assistants** 选项卡。
2. 找到您要使用的 assistant。
3. 点击该 assistant 对应的 **Studio**。

这将打开已选定该 assistant 的 Studio。当您提交输入时（在 **Graph** 或 **Chat** 模式下），assistant 的配置将应用于此次 run。

## 为您的 assistant 创建新版本（UI）

要从 UI 更新 assistant 并创建新版本，您可以使用 **Assistants** 选项卡或 Studio。两种方法都会创建一个新版本并将其设置为 active 版本：

1. 导航到您的部署，选择 **Assistants** 选项卡。
        2. 找到您要编辑的 assistant。
        3. 点击 **Edit**。
        4. 修改 assistant 的名称、描述或配置。
        5. 保存更改。

1. 打开该 assistant 的 Studio。
        2. 点击 **Manage Assistants**。
        3. 编辑 assistant 的配置。
        4. 保存更改。

## 使用之前的 assistant 版本（UI）

要从 Studio 将之前的版本设置为 active：

1. 打开该 assistant 的 Studio。
2. 点击 **Manage Assistants**。
3. 找到该 assistant，并选择您要使用的版本。
4. 切换该版本的 **Active** 开关。

这将更新 assistant，使其在将来所有的 runs 中使用所选版本。

删除一个 assistant 将删除其 **所有** 版本。目前无法单独删除单个版本。要跳过一个版本，只需将另一个版本设置为 active 即可。
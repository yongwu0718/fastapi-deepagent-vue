# Agent Server 中的 A2A 端点

> 使用 A2A 协议在 LangSmith 中实现带有分布式追踪的 agent 间通信。

Agent2Agent（A2A）是 Google 提出的协议，用于实现对话式 AI agent 之间的通信。LangSmith 实现了 A2A 支持，允许您的 agent 通过标准化协议与其他兼容 A2A 的 agent 进行通信。

Agent Server 中的 A2A 端点路径为 `/a2a/{assistant_id}`。

## 支持的方法

Agent Server 支持以下 A2A RPC 方法：

* **message/send**：向 assistant 发送消息并接收完整响应。
* **message/stream**：发送消息并使用 Server-Sent Events (SSE) 实时流式接收响应。
* **tasks/get**：检索先前创建的任务的状态和结果。

## Agent Card 发现

每个 assistant 会自动暴露一张 A2A Agent Card，其中描述了其能力并为其他 agent 提供连接所需的信息。您可以通过以下方式获取任意 assistant 的 agent card：

```
GET /.well-known/agent-card.json?assistant_id={assistant_id}
```

Agent card 包含 assistant 的名称、描述、可用技能、支持的输入/输出模式以及用于通信的 A2A 端点 URL。

## 要求

要使用 A2A，请确保已安装以下依赖：

* `langgraph-api >= 0.4.21`

使用以下命令安装：

```bash
pip install "langgraph-api>=0.4.21"
```

## 使用概览

启用 A2A：

* 升级使用 `langgraph-api>=0.4.21`。
* 部署具有基于消息的状态结构的 agent。
* 使用端点与其他兼容 A2A 的 agent 连接。

## 创建兼容 A2A 的 agent

以下示例创建了一个兼容 A2A 的 agent，该 agent 使用 OpenAI API 处理传入消息并维护对话状态。agent 定义了基于消息的状态结构，并处理 A2A 协议的消息格式。

为了与 A2A 的 "text" 部分兼容，agent 的状态中必须包含 `messages` 键。

A2A 协议使用两个标识符来维持对话的连续性：

* `contextId`：将消息分组到对话线程中（类似于会话 ID）。
* `taskId`：标识该对话中的每个单独请求。

在第一条消息中，省略 `contextId` 和 `taskId`——agent 会生成并返回它们。对于对话中的所有后续消息，请包含先前响应中的 `contextId` 和 `taskId`，以保持线程连续性。

**LangSmith 追踪：** Langsmith Deployment A2A 端点会自动将 A2A `contextId` 转换为 `thread_id` 用于 LangSmith 追踪，将对话中的所有消息分组到同一个线程下。

示例代码：

```python
"""
LangGraph A2A conversational agent.
Supports the A2A protocol with messages input for conversational interactions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from openai import AsyncOpenAI

class Context(TypedDict):
    """Context parameters for the agent."""
    my_configurable_param: str

@dataclass
class State:
    """Input state for the agent.

    Defines the initial structure for A2A conversational messages.
    """
    messages: List[Dict[str, Any]]

async def call_model(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Process conversational messages and returns output using OpenAI."""
    # Initialize OpenAI client
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Process the incoming messages
    latest_message = state.messages[-1] if state.messages else {}
    user_content = latest_message.get("content", "No message content")

    # Create messages for OpenAI API
    openai_messages = [
        {
            "role": "system",
            "content": "You are a helpful conversational agent. Keep responses brief and engaging."
        },
        {
            "role": "user",
            "content": user_content
        }
    ]

    try:
        # Make OpenAI API call
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=openai_messages,
            max_tokens=100,
            temperature=0.7
        )

        ai_response = response.choices[0].message.content

    except Exception as e:
        ai_response = f"I received your message but had trouble processing it. Error: {str(e)[:50]}..."

    # Create a response message
    response_message = {
        "role": "assistant",
        "content": ai_response
    }

    return {
        "messages": state.messages + [response_message]
    }

# Define the graph
graph = (
    StateGraph(State, context_schema=Context)
    .add_node(call_model)
    .add_edge("__start__", "call_model")
    .compile()
)
```

## Agent 间通信

一旦您的 agent 通过 `langgraph dev` 在本地运行或部署到生产环境，您就可以使用 A2A 协议促进它们之间的通信。

以下示例演示了两个 agent 如何通过向彼此的 A2A 端点发送 JSON-RPC 消息进行通信。脚本模拟了一个多轮对话，每个 agent 处理对方的响应并继续对话。

```python
#!/usr/bin/env python3
"""Agent-to-Agent conversation simulation using the LangGraph A2A endpoint."""

import asyncio
import aiohttp
import os
import uuid

def extract_text(result: dict) -> str:
    """Best-effort extraction of response text from an A2A result."""
    for art in result.get("result", {}).get("artifacts", []) or []:
        for part in art.get("parts", []) or []:
            if part.get("kind") == "text" and part.get("text"):
                return part["text"]

    msg = (result.get("result", {}).get("status", {}) or {}).get("message", {}) or {}
    for part in msg.get("parts", []) or []:
        if part.get("kind") == "text" and part.get("text"):
            return part["text"]

    return "(no text found)"

async def send_message(session, port, assistant_id, text, context_id=None, task_id=None):
    """Send an A2A message. Returns (response_text, returned_context_id, returned_task_id)."""
    url = f"http://127.0.0.1:{port}/a2a/{assistant_id}"

    message = {
        "role": "user",
        "parts": [{"kind": "text", "text": text}],
        "messageId": str(uuid.uuid4()),
    }

    # A2A multi-turn continuity: reuse contextId and taskId across turns/agents
    if context_id:
        message["contextId"] = context_id
    if task_id:
        message["taskId"] = task_id

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {"message": message},
    }

    headers = {"Accept": "application/json"}
    async with session.post(url, json=payload, headers=headers) as response:
        result = await response.json()

    returned_context_id = result.get("result", {}).get("contextId") or context_id
    returned_task_id = result.get("result", {}).get("id")
    return extract_text(result), returned_context_id, returned_task_id

async def simulate_conversation():
    """Simulate a conversation between two agents."""

    #Assistant IDs
    agent_a_id = os.getenv("AGENT_A_ID")
    agent_b_id = os.getenv("AGENT_B_ID")

    if not agent_a_id or not agent_b_id:
        print("Set AGENT_A_ID and AGENT_B_ID environment variables")
        return

    message = "Hello! Let's have a conversation."
    context_id = None
    task_id = None

    async with aiohttp.ClientSession() as session:
        for i in range(3):
            print(f"--- Round {i + 1} ---")

            message, context_id, task_id = await send_message(
                session, 2024, agent_a_id, message,
                context_id=context_id,
                task_id=task_id,
            )
            print(f"🔵 Agent A: {message}")

            message, context_id, task_id = await send_message(
                session, 2025, agent_b_id, message,
                context_id=context_id,
                task_id=task_id,
            )
            print(f"🔴 Agent B: {message}\n")

if __name__ == "__main__":
    asyncio.run(simulate_conversation())
```

完整的可用示例请参考：

* 两个 LangGraph agent 通信 - 使用 A2A 协议的两个 LangGraph agent 示例
* Google ADK agent 与 LangChain agent - 使用 A2A 协议的 Google ADK agent 与 LangChain agent 交互示例

## 分布式追踪

当多个 agent 通过 A2A 通信时，LangSmith 可以将它们的所有 trace 分组到单个线程中，为您提供整个多 agent 对话的统一视图。

### contextId 到 thread_id 的映射

Agent Server A2A 端点会自动将 A2A `contextId` 转换为 LangSmith 追踪中的 `thread_id`。这意味着，无需您进行任何额外配置，对话中的每一条消息（跨越所有参与的 agent）都将被分组到 LangSmith 的同一线程下。

流程如下：

1. 在第一条消息中，客户端省略 `contextId`。服务器生成一个并返回在响应中。
2. 客户端在所有后续消息中传递 `contextId`，以保持对话连续性。
3. Agent Server 将 `contextId` 映射到 LangSmith 元数据中的 `thread_id`，因此所有轮次都显示在同一线程中。

### 跨多个 agent 的追踪

当来自不同框架的 agent 通过 A2A 通信时，您可以通过在所有 agent 之间共享相同的 `thread_id` 来统一它们在 LangSmith 中的 trace。使用第一个 agent 返回的 `contextId` 作为所有后续请求的 `thread_id`。

以下代码片段演示了关键概念。有关包含两个 agent 的完整可运行实现，请参考 Google ADK + LangChain 示例。

```python
import asyncio
import aiohttp
import uuid

async def send_message(session, url, text, context_id=None, task_id=None, thread_id=None):
    """Send an A2A message and return (response_text, context_id, task_id)."""

    # --- 1. Build the message ---
    # On follow-up turns, include contextId and taskId inside the message object
    # so the server associates them with the ongoing conversation.
    message = {
        "role": "user",
        "parts": [{"kind": "text", "text": text}],
        "messageId": str(uuid.uuid4()),
    }
    if context_id:
        message["contextId"] = context_id
    if task_id:
        message["taskId"] = task_id

    # --- 2. Set thread_id in metadata ---
    # thread_id goes at the top level of the JSON-RPC payload, not inside params.
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {"message": message},
        "metadata": {"thread_id": thread_id},
    }

    async with session.post(url, json=payload, headers={"Accept": "application/json"}) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {await response.text()}")
        result = await response.json()

    if "error" in result:
        raise RuntimeError(result["error"].get("message", "Unknown error"))

    result_obj = result.get("result", {})
    returned_context_id = result_obj.get("contextId") or context_id
    returned_task_id = result_obj.get("id")
    text_out = next(
        (
            part.get("text", "")
            for art in result_obj.get("artifacts", []) or []
            for part in art.get("parts", []) or []
            if part.get("kind") == "text"
        ),
        "(no text)",
    )
    return text_out, returned_context_id, returned_task_id

async def run_conversation(agent_a_url, agent_b_url):
    # --- 3. Share thread_id across agents ---
    # Generate a shared thread_id upfront. Once the server returns a contextId,
    # use that instead — this keeps the A2A context and LangSmith thread in sync.
    thread_id = str(uuid.uuid4())
    context_id = None
    task_id = None
    message = "Hello! Let's collaborate."

    async with aiohttp.ClientSession() as session:
        for _ in range(3):
            message, context_id, task_id = await send_message(
                session, agent_a_url, message,
                context_id=context_id, task_id=task_id,
                thread_id=context_id or thread_id,
            )

            # Passing the same thread_id to every agent groups all traces in LangSmith
            message, context_id, task_id = await send_message(
                session, agent_b_url, message,
                context_id=context_id, task_id=task_id,
                thread_id=context_id or thread_id,
            )

asyncio.run(run_conversation(
    "http://localhost:2024/a2a/",
    "http://localhost:2025/a2a/",
))
```

**1. 构建消息**：在后续轮次中，在 `message` 对象内部包含 `contextId` 和 `taskId`，以便服务器将它们与正在进行的对话关联起来。在第一条消息中省略它们，因为服务器会生成 `contextId` 并在响应中返回。

**2. 在 metadata 中设置 thread_id**：在 JSON-RPC payload 的顶级 `metadata` 字段中传递 `thread_id`，而不是在 `params` 内部。

**3. 跨 agent 共享 thread_id**：在第一条消息之前生成一个随机的 `thread_id`。一旦服务器返回 `contextId`，就将其用作所有后续请求的 `thread_id`，这可以保持 A2A 对话上下文与 LangSmith 线程同步。将相同的 `thread_id` 传递给每个 agent，以便所有 trace 都分组到一个线程中。

### 在非 LangGraph agent 中接收 thread_id

上一节介绍了客户端方面——在发送消息时传播 `thread_id`。如果您的一个 agent 不是基于 LangGraph 构建的，它还需要在接收端提取并附加 `thread_id`，以便其 trace 落在同一个 LangSmith 线程中。使用 `langsmith.integrations.otel.configure()` 设置自动追踪，并从传入的 A2A 请求 metadata 中提取 `thread_id`，以将 trace 分组到同一线程中。

```python
from fastapi import FastAPI, Request
from langsmith.integrations.otel import configure as configure_otel
from opentelemetry import trace
import json

# --- 1. Configure OTel ---
# Set up automatic tracing to LangSmith for your non-LangGraph agent.
configure_otel(project_name="my-a2a-project")
tracer = trace.get_tracer(__name__)

app = FastAPI()

@app.middleware("http")
async def set_thread_id_middleware(request: Request, call_next):
    thread_id = None
    if request.method == "POST":
        body_bytes = await request.body()
        if body_bytes:
            # --- 2. Extract thread_id from incoming A2A metadata ---
            try:
                body = json.loads(body_bytes)
                thread_id = body.get("metadata", {}).get("thread_id")
            except Exception:
                pass
            # Re-inject the body so downstream handlers can still read it
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive

    # --- 3. Attach thread_id to the trace ---
    # langsmith.metadata.thread_id groups this trace with others in the same thread.
    with tracer.start_as_current_span("agent") as span:
        if thread_id:
            span.set_attribute("langsmith.metadata.thread_id", thread_id)
        return await call_next(request)
```

在此中间件之后，将您的 agent 路由注册到 `app` 上。

在环境中设置 `LANGSMITH_API_KEY` 和可选的 `LANGSMITH_PROJECT` 以启用追踪。对话中的所有 agent 应使用相同的 project，以便它们的 trace 可以一起查看。

### 在 LangSmith 中查看 trace

运行多 agent 对话后，打开 LangSmith UI 并导航到 **Threads**。所有参与 agent 的所有轮次将出现在同一线程下，由共享的 `thread_id` 标识。

## 禁用 A2A

要禁用 A2A 端点，请在 `langgraph.json` 配置文件中将 `disable_a2a` 设置为 `true`：

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "http": {
    "disable_a2a": true
  }
}
```
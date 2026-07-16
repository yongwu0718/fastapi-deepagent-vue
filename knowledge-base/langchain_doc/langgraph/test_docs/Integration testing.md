# 集成测试

> 使用真实的 LLM API 测试 agent，组织测试、管理密钥、处理不稳定性并控制成本。

Integration tests 验证您的 agent 是否与模型 API 和外部服务正确配合工作。与使用 fake 和 mock 的 unit tests 不同，integration tests 会进行真实的网络调用，以确认各组件能协同工作、凭证有效且延迟在可接受范围内。

由于 LLM 的响应是非确定性的，integration tests 需要采用与传统软件测试不同的策略。本指南涵盖如何组织、编写和运行针对 agent 的 integration tests。有关向 LangChain 本身贡献代码时的通用测试基础设施，请参阅 Contributing to code。

## 分离 unit tests 和 integration tests

Integration tests 速度较慢且需要 API 凭证，因此应将其与 unit tests 分开。这样您就可以在每次更改时运行快速的 unit tests，并将 integration tests 保留用于 CI 或部署前检查。

使用 pytest markers 标记 integration tests：

```python
import pytest

@pytest.mark.integration
def test_agent_with_real_model():
    agent = create_agent("claude-sonnet-4-6", tools=[get_weather])
    result = agent.invoke({
        "messages": [HumanMessage(content="What's the weather in SF?")]
    })
    assert len(result["messages"]) > 1
```

配置 pytest 以识别该 marker 并在默认运行中排除 integration tests：

```ini
[pytest]
markers =
    integration: 调用真实 LLM API 的测试
addopts = -m "not integration"
```

```toml
[tool.pytest.ini_options]
markers = [
    "integration: 调用真实 LLM API 的测试"
]
addopts = "-m 'not integration'"
```

显式运行 integration tests：

```bash
pytest -m integration
```

## 管理 API keys

Integration tests 需要真实的 API 凭证。请从环境变量中加载它们，以确保密钥不被纳入源代码控制。

使用 `conftest.py` fixture 验证所需的密钥是否可用：

```python
import os
import pytest

@pytest.fixture(autouse=True)
def check_api_keys():
    # 如果未设置 OPENAI_API_KEY，则跳过测试
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
```

对于本地开发，将密钥存储在 `.env` 文件中并使用 `python-dotenv` 加载：

```bash
OPENAI_API_KEY=sk-...
```

```python
from dotenv import load_dotenv

load_dotenv()
```

将 `.env` 添加到您的 `.gitignore` 中，以避免提交凭证。在 CI 中，通过您所用平台的 secrets 管理（例如 GitHub Actions secrets）注入密钥。

## 对结构而非内容进行断言

LLM 的响应在多次运行之间会有差异。不要对确切的输出字符串进行断言，而应验证响应的结构属性：message 类型、tool call 名称、参数形状以及 message 数量。

```python
def test_agent_calls_weather_tool():
    agent = create_agent("claude-sonnet-4-6", tools=[get_weather])
    result = agent.invoke({
        "messages": [HumanMessage(content="What's the weather in SF?")]
    })

    messages = result["messages"]
    tool_calls = [
        tc
        for msg in messages
        if hasattr(msg, "tool_calls")
        for tc in (msg.tool_calls or [])
    ]

    assert any(tc["name"] == "get_weather" for tc in tool_calls)
    assert isinstance(messages[-1], AIMessage)
    assert len(messages[-1].content) > 0
```

要进行更严格的轨迹断言，可以使用 AgentEvals evaluators，它们支持 `unordered` 和 `superset` 等模糊匹配模式。

## 降低成本和延迟

调用 LLM API 的 integration tests 会产生实际费用。以下一些实践有助于保持测试套件的速度和可负担性：

* **使用更小的模型**：对于只需验证 tool calling 和响应结构的测试，使用 `gemini-3.1-flash-lite` 或同等模型。
* **设置 `maxTokens`**：限制响应长度，以避免冗长、昂贵的生成。
* **限制测试范围**：每个测试只验证一种行为。当单轮测试足够时，避免采用串联多个 LLM 调用的端到端场景。
* **选择性运行**：利用上述的测试分离方式，仅在 CI 或部署前运行 integration tests，而不是每次保存文件时都运行。

```python
agent = create_agent(
    "gemini-3.1-flash-lite",
    tools=[get_weather],
    model_kwargs={"max_tokens": 256},
)
```

## 录制并重放 HTTP calls

对于在 CI 中频繁运行的测试，您可以在首次运行时录制 HTTP 交互，并在后续运行中重放它们，而无需进行真实的 API 调用。这可在首次录制后消除成本和延迟。

`vcrpy` 将 HTTP 请求/响应对记录到 YAML "cassette" 文件中。`pytest-recording` 插件将其与 pytest 集成。

设置 `conftest.py` 以从 cassettes 中过滤敏感信息：

```python
import pytest

@pytest.fixture(scope="session")
def vcr_config():
    return {
        "filter_headers": [
            ("authorization", "XXXX"),
            ("x-api-key", "XXXX"),
        ],
        "filter_query_parameters": [
            ("api_key", "XXXX"),
            ("key", "XXXX"),
        ],
    }
```

配置您的项目以识别 `vcr` marker：

```ini
[pytest]
markers =
    vcr: 通过 VCR 录制/重放 HTTP
addopts = --record-mode=once
```

```toml
[tool.pytest.ini_options]
markers = [
    "vcr: 通过 VCR 录制/重放 HTTP"
]
addopts = "--record-mode=once"
```

`--record-mode=once` 选项在首次运行时录制 HTTP 交互，并在后续运行中重放它们。

使用 `vcr` marker 装饰您的测试：

```python
@pytest.mark.vcr()
def test_agent_trajectory():
    agent = create_agent("claude-sonnet-4-6", tools=[get_weather])
    result = agent.invoke({
        "messages": [HumanMessage(content="What's the weather in SF?")]
    })
    assert any(
        tc["name"] == "get_weather"
        for msg in result["messages"]
        if hasattr(msg, "tool_calls")
        for tc in (msg.tool_calls or [])
    )
```

首次运行会进行真实的网络调用，并在 `tests/cassettes/` 目录下生成一个 cassette 文件。后续运行将重放录制的响应。

当您修改 prompts、添加新的 tools 或更改预期的轨迹时，保存的 cassettes 会过时，现有的测试**将会失败**。删除对应的 cassette 文件并重新运行测试以录制新的交互。

## 下一步

了解如何在 Evals 中使用确定性匹配或 LLM-as-judge evaluators 评估 agent 轨迹。
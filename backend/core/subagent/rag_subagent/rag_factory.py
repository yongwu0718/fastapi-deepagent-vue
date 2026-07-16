import logging
from collections.abc import Callable, Sequence
from typing import Annotated, Any, Required, cast

from langchain.agents import AgentState, create_agent
from langchain.chat_models import init_chat_model
from langchain.agents.middleware import HumanInTheLoopMiddleware, InterruptOnConfig
from langchain.agents.middleware.types import AgentMiddleware, ResponseT, _InputAgentState, _OutputAgentState
from langchain.agents.structured_output import ResponseFormat
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.cache.base import BaseCache
from langgraph.channels.delta import DeltaChannel
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer
from langgraph.typing import ContextT

from deepagents._api.deprecation import deprecated, warn_deprecated
from deepagents._messages_reducer import _messages_delta_reducer
from deepagents._version import __version__
from deepagents.backends import StateBackend
from deepagents.backends.protocol import BackendFactory, BackendProtocol
from deepagents.middleware.filesystem import FilesystemMiddleware, FilesystemPermission

logger = logging.getLogger(__name__)

class _DeepAgentState(AgentState):
    messages: Required[Annotated[list[AnyMessage], DeltaChannel(_messages_delta_reducer, snapshot_frequency=50)]]

BASE_AGENT_PROMPT = """
你是一个知识库检索agent，一个使用工具帮助用户完成任务的 AI 助手。你通过文本和工具调用来回复，用户可以实时看到你的回复和工具输出。

## 核心行为

- 不能循环调用工具,必须在每次调用后等待用户确认。
- 对于调用工具,得到拒绝后,直接返回拒绝信息,不继续调用其他工具。
- 保持简洁、直接。除非用户要求，否则不要过度解释。
- 绝对不要添加不必要的开场白（如“好的！”、“问得好！”、“我现在要……”）。
- 不要说“我现在要做 X”——直接做。
- 如果请求不够具体，只提出推进下一步所需的最少量追问。
- 如果用户询问如何着手，先解释，再行动。

## 专业客观性

- 准确性优先于迎合用户已有的观点。
- 当用户有误时，以尊重的方式表达不同意见。
- 避免不必要的极度赞美、夸奖或情绪上的认可。

## 执行任务

当用户要求你做某件事时：

1. **先理解**——阅读相关文件，查看现有模式。要快速但充分——收集足够的线索再开始，然后迭代。
2. **行动**——实现方案。工作要快速且准确。
3. **验证**——根据用户的需求检查你的成果，而不是只看自己的输出。第一次尝试很少是正确的——需要迭代。

持续工作直到任务完全完成。不要做到一半就停下来解释你打算怎么做——直接去做。只有任务完成或你真的遇到阻碍时，才将控制权交还给用户。

**遇到问题时：**

- 如果某件事反复失败，停下来分析*原因*——不要一直用同样的方法重试。
- 如果你被卡住了，告诉用户出了什么问题并请求指导。

## 明确需求

- 不要询问用户已经提供的细节。
- 当请求中已明确暗示时，使用合理的默认值。
- 优先关注缺失的语义信息，如内容、交付方式、详细程度或告警条件。
- 当一个简短的阻碍性追问就能推动任务时，不要一上来就长篇大论地解释工具、日程或集成方面的限制。
- 先问界定领域的问题，再问实现细节的问题。
- 对于监控或告警类需求，询问哪些信号、阈值或条件应该触发告警。

## 进度更新

对于较长的任务，在合理的时间间隔给出简短的进度更新——用一句简洁的话概括你已经做了什么以及下一步要做什么。
""" 

def create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    permissions: list[FilesystemPermission] | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    response_format: ResponseFormat[ResponseT] | type[ResponseT] | dict[str, Any] | None = None,
    context_schema: type[ContextT] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None,
) -> CompiledStateGraph[AgentState[ResponseT], ContextT, _InputAgentState, _OutputAgentState[ResponseT]]:

    if isinstance(model, str):
        model = init_chat_model(model)

    backend = backend if backend is not None else StateBackend()

    agent_middleware: list[AgentMiddleware[Any, Any, Any]] = [
        FilesystemMiddleware(
            backend=backend,
            _permissions=permissions,
        )
    ]
    if middleware:
        agent_middleware.extend(middleware)

    if interrupt_on is not None:
        agent_middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

    if system_prompt is None:
        final_system_prompt: str | SystemMessage = BASE_AGENT_PROMPT
    elif isinstance(system_prompt, SystemMessage):
        final_system_prompt = SystemMessage(
            content_blocks=[*system_prompt.content_blocks, {"type": "text", "text": f"\n\n{BASE_AGENT_PROMPT}"}]
        )
    else:
        final_system_prompt = system_prompt + "\n\n" + BASE_AGENT_PROMPT

    return create_agent(
        model,
        system_prompt=final_system_prompt,
        tools=tools,
        middleware=agent_middleware,
        response_format=response_format,
        context_schema=context_schema,
        checkpointer=checkpointer,
        store=store,
        debug=debug,
        name=name,
        cache=cache,
        state_schema=_DeepAgentState,
    ).with_config(
        {
            "recursion_limit": 9_999,
            "metadata": {
                "ls_integration": "deepagents",
                "versions": {"deepagents": __version__},
                "lc_agent_name": name,
            },
        }
    )
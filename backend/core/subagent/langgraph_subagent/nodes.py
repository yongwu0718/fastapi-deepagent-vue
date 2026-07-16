from typing import Callable, Any
from langchain.messages import SystemMessage
from backend.config.logger import get_logger
from backend.core.subagent.langgraph_subagent.state_config import MessagesState
from backend.core.subagent.langgraph_subagent.prompt import system_prompt

logger = get_logger(__name__)

def create_llm_nodes(llm, tools: list[Callable[..., Any]]):
    """工厂函数：绑定 tools 到 llm，返回节点函数"""
    llm_with_tools = llm.bind_tools(tools)

    async def call_llm_with_tools(state: MessagesState) -> MessagesState:
        msg_count = len(state["messages"])
        logger.debug("llm_response 调用 | 历史消息数=%d", msg_count)
        # 创建新列表，把 SystemMessage 放在最前面（不修改原 state）
        messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
        response = await llm_with_tools.ainvoke(messages)
        logger.info("LLM 最终响应 | content_len=%d",
                    len(getattr(response, "content", "") or ""))
        return {
            "messages": response
        }

    return call_llm_with_tools
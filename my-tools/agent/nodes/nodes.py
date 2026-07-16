from typing import Callable, Any

from config.state_config import MessagesState
from config.logger import get_logger

logger = get_logger(__name__)

def create_llm_nodes(llm, tools: list[Callable[..., Any]]):
    """工厂函数：绑定 tools 到 llm，返回节点函数"""
    llm_with_tools = llm.bind_tools(tools)

    async def call_llm_with_tools(state: MessagesState) -> MessagesState:
        msg_count = len(state["messages"])
        logger.debug("call_llm_with_tools 调用 | 历史消息数=%d", msg_count)
        response = await llm_with_tools.ainvoke(state["messages"])
        has_tools = bool(getattr(response, "tool_calls", None))
        logger.info("LLM 响应 | has_tool_calls=%s | content_len=%d",
                    has_tools, len(getattr(response, "content", "") or ""))
        return {
            "messages": response
        }

    async def llm_response(state: MessagesState) -> MessagesState:
        msg_count = len(state["messages"])
        logger.debug("llm_response 调用 | 历史消息数=%d", msg_count)
        response = await llm_with_tools.ainvoke(state["messages"])
        logger.info("LLM 最终响应 | content_len=%d",
                    len(getattr(response, "content", "") or ""))
        return {
            "messages": response
        }

    return call_llm_with_tools, llm_response
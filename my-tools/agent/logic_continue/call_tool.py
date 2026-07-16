from typing import Literal
from langgraph.graph import END
from config.state_config import MessagesState
from config.logger import get_logger

logger = get_logger(__name__)

async def should_continue(state: MessagesState) -> Literal["tools", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        logger.debug("LLM 需要调用工具 | tool_count=%d", len(last_message.tool_calls))
        return "tools"

    # Otherwise, we stop (reply to the user)
    logger.debug("LLM 无需调用工具，结束流程")
    return END  
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, END

from .state_config import MessagesState
from backend.core.models.model_factory import llm_ali
from .nodes import create_llm_nodes
from backend.core.subagent.bill_subagent.billing import (
    analyze_billing, analyze_monthly, analyze_expense, analyze_monthly_categories, 
    add, multiply, subtract, divide)
from backend.config.logger import get_logger

from deepagents import CompiledSubAgent

logger = get_logger(__name__)

# 定义 tools 列表
TOOLS = [
    add, multiply, subtract, divide, 
    analyze_billing, analyze_monthly, analyze_expense, analyze_monthly_categories]

# 定义 nodes
call_llm_with_tools, llm_response = create_llm_nodes(llm_ali, TOOLS)

# state
builder = StateGraph(MessagesState)
# node
builder.add_node("call_llm", call_llm_with_tools)
builder.add_node("llm_response", llm_response)
builder.add_node("tools", ToolNode(TOOLS))

# edge
builder.add_edge(START, "call_llm")
builder.add_conditional_edges("call_llm", tools_condition, ["tools", END])
builder.add_edge("tools", "call_llm")
builder.add_edge("call_llm", END)

graph = builder.compile()

custom_agent = CompiledSubAgent(
    name="",
    description="",
    runnable=graph
)
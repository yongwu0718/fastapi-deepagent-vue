from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, END

from config.state_config import MessagesState
from config.model_config import llm_ali, embeddings
from nodes.nodes import create_llm_nodes
from .calculator import add, sub
from .chroma_memory import save_memory, search_memory, update_memory, delete_memory
from config.logger import get_logger

import aiosqlite
from contextlib import asynccontextmanager
from langgraph.store.sqlite.aio import AsyncSqliteStore
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from config.env import CHECKPOINT_DB, STORE_DB

logger = get_logger(__name__)

# 定义 tools 列表
TOOLS = [save_memory, search_memory, update_memory, delete_memory]

@asynccontextmanager
async def init_graph():
    """异步上下文管理器：初始化数据库连接并编译 graph，退出时自动关闭连接"""
    logger.info("正在初始化 Graph | checkpoint_db=%s | store_db=%s", CHECKPOINT_DB, STORE_DB)

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

    async with aiosqlite.connect(CHECKPOINT_DB, check_same_thread=False) as conn_sql_check:
        checkpointer_sql = AsyncSqliteSaver(conn=conn_sql_check)
        logger.debug("Checkpointer 已连接")

        async with aiosqlite.connect(STORE_DB, check_same_thread=False) as conn_sql_store:
            store_sql = AsyncSqliteStore(
                conn=conn_sql_store,
                )
            logger.debug("Store 已连接")

            graph = builder.compile(checkpointer=checkpointer_sql, store=store_sql)
            logger.info("Graph 编译完成")
            yield graph
            logger.info("Graph 已释放")

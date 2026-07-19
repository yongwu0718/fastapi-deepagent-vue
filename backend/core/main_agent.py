# 辅助配置
from contextlib import asynccontextmanager
# agent 配置
from deepagents.graph import create_deep_agent
from backend.core.mcp.mcp_tool import mcp_tool
from backend.core.assembled.backends import backend
from backend.core.assembled.middleware import add_middleware
from backend.core.custom_middleware.model_switcher import ModelContext
from backend.config.env_settings import CHECKPOINT_DB, STORE_DB
from backend.config.logger import get_logger

# 异步数据库配置
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.sqlite.aio import AsyncSqliteStore

# ---------- 日志配置 ----------
logger = get_logger(__name__)

# ---------- 中断配置 ----------
interrupt_on = {
    # 高风险操作
    #"read_file": {"allowed_decisions": ["approve", "reject", "edit"]},
}

# ---------- memory配置 ----------
memory_config =[
    "/AGENT.md"
]

# ---------- skill配置 ----------
skills_config =[
    "/active_skills/"
]

# ---------- 初始化配置 ----------
@asynccontextmanager
async def init_graph():
    """异步上下文管理器：初始化数据库连接并编译 graph，退出时自动关闭连接
    
    每次进入此上下文时，都会重新读取 model_config.yaml、system_prompt.txt、
    mcp_server.json 和 subagents_config.py，确保配置热更新生效。
    """
    # 动态导入以避免模块缓存，确保读最新配置
    from backend.core.models.model_factory import get_active_llm
    from backend.core.prompts.prompt import load_system_prompt
    from backend.memory_skill.skill.subagents.scripts.subagent_loader import load_subagents

    logger.info("正在初始化 Graph | checkpoint_db=%s | store_db=%s", CHECKPOINT_DB, STORE_DB)
    mcp_tools = await mcp_tool()
    subagents_config = await load_subagents()
    tools_list = [ *mcp_tools,]


    async with aiosqlite.connect(CHECKPOINT_DB, check_same_thread=False) as conn_sql_check:
        checkpointer_sql = AsyncSqliteSaver(conn=conn_sql_check)
        logger.debug("Checkpointer 已连接")

        async with aiosqlite.connect(STORE_DB, check_same_thread=False) as conn_sql_store:
            store_sql = AsyncSqliteStore(conn=conn_sql_store)
            logger.debug("Store 已连接")

            agent = create_deep_agent(
                name="index_agent",
                model  = get_active_llm(),
                system_prompt=load_system_prompt(),
                tools=tools_list,
                interrupt_on=interrupt_on,
                backend=backend,
                middleware=add_middleware,
                memory=memory_config,
                skills=skills_config,
                context_schema=ModelContext,
                subagents=subagents_config,
                checkpointer=checkpointer_sql,
                store=store_sql,
            )
            logger.info("Agent 编译完成")
            yield agent
            logger.info("Agent 已释放")

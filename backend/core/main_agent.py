"""异步上下文管理器：初始化数据库连接并编译 graph，退出时自动关闭连接

每次进入此上下文时，都会从用户 cache 读取 model_config、system_prompt、
mcp_server 配置，确保用户隔离的配置生效。
"""
from contextlib import asynccontextmanager

# agent 配置
from deepagents.graph import create_deep_agent
from backend.core.mcp.mcp_tool import mcp_tool
from backend.core.rag_tool import retriever_row_doc_tool, save_memory, delete_memory, search_memory, get_memory, list_memory_keys
from backend.core.assembled.backends import create_backend
from backend.core.assembled.middleware import add_middleware
from backend.core.custom_middleware.model_switcher import ModelContext
from backend.config.env_settings import CHECKPOINT_DB, STORE_DB
from backend.config.logger import get_logger

# 异步数据库配置
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.sqlite.aio import AsyncSqliteStore

import yaml
import json
import os
from pathlib import Path
from diskcache import Cache

from langchain_core.language_models import LLM
from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama
from langchain_qwq import ChatQwen
from langchain_openai import ChatOpenAI

from backend.core.models.env_api_key import LLM_ALI_API_KEY, LLM_OPENAI_API_KEY

# ---------- 日志配置 ----------
logger = get_logger(__name__)

# ---------- 中断配置 ----------
interrupt_on = {
    # 高风险操作
    #"read_file": {"allowed_decisions": ["approve", "reject", "edit"]},
}

# ---------- memory配置 ----------
memory_config =["/AGENT.md"]

# ---------- skill配置 ----------
skills_config =["/active_skills/"]


# ═══════════════════════════════════════
#  从用户 cache 读取配置
# ═══════════════════════════════════════


def _load_yaml_from_cache(cache: Cache, key: str) -> dict:
    """从用户 cache 读取 YAML 配置文本并解析为字典。"""
    from backend.api.services.settings_service import get_user_config
    content = get_user_config(cache, key)
    if not content:
        return {}
    try:
        return yaml.safe_load(content) or {}
    except yaml.YAMLError:
        logger.warning("用户 cache 中 YAML 解析失败 | key=%s", key)
        return {}


def _get_active_llm_from_cache(cache: Cache) -> LLM:
    """根据用户 cache 中的 model_config 动态创建当前激活的模型。"""
    cfg = _load_yaml_from_cache(cache, "model")
    provider = cfg.get("active_provider", "deepseek") or "deepseek"
    logger.info("get_active_llm | provider=%s", provider)

    if provider == "deepseek":
        d = cfg.get("deepseek", {})
        return ChatDeepSeek(
            model=d.get("model"),
            base_url=d.get("base_url"),
            reasoning_effort=d.get("reasoning_effort"),
            extra_body=d.get("extra_body"),
        )
    elif provider == "ali":
        a = cfg.get("aliyun", {})
        return ChatQwen(
            model=a.get("model"),
            base_url=a.get("base_url"),
            enable_thinking=a.get("enable_thinking"),
            api_key=LLM_ALI_API_KEY,
        )
    elif provider == "ollama":
        o = cfg.get("ollama", {})
        return ChatOllama(
            model=o.get("model"),
            base_url=o.get("base_url"),
            reasoning=o.get("reasoning"),
        )
    elif provider == "openai":
        op = cfg.get("openai", {})
        return ChatOpenAI(
            model=op.get("model"),
            base_url=op.get("base_url"),
            extra_body=op.get("extra_body"),
            api_key=LLM_OPENAI_API_KEY,
        )
    else:
        logger.warning("未知的模型厂商 '%s'，回退到 deepseek", provider)
        d = cfg.get("deepseek", {})
        return ChatDeepSeek(
            model=d.get("model"),
            base_url=d.get("base_url"),
        )


def _load_prompt_from_cache(cache: Cache) -> str:
    """从用户 cache 读取系统提示词。"""
    from backend.api.services.settings_service import get_user_config
    return get_user_config(cache, "prompt")


async def _mcp_tool_from_cache(cache: Cache):
    """从用户 cache 读取 MCP 配置并加载工具。"""
    import re
    import sys
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from backend.core.mcp.mcp_tool import _DEPRECATED_TRANSPORTS, _BUILTIN_PLACEHOLDERS

    from backend.api.services.settings_service import get_user_config
    config_text = get_user_config(cache, "mcp")
    if not config_text:
        logger.info("用户 cache 中无 MCP 配置，跳过 MCP 工具加载")
        return []

    try:
        config = json.loads(config_text)
    except json.JSONDecodeError:
        logger.warning("用户 cache 中 MCP JSON 解析失败")
        return []

    builtins = {
        **_BUILTIN_PLACEHOLDERS,
        "MCP_SERVER_DIR": str(Path(__file__).parent / "core" / "mcp"),
    }

    def _resolve_env(obj):
        if isinstance(obj, str):
            return re.sub(
                r"\{(\w+)\}",
                lambda m: builtins.get(m.group(1), os.getenv(m.group(1), m.group(0))),
                obj,
            )
        if isinstance(obj, dict):
            return {k: _resolve_env(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_resolve_env(item) for item in obj]
        return obj

    config = _resolve_env(config)

    all_tools = []
    for server_name, server_config in config.items():
        transport = server_config.get("transport", "")
        if transport in _DEPRECATED_TRANSPORTS:
            logger.warning(
                "MCP 服务 [%s] 使用已弃用的 %s 传输，建议改用 http",
                server_name, transport,
            )
        try:
            client = MultiServerMCPClient({server_name: server_config})
            tools = await client.get_tools()
            all_tools.extend(tools)
            logger.info("MCP 服务 [%s] 加载成功，%d 个工具", server_name, len(tools))
        except Exception as e:
            logger.warning("MCP 服务 [%s] 加载失败: %s", server_name, e)

    logger.info("MCP 工具加载完成，共 %d 个工具", len(all_tools))
    return all_tools


# ---------- 初始化配置 ----------
@asynccontextmanager
async def init_graph(cache: Cache):
    """异步上下文管理器：从用户 cache 读取配置，初始化数据库连接并编译 graph。

    Args:
        cache: 当前用户的 diskcache 实例（包含 model/prompt/mcp 配置）。
    """
    from backend.memory_skill.skill.subagents.scripts.subagent_loader import load_subagents

    logger.info("正在初始化用户 Graph | checkpoint_db=%s | store_db=%s", CHECKPOINT_DB, STORE_DB)
    mcp_tools = await _mcp_tool_from_cache(cache)
    subagents_config = await load_subagents()
    tools_list = [*mcp_tools, retriever_row_doc_tool, save_memory, delete_memory, search_memory, get_memory, list_memory_keys]

    active_llm = _get_active_llm_from_cache(cache)
    system_prompt = _load_prompt_from_cache(cache)
    user_backend = create_backend(cache)

    async with aiosqlite.connect(CHECKPOINT_DB, check_same_thread=False) as conn_sql_check:
        checkpointer_sql = AsyncSqliteSaver(conn=conn_sql_check)
        logger.debug("Checkpointer 已连接")

        async with aiosqlite.connect(STORE_DB, check_same_thread=False) as conn_sql_store:
            store_sql = AsyncSqliteStore(conn=conn_sql_store)
            logger.debug("Store 已连接")

            agent = create_deep_agent(
                name="index_agent",
                model=active_llm,
                system_prompt=system_prompt,
                tools=tools_list,
                interrupt_on=interrupt_on,
                backend=user_backend,
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

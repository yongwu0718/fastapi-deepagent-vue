from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI
from backend.core.main_agent import init_graph
from backend.config.logger import get_logger

logger = get_logger(__name__)

_graph: Any = None
_agent_ctx: Any = None


def get_graph():
    """获取当前 graph 实例。若未初始化则抛出 RuntimeError。"""
    if _graph is None:
        logger.error("Graph 尚未初始化，无法获取实例")
        raise RuntimeError("Graph 尚未初始化，请先调用 lifespan 启动。")
    return _graph


async def rebuild_graph():
    """热重载：关闭旧图 → 重新编译新图。
    
    重新读取 model_config.yaml、system_prompt.txt、mcp_server.json，
    创建新的 agent graph 替换内存中的旧实例。
    """
    global _graph, _agent_ctx
    logger.info("开始重建 Graph ...")

    # 1. 退出旧的 context manager（释放数据库连接）
    if _agent_ctx is not None:
        try:
            await _agent_ctx.__aexit__(None, None, None)
            logger.info("旧 Graph 上下文已退出")
        except Exception as e:
            logger.warning("退出旧 Graph 上下文时出错: %s", e)

    # 2. 重新进入新的 context manager
    _agent_ctx = init_graph()
    _graph = await _agent_ctx.__aenter__()
    logger.info("Graph 重建完成，新配置已生效")
    return {"status": "ok", "message": "Graph 重建完成"}


@asynccontextmanager
async def graph_lifespan(app: FastAPI):
    """FastAPI lifespan：初始化 graph 并在应用关闭时自动清理所有资源。"""
    global _graph, _agent_ctx
    logger.info("Graph 生命周期开始")
    _agent_ctx = init_graph()
    _graph = await _agent_ctx.__aenter__()
    logger.info("Graph 实例已注入")
    yield
    # 退出 init_graph 上下文时，数据库连接自动关闭
    await _agent_ctx.__aexit__(None, None, None)
    _graph = None
    _agent_ctx = None
    logger.info("Graph 实例已清理，数据库连接已释放")
"""Graph 管理服务 —— 按用户隔离的 Graph 实例管理。

每个用户拥有独立的 Graph 实例，配置互不影响。
Graph 实例在首次访问时懒加载，在配置变更时通过 rebuild_graph 重建。
"""
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI
from diskcache import Cache

from backend.core.main_agent import init_graph
from backend.config.logger import get_logger

logger = get_logger(__name__)

# ── 按用户名缓存 Graph 实例 ──
_graphs: dict[str, Any] = {}
_agent_ctxs: dict[str, Any] = {}


def get_graph(username: str) -> Any:
    """获取指定用户的 graph 实例。

    若该用户尚未初始化，则抛出 RuntimeError。
    在 chat 等路由中应通过 get_or_create_graph 获取（自动懒加载）。

    Args:
        username: 用户名。

    Raises:
        RuntimeError: 该用户的 Graph 尚未初始化。
    """
    if username not in _graphs:
        logger.error("用户 Graph 尚未初始化 | username=%s", username)
        raise RuntimeError(f"Graph 尚未初始化，请先调用 rebuild_graph(username={username})")
    return _graphs[username]


async def get_or_create_graph(cache: Cache, username: str) -> Any:
    """获取或创建指定用户的 graph 实例（懒加载）。

    若该用户尚未有 Graph 实例，则使用其 cache 初始化一个新的。

    Args:
        cache: 当前用户的 diskcache 实例。
        username: 用户名。
    """
    if username not in _graphs:
        logger.info("首次访问，懒加载用户 Graph | username=%s", username)
        await rebuild_graph(cache, username)
    return _graphs[username]


async def rebuild_graph(cache: Cache = None, username: str = None):
    """热重载：关闭旧图 → 从用户 cache 重新编译新图。

    Args:
        cache: 当前用户的 diskcache 实例（含 model/prompt/mcp 配置）。
        username: 用户名。

    Returns:
        {"status": "ok", "message": "Graph 重建完成"}
    """
    global _graphs, _agent_ctxs

    if cache is None or username is None:
        logger.error("rebuild_graph 缺少 cache 或 username 参数")
        raise RuntimeError("rebuild_graph 需要 cache 和 username 参数")

    logger.info("开始重建用户 Graph | username=%s", username)

    # 1. 退出旧的 context manager（释放数据库连接）
    old_ctx = _agent_ctxs.pop(username, None)
    if old_ctx is not None:
        try:
            await old_ctx.__aexit__(None, None, None)
            logger.info("旧 Graph 上下文已退出 | username=%s", username)
        except Exception as e:
            logger.warning("退出旧 Graph 上下文时出错 | username=%s | error=%s", username, e)

    # 2. 重新进入新的 context manager（从用户 cache 读取配置）
    new_ctx = init_graph(cache)
    _graphs[username] = await new_ctx.__aenter__()
    _agent_ctxs[username] = new_ctx
    logger.info("Graph 重建完成 | username=%s", username)
    return {"status": "ok", "message": "Graph 重建完成"}


async def close_user_graph(username: str) -> None:
    """关闭指定用户的 Graph（用户注销/禁用时调用）。"""
    ctx = _agent_ctxs.pop(username, None)
    _graphs.pop(username, None)
    if ctx is not None:
        try:
            await ctx.__aexit__(None, None, None)
            logger.info("用户 Graph 已关闭 | username=%s", username)
        except Exception as e:
            logger.warning("关闭用户 Graph 出错 | username=%s | error=%s", username, e)


async def close_all_graphs() -> None:
    """关闭所有用户的 Graph（应用关闭时调用）。"""
    for username in list(_agent_ctxs.keys()):
        await close_user_graph(username)
    logger.info("所有用户 Graph 已清理")


@asynccontextmanager
async def graph_lifespan(app: FastAPI):
    """FastAPI lifespan：应用关闭时自动清理所有用户的 Graph 资源。

    注意：Graph 实例不再在应用启动时全局初始化，
    而是按用户懒加载（首次聊天/配置访问时创建）。
    """
    logger.info("Graph 生命周期开始（懒加载模式）")
    yield
    # 应用关闭时清理所有用户的 Graph
    await close_all_graphs()
    logger.info("所有 Graph 实例已清理，数据库连接已释放")

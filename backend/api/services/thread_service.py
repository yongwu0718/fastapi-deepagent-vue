"""线程（对话）管理业务逻辑。"""

from typing import Optional
from diskcache import Cache

from backend.api.services.graph import get_or_create_graph
from backend.api.utils.message2json import message_to_response
from backend.api.utils.exceptions import NotFoundException, InternalErrorException, ErrorCode
from backend.api.schemas.response import ChatResponse
from backend.api.sql.dele_sql import delete_thread_messages_history
from backend.api.sql.list_threads import list_all_threads
from backend.config.logger import get_logger

logger = get_logger(__name__)


def _tid(username: str, thread_id: str) -> str:
    """将前端 thread_id 转换为内部隔离的 thread_id（username:thread_id）。"""
    return f"{username}:{thread_id}"


async def get_thread_history(thread_id: str, cache: Cache, username: str, checkpoint_id: Optional[str] = None) -> ChatResponse:
    """获取会话历史消息。

    Args:
        thread_id: 对话线程 ID
        cache: 当前用户的 diskcache 实例。
        username: 当前用户名。
        checkpoint_id: 可选，指定检查点 ID。
            - 不传：获取最新状态（当前行为）
            - 传入：获取该检查点对应的分支消息（用于树形分支导航）

    Raises:
        NotFoundException: 线程或检查点不存在
    """
    logger.info("获取会话历史 | thread_id=%s | checkpoint_id=%s | username=%s", thread_id, checkpoint_id, username)
    graph = await get_or_create_graph(cache, username)
    internal_tid = _tid(username, thread_id)
    config = {"configurable": {"thread_id": internal_tid}}
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id

    state = await graph.aget_state(config)

    if state is None or state.values is None:
        detail = f"线程不存在: thread_id={thread_id}"
        if checkpoint_id:
            detail += f", checkpoint_id={checkpoint_id}"
        raise NotFoundException(error_code=ErrorCode.THREAD_NOT_FOUND, detail=detail)

    messages_raw = state.values.get("messages", [])
    filtered = []
    for m in messages_raw:
        resp = message_to_response(m)
        if resp is not None:
            filtered.append(resp)

    logger.info("会话历史获取完成 | thread_id=%s | messages=%d", thread_id, len(filtered))
    head_cid = None
    if state.config and isinstance(state.config, dict):
        head_cid = state.config.get("configurable", {}).get("checkpoint_id")
    return ChatResponse(messages=filtered, head_checkpoint_id=head_cid)


def delete_thread_history(thread_id: str, username: str) -> dict:
    """删除会话历史（同步操作，不依赖 graph）。"""
    internal_tid = _tid(username, thread_id)
    logger.info("删除会话历史 | thread_id=%s | username=%s", thread_id, username)
    result = delete_thread_messages_history(internal_tid)
    logger.info("会话历史已删除 | thread_id=%s | username=%s", thread_id, username)
    return result


def list_threads(username: str) -> dict:
    """列出指定用户的对话线程（同步操作，不依赖 graph）。"""
    logger.debug("列出对话线程 | username=%s", username)
    threads = list_all_threads(username)
    logger.info("线程列表获取完成 | username=%s | count=%d", username, len(threads))
    return {"threads": threads}

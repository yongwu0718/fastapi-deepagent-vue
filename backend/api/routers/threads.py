"""线程管理路由 —— 历史/删除/列表。"""

from typing import Optional

from fastapi import APIRouter, Query

from backend.api.schemas.response import ChatResponse
from backend.api.services.thread_service import get_thread_history, delete_thread_history, list_threads
from backend.api.utils.error_handlers import handle_endpoint_errors
from backend.api.utils.exceptions import ErrorCode, NotFoundException
from backend.config.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["threads"])


@router.get("/chat/{thread_id}/get-messages-history", response_model=ChatResponse)
@handle_endpoint_errors(
    ErrorCode.THREAD_HISTORY_FAILED,
    log_msg="获取会话历史异常 | thread_id={thread_id}",
    detail_msg="获取会话历史失败: thread_id={thread_id}",
)
async def get_messages_history(
    thread_id: str,
    checkpoint_id: Optional[str] = Query(default=None, description="可选，指定检查点 ID 以获取对应分支的消息"),
):
    """获取会话历史消息。

    - 不传 checkpoint_id：获取最新状态
    - 传入 checkpoint_id：获取指定检查点对应的分支消息（用于树形分支导航）
    """
    logger.info("GET /chat/%s/get-messages-history | checkpoint_id=%s", thread_id, checkpoint_id)
    return await get_thread_history(thread_id, checkpoint_id=checkpoint_id)


@router.delete("/chat/{thread_id}/delete-messages-history")
@handle_endpoint_errors(
    ErrorCode.THREAD_DELETE_FAILED,
    log_msg="删除会话历史异常 | thread_id={thread_id}",
    detail_msg="删除会话历史失败: thread_id={thread_id}",
)
async def delete_messages_history(thread_id: str):
    """删除会话历史"""
    logger.info("DELETE /chat/%s/delete-messages-history", thread_id)
    result = delete_thread_history(thread_id)
    if isinstance(result, dict) and result.get("status") == "error":
        raise NotFoundException(
            error_code=ErrorCode.THREAD_NOT_FOUND,
            detail=result.get("message", f"线程不存在或删除失败: thread_id={thread_id}"),
        )
    return result


@router.get("/threads")
async def list_threads_endpoint():
    """列出所有对话线程"""
    logger.debug("GET /threads")
    return list_threads()

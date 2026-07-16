from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from backend.api.schemas.checkpoint import ReplayRequest, ForkRequest, CheckpointHistoryResponse
from backend.api.services.checkpoint_service import (
    list_input_checkpoints,
    replay_from_checkpoint,
    fork_from_checkpoint,
)
from backend.api.utils.error_handlers import handle_endpoint_errors
from backend.api.utils.exceptions import ErrorCode
from backend.config.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


@router.get("/{thread_id}/inputs", response_model=CheckpointHistoryResponse)
@handle_endpoint_errors(
    ErrorCode.CHECKPOINT_LIST_FAILED,
    log_msg="获取输入检查点列表异常 | thread_id={thread_id}",
    detail_msg="获取检查点列表失败: thread_id={thread_id}",
)
async def get_input_checkpoints(
    thread_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="每页数量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
):
    """获取对话线程中所有 input 检查点列表。

    每次用户发送消息时 LangGraph 自动生成 input 检查点。
    前端可从中选择检查点进行 replay / fork 操作。
    """
    logger.info("GET /checkpoints/%s/inputs | limit=%d | offset=%d", thread_id, limit, offset)
    return await list_input_checkpoints(thread_id, limit=limit, offset=offset)


@router.post("/{thread_id}/replay")
@handle_endpoint_errors(
    ErrorCode.CHECKPOINT_REPLAY_FAILED,
    log_msg="重放异常 | thread_id={thread_id} | checkpoint_id={body.checkpoint_id}",
    detail_msg="检查点重放失败: thread_id={thread_id}, checkpoint_id={body.checkpoint_id}",
)
async def replay_checkpoint(thread_id: str, body: ReplayRequest):
    """从指定检查点重放执行。

    从该检查点重新执行后续节点，以 SSE 流式返回结果。
    检查点之前的节点不重新执行（结果已缓存），遇到中断时仍会触发。
    传入 messages 时注入用户输入，触发模型重新生成。
    """
    logger.info("POST /checkpoints/%s/replay | checkpoint_id=%s | has_messages=%s",
                thread_id, body.checkpoint_id, body.messages is not None)
    return StreamingResponse(
        await replay_from_checkpoint(
            thread_id, body.checkpoint_id, body.checkpoint_ns, body.messages,
        ),
        media_type="text/event-stream",
    )


@router.post("/{thread_id}/fork")
@handle_endpoint_errors(
    ErrorCode.CHECKPOINT_FORK_FAILED,
    log_msg="分叉异常 | thread_id={thread_id} | checkpoint_id={body.checkpoint_id}",
    detail_msg="检查点分叉失败: thread_id={thread_id}, checkpoint_id={body.checkpoint_id}",
)
async def fork_checkpoint(thread_id: str, body: ForkRequest):
    """从指定检查点分叉执行。

    在历史检查点基础上传入新的状态值（如 messages），创建新分支继续执行。
    原始执行链完整保留，新分支独立发展，以 SSE 流式返回结果。
    """
    logger.info("POST /checkpoints/%s/fork | checkpoint_id=%s", thread_id, body.checkpoint_id)
    return StreamingResponse(
        await fork_from_checkpoint(
            thread_id,
            body.checkpoint_id,
            body.checkpoint_ns,
            body.values,
        ),
        media_type="text/event-stream",
    )
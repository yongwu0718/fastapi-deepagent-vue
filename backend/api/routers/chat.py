from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from backend.api.schemas.request import ChatRequest
from backend.api.schemas.response import ChatResponse
from backend.api.schemas.interrupt import ResumeRequest
from backend.api.services.chat_service import (
    invoke_chat, stream_chat, resume_chat,
    invoke_chat_with_files, stream_chat_with_files,
)
from backend.api.utils.file_handler import SUPPORTED_EXTENSIONS
from backend.api.utils.error_handlers import handle_endpoint_errors
from backend.api.utils.exceptions import AppException, ErrorCode
from backend.config.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{thread_id}", response_model=ChatResponse, response_model_exclude_none=True)
@handle_endpoint_errors(
    ErrorCode.CHAT_INVOKE_FAILED,
    log_msg="非流式聊天异常 | thread_id={thread_id}",
    detail_msg="非流式聊天失败: thread_id={thread_id}",
)
async def chat_endpoint(chat_request: ChatRequest, thread_id: str):
    """非流式聊天端点"""
    logger.info("POST /chat/%s | 非流式请求", thread_id)
    return await invoke_chat(chat_request, thread_id)


@router.post("/{thread_id}/stream")
@handle_endpoint_errors(
    ErrorCode.CHAT_STREAM_FAILED,
    log_msg="流式聊天异常 | thread_id={thread_id}",
    detail_msg="流式聊天启动失败: thread_id={thread_id}",
)
async def chat_stream(chat_request: ChatRequest, thread_id: str):
    """流式聊天端点（支持中断检测 & 检查点恢复）"""
    logger.info(
        "POST /chat/%s/stream | 流式请求 | checkpoint_id=%s checkpoint_ns=%s",
        thread_id, chat_request.checkpoint_id, chat_request.checkpoint_ns,
    )
    return StreamingResponse(
        stream_chat(chat_request, thread_id),
        media_type="text/event-stream",
    )


@router.post("/{thread_id}/resume")
@handle_endpoint_errors(
    ErrorCode.CHAT_RESUME_FAILED,
    log_msg="恢复聊天异常 | thread_id={thread_id}",
    detail_msg="恢复聊天失败: thread_id={thread_id}",
)
async def resume_chat_endpoint(resume_request: ResumeRequest, thread_id: str):
    """恢复中断的对话 —— 传入用户决策后继续流式返回结果"""
    logger.info("POST /chat/%s/resume | 恢复请求", thread_id)
    return StreamingResponse(
        resume_chat(resume_request, thread_id),
        media_type="text/event-stream",
    )


# ═══════════════════════════════════════════
#  带文件附件的聊天端点
# ═══════════════════════════════════════════

@router.post("/{thread_id}/with-files", response_model=ChatResponse, response_model_exclude_none=True)
@handle_endpoint_errors(
    ErrorCode.CHAT_INVOKE_FAILED,
    log_msg="带文件非流式聊天异常 | thread_id={thread_id}",
    detail_msg="带文件非流式聊天失败: thread_id={thread_id}",
)
async def chat_with_files_endpoint(
    thread_id: str,
    messages: str = Form(..., description='JSON 字符串，形如 {"messages": [{"role":"user","content":"..."}]}'),
    files: list[UploadFile] = File(default_factory=list, description="PDF / DOCX 文件列表"),
):
    """非流式聊天（支持上传 PDF / DOCX 附件）。"""
    logger.info("POST /chat/%s/with-files | 非流式 | files=%d", thread_id, len(files))
    file_data = await _read_upload_files(files)
    return await invoke_chat_with_files(file_data, messages, thread_id)


@router.post("/{thread_id}/with-files/stream")
@handle_endpoint_errors(
    ErrorCode.CHAT_STREAM_FAILED,
    log_msg="带文件流式聊天异常 | thread_id={thread_id}",
    detail_msg="带文件流式聊天启动失败: thread_id={thread_id}",
)
async def chat_with_files_stream_endpoint(
    thread_id: str,
    messages: str = Form(..., description='JSON 字符串，形如 {"messages": [{"role":"user","content":"..."}]}'),
    files: list[UploadFile] = File(default_factory=list, description="PDF / DOCX 文件列表"),
):
    """流式聊天（支持上传 PDF / DOCX 附件）。"""
    logger.info("POST /chat/%s/with-files/stream | 流式 | files=%d", thread_id, len(files))
    file_data = await _read_upload_files(files)
    return StreamingResponse(
        stream_chat_with_files(file_data, messages, thread_id),
        media_type="text/event-stream",
    )


async def _read_upload_files(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    """读取上传文件列表，校验格式，返回 [(file_name, file_bytes), ...]。

    Raises:
        AppException: 文件格式不支持时抛出 400。
    """
    import os

    result: list[tuple[str, bytes]] = []
    for f in files:
        file_name = f.filename or "unknown"
        ext = os.path.splitext(file_name.lower())[1]
        if ext not in SUPPORTED_EXTENSIONS:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.VALIDATION_ERROR,
                detail=f"不支持的文件格式: {ext} （仅支持 {', '.join(SUPPORTED_EXTENSIONS)}）",
            )
        content = await f.read()
        result.append((file_name, content))
        logger.info("文件已接收 | name=%s size=%d", file_name, len(content))
    return result

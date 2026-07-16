"""聊天业务逻辑 —— 非流式/流式调用 & 中断恢复 & 文件附件处理。"""

import asyncio
import os
from typing import List, Optional

from langgraph.types import Command

from backend.api.services.graph import get_graph
from backend.api.utils.dict2json import dump_messages, langchain_result_to_response
from backend.api.utils.stream import _sse_stream
from backend.api.utils.file_handler import (
    FILE_EXTRACTORS, IMAGE_MIME_MAP, IMAGE_EXTENSIONS,
    compress_image, image_to_base64_data_url, save_extracted_text,
)
from backend.api.schemas.request import ChatRequest
from backend.api.schemas.interrupt import ResumeRequest
from backend.config.logger import get_logger
from backend.config.env_settings import LANGFUSE_TRACING_ENABLED
from backend.config.observability import build_langfuse_config

logger = get_logger(__name__)


async def invoke_chat(chat_request: ChatRequest, thread_id: str):
    """非流式聊天"""
    logger.info("非流式聊天 | thread_id=%s | messages=%d", thread_id, len(chat_request.messages))
    dict_messages = dump_messages(chat_request.messages)
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    if chat_request.checkpoint_id:
        config["configurable"]["checkpoint_id"] = chat_request.checkpoint_id
    if chat_request.checkpoint_ns:
        config["configurable"]["checkpoint_ns"] = chat_request.checkpoint_ns
    if LANGFUSE_TRACING_ENABLED:
        config.update(build_langfuse_config(thread_id=thread_id))
    input_data = {"messages": dict_messages}
    if chat_request.rubric:
        input_data["rubric"] = chat_request.rubric
        logger.info("Loop Engineering 模式 | thread_id=%s | rubric 长度=%d", thread_id, len(chat_request.rubric))
    result = await graph.ainvoke(
        input_data,
        config=config,
    )
    logger.info("非流式聊天完成 | thread_id=%s", thread_id)
    return langchain_result_to_response(result)


def stream_chat(chat_request: ChatRequest, thread_id: str):
    """流式聊天（返回 SSE 异步生成器）"""
    logger.info("流式聊天开始 | thread_id=%s | messages=%d", thread_id, len(chat_request.messages))
    dict_messages = dump_messages(chat_request.messages)
    graph = get_graph()
    input_data = {"messages": dict_messages}
    if chat_request.rubric:
        input_data["rubric"] = chat_request.rubric
        logger.info("Loop Engineering 流式模式 | thread_id=%s | rubric 长度=%d", thread_id, len(chat_request.rubric))
    return _sse_stream(
        graph,
        input_data,
        thread_id,
        checkpoint_id=chat_request.checkpoint_id,
        checkpoint_ns=chat_request.checkpoint_ns,
    )


def resume_chat(resume_request: ResumeRequest, thread_id: str):
    """恢复中断的对话 —— 流式返回结果"""
    logger.info("恢复中断对话 | thread_id=%s | decisions=%d", thread_id, len(resume_request.decisions))
    decisions = [
        d.model_dump(mode="json", exclude_none=True)
        for d in resume_request.decisions
    ]
    graph = get_graph()
    return _sse_stream(graph, Command(resume={"decisions": decisions}), thread_id)


# ═══════════════════════════════════════════
#  带文件附件的聊天
# ═══════════════════════════════════════════

async def _extract_and_build_content(
    files: list[tuple[str, bytes]],
    messages_json: str,
) -> tuple[list[dict], list[dict]]:
    """提取文件文本，构建 content_blocks 和保存信息。

    Args:
        files: [(file_name, file_bytes), ...]
        messages_json: JSON 字符串，形如 {"messages": [{...}]}

    Returns:
        (content_blocks, saved_files) — content_blocks 可直接传给 graph，
        saved_files 供日志/响应使用。
    """
    import json
    msg_data = json.loads(messages_json)
    messages = msg_data.get("messages", [])
    checkpoint_id: Optional[str] = msg_data.get("checkpoint_id")
    checkpoint_ns: Optional[str] = msg_data.get("checkpoint_ns")

    # 用户消息文本
    user_texts: list[str] = []
    for m in messages:
        if m.get("role") == "user" and m.get("content"):
            user_texts.append(m["content"])
    question = "\n".join(user_texts)

    # 构建 content_blocks（多模态格式）
    content_blocks: list[dict] = []
    if question:
        content_blocks.append({"type": "text", "text": question})

    # 提取附件文本
    attachment_texts: list[tuple[str, str]] = []
    for file_name, file_bytes in files:
        ext = os.path.splitext(file_name.lower())[1]

        # 图片文件：压缩后转为 base64 data URL，直接构建 image_url block
        if ext in IMAGE_EXTENSIONS:
            compressed_bytes = compress_image(file_bytes)
            data_url = image_to_base64_data_url(compressed_bytes, "image/jpeg")
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": data_url},
            })
            logger.info(
                "图片已压缩并转 base64 | name=%s raw=%d compressed=%d",
                file_name, len(file_bytes), len(compressed_bytes),
            )
            continue

        extractor = FILE_EXTRACTORS.get(ext)
        if extractor is None:
            logger.warning("不支持的文件格式，已跳过 | name=%s", file_name)
            continue

        if ext == ".pdf":
            import io
            file_source = io.BytesIO(file_bytes)
            file_text = await asyncio.to_thread(extractor, file_source)
        elif ext == ".docx":
            file_text = await asyncio.to_thread(extractor, file_bytes)
        else:
            logger.warning("未处理的附件类型 | ext=%s name=%s", ext, file_name)
            continue

        attachment_texts.append((file_name, file_text))
        logger.info("文件文本提取完成 | name=%s chars=%d", file_name, len(file_text))

    # 拼入附件文本
    for i, (name, text) in enumerate(attachment_texts):
        content_blocks.append({"type": "text", "text": f"[附件 {i + 1}: {name}]\n{text}"})

    saved_files = [
        {"name": name, "text": text} for name, text in attachment_texts
    ]

    return content_blocks, saved_files, checkpoint_id, checkpoint_ns


async def _save_attachment_texts(saved_files: list[dict]) -> None:
    """将提取的附件文本异步写入 uploads 目录。"""
    for item in saved_files:
        try:
            path = await save_extracted_text(item["name"], item["text"])
            logger.info("附件文本已保存 | path=%s", path)
        except Exception:
            logger.exception("保存附件文本失败 | name=%s", item["name"])


async def invoke_chat_with_files(
    files: list[tuple[str, bytes]],
    messages_json: str,
    thread_id: str,
) -> dict:
    """非流式聊天（带文件附件）。

    Args:
        files: [(file_name, file_bytes), ...]
        messages_json: JSON 字符串，形如 {"messages": [...]}
        thread_id: 对话线程 ID

    Returns:
        ChatResponse（Pydantic model）
    """
    logger.info("非流式聊天(带文件) | thread_id=%s | files=%d", thread_id, len(files))
    content_blocks, saved_files, checkpoint_id, checkpoint_ns = await _extract_and_build_content(files, messages_json)

    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id
    if checkpoint_ns:
        config["configurable"]["checkpoint_ns"] = checkpoint_ns
    if LANGFUSE_TRACING_ENABLED:
        config.update(build_langfuse_config(thread_id=thread_id))

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": content_blocks}]},
        config=config,
    )
    logger.info("非流式聊天(带文件)完成 | thread_id=%s", thread_id)

    # 异步保存附件文本（不阻塞响应）
    asyncio.create_task(_save_attachment_texts(saved_files))

    return langchain_result_to_response(result)


def stream_chat_with_files(
    files: list[tuple[str, bytes]],
    messages_json: str,
    thread_id: str,
):
    """流式聊天（带文件附件，返回 SSE 异步生成器）。

    Args:
        files: [(file_name, file_bytes), ...]
        messages_json: JSON 字符串，形如 {"messages": [...]}
        thread_id: 对话线程 ID
    """
    logger.info("流式聊天(带文件)开始 | thread_id=%s | files=%d", thread_id, len(files))

    async def _generator():
        content_blocks, saved_files, checkpoint_id, checkpoint_ns = await _extract_and_build_content(files, messages_json)
        graph = get_graph()

        # 异步保存附件文本
        asyncio.create_task(_save_attachment_texts(saved_files))

        async for chunk in _sse_stream(
            graph,
            {"messages": [{"role": "user", "content": content_blocks}]},
            thread_id,
            checkpoint_id=checkpoint_id,
            checkpoint_ns=checkpoint_ns,
        ):
            yield chunk

    return _generator()

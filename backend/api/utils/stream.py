import json
import asyncio
from typing import Dict, List, Optional, Tuple

from langgraph.types import Command
from langchain_core.messages import AIMessageChunk, AIMessage
from backend.api.schemas.response import StreamResponse
from backend.api.utils.exceptions import AppException, ErrorCode
from backend.config.logger import get_logger
from backend.config.env_settings import LANGFUSE_TRACING_ENABLED
from backend.config.observability import build_langfuse_config

logger = get_logger(__name__)

# ---------- 流处理类 ----------
class StreamProcessor:
    @staticmethod
    def _handle_message_chunk(
        chunk: Dict, last_type: Optional[str], ns: tuple = ()
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Dict[str, Optional[str]]]:
        token, metadata = chunk["data"]
        extra: Dict[str, Optional[str]] = {}

        if isinstance(token, AIMessageChunk):
            # 1. 推理内容
            reasoning_text = token.additional_kwargs.get("reasoning_content", "")
            if reasoning_text:
                if last_type != "reasoning":
                    last_type = "reasoning"
                return reasoning_text, last_type, "reasoning", extra

            # 2. 工具调用（修复点）
            if token.tool_calls:
                # 通常一个 chunk 只包含一个 tool_call 的增量信息
                tool_call = token.tool_calls[0]
                if last_type != "tool_call":
                    last_type = "tool_call"

                extra["tool_call_id"] = tool_call.get("id", "")
                # name 可能不在每个 chunk 中都出现（增量流），优先使用已有 name
                tool_name = tool_call.get("name") or ""
                extra["tool_call_name"] = tool_name
                # 参数可能是不完整的 JSON 片段，这里直接序列化当前 args
                args = tool_call.get("args", {})
                extra["tool_call_args"] = json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else str(args)

                # 返回内容为工具名称（若无名称则返回空，前端可根据 type 判断）
                return tool_name, last_type, "tool_call", extra

            # 3. 普通文本 / 多模态内容
            if token.content:
                if isinstance(token.content, list):
                    # 视觉模型等返回的多模态 content blocks
                    text_parts = []
                    images = []
                    for block in token.content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                            elif block.get("type") == "image_url":
                                images.append(block.get("image_url", {}))
                    combined_text = "".join(text_parts)
                    if combined_text or images:
                        if last_type != "text":
                            last_type = "text"
                        if images:
                            extra["images"] = json.dumps(images, ensure_ascii=False)
                        return combined_text, last_type, "text", extra
                else:
                    if last_type != "text":
                        last_type = "text"
                    return token.content, last_type, "text", extra

            return None, last_type, None, extra

        # 非 AI 消息（工具结果等）
        else:
            if hasattr(token, 'content') and token.content:
                if last_type != "tool_result":
                    last_type = "tool_result"
                extra["tool_call_id"] = getattr(token, 'tool_call_id', None) or ""
                return str(token.content), last_type, "tool_result", extra
            return None, last_type, None, extra

    @staticmethod
    def _extract_images_from_message(msg) -> list[dict]:
        """从一条完整消息中提取所有 image_url blocks。"""
        images = []
        content = getattr(msg, 'content', None)
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "image_url":
                    images.append(block.get("image_url", {}))
        return images

    @staticmethod
    def _handle_checkpoint_chunk(chunk: Dict, ns: tuple = ()):
        """提取检查点的 checkpoint_id / parent_checkpoint_id，返回 (info, kind)。
        
        kind:
          - "input" : source=='input'，前端绑定到 user 消息（retry/fork）
          - "leaf"  : next==[] 叶子节点，前端用于树形分支导航
          - None    : 不感兴趣的检查点
        """
        if chunk["type"] != "checkpoints":
            return None, None

        data = chunk["data"]
        config = data.get("config", {}) or {}
        configurable = config.get("configurable", {})
        parent_config = data.get("parent_config") or {}
        parent_conf = parent_config.get("configurable", {})

        base_info = {
            "checkpoint_id": configurable.get("checkpoint_id", ""),
            "parent_checkpoint_id": parent_conf.get("checkpoint_id"),
        }

        metadata = data.get("metadata", {})
        is_input = metadata.get("source") == "input"
        is_leaf = not data.get("next")  # next 为空/不存在 = 叶子节点

        # 优先判断：叶子节点且同时是 input（流结束时的最后一条 input checkpoint）
        if is_leaf and is_input:
            base_info["kind"] = "input"
            return base_info, "input"

        if is_input:
            base_info["kind"] = "input"
            return base_info, "input"

        if is_leaf:
            base_info["kind"] = "leaf"
            return base_info, "leaf"

        return None, None

# ── 共享 SSE 流生成器（同时处理消息、更新和中断） ──
async def _sse_stream(
    graph,
    input_data,
    thread_id: str,
    checkpoint_id: Optional[str] = None,
    checkpoint_ns: str = "",
):
    """共享 SSE 流生成器。

    Args:
        graph: LangGraph 编译后的 graph 实例
        input_data: graph.astream 的输入（消息字典或 Command）
        thread_id: 对话线程 ID
        checkpoint_id: 可选检查点 ID，从指定检查点恢复/重放
        checkpoint_ns: 可选检查点命名空间（子图场景）
    """
    config = {"configurable": {"thread_id": thread_id}}
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id
        logger.debug("SSE 流使用检查点 | thread_id=%s checkpoint_id=%s", thread_id, checkpoint_id)
    if checkpoint_ns:
        config["configurable"]["checkpoint_ns"] = checkpoint_ns
        logger.debug("SSE 流使用 checkpoint_ns | thread_id=%s checkpoint_ns=%s", thread_id, checkpoint_ns)
    if LANGFUSE_TRACING_ENABLED:
        config.update(build_langfuse_config(thread_id=thread_id))
    last_type: Optional[str] = None

    try:
        async for chunk in graph.astream(
            input_data,
            config=config,
            version="v2",
            stream_mode=["messages", "checkpoints", "updates", "custom"],
            subgraphs=True,
        ):
            ns = chunk.get("ns", ())
            if chunk["type"] == "messages":
                text, last_type, msg_type, extra = StreamProcessor._handle_message_chunk(
                    chunk, last_type, ns
                )
                if text and msg_type:
                    response = StreamResponse(
                        type=msg_type,
                        content=text,
                        done=False,
                        tool_call_id=extra.get("tool_call_id"),
                        tool_call_name=extra.get("tool_call_name"),
                        tool_call_args=extra.get("tool_call_args"),
                    )
                    yield f"data: {json.dumps(response.model_dump(mode='json'), ensure_ascii=False)}\n\n"

                # 多模态：额外推送 image 事件
                if extra.get("images"):
                    for img in json.loads(extra["images"]):
                        img_response = StreamResponse(
                            type="image",
                            content=img,
                            done=False,
                        )
                        yield f"data: {json.dumps(img_response.model_dump(mode='json'), ensure_ascii=False)}\n\n"

            elif chunk["type"] == "checkpoints":
                info, kind = StreamProcessor._handle_checkpoint_chunk(chunk, ns)
                if info is None:
                    continue

                response = StreamResponse(
                    type="checkpoint",
                    content=json.dumps(info, ensure_ascii=False),
                    done=False,
                )
                yield f"data: {json.dumps(response.model_dump(mode='json'), ensure_ascii=False)}\n\n"

            elif chunk["type"] == "updates":
                data = chunk["data"]
                if "__interrupt__" in data:
                    interrupt_value = data["__interrupt__"][0].value
                    logger.info("SSE 流检测到中断 | thread_id=%s", thread_id)
                    response = StreamResponse(
                        type="interrupt",
                        content=json.dumps(interrupt_value, ensure_ascii=False),
                        done=False,
                    )
                    yield f"data: {json.dumps(response.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                    return

            elif chunk["type"] == "custom":
                data = chunk.get("data")
                if isinstance(data, dict) and isinstance(data.get("type"), str) and data["type"].startswith("rubric_"):
                    logger.info(
                        "Rubric 评估事件 | thread_id=%s | event=%s | iteration=%s",
                        thread_id, data.get("type"), data.get("iteration"),
                    )
                    response = StreamResponse(
                        type="rubric",
                        content=json.dumps(data, ensure_ascii=False),
                        done=False,
                    )
                    yield f"data: {json.dumps(response.model_dump(mode='json'), ensure_ascii=False)}\n\n"

        # 流正常结束：检查最终状态中的多模态内容（图片）
        logger.debug("SSE 流正常结束 | thread_id=%s", thread_id)
        try:
            state = await graph.aget_state(config)
            if state and state.values:
                messages = state.values.get("messages", [])
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        images = StreamProcessor._extract_images_from_message(msg)
                        for img in images:
                            img_response = StreamResponse(
                                type="image",
                                content=img,
                                done=False,
                            )
                            yield f"data: {json.dumps(img_response.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                        if images:
                            break  # 只检查最后一条 AI 消息
        except Exception:
            logger.exception("检查最终状态多模态内容失败 | thread_id=%s", thread_id)

        final = StreamResponse(type="done", done=True)
        yield f"data: {json.dumps(final.model_dump(mode='json'), ensure_ascii=False)}\n\n"

    except AppException as e:
        logger.warning(
            "SSE 流业务异常 | thread_id=%s | error_code=%s | detail=%s",
            thread_id, e.error_code.value, e.detail,
        )
        error = StreamResponse(
            type="error",
            content=str(e.detail),
            error_code=e.error_code.value,
            done=True,
        )
        yield f"data: {json.dumps(error.model_dump(mode='json'), ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.exception("SSE 流异常 | thread_id=%s | error=%s", thread_id, e)
        error = StreamResponse(
            type="error",
            content=str(e),
            error_code=ErrorCode.STREAM_INTERNAL_ERROR.value,
            done=True,
        )
        yield f"data: {json.dumps(error.model_dump(mode='json'), ensure_ascii=False)}\n\n"

from backend.api.schemas.request import Message
from backend.api.schemas.response import MessageResponse, ChatResponse


def _normalize_content(content):
    """将 langchain 消息的 content 标准化：若为 list 且只有单个 text block，展开为纯字符串。"""
    if isinstance(content, list):
        text_parts = []
        non_text = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            else:
                non_text.append(block)
        if not non_text:
            return "".join(text_parts)
        # 含非 text block（如图片），保持 list 格式
        return content
    return content


def dump_messages(messages: list[Message]) -> list[dict]:
    """将 Message 列表转换为 dict 列表"""
    return [message.model_dump() for message in messages]

def langchain_result_to_response(result: dict) -> ChatResponse:
    """将 graph.ainvoke 返回的 dict 转成 ChatResponse"""
    msgs = []
    for msg in result["messages"]:
        role = ""
        content = ""
        reason_content = None

        if msg.type == "human":
            role = "human"
            content = _normalize_content(msg.content)
            # reason_content 保持 None，最终不会出现在 JSON 中
        elif msg.type == "ai":
            role = "ai"
            content = _normalize_content(msg.content)
            # 提取推理内容
            reason_content = msg.additional_kwargs.get("reasoning_content")
            # 不需要处理 tool_calls
        elif msg.type == "tool":
            role = "tool"
            content = _normalize_content(msg.content)
            # reason_content 保持 None
        else:
            continue

        msgs.append(MessageResponse(
            role=role,
            content=content,
            reason_content=reason_content,
            # 不再传入 tool_calls
        ))
    return ChatResponse(messages=msgs)

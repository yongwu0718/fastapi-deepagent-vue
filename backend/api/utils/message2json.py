from backend.api.schemas.response import MessageResponse

# 允许 user、assistant、tool 三种角色通过
_CHAT_ROLES = {"user", "assistant", "tool"}


def _extract_text_blocks(content) -> list[str]:
    """从 content 中提取所有 text 类型的文本块。

    LangChain 附件消息的 content 为 list 格式：
        [{'type':'text','text':'总结一下'}, {'type':'text','text':'[附件]\\n文档...'}]
    返回：['总结一下', '[附件]\\n文档...']
    """
    if isinstance(content, str):
        return [content]

    if not isinstance(content, list):
        return [str(content)]

    parts: list[str] = []
    for block in content:
        text = None
        if isinstance(block, dict):
            if block.get("type") == "text":
                text = block.get("text", "")
        elif hasattr(block, "text"):
            text = getattr(block, "text", "")
        elif hasattr(block, "type") and getattr(block, "type", "") == "text":
            text = getattr(block, "text", "")
        if text is not None:
            parts.append(str(text))
    return parts


def message_to_response(msg) -> MessageResponse | None:
    """将 LangChain 消息对象转为 MessageResponse，非聊天角色返回 None

    允许 assistant 消息仅包含推理内容而无需文本输出（模型可能只输出思考链但未生成文本）。
    """
    role_map = {
        "human": "user",
        "ai": "assistant",
        "tool": "tool",
    }
    role = role_map.get(msg.type, msg.type)

    # 跳过非允许角色
    if role not in _CHAT_ROLES:
        return None

    # 先尝试提取 reasoning_content（思考过程），以便后续无文本块时回退
    reason = None
    if hasattr(msg, "additional_kwargs"):
        reason = msg.additional_kwargs.get("reasoning_content")
    if reason is None and hasattr(msg, "response_metadata"):
        reason = msg.response_metadata.get("reasoning_content")

    blocks = _extract_text_blocks(msg.content)
    if not blocks:
        # 没有文本内容，但有推理内容 → 保留为仅推理的 assistant 消息
        if reason and role == "assistant":
            return MessageResponse(role="assistant", content="", reason_content=reason)
        return None

    # 用户消息只取第一个文本块（用户实际提问），过滤附件内容避免撑满页面
    if role == "user":
        content = blocks[0]
    else:
        content = "\n".join(blocks)

    if not content:
        # 合并后为空，但有推理内容 → 保留
        if reason and role == "assistant":
            return MessageResponse(role="assistant", content="", reason_content=reason)
        return None

    return MessageResponse(role=role, content=content, reason_content=reason)

from __future__ import annotations

from collections.abc import Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import ToolMessage, AnyMessage

class TruncateToolMessagesMiddleware(AgentMiddleware):
    """
    轻量级中间件：将历史中的 ToolMessage 内容替换为占位符，
    避免旧的检索结果（或其他大型 tool 输出）持续占用上下文窗口。

    默认策略：保留最近 keep_recent 个 ToolMessage 不被修改。
    """

    def __init__(
        self,
        keep_recent: int = 2,
        placeholder: str = "[Earlier tool outputs are omitted for context management.]",
    ) -> None:
        super().__init__()
        self.keep_recent = keep_recent
        self.placeholder = placeholder

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        messages = request.messages
        modified_messages = self._truncate_old_tool_messages(messages)

        if modified_messages is not messages:
            request = request.override(messages=modified_messages)

        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        messages = request.messages
        modified_messages = self._truncate_old_tool_messages(messages)

        if modified_messages is not messages:
            request = request.override(messages=modified_messages)

        return await handler(request)

    def _truncate_old_tool_messages(
        self, messages: list[AnyMessage]
    ) -> list[AnyMessage]:
        """
        保留最近 keep_recent 个 ToolMessage，将其余的 ToolMessage 内容替换为占位符。
        """
        found = 0
        cutoff = len(messages)
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], ToolMessage):
                found += 1
                if found >= self.keep_recent:
                    cutoff = i
                    break

        if found < self.keep_recent:
            return messages

        new_messages = []
        modified = False
        for i, msg in enumerate(messages):
            if i < cutoff and isinstance(msg, ToolMessage):
                new_msg = ToolMessage(
                    content=self.placeholder,
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                )
                new_messages.append(new_msg)
                modified = True
            else:
                new_messages.append(msg)

        return new_messages if modified else messages
"""响应模型 —— FastAPI 输出 / SSE 流式推送。"""

from typing import Literal, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    """单条消息响应"""
    role: str
    content: Union[str, List[dict]] = ""
    reason_content: Optional[str] = None
    model_config = ConfigDict(exclude_none=True)


class ChatResponse(BaseModel):
    """聊天响应"""
    messages: List[MessageResponse]


class StreamResponse(BaseModel):
    """流式响应的单个数据块（SSE 推送）"""
    type: Literal["text", "reasoning", "tool_call", "tool_result", "error", "done", "interrupt", "checkpoint", "rubric", "image"] = "text"
    content: Union[str, List[dict]] = Field(default="", description="当前数据块的内容，纯文本或图像元数据")
    tool_call_id: Optional[str] = Field(default=None, description="工具调用 ID")
    tool_call_name: Optional[str] = Field(default=None, description="工具调用名称")
    tool_call_args: Optional[str] = Field(default=None, description="工具调用参数 JSON 字符串")
    checkpoint_id: Optional[str] = Field(default=None, description="user 消息的检查点 ID")
    parent_checkpoint_id: Optional[str] = Field(default=None, description="user 消息的父检查点 ID")
    error_code: Optional[str] = Field(default=None, description="错误码（type=error 时携带）")
    done: bool = False
    model_config = ConfigDict(exclude_none=True)

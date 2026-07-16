"""请求模型 —— 对话输入 / 中断恢复请求。"""

from typing import Literal, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

class Message(BaseModel):
    """单个消息模型"""
    model_config = ConfigDict(extra="ignore")
    role: Literal["user", "assistant", "system"] = Field(..., description="消息发送者角色")
    content: Union[str, List[dict]] = Field(..., description="消息内容：纯文本字符串或多模态 content blocks 列表")


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[Message] = Field(..., description="对话消息列表", min_length=1)
    checkpoint_id: Optional[str] = Field(default=None, description="检查点 ID，用于从指定检查点恢复/重放")
    checkpoint_ns: Optional[str] = Field(default=None, description="检查点命名空间（子图场景）")
    rubric: Optional[str] = Field(default=None, description="完成条件（rubric）。设定后 Agent 自然停止时由独立评估器判断是否满足，未满足则自动注入反馈继续循环，直到满足或达到迭代上限")

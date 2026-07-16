"""中断恢复模型 —— 人工审批 / 编辑决策。"""

from typing import Literal, List, Optional

from pydantic import BaseModel, Field


class Decision(BaseModel):
    """单条决策"""
    type: Literal["approve", "reject", "edit"] = Field(..., description="决策类型")
    edited_action: Optional[dict] = Field(default=None, description="编辑后的动作（type=edit 时）")


class ResumeRequest(BaseModel):
    """中断恢复请求"""
    decisions: List[Decision] = Field(..., description="用户决策列表", min_length=1)

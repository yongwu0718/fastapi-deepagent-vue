"""定时任务 Pydantic Schema。"""

from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    """创建定时任务请求体。"""

    title: str = Field(default="", max_length=100, description="任务名称")
    message: str = Field(min_length=1, description="预设消息内容")
    execute_hour: int = Field(ge=0, le=23, description="执行小时（0-23，24小时制）")
    execute_minute: int = Field(ge=0, le=59, description="执行分钟（0-59）")


class UpdateTaskRequest(BaseModel):
    """更新定时任务请求体。"""

    title: str | None = Field(default=None, max_length=100, description="任务名称")
    message: str | None = Field(default=None, min_length=1, description="预设消息内容")
    execute_hour: int | None = Field(default=None, ge=0, le=23, description="执行小时")
    execute_minute: int | None = Field(default=None, ge=0, le=59, description="执行分钟")
    is_active: bool | None = Field(default=None, description="是否启用")


class TaskResponse(BaseModel):
    """定时任务响应。"""

    id: str
    username: str
    title: str
    message: str
    execute_hour: int
    execute_minute: int
    is_active: bool
    last_run_at: str | None = None
    created_at: str

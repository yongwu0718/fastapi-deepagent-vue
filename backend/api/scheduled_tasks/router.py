"""定时任务路由 —— 用户管理自己的定时对话任务。"""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from backend.api.auth.dependencies import CurrentUserDep
from backend.api.scheduled_tasks.db import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)
from backend.api.scheduled_tasks.schemas import (
    CreateTaskRequest,
    TaskResponse,
    UpdateTaskRequest,
)
from backend.api.auth.schemas import OperationResult
from backend.config.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/scheduled-tasks", tags=["scheduled-tasks"])


@router.post("", response_model=TaskResponse)
def create_scheduled_task(
    body: CreateTaskRequest,
    current_user: CurrentUserDep,
) -> TaskResponse:
    """创建定时任务。"""
    task_id = str(uuid.uuid4())
    task = create_task(
        task_id, current_user.username, body.title, body.message,
        body.execute_hour, body.execute_minute,
    )
    logger.info("POST /scheduled-tasks | id=%s | username=%s", task_id, current_user.username)
    return TaskResponse(**task)


@router.get("", response_model=list[TaskResponse])
def list_scheduled_tasks(current_user: CurrentUserDep) -> list[TaskResponse]:
    """列出当前用户的定时任务。"""
    tasks = list_tasks(current_user.username)
    return [TaskResponse(**t) for t in tasks]


@router.put("/{task_id}", response_model=TaskResponse)
def update_scheduled_task(
    task_id: Annotated[str, Path(description="任务 ID")],
    body: UpdateTaskRequest,
    current_user: CurrentUserDep,
) -> TaskResponse:
    """更新定时任务。"""
    fields = body.model_dump(exclude_none=True)
    if "is_active" in fields:
        fields["is_active"] = int(fields["is_active"])
    task = update_task(task_id, current_user.username, **fields)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}",
        )
    return TaskResponse(**task)


@router.delete("/{task_id}", response_model=OperationResult)
def delete_scheduled_task(
    task_id: Annotated[str, Path(description="任务 ID")],
    current_user: CurrentUserDep,
) -> OperationResult:
    """删除定时任务。"""
    if not delete_task(task_id, current_user.username):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}",
        )
    return OperationResult(success=True, message="任务已删除")

"""定时任务调度器 —— 每分钟检查并执行到点任务。

执行流程:
    1. 每分钟查询 is_active=1 且时间匹配且今日未执行的任务
    2. 对每个任务: 绑定日志上下文 → 获取用户 cache → 获取/创建用户 graph → 发送预设消息
    3. 结果自动存到对话历史（LangGraph checkpointer 自动保存）
    4. 更新 last_run_at 防止重复执行
"""

import asyncio
from datetime import datetime

from backend.api.scheduled_tasks.db import get_due_tasks, init_db, mark_task_run
from backend.config.logger import get_logger, bind_context, clear_context
from backend.core.cache.manager import get_cache_manager

logger = get_logger(__name__)

_scheduler_task: asyncio.Task | None = None


async def _execute_task(task: dict) -> None:
    """执行单个定时任务：绑定日志上下文 → 获取用户 graph → 发送预设消息 → 存到对话历史。"""
    username = task["username"]
    task_id = task["id"]
    message = task["message"]
    title = task.get("title") or "定时任务"

    # 绑定日志上下文（路由到对应用户日志目录）
    bind_context(username=username, task_id=task_id, component="scheduler")

    logger.info(
        "定时任务开始执行 | id=%s | username=%s | title=%s | message_len=%d",
        task_id, username, title, len(message),
    )

    try:
        from backend.api.services.graph import get_or_create_graph

        cache = get_cache_manager().get_user_cache(username)
        graph = await get_or_create_graph(cache, username)

        # 使用用户隔离的 thread_id
        thread_id = f"{username}:scheduled-{task_id}"
        config = {"configurable": {"thread_id": thread_id}}

        logger.info("调用 Graph | thread_id=%s", thread_id)

        result = await graph.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )

        # 提取执行结果摘要
        messages = result.get("messages", []) if isinstance(result, dict) else []
        last_msg = messages[-1] if messages else None
        result_preview = ""
        if last_msg:
            content = getattr(last_msg, "content", str(last_msg))
            result_preview = str(content)[:200]

        logger.info(
            "定时任务执行完成 | id=%s | username=%s | messages_count=%d | result_preview=%s",
            task_id, username, len(messages), result_preview,
        )
    except Exception as e:
        logger.exception(
            "定时任务执行失败 | id=%s | username=%s | error=%s",
            task_id, username, str(e),
        )
    finally:
        clear_context()


async def _scheduler_loop():
    """调度循环：每分钟检查到点任务并执行。"""
    logger.info("定时任务调度器已启动 | 检查间隔=60s")
    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            due_tasks = get_due_tasks(now.hour, now.minute, today_str)

            if due_tasks:
                logger.info(
                    "调度器检查 | 当前时间=%s | 发现 %d 个待执行任务",
                    now.strftime("%Y-%m-%d %H:%M:%S"), len(due_tasks),
                )
                for task in due_tasks:
                    await _execute_task(task)
                    mark_task_run(
                        task["id"],
                        task["username"],
                        now.strftime("%Y-%m-%d %H:%M:%S"),
                    )
            else:
                logger.trace(
                    "调度器检查 | 时间=%s | 无待执行任务",
                    now.strftime("%H:%M"),
                )
        except Exception:
            logger.exception("调度器循环异常")

        await asyncio.sleep(60)


def start_scheduler():
    """启动调度器（在 FastAPI lifespan 中调用）。"""
    global _scheduler_task
    init_db()
    _scheduler_task = asyncio.create_task(_scheduler_loop())


async def stop_scheduler():
    """停止调度器（在 FastAPI lifespan 退出时调用）。"""
    global _scheduler_task
    if _scheduler_task is not None:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
    logger.info("定时任务调度器已停止")

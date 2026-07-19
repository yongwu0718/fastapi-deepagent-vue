import asyncio
import os
from datetime import datetime
from typing import Optional

from backend.cli.runtime.save_state import save_snapshot_to_json
from backend.config.logger import setup_logging, get_logger
from backend.core.main_agent import init_graph

logger = get_logger(__name__)


async def query_state(thread_id: str, checkpoint_id: Optional[str] = None):
    async with init_graph() as graph:
        state = await graph.aget_state(
            {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}
        )

        messages = state.values.get("messages", []) or []
        print(f"会话 {thread_id} 共有 {len(messages)} 条消息")

        if state.next:
            print(f"待执行节点 (next): {list(state.next)}")

        interrupts = state.interrupts if hasattr(state, "interrupts") else []
        if interrupts:
            print(f"中断数: {len(list(interrupts))}")

        created_at = state.created_at if hasattr(state, "created_at") else None
        if created_at:
            print(f"快照时间: {created_at}")

        # 构造输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(os.getcwd(), f"snapshot_{thread_id[:8]}_{timestamp}.json")

        save_snapshot_to_json(state, output_file)
        print(f"已保存至: {output_file}")
        return output_file


if __name__ == "__main__":
    setup_logging()
    logger.info("查询状态快照启动")
    asyncio.run(query_state(
        thread_id="32f4ad2c-9b04-44b0-aa02-0b5c047b2139",
        # checkpoint_id="1f16a293-065d-614e-8003-7036fc1d4640"
    ))

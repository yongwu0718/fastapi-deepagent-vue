import asyncio
import sys
from pathlib import Path

# 将 agent 目录加入 sys.path，确保能导入同级模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage
from graph_compile import init_graph

THREAD_ID = "b3d363f7-8277-443b-b204-59a57b231301"
CHECKPOINT_ID = "1f1688ea-4221-6169-bfff-0ded93d6b952"

async def test_fork():
    config = {
        "configurable": {
            "thread_id": THREAD_ID,
            "checkpoint_id": CHECKPOINT_ID
        }
    }

    async with init_graph() as graph:
        # 分支：从历史检查点开始，传入新的用户消息（注意格式）
        async for event in graph.astream(
            input={"messages": [HumanMessage(content="7-4")]},  # ✅ 正确格式
            config=config,
            stream_mode="updates"
        ):
            print(event)

        # 查看最终状态
        final_state = await graph.aget_state(config)
        print("\n分支后的最终消息：", final_state.values.get("messages", []))

if __name__ == "__main__":
    asyncio.run(test_fork())
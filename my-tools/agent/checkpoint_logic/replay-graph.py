import asyncio
import sys
from pathlib import Path

# 将 agent 目录加入 sys.path，确保能导入同级模块
sys.path.insert(0, str(Path(__file__).parent.parent))
from langchain_core.messages import HumanMessage
from graph_compile import init_graph
from runtime.stream import StreamProcessor

# 线程 ID 和要重放的检查点 ID
THREAD_ID = "0d258a04-7d9a-413e-b76f-e939004d2e42"
CHECKPOINT_ID = "1f1698a9-c031-66d5-bfff-68259dba858a"


async def test_replay():
    config = {
        "configurable": {
            "thread_id": THREAD_ID,
            "checkpoint_id": CHECKPOINT_ID,
        }
    }

    async with init_graph() as graph:
        print(f"从检查点 {CHECKPOINT_ID} 开始重放.")

        last_type = None
        resume_command = None
        interrupted = False

        # 重放：input=None 表示不添加新消息，纯粹从该检查点继续执行
        # 如果图中有 interrupt，重放时仍会触发中断，可用 Command(resume=.) 恢复
        async for chunk in graph.astream(
            input={"messages": [HumanMessage(content="7-4")]},
            config=config,
            version="v2",
            stream_mode=["messages", "checkpoints", "updates"],
            subgraphs=True,
        ):
            ns = chunk.get("ns", ())
            if chunk["type"] == "messages":
                last_type = StreamProcessor._handle_message_chunk(chunk, last_type, ns)
            elif chunk["type"] == "checkpoints":
                cp_info = StreamProcessor._handle_checkpoint_chunk(chunk, ns)
                if cp_info:
                    print(f"\n[checkpoint] id={cp_info['checkpoint_id']}, parent={cp_info['parent_checkpoint_id']}")
            elif chunk["type"] == "updates":
                if last_type:
                    print()
                    last_type = None
                cmd = await StreamProcessor._handle_updates_chunk(chunk, config, ns)
                if cmd:
                    resume_command = cmd
                    interrupted = True
                    break

        if interrupted:
            print("\n⏸️  执行被中断，可使用 Command(resume=.) 恢复")
        else:
            print("\n✅ 重放完成")

        # 查看最终状态
        final_state = await graph.aget_state(config)
        print("\n重放后的最终状态：", final_state.values)


if __name__ == "__main__":
    asyncio.run(test_replay())

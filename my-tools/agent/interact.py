import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
import uuid
import asyncio
from langchain_core.messages import HumanMessage
from graph_compile import init_graph
from runtime.save_state import save_snapshot_to_json
from runtime.chat_log import append_chat_log
from runtime.stream import StreamProcessor
from config.env import CHAT_LOG_DIR, SAVE_STATE_DIR
from config.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

id = str(uuid.uuid4())
MD_FILE = f"{CHAT_LOG_DIR}\\chat_log_{id}.md"

async def main():
    async with init_graph() as graph:
        config = {"configurable": {"thread_id": id, "checkpoint_id": "1f168671-06f2-6005-bfff-e1f670788ee5"}}
        logger.info("会话启动 | thread_id=%s", id)
        # ---------- 初始化消息计数 ----------
        initial_snapshot = await graph.aget_state(config)
        all_existing = initial_snapshot.values.get("messages", [])
        msg_count = len(all_existing)
        if msg_count > 0:
            print(f"\U0001f4c2 当前会话已有 {msg_count} 条消息，将从断点继续记录。")
            logger.info("从断点恢复 | 已有消息数=%d", msg_count)
        else:
            print("\U0001f4dd 全新对话开始，日志将实时追加到", MD_FILE)
            logger.info("全新对话 | log_file=%s", MD_FILE)

        last_type = None
        resume_command = None

        while True:
            if resume_command is not None:
                current_input = resume_command
                resume_command = None
                logger.info("恢复中断命令")
            else:
                question = await asyncio.to_thread(
                    input, "输入exit或quit退出对话，请输入您的问题：\n"
                )
                if question.lower() in ("exit", "quit"):
                    logger.info("用户退出对话")
                    print("对话结束。")
                    break

                current_input = {
                    "messages": [
                        HumanMessage(content=question)
                    ]
                }
                logger.info("用户输入 | question=%s", question[:100])

            interrupted = False
            try:
                async for chunk in graph.astream(
                    input=current_input,
                    config=config,
                    version="v2",
                    stream_mode=["messages", "updates"],
                    subgraphs=True
                ):
                    ns = chunk.get("ns", ())
                    if chunk["type"] == "messages":
                        last_type = StreamProcessor._handle_message_chunk(chunk, last_type, ns)
                        
                    elif chunk["type"] == "updates":
                        if last_type:
                            print()
                            last_type = None
                        cmd = await StreamProcessor._handle_updates_chunk(chunk, config, ns)
                        if cmd:
                            resume_command = cmd
                            interrupted = True
                            logger.info("检测到中断，等待审批")
                            break
            except Exception as e:
                logger.exception("Graph 流处理异常 | error=%s", e)
                raise

            # ---------- 记录本轮新增消息 ----------
            snapshot = await graph.aget_state(config)
            all_messages = snapshot.values.get("messages", [])
            new_messages = all_messages[msg_count:]
            msg_count = len(all_messages)
            if new_messages:
                await append_chat_log(MD_FILE, new_messages)
                logger.info("本轮对话已追加 | 新增消息数=%d | log_file=%s", len(new_messages), MD_FILE)
                print(f"\n\U0001f4dd 本轮对话已追加至 {MD_FILE}")

            if interrupted:
                await save_snapshot_to_json(snapshot, "state_snapshot.json")
            else:
                print("\n✅ 本轮处理完成")

        # 最终保存全量状态
        path_state = SAVE_STATE_DIR
        history = await graph.aget_state(config)
        await save_snapshot_to_json(history, os.path.join(path_state, f"state_snapshot_{id}.json"))
        logger.info("会话结束 | 全量状态已保存 | thread_id=%s", id)


if __name__ == "__main__":
    asyncio.run(main())
    
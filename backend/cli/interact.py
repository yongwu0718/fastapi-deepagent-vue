import uuid
import asyncio
import os

from markitdown import MarkItDown

from langchain_core.messages import HumanMessage
from backend.core.main_agent import init_graph
#from backend.core.subagent import init_graph

from backend.api.utils.file_handler import FILE_EXTRACTORS, SUPPORTED_EXTENSIONS
from backend.cli.runtime.chat_log import append_chat_log
from backend.cli.runtime.stream import StreamProcessor
from backend.config.env_settings import CHAT_LOG_DIR, LANGFUSE_TRACING_ENABLED
from backend.config.logger import setup_logging, get_logger
from backend.config.observability import build_langfuse_config

logger = get_logger(__name__)

async def _main(thread_id=None):
    # 确保 thread_id 不为 None
    if thread_id is None:
        thread_id = str(uuid.uuid4())

    setup_logging()  # 只在此处初始化
    logger.info("交互式命令行启动 | thread_id=%s", thread_id)

    async with init_graph() as index_agent:
        id = thread_id
        MD_FILE = os.path.join(CHAT_LOG_DIR, f"{id}.md")
        config = {"configurable": {"thread_id": id}}
        if LANGFUSE_TRACING_ENABLED:
            langfuse_cfg = build_langfuse_config(thread_id=id, tags=["interactive-cli"])
            config["callbacks"] = langfuse_cfg["callbacks"]
            config["metadata"] = langfuse_cfg["metadata"]

        initial_snapshot = await index_agent.aget_state(config)
        all_existing = initial_snapshot.values.get("messages", [])
        msg_count = len(all_existing)
        if msg_count > 0:
            print(f"\U0001f4c2 当前会话已有 {msg_count} 条消息，将从断点继续记录。")
        else:
            print("\U0001f4dd 全新对话开始，日志将实时追加到", MD_FILE)

        last_type = None
        resume_command = None

        while True:
            if resume_command is not None:
                current_input = resume_command
                resume_command = None
            else:
                raw = await asyncio.to_thread(
                    input, "输入exit或quit退出对话，请输入您的问题：\n"
                )
                if raw.lower() in ("exit", "quit"):
                    print("对话结束。")
                    break

                # ---- 检测附件（PDF / DOCX） ----
                attachment_texts = []
                parts = raw.split(maxsplit=1)
                if len(parts) == 2:
                    possible_path, user_question = parts
                    # 支持多个附件路径，用空格分隔
                    file_paths: list[str] = []
                    remaining = possible_path
                    while os.path.isfile(remaining) and os.path.splitext(remaining.lower())[1] in SUPPORTED_EXTENSIONS:
                        file_paths.append(remaining)
                        # 继续检测 user_question 中是否还有路径
                        sub_parts = user_question.split(maxsplit=1)
                        if len(sub_parts) == 2:
                            sub_path = sub_parts[0]
                            if os.path.isfile(sub_path) and os.path.splitext(sub_path.lower())[1] in SUPPORTED_EXTENSIONS:
                                file_paths.append(sub_path)
                                user_question = sub_parts[1]
                            else:
                                break
                        else:
                            break

                    if file_paths:
                        for file_path in file_paths:
                            ext = os.path.splitext(file_path.lower())[1]
                            extractor = FILE_EXTRACTORS[ext]
                            logger.info("正在加载附件: %s", file_path)
                            file_text = await asyncio.to_thread(extractor, file_path)
                            attachment_texts.append((os.path.basename(file_path), file_text))
                            print(f"\U0001f4ce 已加载附件: {os.path.basename(file_path)} ({len(file_text)} 字符)")
                        raw = user_question
                    else:
                        raw = raw  # 没有检测到支持的文件附件，保持原样

                # ---- 构建消息 ----
                if attachment_texts:
                    attachment_content = "\n\n".join(
                        f"--- 附件 {i+1}: {name} ---\n{content}"
                        for i, (name, content) in enumerate(attachment_texts)
                    )
                    msg_content = f"{raw}\n\n[附件内容]\n{attachment_content}"
                else:
                    msg_content = raw

                current_input = {
                    "messages": [HumanMessage(content=msg_content)]
                }

                interrupted = False
                async for chunk in index_agent.astream(
                    input=current_input,
                    config=config,
                    version="v2",
                    stream_mode=["messages", "updates", "checkpoints"],
                    subgraphs=True
                ):
                    ns = chunk.get("ns", ())
                    if chunk["type"] == "messages":
                        last_type = StreamProcessor._handle_message_chunk(chunk, last_type, ns)

                    elif chunk["type"] == "checkpoints":
                        checkpoint_info = StreamProcessor._handle_checkpoint_chunk(chunk, ns)
                        if checkpoint_info:
                            print(f"检查点信息: {checkpoint_info}")

                    elif chunk["type"] == "updates":
                        if last_type:
                            print()
                            last_type = None
                        cmd = await StreamProcessor._handle_updates_chunk(chunk, config, ns)
                        if cmd:
                            resume_command = cmd
                            interrupted = True
                            break

                # ---------- 记录本轮新增消息 ----------
                snapshot = await index_agent.aget_state(config)
                all_messages = snapshot.values.get("messages", [])
                new_messages = all_messages[msg_count:]
                msg_count = len(all_messages)

                if new_messages:
                    await append_chat_log(MD_FILE, new_messages)
                    print(f"\n\U0001f4dd 本轮对话已追加至 {MD_FILE}")
                else:
                    print("\n✅ 本轮处理完成")

def main(thread_id=None):
    """同步入口，供 console script 调用"""
    asyncio.run(_main(thread_id=thread_id))

if __name__ == "__main__":
    # 日志已在 _main 内初始化，此处不再重复
    thread_id = None
    if thread_id is None:
        thread_id = str(uuid.uuid4())
    else:
        thread_id = thread_id
    asyncio.run(_main(thread_id=thread_id))
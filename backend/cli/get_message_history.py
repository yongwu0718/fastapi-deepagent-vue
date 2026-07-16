import asyncio
import os
import re
from datetime import datetime
from typing import List
from typing import Optional

from langchain_core.messages import BaseMessage, HumanMessage

from backend.cli.runtime.chat_log import write_chat_log
from backend.config.env_settings import CHAT_LOG_DIR
from backend.config.logger import setup_logging, get_logger
from backend.core.main_agent import init_graph

logger = get_logger(__name__)


def _sanitize_filename(name: str, max_len: int = 10) -> str:
    """清理非法字符并截断长度，确保可作为 Windows/Unix 文件名。"""
    if not name:
        return ""
    # 去掉 Windows 非法字符与首尾空白
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name).strip().strip(".")
    return name[:max_len]


def _first_human_title(messages: List[BaseMessage], max_len: int = 10) -> str:
    """从消息列表中取第一条 HumanMessage 的 content，限制 max_len 字符。"""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            return _sanitize_filename(content, max_len)
    return ""


async def print_history(thread_id: str, checkpoint_id: Optional[str] = None):
    assert CHAT_LOG_DIR is not None, "CHAT_LOG_DIR 未配置，请检查 .env.agent"
    async with init_graph() as graph:
        if checkpoint_id:
            checkpoint_id = checkpoint_id
        else:
            checkpoint_id = None
        state = await graph.aget_state({"configurable": {"thread_id": thread_id,"checkpoint_id":checkpoint_id}})
        #print(state.values)
        messages = state.values.get("messages", []) or []
        print(f"会话 {thread_id} 共有 {len(messages)} 条消息")

        # 构造文件路径：CHAT_LOG_DIR/<第一条human消息前10字>_<时间戳>.md
        os.makedirs(CHAT_LOG_DIR, exist_ok=True)
        title = _first_human_title(messages, max_len=10) or thread_id[:10]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_file = os.path.join(CHAT_LOG_DIR, f"{title}_{timestamp}.md")

        await write_chat_log(md_file, messages)
        print(f"已保存至: {md_file}")
        return md_file


if __name__ == "__main__":
    setup_logging()
    logger.info("获取消息历史启动")
    asyncio.run(print_history(
        thread_id="9f91ea1c-dbde-47ed-b348-3e18f2dd0a10",
        #checkpoint_id="1f16a293-065d-614e-8003-7036fc1d4640"
        ))
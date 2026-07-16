import asyncio
from re import M
import aiofiles
import os
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from backend.config.logger import get_logger

logger = get_logger(__name__)


def messages_to_markdown(messages: list) -> str:
    md = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            md += "<span style=\"color: blue; font-weight: bold;\">user</span>\n"
            md += ""
            md += f"{msg.content}\n"
        elif isinstance(msg, AIMessage):
            reasoning = msg.additional_kwargs.get("reasoning_content")
            if reasoning:
                md += "<span style=\"color: green; font-weight: bold;\">推理内容</span>\n"
                md += ""
                md += f"{reasoning}\n"
            if msg.content:
                md += "<span style=\"color:violet ;font-weight: bold;\">响应生成</span>\n"
                md += ""
                md += f"{msg.content}\n"
            if msg.tool_calls:
                md += "<span style=\"color: red; font-weight: bold;\">tool_calls</span>\n"
                for tc in msg.tool_calls:
                    md += f"  Call name='{tc['name']}' args={tc.get('args', {})} \n"
    return md


async def write_chat_log(md_file: str, messages: list) -> None:
    """将完整消息列表写入一个 Markdown 文件（覆盖写）。"""
    if not messages:
        logger.warning("消息列表为空，跳过写入 | file=%s", md_file)
        return
    logger.debug("写入聊天日志 | file=%s | messages=%d", md_file, len(messages))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = f"# 📅 {timestamp}\n\n"
    md += messages_to_markdown(messages)
    # 确保父目录存在
    parent_dir = os.path.dirname(md_file)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    async with aiofiles.open(md_file, "w", encoding="utf-8") as f:
        await f.write(md)
    logger.trace("聊天日志写入完成 | file=%s", md_file)


async def append_chat_log(md_file: str, messages_to_append: list) -> None:
    if not messages_to_append:
        return
    logger.debug("追加聊天日志 | file=%s | messages=%d", md_file, len(messages_to_append))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = f"# 📅 {timestamp}\n\n"
    md += messages_to_markdown(messages_to_append)
    md += "---\n\n"
    parent_dir = os.path.dirname(md_file)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    async with aiofiles.open(md_file, "a", encoding="utf-8") as f:
        await f.write(md)
    logger.trace("聊天日志写入完成 | file=%s", md_file)
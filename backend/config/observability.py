"""Langfuse 可观测性模块 —— 初始化客户端 & 提供 CallbackHandler 单例。"""

import os
from typing import Any

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from .logger import get_logger

logger = get_logger(__name__)

# ========== Langfuse 配置 ==========
LANGFUSE_TRACING_ENABLED = os.getenv("LANGFUSE_TRACING_ENABLED", "true").lower() in (
    "true", "1", "t", "yes",
)
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL")


def langfuse_init():
    """初始化 Langfuse 客户端，验证连接。禁用时跳过。"""
    if not LANGFUSE_TRACING_ENABLED:
        logger.info("Langfuse 已禁用 | tracing_enabled=False")
        return

    langfuse = Langfuse(
        tracing_enabled=LANGFUSE_TRACING_ENABLED,
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        base_url=LANGFUSE_BASE_URL,
    )

    try:
        if langfuse.auth_check():
            logger.info("Langfuse 连接验证成功 | host=%s", LANGFUSE_BASE_URL)
        else:
            logger.warning("Langfuse 连接验证失败 | host=%s", LANGFUSE_BASE_URL)
    except Exception as e:
        logger.warning("Langfuse 连接异常，已跳过 | host=%s | error=%s", LANGFUSE_BASE_URL, e)


_langfuse_callback_handler: CallbackHandler | None = None


def get_langfuse_callback_handler() -> CallbackHandler:
    """惰性创建 Langfuse CallbackHandler 单例，用于追踪 LLM 交互。

    延迟初始化确保在 load_dotenv() 之后才创建 —— 避免因 env 加载顺序
    导致 Langfuse 使用错误或缺失的凭证。

    Returns:
        CallbackHandler: 配置好的 Langfuse callback handler。
    """
    global _langfuse_callback_handler
    if _langfuse_callback_handler is None:
        _langfuse_callback_handler = CallbackHandler()
        logger.debug("Langfuse CallbackHandler 已创建（惰性初始化）")
    return _langfuse_callback_handler


def build_langfuse_config(thread_id: str, user_id: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
    """为 LangGraph 调用构建包含 Langfuse 会话追踪的配置字典。

    将 CallbackHandler 放入 callbacks，将 session_id / user_id / tags 放入 metadata。
    这是 Langfuse Python SDK v3 推荐的做法 —— CallbackHandler 从 metadata 中动态读取
    langfuse_session_id、langfuse_user_id、langfuse_tags 等属性。

    Args:
        thread_id: 会话唯一标识，用作 session_id，在 Langfuse UI 中按会话聚合 traces。
        user_id: 可选，用户标识。
        tags: 可选，标签列表（如 ["production", "chat"]）。

    Returns:
        dict: 包含 callbacks 和 metadata 的配置字典，可直接 merge 到 LangGraph config 中。
    """
    config: dict[str, Any] = {
        "callbacks": [get_langfuse_callback_handler()],
        "metadata": {
            "langfuse_session_id": thread_id,
        },
    }
    if user_id:
        config["metadata"]["langfuse_user_id"] = user_id
    if tags:
        config["metadata"]["langfuse_tags"] = tags
    return config

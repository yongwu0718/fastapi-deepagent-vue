import os
import sys
import re
import json
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from backend.config.logger import get_logger
from backend.core.models.env_api_key import App_ID, App_Secret

load_dotenv()
logger = get_logger(__name__)

# MCP 规范已弃用 SSE 传输 (streamable-http)，推荐使用 http 替代
_DEPRECATED_TRANSPORTS: set[str] = {"sse"}

# 内置占位符映射（非环境变量，由代码直接提供）
_BUILTIN_PLACEHOLDERS: dict[str, str] = {
    "PYTHON_EXECUTABLE": sys.executable,
}


async def mcp_tool() -> list[Any]:

    # 加载 JSON 配置并替换占位符（格式：{VAR_NAME}，优先查内置映射，其次查环境变量）
    config_path = Path(__file__).parent / "mcp_server.json"
    config_text = config_path.read_text(encoding="utf-8")
    config = json.loads(config_text)

    # 动态内置占位符（依赖 config_path 的路径）
    builtins = {
        **_BUILTIN_PLACEHOLDERS,
        "MCP_SERVER_DIR": str(config_path.parent),
    }

    def _resolve_env(obj: Any) -> Any:
        """递归替换配置中的 {VAR} 占位符。

        支持嵌入在字符串中的占位符，如 "Bearer {API_KEY}"。
        解析顺序：内置映射 > 环境变量 > 保留原样。
        """
        if isinstance(obj, str):
            return re.sub(
                r"\{(\w+)\}",
                lambda m: builtins.get(m.group(1), os.getenv(m.group(1), m.group(0))),
                obj,
            )
        if isinstance(obj, dict):
            return {k: _resolve_env(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_resolve_env(item) for item in obj]
        return obj

    config = _resolve_env(config)

    # 逐服务加载工具，单个失败不影响其他服务
    all_tools: list[Any] = []
    for server_name, server_config in config.items():
        transport = server_config.get("transport", "")
        if transport in _DEPRECATED_TRANSPORTS:
            logger.warning(
                "MCP 服务 [%s] 使用已弃用的 %s 传输，建议改用 http (streamable-http)",
                server_name,
                transport,
            )

        try:
            client = MultiServerMCPClient({server_name: server_config})
            tools = await client.get_tools()
            all_tools.extend(tools)
            logger.info("MCP 服务 [%s] 加载成功，%d 个工具", server_name, len(tools))
        except Exception as e:
            logger.warning("MCP 服务 [%s] 加载失败: %s", server_name, e)

    logger.info("MCP 工具加载完成，共 %d 个工具", len(all_tools))
    return all_tools
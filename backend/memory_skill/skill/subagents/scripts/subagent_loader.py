"""
Subagent 配置热加载器 —— 对标 mcp_tool.py 的动态加载模式。

每次调用 load_subagents() 都会通过 importlib 重新加载
subagents_config.py 模块，确保配置修改后无需重启即可生效。
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

from backend.config.logger import get_logger

logger = get_logger(__name__)

# subagents_config.py 的绝对路径
_CONFIG_PATH = Path(__file__).parent / "subagents_config.py"

_MODULE_NAME = "subagents_config"


async def load_subagents() -> list[dict[str, Any]]:
    """动态加载 subagents_config.py 并返回其中定义的 subagents 列表。

    每次调用都会移除已缓存的模块并重新加载，以支持配置热更新。
    加载失败时返回空列表，不影响主 agent 正常运行。

    对标 mcp_tool() 的设计：
    - 配置与加载器分离
    - 单个条目失败不影响整体
    - 热重载零停机
    """
    # 移除已缓存的模块，强制重新加载
    if _MODULE_NAME in sys.modules:
        del sys.modules[_MODULE_NAME]

    try:
        spec = importlib.util.spec_from_file_location(_MODULE_NAME, _CONFIG_PATH)
        if spec is None or spec.loader is None:
            logger.warning("无法加载 subagents_config.py，返回空列表")
            return []

        module = importlib.util.module_from_spec(spec)
        sys.modules[_MODULE_NAME] = module
        spec.loader.exec_module(module)

        subagents = getattr(module, "subagents", [])
        names = [s.get("name", "?") for s in subagents]
        logger.info("Subagent 配置加载完成，共 %d 个: %s", len(subagents), names)
        return subagents

    except Exception as e:
        logger.warning("Subagent 配置加载失败: %s，返回空列表", e)
        return []

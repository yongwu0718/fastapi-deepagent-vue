# memory_tools.py
from typing import Any
from langchain.tools import tool, ToolRuntime

@tool
async def get_memory_info(memory_key: str, runtime:ToolRuntime) -> str:
    """获取持久化记忆信息（异步版本）

    Args:
        memory_key: 记忆键
    Returns:
        记忆值
    """
    store = runtime.store
    item = await store.aget(("users",), memory_key)   # 异步获取
    return str(item.value) if item else "Unknown user"


@tool
async def save_memory_info(memory_key: str, memory_value: dict[str, Any], runtime:ToolRuntime) -> str:
    """保存持久化记忆信息（异步版本）

    Args:
        memory_key: 记忆键
        memory_value: 要保存的字典值
    Returns:
        保存确认信息
    """
    store = runtime.store
    await store.aput(("users",), memory_key, memory_value)  # 异步写入
    return f"Successfully saved memory info: {memory_key}"

@tool
async def search_memory(
    query: str,
    runtime: ToolRuntime,      # 没有默认值，放在前面
    limit: int = 3,            # 有默认值，放在后面
) -> str:
    """使用向量相似度搜索记忆（需要 store 配置了 index）

    Args:
        query: 搜索文本
        runtime: 运行时上下文（自动注入）
        limit: 返回的最大结果数
    Returns:
        搜索结果，格式为 'key: value (score: 0.xx)'
    """
    store = runtime.store
    results = await store.asearch(("users",), query=query, limit=limit)
    if not results:
        return "No matching memories found."
    lines = []
    for item in results:
        lines.append(f"{item.key}: {item.value} (score: {item.score:.3f})")
    return "\n".join(lines)
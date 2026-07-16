import asyncio
import sys
from pathlib import Path

# 将 agent 目录加入 sys.path，确保能导入同级模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph_compile import init_graph


async def list_input_checkpoints(
    thread_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """获取对话线程中所有 input 检查点列表。

    每次用户发送消息时 LangGraph 自动生成 input 检查点。
    可从中选择检查点进行 replay / fork 操作。

    Args:
        thread_id: 会话线程 ID
        limit: 每页数量
        offset: 偏移量

    Returns:
        [{"checkpoint_id": str, "input_preview": str | None, "parent_checkpoint_id": str | None}, .]
    """
    config = {"configurable": {"thread_id": thread_id}}

    async with init_graph() as graph:
        # 用 async for 收集所有历史快照
        snapshots = []
        async for snapshot in graph.aget_state_history(config):
            snapshots.append(snapshot)

        # 找到 input 检查点
        input_snapshots = [
            s for s in snapshots
            if s.metadata.get("source") == "input"
        ]

        # 分页
        total = len(input_snapshots)
        page = input_snapshots[offset : offset + limit]

        checkpoints = []
        for snapshot in page:
            cid = snapshot.config["configurable"]["checkpoint_id"]
            cns = snapshot.config["configurable"].get("checkpoint_ns", "")
            parent_cid = None
            if snapshot.parent_config:
                parent_cid = snapshot.parent_config["configurable"].get("checkpoint_id")

            # 提取用户输入内容（和 API service 保持一致）
            input_preview = _extract_input_preview(snapshot)

            checkpoints.append({
                "checkpoint_id": cid,
                "checkpoint_ns": cns,
                "parent_checkpoint_id": parent_cid,
                "input_preview": input_preview,
            })

        print(f"共 {total} 个 input 检查点，当前页 {offset}-{offset + len(page)}")
        return checkpoints


def _extract_input_preview(snapshot) -> str | None:
    """从快照中提取最后一条用户输入内容（截取前 80 字符）"""
    if not snapshot.tasks:
        return None

    task = snapshot.tasks[0]
    result = task.result
    if not result or "messages" not in result:
        return None

    messages = result["messages"]
    label = ""
    for m in reversed(messages):
        msg_type = None
        if isinstance(m, dict):
            msg_type = m.get("type")
            if msg_type == "human":
                content = m.get("content", "")
                if isinstance(content, list):
                    label = ", ".join(str(c) for c in content if c)
                else:
                    label = str(content) if content else ""
                break
        elif hasattr(m, "type"):
            msg_type = m.type
            if msg_type == "human":
                label = getattr(m, "content", "")
                break

    return label[:80] if label else None


if __name__ == "__main__":
    # 使用示例：传入 thread_id 即可
    asyncio.run(list_input_checkpoints(
        thread_id="b3d363f7-8277-443b-b204-59a57b231301",
    ))

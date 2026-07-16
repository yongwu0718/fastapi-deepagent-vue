import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# 将 agent 目录加入 sys.path，确保能导入同级模块
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiofiles
from graph_compile import init_graph


# ---------- 参考脚本中的序列化函数 ----------
def serialize_message(msg) -> List:
    """将单条消息序列化为 [类名, 属性字典] 格式"""
    class_name = type(msg).__name__

    if hasattr(msg, "dict"):
        data = msg.dict()
    else:
        data = {
            "content": getattr(msg, "content", None),
        }
        for attr in [
            "additional_kwargs",
            "response_metadata",
            "id",
            "tool_calls",
            "invalid_tool_calls",
            "usage_metadata",
            "name",
            "tool_call_id",
        ]:
            if hasattr(msg, attr):
                data[attr] = getattr(msg, attr)

    # 添加 type 字段（优先使用消息自带的 type，否则用类名小写）
    data["type"] = msg.type if hasattr(msg, "type") else class_name.lower()

    return [class_name, data]


def snapshot_to_dict(snapshot) -> dict:
    """将 StateSnapshot 转为可序列化的字典（完全按参考脚本格式）"""
    data = {}

    # 1. values（重点处理 messages）
    values = snapshot.values
    if isinstance(values, dict) and "messages" in values:
        serialized = dict(values)
        serialized["messages"] = [serialize_message(m) for m in values["messages"]]
        data["values"] = serialized
    else:
        data["values"] = dict(values) if hasattr(values, "items") else values

    # 2. next（转为列表）
    data["next"] = list(snapshot.next) if snapshot.next else []

    # 3. config
    config = snapshot.config
    data["config"] = dict(config) if hasattr(config, "items") else config

    # 4. metadata
    metadata = snapshot.metadata
    data["metadata"] = dict(metadata) if hasattr(metadata, "items") else metadata

    # 5. created_at（datetime → ISO 格式字符串）
    created_at = snapshot.created_at
    if isinstance(created_at, datetime):
        data["created_at"] = created_at.isoformat()
    else:
        data["created_at"] = str(created_at) if created_at else None

    # 6. parent_config（可能为 None）
    pc = snapshot.parent_config
    if pc is not None:
        data["parent_config"] = dict(pc) if hasattr(pc, "items") else pc
    else:
        data["parent_config"] = None

    # 7. tasks
    data["tasks"] = list(snapshot.tasks) if hasattr(snapshot, "tasks") else []

    # 8. interrupts
    data["interrupts"] = (
        list(snapshot.interrupts) if hasattr(snapshot, "interrupts") else []
    )

    return data


# ---------- 主逻辑 ----------
async def main(config: dict, limit: int = 50):
    """
    导出 LangGraph 状态历史到 state.json，完全采用参考脚本的 JSON 格式。
    """
    output_path = "state.json"
    all_snapshots = []  # 收集所有状态字典

    try:
        async with init_graph() as graph:
            async for state in graph.aget_state_history(config, limit=limit):
                # 使用参考脚本的函数转换当前状态
                snapshot_dict = snapshot_to_dict(state)
                all_snapshots.append(snapshot_dict)

        # 一次性将整个数组写入文件
        json_str = json.dumps(
            all_snapshots, indent=2, ensure_ascii=False, default=str
        )
        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(json_str)

        print(f"成功导出 {len(all_snapshots)} 条状态历史至 {output_path}")

    except Exception as e:
        print(f"处理状态历史时出错: {e}")


if __name__ == "__main__":
    sample_config = {
        "configurable": {
            "thread_id": "256d93cb-d3d9-45d4-94f3-4ed774899ed6"
        }
    }
    asyncio.run(main(config=sample_config, limit=50))
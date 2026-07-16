import json
import aiofiles
from datetime import datetime
from typing import List
from config.logger import get_logger

logger = get_logger(__name__)


def serialize_message(msg) -> List:
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

    data["type"] = msg.type if hasattr(msg, "type") else class_name.lower()

    return [class_name, data]


def snapshot_to_dict(snapshot) -> dict:
    data = {}

    values = snapshot.values
    if isinstance(values, dict) and "messages" in values:
        serialized = dict(values)
        serialized["messages"] = [serialize_message(m) for m in values["messages"]]
        data["values"] = serialized
    else:
        data["values"] = dict(values) if hasattr(values, "items") else values

    data["next"] = list(snapshot.next) if snapshot.next else []

    config = snapshot.config
    data["config"] = dict(config) if hasattr(config, "items") else config

    metadata = snapshot.metadata
    data["metadata"] = dict(metadata) if hasattr(metadata, "items") else metadata

    created_at = snapshot.created_at
    if isinstance(created_at, datetime):
        data["created_at"] = created_at.isoformat()
    else:
        data["created_at"] = str(created_at) if created_at else None

    pc = snapshot.parent_config
    if pc is not None:
        data["parent_config"] = dict(pc) if hasattr(pc, "items") else pc
    else:
        data["parent_config"] = None

    data["tasks"] = list(snapshot.tasks) if hasattr(snapshot, "tasks") else []

    data["interrupts"] = (
        list(snapshot.interrupts) if hasattr(snapshot, "interrupts") else []
    )

    return data


async def save_snapshot_to_json(snapshot, filepath: str):
    logger.debug("保存快照 | path=%s", filepath)
    data = snapshot_to_dict(snapshot)
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    logger.info("快照已保存 | path=%s", filepath)
    print(f"Snapshot saved to {filepath}")
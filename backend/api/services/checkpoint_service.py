"""检查点业务逻辑 —— 输入检查点列表 / 重放 / 分叉。"""
from typing import Dict, List, Optional

from backend.api.schemas.checkpoint import CheckpointSummary, CheckpointHistoryResponse
from backend.api.services.graph import get_graph
from backend.api.utils.exceptions import NotFoundException, ErrorCode
from backend.api.utils.stream import _sse_stream
from backend.config.logger import get_logger

logger = get_logger(__name__)

def _compute_leaf_for_inputs(
    input_snapshots: List[object],
    all_snapshots: List[object],
) -> Dict[str, Optional[str]]:
    """为每个 input 检查点计算其叶子检查点 ID。
    
    Returns:
        {input_checkpoint_id: leaf_checkpoint_id}
    """
    # 建立完整的 cid → snapshot 映射（包含所有快照，不只是 input/fork）
    cid_to_snapshot: Dict[str, object] = {}
    for snap in all_snapshots:
        try:
            cid = snap.config["configurable"]["checkpoint_id"]
            cid_to_snapshot[cid] = snap
        except (KeyError, TypeError):
            continue
    
    # 为孩子→父亲建立索引
    child_to_parent: Dict[str, str] = {}
    for cid, snap in cid_to_snapshot.items():
        parent_cid: Optional[str] = None
        if snap.parent_config:
            parent_conf = snap.parent_config.get("configurable", {})
            parent_cid = parent_conf.get("checkpoint_id")
        if parent_cid and parent_cid in cid_to_snapshot:
            child_to_parent[cid] = parent_cid
    
    result: Dict[str, Optional[str]] = {}
    for snap in input_snapshots:
        try:
            input_cid = snap.config["configurable"]["checkpoint_id"]
        except (KeyError, TypeError):
            continue
        
        # 找该 input 之后、next=[] 的叶子节点
        leaf = input_cid
        current = input_cid
        visited = set()
        while current in cid_to_snapshot and current not in visited:
            visited.add(current)
            current_snap = cid_to_snapshot[current]
            # 找下一跳：parent_config 指向 current 的子节点
            children = [c for c, p in child_to_parent.items() if p == current]
            if not children:
                # 无子节点，当前就是叶子
                break
            # 有子节点 → 继续沿链走
            current = children[0]  # 优先走第一条子链
        leaf = current
        
        result[input_cid] = leaf if leaf != input_cid else input_cid
    
    return result


async def list_input_checkpoints(thread_id: str, limit: int = 50, offset: int = 0) -> CheckpointHistoryResponse:
    
    logger.info("获取输入检查点列表 | thread_id=%s | limit=%d | offset=%d", thread_id, limit, offset)
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    snapshots = []
    async for snapshot in graph.aget_state_history(config):
        snapshots.append(snapshot)

    # 筛选 source == "input" 或 "fork" 的检查点
    # - input: user 消息检查点（retry/fork 起点 / 分支切换目标）
    # - fork: 分支起点（重试用，parent_checkpoint_id 指向分叉前的 input 节点）
    # - loop: 中间步骤，过滤掉
    filtered = [
        s for s in snapshots
        if s.metadata.get("source") in ("input", "fork")
    ]

    # 计算每个 input 检查点的叶子节点
    leaf_map = _compute_leaf_for_inputs(filtered, snapshots)

    total = len(filtered)
    page = filtered[offset : offset + limit]

    checkpoints: List[CheckpointSummary] = []
    for snapshot in page:
        cid = snapshot.config["configurable"]["checkpoint_id"]
        checkpoint_ns = snapshot.config["configurable"]["checkpoint_ns"]

        # 提取 parent_checkpoint_id
        parent_cid: Optional[str] = None
        if snapshot.parent_config:
            parent_conf = snapshot.parent_config.get("configurable", {})
            parent_cid = parent_conf.get("checkpoint_id")

        # 提取 source（input / loop / fork）
        source = snapshot.metadata.get("source", "")

        # 提取叶子检查点 ID
        leaf_cid = leaf_map.get(cid)

        # 提取用户输入内容预览 + 触发消息 ID
        label = ""
        trigger_msg_id: Optional[str] = None
        if snapshot.tasks:
            task = snapshot.tasks[0]
            result = task.result
            if result and "messages" in result:
                raw_messages = result["messages"]
                for m in reversed(raw_messages):
                    if isinstance(m, dict):
                        msg_content = m.get("content", "")
                        if m.get("type") == "human":
                            if isinstance(msg_content, list):
                                label = ",".join(
                                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                                    for item in msg_content
                                )
                            else:
                                label = str(msg_content)
                            trigger_msg_id = m.get("id")
                            break
                    elif hasattr(m, "content") and getattr(m, "type", None) == "human":
                        label = str(m.content)
                        trigger_msg_id = getattr(m, "id", None)
                        break

        checkpoints.append(CheckpointSummary(
            config=snapshot.config,
            next_nodes=snapshot.next or [],
            input_preview=label[:80] if label else None,
            parent_checkpoint_id=parent_cid,
            source=source,
            leaf_checkpoint_id=leaf_cid,
            trigger_message_id=trigger_msg_id,
        ))

    logger.info("输入检查点列表获取完成 | thread_id=%s | total=%d | returned=%d", thread_id, total, len(checkpoints))
    return CheckpointHistoryResponse(
        thread_id=thread_id,
        checkpoints=checkpoints,
    )


async def _check_checkpoint_exists(thread_id: str, checkpoint_id: str) -> None:
    """校验检查点是否存在，不存在则抛出 NotFoundException。"""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}
    state = await graph.aget_state(config)
    if state is None or state.values is None:
        raise NotFoundException(
            error_code=ErrorCode.CHECKPOINT_NOT_FOUND,
            detail=f"检查点不存在: thread_id={thread_id}, checkpoint_id={checkpoint_id}",
        )


async def replay_from_checkpoint(
    thread_id: str,
    checkpoint_id: str,
    checkpoint_ns: str = "",
    messages: Optional[List[dict]] = None,
):
    """从指定检查点重放执行 —— 返回 SSE 流。

    从该检查点重新执行后续节点：
    - 检查点之前的节点不重新执行（结果已缓存）
    - 遇到中断时仍会触发，前端通过 SSE interrupt 事件接收
    - 传入 messages 时作为新用户输入，触发模型重新生成
    """
    logger.info("重放检查点 | thread_id=%s | checkpoint_id=%s | ns=%s | has_messages=%s",
                thread_id, checkpoint_id, checkpoint_ns, messages is not None)
    await _check_checkpoint_exists(thread_id, checkpoint_id)
    graph = get_graph()
    input_data = {"messages": messages} if messages else None
    return _sse_stream(
        graph,
        input_data,
        thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )


async def fork_from_checkpoint(
    thread_id: str,
    checkpoint_id: str,
    checkpoint_ns: str = "",
    values: dict = None,
):
    """从指定检查点分叉执行 —— 返回 SSE 流。

    在历史检查点基础上传入新的 state 值（如 messages），创建新分支继续执行。
    原始执行链完整保留，新分支独立发展。

    values 示例：{"messages": [{"role": "user", "content": "hello"}]}
    空 dict 或 None 等同于纯重放。
    """
    logger.info("分叉检查点 | thread_id=%s | checkpoint_id=%s | ns=%s", thread_id, checkpoint_id, checkpoint_ns)
    await _check_checkpoint_exists(thread_id, checkpoint_id)
    graph = get_graph()

    input_data = values if values else None
    return _sse_stream(
        graph,
        input_data,
        thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )
"""检查点 & 时间旅行模型 —— 时间线侧边栏 / 重放 / 分叉。"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from backend.api.schemas.response import MessageResponse

# ── 中断子模型 ──────────────────────────────────────────────

class CheckpointInterrupt(BaseModel):
    """检查点中的结构化中断数据。

    对应用 LangGraph state 中的中断内容。
    前端据此渲染审批 / 编辑 UI，无需从字符串二次解析。
    """
    action_requests: List[dict] = Field(
        default_factory=list,
        description="待审批的工具调用列表，每项 {name, args}",
    )
    review_configs: List[dict] = Field(
        default_factory=list,
        description="审批配置，每项 {action_name, allowed_decisions: [approve|reject|edit]}",
    )
    interrupt_id: Optional[str] = Field(
        default=None, description="中断唯一标识（LangGraph interrupt id）"
    )


class SubgraphState(BaseModel):
    """子图检查点 —— 用于子图内部节点间的时间旅行。

    通过 parent_state = graph.get_state(config, subgraphs=True)
    获取后，前端可用此 config 在子图特定检查点上进行 replay/fork。
    """
    config: dict = Field(
        default_factory=dict,
        description="子图检查点的完整 config，可直接传给 replay/fork 端点",
    )
    next_nodes: List[str] = Field(
        default_factory=list, description="子图待执行节点"
    )
    interrupts: List[CheckpointInterrupt] = Field(
        default_factory=list, description="子图中断数据"
    )


# ── 确定检查点 ────────────────────────────────────────────

class CheckpointSummary(BaseModel):
    """检查点摘要 — 时间线侧边栏中的每个条目。

    parent_checkpoint_id 来自 LangGraph state.parent_config，
    表示线性执行链中的前一个检查点。同 parent 的子节点为兄弟分支。
    """
    config: dict = Field(
        default_factory=dict,
        description="完整 config {configurable: {thread_id, checkpoint_id, checkpoint_ns}}，可直接用于 replay/fork",
    )
    next_nodes: List[str] = Field(
        default_factory=list,
        description="接下来将执行的节点列表（为空表示已完成）",
    )
    input_preview: Optional[str] = Field(
        default=None,
        description="用户输入内容的前 80 字预览",
    )
    parent_checkpoint_id: Optional[str] = Field(
        default=None,
        description="父检查点 ID（根节点为 None）。前端按此字段分组得到兄弟分支",
    )
    source: str = Field(
        default="",
        description="检查点来源：input / loop / fork。前端据此标注 原始/重试/分支",
    )
    leaf_checkpoint_id: Optional[str] = Field(
        default=None,
        description="该 input 所在分支的叶子检查点 ID，用于分支切换时加载完整历史。None 表示尚未计算或分支未完成。",
    )
    trigger_message_id: Optional[str] = Field(
        default=None,
        description="触发此检查点的用户消息 ID（LangChain message.id），用于前端刷新后权威绑定消息与检查点。None 表示无用户消息（如 resume 产生的检查点）。",
    )


class CheckpointHistoryResponse(BaseModel):
    """检查点历史列表（支持分页）"""
    thread_id: str
    checkpoints: List[CheckpointSummary]


# ── 检查点详情面板 ──────────────────────────────────────────

class CheckpointDetail(BaseModel):
    """单个检查点的完整信息（inspector 面板）。

    与 CheckpointSummary 的区别：携带完整 state values、messages、interrupts 详情。
    """
    checkpoint_id: str
    checkpoint_ns: str = ""
    parent_checkpoint_id: Optional[str] = Field(
        default=None,
        description="线性链中的前一个检查点 ID",
    )
    config: dict = Field(
        default_factory=dict,
        description="完整 config，可直接用于 graph.invoke / graph.update_state",
    )
    next_nodes: List[str] = Field(
        default_factory=list,
        description="待执行节点列表",
    )
    tasks: List[dict] = Field(
        default_factory=list,
        description="任务执行信息",
    )
    interrupts: List[CheckpointInterrupt] = Field(
        default_factory=list,
        description="结构化中断数据（含 action_requests + review_configs）",
    )
    messages: List[MessageResponse] = Field(
        default_factory=list,
        description="当前检查点处的消息快照（精简展示用）",
    )
    values: dict = Field(
        default_factory=dict,
        description="完整 state values 字典（含 messages 及自定义字段原始数据）",
    )
    subgraphs: List[SubgraphState] = Field(
        default_factory=list,
        description="子图检查点列表（仅当子图启用独立 checkpointer 时非空）",
    )


# ── 重放 ────────────────────────────────────────────────────

class ReplayRequest(BaseModel):
    """重放请求 — 从指定检查点恢复执行。

    后端调用 graph.invoke(None, config) 从该检查点重新执行后续节点：
    - 检查点之前的节点：不重新执行（结果已缓存）
    - 检查点之后的节点：重新执行（LLM / API / 中断会再次触发，结果可能不同）
    - 从最终检查点（next 为空）重放：无操作
    - 提供 messages 时：注入用户消息作为新输入，触发模型重新生成
    """
    thread_id: str = Field(..., description="对话线程 ID")
    checkpoint_id: str = Field(..., description="目标检查点 ID")
    checkpoint_ns: str = Field(default="", description="检查点命名空间（子图场景）")
    messages: Optional[List[dict]] = Field(
        default=None,
        description="要注入的用户消息列表，格式 [{'role':'user','content':'.'}]",
    )
    stream: bool = Field(
        default=True,
        description="True 时通过 SSE (text/event-stream) 流式返回",
    )


# ── 分支出 ───────────────────────────────────────────────────

class ForkRequest(BaseModel):
    """分支出请求 — 从检查点分叉，可同时修改状态后继续执行。

    后端先调用 graph.update_state(config, values={.}) 创建新分支检查点，
    再调用 graph.invoke(None, fork_config) 继续执行。

    关键语义：
    - update_state 不修改原线程历史；原始执行链完整保留
    - 新分支从指定检查点独立发展，前端应展示为对话树
    - values 可传入任意 state 字段（如 messages、自定义字段），通过对应 reducer 应用
    - 遇到中断时总是重新触发
    - as_node 在并行分支 / 跳过节点 / 新线程场景下显式指定
    """
    thread_id: str = Field(..., description="对话线程 ID")
    checkpoint_id: str = Field(..., description="分支出起点检查点 ID")
    checkpoint_ns: str = Field(default="", description="检查点命名空间（子图场景）")
    values: dict = Field(
        default_factory=dict,
        description=(
            "要修改的 state 字段。如 {'messages': [.]} 或 {'topic': 'new'}。"
            "空 dict 表示仅创建分支引用"
        ),
    )
    as_node: Optional[str] = Field(
        default=None,
        description="显式指定产生此更新的节点名（并行分支 / 跳过节点 / 新线程场景）",
    )
    stream: bool = Field(
        default=True,
        description="True 时通过 SSE 流式返回",
    )


# ── 消息元数据（分支出导航） ─────────────────────────────────

class MessageMetadataItem(BaseModel):
    """单条消息的元数据 —— 包含重新生成/编辑所需的分支出起点检查点。

    对应前端 Branching chat 中的 getMessagesMetadata()：
      - fork_checkpoint_id：编辑或重新生成时作为分支出目标的检查点
        （即该消息被处理之前的快照，从该处 fork 即可重新生成此消息）
      - checkpoint_ns：命名空间（子图场景）
    """
    message_index: int
    role: str
    content: str = ""
    fork_checkpoint_id: Optional[str] = Field(
        default=None,
        description="编辑此消息时的分支出目标检查点（消息被处理前的快照）",
    )
    checkpoint_ns: str = ""


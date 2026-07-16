import asyncio
import json
from typing import Any, Dict, List, Optional
from langgraph.types import Command
from langchain_core.messages import AIMessageChunk

# ---------- 获取用户决策函数 ----------
async def get_user_decision(action_requests: List[Dict], review_configs: List[Dict]) -> List[Dict]:
    config_map = {cfg["action_name"]: cfg for cfg in review_configs}

    print("\n🤔 需要您的审批：")
    for i, action in enumerate(action_requests):
        review_config = config_map[action["name"]]
        print(f"  [{i+1}] 工具: {action['name']}")
        print(f"      参数: {action['args']}")
        print(f"      允许的决策: {review_config['allowed_decisions']}")

    decisions = []
    for action in action_requests:
        review_config = config_map[action["name"]]
        allowed = review_config["allowed_decisions"]

        print(f"\n工具 {action['name']} 的决策：")
        for i, opt in enumerate(allowed):
            print(f"  {i+1}. {opt}")
        choice = (await asyncio.to_thread(input, "请选择序号: ")).strip()
        try:
            idx = int(choice) - 1
            decision_type = allowed[idx]
        except (ValueError, IndexError):
            print("无效选择，默认拒绝。")
            decision_type = "reject"

        if decision_type == "edit":
            new_args = (await asyncio.to_thread(input, "请输入新的参数 (JSON 格式): ")).strip()
            try:
                edited_args = json.loads(new_args)
            except json.JSONDecodeError:
                edited_args = action["args"]
            decisions.append({
                "type": "edit",
                "edited_action": {
                    "name": action["name"],
                    "args": edited_args
                }
            })
        else:
            decisions.append({"type": decision_type})

    return decisions

# ---------- 流处理类 ----------
class StreamProcessor:
    # ---------- 处理消息块函数 ----------
    @staticmethod
    def _handle_message_chunk(chunk: Dict, last_type: Optional[str], ns: tuple = ()) -> Optional[str]:
        token, metadata = chunk["data"]
        current_last_type = last_type

        is_subagent = len(ns) > 0
        source_label = "subagent" if is_subagent else "main"

        if isinstance(token, AIMessageChunk):
            reasoning_text = token.additional_kwargs.get("reasoning_content", "")
            if reasoning_text:
                if current_last_type != "reasoning":
                    print(f"\n[{source_label}] reasoning: ", end="")
                    current_last_type = "reasoning"
                print(f"\033[90m{reasoning_text}\033[0m", end="", flush=True)

            blocks = getattr(token, "content_blocks", None)
            if blocks:
                for block in blocks:
                    block_type = block.get("type")

                    if block_type == "text":
                        if current_last_type != "text":
                            print(f"\n[{source_label}] ai: ", end="")
                            current_last_type = "text"
                        print(block.get("text", ""), end="", flush=True)

                    elif block_type in ("tool_use", "tool_call"):
                        if current_last_type != "tool":
                            print(f"\n[{source_label}] 🔧 tool call: ", end="")
                            current_last_type = "tool"
                        tool_name = block.get("name") or block.get("tool_name", "unknown")
                        print(f"{tool_name} ", end="")
                        args = block.get("args") or block.get("input", {})
                        if args:
                            print(args, end="", flush=True)
                        print("\n---")
            else:
                if token.content:
                    if current_last_type != "text":
                        print(f"\n[{source_label}] ai: ", end="")
                        current_last_type = "text"
                    print(token.content, end="", flush=True)
        else:
            if token.content:
                if current_last_type != "tool_result":
                    print(f"\n[{source_label}] tool: ", end="")
                    current_last_type = "tool_result"
                print(token.content, end="", flush=True)

        return current_last_type

    # ---------- 处理更新块函数 ----------
    @staticmethod
    async def _handle_updates_chunk(chunk: Dict, config: Dict, ns: tuple = ()) -> Optional[Command]:
        is_subagent = len(ns) > 0
        source_label = "subagent" if is_subagent else "main"
        data = chunk["data"]

        for node_name, node_data in data.items():
            print(f"\n[{source_label}] next node: {node_name}")

        if "__interrupt__" not in data:
            return None

        interrupt_value = data["__interrupt__"][0].value
        action_requests = interrupt_value["action_requests"]
        review_configs = interrupt_value["review_configs"]

        decisions = await get_user_decision(action_requests, review_configs)
        return Command(resume={"decisions": decisions})

     # ---------- 处理检查点块函数 ----------

    @staticmethod
    def _handle_checkpoint_chunk(chunk: Dict, ns: tuple = ()):
        """提取 source=='input' 检查点的 checkpoint_id 和 parent_checkpoint_id。
        
        source='input' 的检查点是 replay/fork 的正确起点：
        - messages 为空是正常的（LangGraph 在 __start__ 才注入 HumanMessage）
        - replay 时会从 __start__ 节点重新执行，正确恢复用户输入
        """
        if chunk["type"] == "checkpoints":
            data = chunk["data"]
            metadata = data.get("metadata", {})
            if metadata.get("source") == "input":
                config = data.get("config", {}) or {}
                configurable = config.get("configurable", {})
                parent_config = data.get("parent_config") or {}
                parent_conf = parent_config.get("configurable", {})
                return {
                    "checkpoint_id": configurable.get("checkpoint_id", ""),
                    "parent_checkpoint_id": parent_conf.get("checkpoint_id"),
                }
        return None
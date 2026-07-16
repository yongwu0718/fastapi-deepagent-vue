from langchain.tools import tool
from langgraph.types import interrupt

@tool
def add(a: int, b: int) -> str:
    """Add two numbers together.
    Args:
        a: The first number to add.
        b: The second number to add.
    Returns:
        The sum of a and b.
    """
    logger.info("工具 add 被调用 | a=%d | b=%d", a, b)
    # 暂停执行，提交审批请求给用户
    # interrupt 负载必须包含 action_requests 和 review_configs
    response = interrupt({
        "action_requests": [
            {
                "name": "add",
                "args": {"a": a, "b": b}
            }
        ],
        "review_configs": [
            {
                "action_name": "add",
                "allowed_decisions": ["approve", "reject", "edit"]
            }
        ]
    })

    # resume 后 response 格式: {"decisions": [{"type": "approve|reject|edit", .}]}
    decisions = response["decisions"]
    decision = decisions[0]
    logger.info("工具 add 审批结果 | decision=%s", decision.get("type"))

    if decision["type"] == "reject":
        logger.info("工具 add 被用户拒绝")
        return "用户取消了计算"

    if decision["type"] == "edit":
        edited = decision.get("edited_action", {})
        a = edited.get("args", {}).get("a", a)
        b = edited.get("args", {}).get("b", b)
        logger.info("工具 add 参数被编辑 | a=%d | b=%d", a, b)

    result = str(a + b)
    logger.info("工具 add 完成 | result=%s", result)
    return result

@tool
def sub(a: int, b: int) -> str:
    """Subtract two numbers.
    Args:
        a: The first number to subtract.
        b: The second number to subtract.
    Returns:
        The difference of a and b.
    """
    logger.info("工具 sub 被调用 | a=%d | b=%d", a, b)
    result = str(a - b)
    logger.info("工具 sub 完成 | result=%s", result)
    return result
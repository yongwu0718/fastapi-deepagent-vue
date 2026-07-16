"""
模型动态切换中间件

功能：
1. 主动选择：根据 context 中用户指定的模型进行切换（无需重新构建 agent）
2. 被动故障转移：当主模型 API 掉线/超时时，自动降级到备用模型
3. 同模型重试：瞬时错误（如网络抖动）先在当前模型上重试，仍失败再切备用
"""

from dataclasses import dataclass, field
from collections.abc import Callable

from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.chat_models import BaseChatModel

from backend.core.models.model_factory import llm_deepseek, llm_ali,llm_ollama
from backend.config.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Context 类 —— 用户在调用时传入，不需要中间件之外的额外配置
# =============================================================================
@dataclass
class ModelContext:
    """用户可通过 invoke 时传入的上下文，指定要使用的模型名称。

    字段说明：
        model: 模型标识符字符串，如 "deepseek" / "ali" / "moonshot" / "ollama"
               留空时使用默认模型（llm_deepseek）
    """
    model: str = ""


# =============================================================================
# 模型注册表 —— 名称到实例的映射
# =============================================================================
MODEL_MAP: dict[str, BaseChatModel] = {
    "deepseek": llm_deepseek,
    "ali": llm_ali,
    "ollama": llm_ollama,
}

# 故障转移优先级链：按顺序尝试，ollama 本地模型作为最终兜底
FALLBACK_CHAIN: list[str] = ["deepseek", "ali", "ollama"]

# 同模型最大重试次数（瞬时错误先行重试，不立即切换模型）
MAX_RETRIES_PER_MODEL: int = 2


# =============================================================================
# 辅助函数
# =============================================================================
def _resolve_model(request: ModelRequest) -> tuple[str, BaseChatModel]:
    """根据 context 或默认值解析应该使用的模型。

    返回 (model_name, model_instance)
    """
    context = request.runtime.context
    model_name = getattr(context, "model", "") or "deepseek"
    if model_name not in MODEL_MAP:
        logger.warning("未知模型名称 '%s'，回退到 deepseek", model_name)
        model_name = "deepseek"
    return model_name, MODEL_MAP[model_name]


def _build_fallback_sequence(start_model: str) -> list[str]:
    """构建故障转移序列：从当前模型开始，按 FALLBACK_CHAIN 顺序排列后面的模型。"""
    if start_model not in FALLBACK_CHAIN:
        return [start_model] + FALLBACK_CHAIN
    idx = FALLBACK_CHAIN.index(start_model)
    return FALLBACK_CHAIN[idx:]  # 从当前开始的剩余链


# =============================================================================
# 中间件入口
# =============================================================================
@wrap_model_call
async def dynamic_model_switcher(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """模型动态切换中间件。

    执行逻辑：
      1. 从 request.runtime.context 中读取用户指定的模型名称
      2. 尝试用选中的模型调用 LLM
      3. 若失败，在同一个模型上重试 MAX_RETRIES_PER_MODEL 次（应对瞬时网络抖动）
      4. 若仍失败，按 FALLBACK_CHAIN 切换到下一个备用模型，从步骤 2 重新开始
      5. 所有模型都失败后，重新抛出最后一个异常
    """
    # 第一步：解析用户指定的模型
    current_name, current_model = _resolve_model(request)
    fallback_sequence = _build_fallback_sequence(current_name)
    logger.info("模型切换中间件启动 | 起始模型=%s | 故障转移链=%s", current_name, fallback_sequence)

    last_exception: Exception | None = None

    # 第二步：遍历故障转移链
    for model_name in fallback_sequence:
        model = MODEL_MAP[model_name]

        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
            try:
                # 用当前模型发出请求
                modified_request = request.override(model=model)
                result = await handler(modified_request)

                if model_name != current_name:
                    logger.warning("模型已从 '%s' 切换到 '%s'（故障转移生效）", current_name, model_name)
                return result

            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "模型 '%s' 第 %d/%d 次调用失败: %s",
                    model_name, attempt, MAX_RETRIES_PER_MODEL, exc,
                )
                # 同模型重试次数未用完：继续用同一模型重试
                if attempt < MAX_RETRIES_PER_MODEL:
                    continue
                # 重试已耗尽：跳出内层循环，进入下一个备用模型
                break

        logger.error("模型 '%s' 所有重试均已失败，切换到下一个备用模型", model_name)

    # 所有模型全部失败
    logger.critical("所有模型均已不可用，故障转移链耗尽")
    raise last_exception  # type: ignore[misc]

logger.info("模型动态切换中间件已就绪")

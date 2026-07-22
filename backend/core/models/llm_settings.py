import os
import yaml
from backend.config.env_settings import MODEL_CONFIG_PATH

_config: dict = {}
_SENTINEL = object()


def _load_yaml_config() -> dict:
    """读取 model_config.yaml 并返回解析后的字典。"""
    with open(MODEL_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _env_or_yaml(env_key: str, *yaml_path: str, default=None):
    """优先读取环境变量，未设置时回退到 YAML 配置值"""
    env_val = os.getenv(env_key)
    if env_val is not None:
        return env_val
    val = _config
    for key in yaml_path:
        if not isinstance(val, dict):
            return default
        val = val.get(key, _SENTINEL)
        if val is _SENTINEL:
            return default
    return val


def reload_model_config():
    """重新加载 model_config.yaml 并更新所有模块级配置变量。"""
    global _config
    global LLM_ACTIVE_PROVIDER
    global LLM_DEEPSEEK_BASE_URL, LLM_JSON_MODEL, LLM_DEEPSEEK_MODEL
    global LLM_DEEPSEEK_REASONING_EFFORT, LLM_DEEPSEEK_EXTRA_BODY, LLM_DEEPSEEK_JSON_KWARGS
    global LLM_OLLAMA_BASE_URL, LLM_OLLAMA_MODEL, LLM_OLLAMA_REASONING
    global LLM_ALI_BASE_URL, LLM_ALI_MODEL, LLM_ALI_ENABLE_THINKING
    global LLM_OPENAI_BASE_URL, LLM_OPENAI_MODEL, LLM_OPENAI_EXTRA_BODY
    global EMBEDDING_MODEL, EMBEDDING_BASE_URL
    global RERANK_MODEL, RERANK_TOP_N

    _config = _load_yaml_config()

    LLM_ACTIVE_PROVIDER = _env_or_yaml("LLM_ACTIVE_PROVIDER", "active_provider", default="deepseek")

    LLM_DEEPSEEK_BASE_URL = _env_or_yaml("LLM_DEEPSEEK_BASE_URL", "deepseek", "base_url")
    LLM_JSON_MODEL = _env_or_yaml("LLM_JSON_MODEL", "deepseek", "json_model")
    LLM_DEEPSEEK_MODEL = _env_or_yaml("LLM_DEEPSEEK_MODEL", "deepseek", "model")
    LLM_DEEPSEEK_REASONING_EFFORT = _env_or_yaml("LLM_DEEPSEEK_REASONING_EFFORT", "deepseek", "reasoning_effort")
    LLM_DEEPSEEK_EXTRA_BODY = _env_or_yaml("LLM_DEEPSEEK_EXTRA_BODY", "deepseek", "extra_body")
    LLM_DEEPSEEK_JSON_KWARGS = _env_or_yaml("LLM_DEEPSEEK_JSON_KWARGS", "deepseek", "json_kwargs")

    LLM_OLLAMA_BASE_URL = _env_or_yaml("LLM_OLLAMA_BASE_URL", "ollama", "base_url")
    LLM_OLLAMA_MODEL = _env_or_yaml("LLM_OLLAMA_MODEL", "ollama", "model")
    LLM_OLLAMA_REASONING = _env_or_yaml("LLM_OLLAMA_REASONING", "ollama", "reasoning")

    LLM_ALI_BASE_URL = _env_or_yaml("LLM_ALI_BASE_URL", "aliyun", "base_url")
    LLM_ALI_MODEL = _env_or_yaml("LLM_ALI_MODEL", "aliyun", "model")
    LLM_ALI_ENABLE_THINKING = _env_or_yaml("LLM_ALI_ENABLE_THINKING", "aliyun", "enable_thinking")

    LLM_OPENAI_BASE_URL = _env_or_yaml("LLM_OPENAI_BASE_URL", "openai", "base_url")
    LLM_OPENAI_MODEL = _env_or_yaml("LLM_OPENAI_MODEL", "openai", "model")
    LLM_OPENAI_EXTRA_BODY = _env_or_yaml("LLM_OPENAI_EXTRA_BODY", "openai", "extra_body")

    EMBEDDING_MODEL = _env_or_yaml("EMBEDDING_MODEL", "embedding", "model")
    EMBEDDING_BASE_URL = _env_or_yaml("EMBEDDING_BASE_URL", "embedding", "base_url")

    RERANK_MODEL = _env_or_yaml("RERANK_MODEL", "reranker", "model")
    RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", _config["reranker"].get("top_n", 10)))


# 首次加载
reload_model_config()

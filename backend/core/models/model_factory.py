import os
from langchain_core.language_models import LLM
from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama
from langchain_qwq import ChatQwen
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaEmbeddings


from backend.core.models.reranker import DashScopeRerank
from backend.core.models.llm_settings import (
    LLM_DEEPSEEK_BASE_URL, LLM_JSON_MODEL, LLM_DEEPSEEK_MODEL,
    LLM_DEEPSEEK_REASONING_EFFORT, LLM_DEEPSEEK_EXTRA_BODY, LLM_DEEPSEEK_JSON_KWARGS,
    LLM_OLLAMA_BASE_URL, LLM_OLLAMA_MODEL, LLM_OLLAMA_REASONING,
    LLM_ALI_BASE_URL, LLM_ALI_MODEL, LLM_ALI_ENABLE_THINKING,
    LLM_OPENAI_BASE_URL, LLM_OPENAI_MODEL, LLM_OPENAI_EXTRA_BODY,
    EMBEDDING_MODEL, EMBEDDING_BASE_URL,
    RERANK_MODEL, RERANK_TOP_N,
)
from backend.core.models.env_api_key import LLM_ALI_API_KEY, LLM_OPENAI_API_KEY


def _reload_settings():
    """重新加载 llm_settings 模块以获取最新 YAML 配置。"""
    from backend.core.models import llm_settings as _ls
    _ls.reload_model_config()
    return _ls


# ---------- 结构化输出模型配置 ----------
llm_json = ChatDeepSeek(
    model=LLM_JSON_MODEL,
    base_url=LLM_DEEPSEEK_BASE_URL,
    reasoning_effort=LLM_DEEPSEEK_REASONING_EFFORT,
    extra_body=LLM_DEEPSEEK_EXTRA_BODY,
    model_kwargs=LLM_DEEPSEEK_JSON_KWARGS,
)

# ---------- 普通输出模型配置 ----------
llm_ollama = ChatOllama(
    model=LLM_OLLAMA_MODEL,
    base_url=LLM_OLLAMA_BASE_URL,
    reasoning=LLM_OLLAMA_REASONING,
)

llm_deepseek = ChatDeepSeek(
    model=LLM_DEEPSEEK_MODEL,
    base_url=LLM_DEEPSEEK_BASE_URL,
    reasoning_effort=LLM_DEEPSEEK_REASONING_EFFORT,
    extra_body=LLM_DEEPSEEK_EXTRA_BODY,
)

llm_ali = ChatQwen(
    model=LLM_ALI_MODEL,
    base_url=LLM_ALI_BASE_URL,
    enable_thinking=LLM_ALI_ENABLE_THINKING,
    api_key=LLM_ALI_API_KEY,
)

llm_openai = ChatOpenAI(
    model=LLM_OPENAI_MODEL,
    base_url=LLM_OPENAI_BASE_URL,
    extra_body=LLM_OPENAI_EXTRA_BODY,
    api_key=LLM_OPENAI_API_KEY,
)



# ---------- 嵌入模型配置 ----------
embeddings = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=EMBEDDING_BASE_URL,
)

# ---------- Reranker 模型配置 ----------
rerank_model = DashScopeRerank(
    model=RERANK_MODEL,
    dashscope_api_key=LLM_ALI_API_KEY,
    top_n=RERANK_TOP_N,
)


# ---------- 工厂函数（支持热重载） ----------
def create_llm_ali():
    """动态创建 Aliyun 模型（每次调用读取最新配置）。"""
    settings = _reload_settings()
    from backend.core.models.env_api_key import LLM_ALI_API_KEY as api_key
    return ChatQwen(
        model=settings.LLM_ALI_MODEL,
        base_url=settings.LLM_ALI_BASE_URL,
        enable_thinking=settings.LLM_ALI_ENABLE_THINKING,
        api_key=api_key,
    )

def create_llm_deepseek():
    """动态创建 DeepSeek 模型（每次调用读取最新配置）。"""
    settings = _reload_settings()
    return ChatDeepSeek(
        model=settings.LLM_DEEPSEEK_MODEL,
        base_url=settings.LLM_DEEPSEEK_BASE_URL,
        reasoning_effort=settings.LLM_DEEPSEEK_REASONING_EFFORT,
        extra_body=settings.LLM_DEEPSEEK_EXTRA_BODY,
    )

def create_llm_openai():
    """动态创建 OpenAI 模型（每次调用读取最新配置）。"""
    settings = _reload_settings()
    return ChatOpenAI(
        model=settings.LLM_OPENAI_MODEL,
        base_url=settings.LLM_OPENAI_BASE_URL,
        extra_body=settings.LLM_OPENAI_EXTRA_BODY,
    )

def create_llm_ollama():
    """动态创建 Ollama 模型（每次调用读取最新配置）。"""
    settings = _reload_settings()
    return ChatOllama(
        model=settings.LLM_OLLAMA_MODEL,
        base_url=settings.LLM_OLLAMA_BASE_URL,
        reasoning=settings.LLM_OLLAMA_REASONING,
    )

# ---------- 厂商到工厂函数的映射 ----------
_PROVIDER_FACTORIES = {
    "deepseek": create_llm_deepseek,
    "ali": create_llm_ali,
    "ollama": create_llm_ollama,
    "openai": create_llm_openai,
    
}


def get_active_llm():
    """根据 model_config.yaml 中的 active_provider 动态创建当前激活的模型。
    
    每次 graph 热重载时调用，确保读取最新配置。
    """
    from backend.config.logger import get_logger
    _log = get_logger(__name__)

    settings = _reload_settings()
    provider = getattr(settings, "LLM_ACTIVE_PROVIDER", "deepseek") or "deepseek"
    _log.info("get_active_llm | active_provider=%s", provider)

    factory = _PROVIDER_FACTORIES.get(provider)
    if factory is None:
        _log.warning("未知的模型厂商 '%s'，回退到 deepseek", provider)
        factory = create_llm_deepseek
    return factory()


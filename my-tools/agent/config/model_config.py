import os
from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama
from langchain_qwq import ChatQwen
from langchain_moonshot import ChatMoonshot
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaEmbeddings

from .env import (
    LLM_DEEPSEEK_BASE_URL, LLM_JSON_MODEL, LLM_DEEPSEEK_MODEL,
    LLM_OLLAMA_BASE_URL, LLM_OLLAMA_MODEL,
    LLM_ALI_BASE_URL, LLM_ALI_MODEL,
    LLM_MOONSHOT_MODEL,
    EMBEDDING_MODEL, EMBEDDING_BASE_URL,
    LLM_ALI_API_KEY,
)

# ---------- 结构化输出模型配置 ----------
llm_json = ChatDeepSeek(
    model=LLM_JSON_MODEL,
    base_url=LLM_DEEPSEEK_BASE_URL,
    reasoning_effort="max",
    extra_body={"thinking": {"type": "enabled"}},
    model_kwargs={"response_format": {"type": "json_object"}},
)

# ---------- 普通输出模型配置 ----------
llm_ollama = ChatOllama(
    model=LLM_OLLAMA_MODEL,
    base_url=LLM_OLLAMA_BASE_URL,
    reasoning="low",
)

llm_deepseek = ChatDeepSeek(
    model=LLM_DEEPSEEK_MODEL,
    base_url=LLM_DEEPSEEK_BASE_URL,
    reasoning_effort="max",
    extra_body={"thinking": {"type": "enabled"}},
)

llm_ali = ChatQwen(
    model=LLM_ALI_MODEL,
    base_url=LLM_ALI_BASE_URL,
    enable_thinking=True,
    api_key=LLM_ALI_API_KEY,
)

llm_moonshot = ChatMoonshot(
    model=LLM_MOONSHOT_MODEL,
    thinking=True,
)

# ---------- 嵌入模型配置 ----------
embeddings = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=EMBEDDING_BASE_URL,
)
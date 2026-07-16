import os
from dotenv import load_dotenv

# ========== 查找.env 文件 ==========
def _find_project_root(marker: str = ".env") -> str:
    """从当前文件所在目录开始，向上查找包含 marker 文件的目录作为项目根"""
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(current, marker)):
            return current
        parent = os.path.dirname(current)
        if parent == current:   # 到达文件系统根仍未找到
            raise FileNotFoundError(f"Project root not found: no '{marker}' found in ancestor directories")
        current = parent

_PROJECT_ROOT = _find_project_root()

# 显式指定 .env 路径 + 强制覆盖已有的环境变量
load_dotenv(
    os.path.join(_PROJECT_ROOT, ".env"),
    override=True,
)

def _resolve(path: str | None) -> str | None:
    """将相对路径解析为基于项目根目录的绝对路径"""
    if path and not os.path.isabs(path):
        return os.path.normpath(os.path.join(_PROJECT_ROOT, path))
    return path

# ========== 路径配置（读取 .env，） ==========
# agent 相关路径
MEMORY_DIR = _resolve(os.getenv("MEMORY_DIR"))
SKILLS_DIR = _resolve(os.getenv("SKILLS_DIR"))
WORKSPACE_DIR = _resolve(os.getenv("WORKSPACE_DIR"))


# 文档相关路径
DOC_INDEX = _resolve(os.getenv("DOC_INDEX"))
DOC_RAW_DIR = _resolve(os.getenv("DOC_RAW_DIR"))


# 检查点数据库
CHECKPOINT_DB = _resolve(os.getenv("CHECKPOINT_DB"))
POSTGRES_URI = os.getenv("POSTGRES_URI")

# 存储数据库
STORE_DB = _resolve(os.getenv("STORE_DB"))
MONGODB_URI = os.getenv("MONGODB_URI")

# Chroma 数据库
CHROMA_DB = _resolve(os.getenv("CHROMA_DB"))
COLLECTION_DEEPAGENT_NAME = os.getenv("COLLECTION_DEEPAGENT_NAME")

CHROMA_MEMORY_DB = _resolve(os.getenv("CHROMA_MEMORY_DB"))
COLLECTION_MEMORY_NAME = os.getenv("COLLECTION_MEMORY_NAME")



# 运行相关路径
SUMMARIZATION_DIR = _resolve(os.getenv("SUMMARIZATION_DIR"))
SAVE_STATE_DIR = _resolve(os.getenv("SAVE_STATE_DIR"))
CHAT_LOG_DIR = _resolve(os.getenv("CHAT_LOG_DIR"))
PREVIEW_CHUNKS_DIR = _resolve(os.getenv("PREVIEW_CHUNKS_DIR"))


# ========== LLM 模型配置 ==========
# DeepSeek 模型
LLM_DEEPSEEK_BASE_URL = (os.getenv("LLM_DEEPSEEK_BASE_URL"))
LLM_JSON_MODEL = (os.getenv("LLM_JSON_MODEL"))
LLM_DEEPSEEK_MODEL = (os.getenv("LLM_DEEPSEEK_MODEL"))

# Ollama 模型
LLM_OLLAMA_BASE_URL = (os.getenv("LLM_OLLAMA_BASE_URL"))
LLM_OLLAMA_MODEL = (os.getenv("LLM_OLLAMA_MODEL"))

# Aliyun 模型
LLM_ALI_BASE_URL = (os.getenv("LLM_ALI_BASE_URL"))
LLM_ALI_MODEL = (os.getenv("LLM_ALI_MODEL"))
LLM_ALI_API_KEY = (os.getenv("DASHSCOPE_API_KEY"))

# Moonshot 模型
LLM_MOONSHOT_MODEL = (os.getenv("LLM_MOONSHOT_MODEL"))

# ========== 嵌入 & Reranker ==========
# 嵌入模型配置
EMBEDDING_MODEL = (os.getenv("EMBEDDING_MODEL"))
EMBEDDING_BASE_URL = (os.getenv("EMBEDDING_BASE_URL"))

# Reranker 模型配置
RERANK_MODEL = (os.getenv("RERANK_MODEL"))

# ========== Langfuse 配置 ==========
LANGFUSE_TRACING_ENABLED = (os.getenv("LANGFUSE_TRACING_ENABLED", "true")).lower() in (
    "true", "1", "t", "yes",
)
LANGFUSE_PUBLIC_KEY = (os.getenv("LANGFUSE_PUBLIC_KEY"))
LANGFUSE_SECRET_KEY = (os.getenv("LANGFUSE_SECRET_KEY"))
LANGFUSE_BASE_URL = (os.getenv("LANGFUSE_BASE_URL"))

# ========== CORS ==========
CORS_ORIGINS = (os.getenv("CORS_ORIGINS"))

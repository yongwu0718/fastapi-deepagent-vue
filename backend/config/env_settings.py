import os
from dotenv import load_dotenv
from wechatbot import UploadResult

# ========== 查找.env 文件 ==========
def _find_project_root(marker: str = ".env") -> str:
    """从当前文件所在目录开始，向上查找包含 marker 文件的目录作为项目根"""
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(current, marker)):
            return current
        parent = os.path.dirname(current)
        if parent == current:  # 到达文件系统根仍未找到
            raise FileNotFoundError(
                f"Project root not found: no '{marker}' found in ancestor directories"
            )
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


# ========== 路径配置 ==========
# ── Settings 管理的配置文件路径 ──
MODEL_CONFIG_PATH = _resolve(os.getenv("MODEL_CONFIG_DIR"))
SYSTEM_PROMPT_PATH = _resolve(os.getenv("SYSTEM_PROMPT_DIR"))
MCP_SERVER_PATH = _resolve(os.getenv("MCP_SERVER_DIR"))
MEMORY_DIR = _resolve(os.getenv("MEMORY_DIR"))
SKILLS_DIR = _resolve(os.getenv("SKILLS_DIR"))
SKILLS_CONFIG_PATH = _resolve(os.getenv("SKILLS_CONFIG_PATH"))
    
# 文档相关路径
DOC_INDEX = _resolve(os.getenv("DOC_INDEX"))
WORKSPACE_DIR = _resolve(os.getenv("WORKSPACE_DIR"))
UPLOADS_DIR = _resolve(os.getenv("UPLOADS_DIR"))

# RAG 相关路径
RAW_DOCS_DIR = _resolve(os.getenv("RAW_DOCS_DIR"))
CLEAN_DOCS_DIR = _resolve(os.getenv("CLEAN_DOCS_DIR"))

# 检查点数据库
CHECKPOINT_DB = _resolve(os.getenv("CHECKPOINT_DB"))

# 存储数据库
STORE_DB = _resolve(os.getenv("STORE_DB"))

# Chroma 数据库
CHROMA_DB = _resolve(os.getenv("CHROMA_DB"))
COLLECTION_MEMORY_NAME = os.getenv("COLLECTION_MEMORY_NAME")

# 运行相关路径
SUMMARIZATION_DIR = _resolve(os.getenv("SUMMARIZATION_DIR"))
SAVE_STATE_DIR = _resolve(os.getenv("SAVE_STATE_DIR"))
CHAT_LOG_DIR = _resolve(os.getenv("CHAT_LOG_DIR"))
PREVIEW_CHUNKS_DIR = _resolve(os.getenv("PREVIEW_CHUNKS_DIR"))

# ========== CORS ==========
CORS_ORIGINS = os.getenv("CORS_ORIGINS")

# ========== Langfuse 配置 ==========
LANGFUSE_TRACING_ENABLED = (os.getenv("LANGFUSE_TRACING_ENABLED", "true")).lower() in (
    "true", "1", "t", "yes",
)
LANGFUSE_PUBLIC_KEY = (os.getenv("LANGFUSE_PUBLIC_KEY"))
LANGFUSE_SECRET_KEY = (os.getenv("LANGFUSE_SECRET_KEY"))
LANGFUSE_BASE_URL = (os.getenv("LANGFUSE_BASE_URL"))

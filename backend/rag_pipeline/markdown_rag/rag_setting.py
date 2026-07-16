import os
import yaml

_PROJECT_ROOT: str | None = None
_config: dict = {}
_SENTINEL = object()


def _find_project_root(marker: str = "rag_config.yaml") -> str:
    """从当前文件所在目录开始，向上查找包含 marker 文件的目录作为项目根"""
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(current, marker)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(f"Project root not found: no '{marker}' found in ancestor directories")
        current = parent


def _load_yaml_config() -> dict:
    """读取 rag_config.yaml 并返回解析后的字典。"""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = _find_project_root()
    config_path = os.path.join(_PROJECT_ROOT, "rag_config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
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


def reload_rag_config():
    """重新加载 rag_config.yaml 并更新所有模块级配置变量。"""
    global _config
    global EMBEDDING_MODEL, EMBEDDING_BASE_URL
    global RAG_SPLITTER_HEADERS, RAG_SPLITTER_RETURN_EACH_LINE, RAG_SPLITTER_STRIP_HEADERS
    global RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_ENABLE_CHAR_SPLIT
    global RAG_HNSW_CONFIG
    global RAG_PROCESSING_PREVIEW_DIR, RAG_PROCESSING_INTERACTIVE

    _config = _load_yaml_config()

    # ── 嵌入模型 ──
    EMBEDDING_MODEL = _env_or_yaml("EMBEDDING_MODEL", "embedding", "model")
    EMBEDDING_BASE_URL = _env_or_yaml("EMBEDDING_BASE_URL", "embedding", "base_url")

    # ── 文档分割器 ──
    RAG_SPLITTER_HEADERS = _config.get("rag", {}).get("splitter", {}).get("headers", ["#", "##", "###"])
    RAG_SPLITTER_RETURN_EACH_LINE = _config.get("rag", {}).get("splitter", {}).get("return_each_line", False)
    RAG_SPLITTER_STRIP_HEADERS = _config.get("rag", {}).get("splitter", {}).get("strip_headers", False)
    RAG_ENABLE_CHAR_SPLIT = _config.get("rag", {}).get("splitter", {}).get("enable_char_split", False)
    RAG_CHUNK_SIZE = int(_config.get("rag", {}).get("splitter", {}).get("chunk_size", 1000))
    RAG_CHUNK_OVERLAP = int(_config.get("rag", {}).get("splitter", {}).get("chunk_overlap", 200))

    # ── HNSW 索引参数 ──
    RAG_HNSW_CONFIG = _config.get("rag", {}).get("hnsw", {})

    # ── 处理参数 ──
    RAG_PROCESSING_PREVIEW_DIR = _config.get("rag", {}).get("processing", {}).get("preview_output_dir", "preview")
    RAG_PROCESSING_INTERACTIVE = _config.get("rag", {}).get("processing", {}).get("enable_interactive", True)


# 首次加载
reload_rag_config()

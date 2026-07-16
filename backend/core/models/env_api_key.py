import os
from dotenv import load_dotenv

# ========== 查找.env 文件 ==========
def _find_project_root(marker: str = ".env.api_key") -> str:
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

_ = load_dotenv(
    os.path.join(_PROJECT_ROOT, ".env.api_key"),
    override=True,
)

LLM_ALI_API_KEY = os.getenv("DASHSCOPE_API_KEY")
LLM_DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
LLM_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
App_ID = os.getenv("App_ID")
App_Secret = os.getenv("App_Secret")
user_token = os.getenv("user_token")

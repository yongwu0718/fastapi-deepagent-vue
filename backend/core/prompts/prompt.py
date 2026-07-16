from pathlib import Path

def load_system_prompt() -> str:
    """从文件加载系统提示词，每次调用重新读取以支持热更新。"""
    prompt_file = Path(__file__).parent / "system_prompt.txt"
    return prompt_file.read_text(encoding="utf-8")

# 向后兼容：模块级别名（首次加载时的值）
system_prompt = load_system_prompt()
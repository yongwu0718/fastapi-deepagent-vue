from langchain_quickjs.middleware import CodeInterpreterMiddleware

from deepagents.backends import FilesystemBackend
from deepagents.middleware.summarization import SummarizationMiddleware, SummarizationToolMiddleware
from deepagents.middleware.rubric import RubricMiddleware
from backend.config.env_settings import SUMMARIZATION_DIR
from backend.core.models.model_factory import llm_ali,llm_deepseek

from backend.core.custom_middleware.truncate_toolmessage import TruncateToolMessagesMiddleware
from backend.core.custom_middleware.model_switcher import ModelContext,dynamic_model_switcher

# ---------- 摘要中间件配置 ----------
backend_summarization = FilesystemBackend(
    root_dir=SUMMARIZATION_DIR,
    virtual_mode=True
)

# ---------- 自动摘要中间件配置 ----------
auto_summarization = SummarizationMiddleware(
    model=llm_deepseek,
    backend=backend_summarization,
    trigger=("tokens", 750_000),
    keep=("tokens", 150_000),
    trim_tokens_to_summarize=40_000,
    truncate_args_settings={
        "trigger": ("tokens", 190_000),
        "keep": ("tokens", 100_000),
        "max_length": 4000,
        "truncation_text": ".[content truncated]",
    },
)
# ---------- 手动摘要工具中间件配置 ----------
manual_tool = SummarizationToolMiddleware(auto_summarization)

# ---------- 截断中间件配置 ----------
truncate_tool_calls = TruncateToolMessagesMiddleware(
    keep_recent=15,
    placeholder="[Earlier tool outputs are omitted for context management.]",
)

# ---------- 评分中间件配置 ----------
rubric_middleware = RubricMiddleware(
    model=llm_deepseek,
    max_iterations=10,
)


add_middleware=[
    manual_tool,
    truncate_tool_calls,
    CodeInterpreterMiddleware(),
    rubric_middleware,
]
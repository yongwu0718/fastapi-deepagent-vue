---
type: component
title: Agent Core — Graph Assembly, Model Factory, Middleware, Composite Backend
description: "How the DeepAgents graph is configured: model factory and provider switching, the middleware chain (truncate, quickjs code interpreter, rubric), CompositeBackend routes, and the system prompt. Includes the moonshot dead-config gap."
tags: [backend, agent, deepagents, middleware, models]
---

# Agent Core

## Model factory — `backend/core/models/model_factory.py`

Four provider factories are registered in `_PROVIDER_FACTORIES`:

| Key | Factory | Class |
|---|---|---|
| `deepseek` | `create_llm_deepseek` | `ChatDeepSeek` (base_url api.deepseek.com, reasoning_effort, extra_body thinking) |
| `ali` | `create_llm_ali` | `ChatQwen` (DashScope compatible-mode, enable_thinking) |
| `ollama` | `create_llm_ollama` | `ChatOllama` (localhost:11434) |
| `openai` | `create_llm_openai` | `ChatOpenAI` (tokenhub.tencentmaas.com) |

- Module-level singletons (`llm_deepseek`, `llm_ali`, `llm_ollama`, `llm_openai`, `llm_json`, `embeddings`, `rerank_model`) are built at import; the `create_*` factories re-read YAML each call (`llm_settings.reload_model_config()`) so hot reload picks up changes.
- `get_active_llm()` resolves `LLM_ACTIVE_PROVIDER` from config and returns `factory()`; unknown provider logs a warning and falls back to `deepseek`.
- **Moonshot dead-end (4 advertising surfaces, zero implementation)**: `model_config.yaml` ships a `moonshot` section (`model: kimi-k2.5`, `thinking: true`), `.env.api_key.example` ships `MOONSHOT_API_KEY`, `model_switcher.ModelContext`'s docstring lists `"moonshot"` as an example model name, and `pyproject.toml` depends on `langchain-moonshot>=0.1.0`. But `backend/core/models/env_api_key.py` does **not** read `MOONSHOT_API_KEY` (only `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `App_ID`, `App_Secret`), `llm_settings.reload_model_config()` has no moonshot reader, `_PROVIDER_FACTORIES` maps only `deepseek/ali/ollama/openai` (so `get_active_llm()` logs "未知的模型厂商" and falls back to deepseek), and `MODEL_MAP`/`FALLBACK_CHAIN` have no moonshot entry (so `_resolve_model` warns "未知模型名称" and resolves to deepseek). Selecting moonshot in the UI therefore always runs DeepSeek.
  - **Minimal change set to make it usable**: (1) read `MOONSHOT_API_KEY` in `env_api_key.py`; (2) add a `moonshot` reader section to `llm_settings.reload_model_config()` (base_url/model/thinking keys); (3) add a `create_llm_moonshot` factory (via `langchain_moonshot`) plus a `_PROVIDER_FACTORIES["moonshot"]` registry entry; (4) add `moonshot` to `model_switcher.MODEL_MAP` and `FALLBACK_CHAIN`. Missing any one surface keeps a specific behavior broken: without (1) the API key is silently absent; without (2) the YAML section stays unread; without (3) `active_provider: moonshot` warns and falls back to deepseek; without (4) per-request `model="moonshot"` warns and falls back to deepseek.
- Embeddings: `OllamaEmbeddings(my-qwen3-embed:latest)`; reranker: `DashScopeRerank(gte-rerank-v2, top_n=10)` (custom wrapper in `models/reranker.py`).

## Dynamic model switcher — `backend/core/custom_middleware/model_switcher.py`

A `@wrap_model_call` middleware used as the graph's `context_schema` (`ModelContext` dataclass with `model: str`):

- `_resolve_model()` picks the model from `request.runtime.context.model`, defaulting to `deepseek`; unknown names warn and fall back.
- Failure behavior: try same model up to `MAX_RETRIES_PER_MODEL = 2`, then walk `FALLBACK_CHAIN = ["deepseek", "ali", "ollama"]` (Ollama local is the last resort); if all fail, re-raise the last exception.
- Note: `dynamic_model_switcher` itself is **defined** here but is not in `add_middleware` (see below) — the active switching surface for the compiled graph is the per-run `ModelContext` (context_schema), while this middleware is available but not installed. Runtime evidence about model fallback: see [runtime behavior](../runtime-behavior.md) (this pull contains no runs of this code path).

## Middleware chain — `backend/core/assembled/middleware.py`

`add_middleware` passed to `create_deep_agent`:

1. `TruncateToolMessagesMiddleware(keep_recent=15, placeholder="[Earlier tool outputs are omitted...]")` — custom (`custom_middleware/truncate_toolmessage.py`); replaces all but the 15 most recent `ToolMessage` contents with a placeholder before each model call, keeping old tool outputs (e.g. big retrieval results) from filling the context window. No-op when fewer than 15 tool messages exist.
2. `CodeInterpreterMiddleware()` — from `langchain_quickjs`; adds a JS code-interpreter tool.
3. `RubricMiddleware(model=llm_deepseek, max_iterations=10)` — Loop Engineering evaluator (see [chat flow](chat-flow.md)).

Also instantiated but **not enabled**: `auto_summarization = SummarizationMiddleware(model=llm_deepseek, trigger=("tokens", 750_000), keep=("tokens", 150_000), ...)` and `manual_tool = SummarizationToolMiddleware(auto_summarization)` — the `manual_tool` entry is commented out of the list, and `auto_summarization` is only referenced by `manual_tool`. So the summarization subsystem is installed-but-unused: token thresholds (750k trigger / 190k truncate) never fire in production runs.

The DeepAgents `create_deep_agent` prepends `FilesystemMiddleware(backend=backend)` and appends `HumanInTheLoopMiddleware(interrupt_on={})` (empty, never interrupts).

## Composite backend — `backend/core/assembled/backends.py`

```python
backend = CompositeBackend(
    default=LocalShellBackend(root_dir=WORKSPACE_DIR, virtual_mode=True, inherit_env=True,
                              env={"PATH": merged_path}),  # D:\python_3.12, D:\node + system PATH
    routes={
        "/memory/":      FilesystemBackend(root_dir=MEMORY_DIR, virtual_mode=True),
        "/active_skills/": SkillFilteredBackend(FilesystemBackend(root_dir=SKILLS_DIR, virtual_mode=True)),
        "/knowledge/":   FilesystemBackend(root_dir=DOC_INDEX, virtual_mode=True),
    },
)
```

- The default backend gives the agent shell `execute` in the workspace; `/memory/`, `/active_skills/`, `/knowledge/` are virtual filesystem routes. The system prompt instructs the agent to map the virtual path `/active_skills/` to the local `F:\index_rag\backend\memory_skill\skill\` when constructing shell commands.
- `SkillFilteredBackend` (see [memory & skills](memory-skills.md)) hides disabled skills from `ls`.

## System prompt — `backend/core/prompts/system_prompt.txt` (loaded by `prompts/prompt.py`)

Chinese-language deep-agent prompt. Hard rules an agent must follow:

- Quality gate: before calling tools, internal reasoning must run three steps (essence questioning, argument skeleton, anti-intuition self-check) — never call tools before reasoning.
- Tool-call budget: at most 2 failed calls per tool; retrieval tools at most 2 uses; no redundant calls for the same target.
- `execute` rules: max 1 retry after cleaning WAL/SHM/journal lock files; never bypass CLI to write SQLite, never taskkill, never write substitute Python scripts; merge independent commands into one `execute` with `&&`.
- Path mapping table for virtual paths (e.g. `/active_skills/` → local path).
- Skill files are read once per session (counts against the message budget); output in Chinese; Markdown tables use `<br>` for long cells.

DeepAgents appends its own BASE_AGENT_PROMPT (English behavioral rules) after the system prompt.

## Runtime evidence cross-links

- The tool-call budget rules exist because redundant/retried calls were observed problems; production telemetry for this repo's agent is traced to **Langfuse**, and the separate **LangSmith** sample (project `openwiki`) contains no runs of this agent — see [runtime behavior](../runtime-behavior.md) for what the sample does and does not show.

## Related pages

- [Backend overview](overview.md) — graph lifecycle and `create_deep_agent` call
- [Tools](tools.md) — what the agent can call
- [Config](config.md) — model_config.yaml and the moonshot gap
- [Memory & skills](memory-skills.md) — the skills backend

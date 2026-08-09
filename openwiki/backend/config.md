---
type: configuration
title: Backend Configuration — Env, YAML Files, Logging, Observability
description: "Every configuration surface of the backend: env path resolution, model_config.yaml and rag_config.yaml, MCP server registry, skills config, logger layout, Langfuse wiring, plus the known .env.example gaps that break a fresh setup."
tags: [backend, configuration, env, logging, langfuse]
---

# Backend Configuration

## Environment loading — `backend/config/env_settings.py`

- Finds the project root by walking up from the file until a `.env` marker file is found (`_find_project_root`), then loads it with `load_dotenv(..., override=True)`.
- `_resolve(path)` turns relative env values into absolute paths anchored at the project root.
- Two separate dotenv files are loaded by different modules: `.env` (paths/settings, loaded by `env_settings.py`) and `.env.api_key` (API keys, loaded by `backend/core/models/env_api_key.py` via its own root-finding loop). The example file `.env.api_key.example` lists six keys, but `env_api_key.py` actually reads only five: `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `App_ID`, `App_Secret`. `MOONSHOT_API_KEY` is **never read** anywhere (the moonshot dead-end is detailed in [agent core](agent-core.md)).

### Path resolution footgun (MODEL_CONFIG_DIR vs MODEL_CONFIG_PATH)

`env_settings.py` assigns `MODEL_CONFIG_PATH` **twice**:

```python
MODEL_CONFIG_PATH = _resolve(os.getenv("MODEL_CONFIG_DIR"))    # line 35 — dead
MODEL_CONFIG_PATH = _resolve(os.getenv("MODEL_CONFIG_PATH"))   # line 42 — wins
```

Only `MODEL_CONFIG_PATH` is effective. The same file also resolves `SYSTEM_PROMPT_PATH`, `MCP_SERVER_PATH`, `MEMORY_DIR`, `SKILLS_DIR`, `SKILLS_CONFIG_PATH`, `RAG_CONFIG_PATH`, `DOC_INDEX`, `WORKSPACE_DIR`, `UPLOADS_DIR`, `CHECKPOINT_DB`, `STORE_DB`, `SUMMARIZATION_DIR`, `SAVE_STATE_DIR`, `CHAT_LOG_DIR`, `CORS_ORIGINS`, and Langfuse vars.

### Known `.env.example` gaps (fresh setup fails)

The README's documented setup is `copy .env.example .env`, but `.env.example` (line 9) only sets `MODEL_CONFIG_DIR`, **not** `MODEL_CONFIG_PATH` or `RAG_CONFIG_PATH`:

- `backend/core/models/llm_settings.py` line 11 does `open(MODEL_CONFIG_PATH)` → `TypeError` at import when unset. The import chain `backend/main.py → routers → services → main_agent.py → model_factory → llm_settings` means the **backend will not boot**.
- `backend/api/markdown_rag/rag_setting.py` line 8 does `open(RAG_CONFIG_PATH)` → same crash (imported through the rag_pipeline router chain, and independently by `rag_tool/retrieve_tool.py`).

Also stale: `.env.example` line 15 sets `MCP_SERVER_DIR = backend/core/utils/mcp/mcp_server.json`, but `backend/core/utils/` does not exist. The real registry is `backend/core/mcp/mcp_server.json` and `backend/core/mcp/mcp_tool.py` reads it via `Path(__file__).parent` — **not** via the env var. The env var only feeds `settings_service._FILE_PATHS["mcp"]`, so the frontend settings "MCP" tab would 404 against a nonexistent path.

Legacy dead env keys that no current code reads: `CHROMA_DB`, `COLLECTION_NAME`, `COLLECTION_MEMORY_NAME`, `RAW_DOCS_DIR`, `CLEAN_DOCS_DIR`, `PREVIEW_CHUNKS_DIR` (superseded by `rag_config.yaml`), plus `EXTRA_PATH` (present in the committed `.env` as a Windows PATH list, e.g. `D:\python_3.12;D:\python_3.12\Scripts;D:\node`) — no Python module reads any of them.

> A working fresh `.env` must add at least `MODEL_CONFIG_PATH=model_config.yaml` and `RAG_CONFIG_PATH=backend/api/markdown_rag/rag_config.yaml`, and correct `MCP_SERVER_DIR=backend/core/mcp/mcp_server.json`. Details are repeated in [operations](../operations.md).

## `model_config.yaml` (repo root)

Loaded by `backend/core/models/llm_settings.py` (`reload_model_config()`), which re-reads the file each time `get_active_llm()` is called. Resolution order per key: env var → YAML → default.

| Section | Keys read by `llm_settings.py` | Notes |
|---|---|---|
| `active_provider` | `LLM_ACTIVE_PROVIDER` (default `deepseek`) | must match a factory key, else warning + deepseek fallback |
| `deepseek` | base_url, model, json_model, reasoning_effort, extra_body, json_kwargs | default provider; `deepseek-v4-flash` / `deepseek-v4-pro` |
| `ollama` | base_url, model, reasoning | `qwen3.5` @ localhost:11434 |
| `aliyun` | base_url, model, enable_thinking | `qwen3.7-max-2026-05-17` via DashScope compatible-mode |
| `openai` | base_url, model, extra_body | `glm-5.2` via tokenhub.tencentmaas.com |
| `moonshot` | **NOT read** | configured in YAML and editable in the UI, but no code loads it (see [agent core](agent-core.md)) |
| `embedding` | model, base_url | `my-qwen3-embed:latest` @ Ollama |
| `reranker` | model, top_n | `gte-rerank-v2`, top_n=10; `RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", _config["reranker"].get("top_n", 10)))` — env var wins and is **coerced to `int`** (a non-numeric env value raises `ValueError` at reload) |

### Hot-reload chains (config edits → running graph)

- **Model/prompt/MCP config**: `PUT /settings/model-config/write` (router `write_model_config_endpoint`) only overwrites the file via `settings_service.write_config_file` — it does **not** rebuild the graph itself. The frontend settings page ("保存并重建" button, `SettingsView.vue`) then calls `POST /settings/rebuild` → `graph.rebuild_graph()`, which `__aexit__`s the old `init_graph()` context (closing the SQLite connections) and `__aenter__`s a new one — re-reading `model_config.yaml`, `system_prompt.txt`, and `mcp_server.json` on entry (dynamic imports inside `init_graph` bypass module cache). So the effective chain is write → explicit rebuild → new graph instance.
- **Skills**: `PUT /settings/skills` writes `skills_config.yaml` and calls `rebuild_graph()` automatically in the router.
- **RAG config**: `PUT /api/rag/config` rewrites `rag_config.yaml` and calls `rag_setting.reload_rag_config()` (pure YAML, no env fallback) — see [RAG pipeline](rag-pipeline.md) for the caveat that the existing Chroma singleton is not invalidated.

## `backend/api/markdown_rag/rag_config.yaml`

Loaded by `backend/api/markdown_rag/rag_setting.py` (`reload_rag_config()`; pure YAML, no env overrides). Controls the RAG pipeline: splitter headers `#`/`##`/`###`, `chunk_size=1000`, `chunk_overlap=200`, `enable_char_split=false`, HNSW params (cosine, ef_construction 200, max_neighbors 32, ef_search 200), and collection settings — default collection name is `sunzi`, persist dir `backend/data/chroma_db`. Editable at runtime via `GET/PUT /api/rag/config` (see [RAG pipeline](rag-pipeline.md)).

## `backend/core/mcp/mcp_server.json`

MCP server registry consumed by `mcp_tool()`:

| Server | Transport | Command/URL | Tools |
|---|---|---|---|
| `math` | stdio | `{PYTHON_EXECUTABLE} {MCP_SERVER_DIR}/local_mcp.py` | add, multiply (FastMCP) |
| `WebSearch` | http | `https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/mcp`, bearer `{DASHSCOPE_API_KEY}` | Aliyun web search |
| `lark-mcp` | stdio | `npx -y @larksuiteoapi/lark-mcp ... -a {App_ID} -s {App_Secret}` | Feishu calendar preset |

Placeholders `{VAR}` are substituted with built-ins (`PYTHON_EXECUTABLE`, `MCP_SERVER_DIR`) then env vars (see [tools](tools.md)).

## `backend/core/skill_manager/skills_config.yaml`

`enabled:` list (billing_analyze, fastapi, gonghao-baowen-writing, subagents, sunzi-bingfa, task-planner, vocab-tutor). Consumed by `SkillFilteredBackend` (filters `/active_skills/` ls results) and by the settings service for the skills UI (see [memory & skills](memory-skills.md)).

## Logging — `backend/config/logger.py`

- **Idempotent init**: `setup_logging()` guards on the module flag `_initialized` — later calls are no-ops. Defaults: `max_bytes=10MB`, `backup_count=5`, `run_log_ttl_days=1`, `app_log_ttl_days=7`.
- **File layout** under `backend/logs/<YYYY-MM-DD>/`: cumulative `app.log` (a `RotatingFileHandler` with `maxBytes`/`backupCount`; its `namer = _daily_namer` renames rotated files to `app.<YYYYMMDD-HHMMSS>.log` instead of `app.log.1`) plus one per-run `run_HH-MM-SS_pid<pid>.log` created with `mode="w"` (unique per process, so overwrite is safe). `CURRENT_DATE_DIR` / `CURRENT_RUN_LOG_FILE` module globals expose the active date dir and run file.
- **Levels**: custom `TRACE = 5` registered via `addLevelName` and patched onto `logging.Logger` (`logger.trace(...)`); the **root logger is set to TRACE** and each handler filters (`setLevel(TRACE)`) independently.
- **TTL cleanup** runs at startup inside `setup_logging()`:
  - `_cleanup_expired_run_logs(run_log_ttl_days)` — deletes `run_*.log` in date dirs older than the cutoff (kept `[today-ttl+1, today]`), with an mtime-based fallback for legacy flat `run_*.log` files directly under `LOG_ROOT`; skipped entirely when `ttl <= 0`.
  - `_cleanup_expired_date_dirs(app_log_ttl_days)` — removes whole date directories (including `app.log` and any remaining run files) older than `today - ttl_days`; today's dir is never touched; `ttl <= 0` disables.
- **Request context**: `ContextVar` `_request_context`; `bind_context(**kwargs)` / `clear_context()` / `get_context()` manage it; `ContextFormatter` appends `| ctx: k=v` to each formatted line; `ContextFilter` (attached to both handlers) copies the bound fields onto every `LogRecord`.
- **Noise suppression**: `HeartbeatFilter` (attached to both handlers) drops records whose message contains `PingRequest` (MCP heartbeat traffic); third-party loggers `httpx`, `httpcore`, `urllib3`, `asyncio`, `aiosqlite`, `watchfiles` are suppressed to `WARNING`.
- **Entry points** that call `setup_logging()` and why: `backend/main.py` at import (web server); `backend/wechat_bot.py` at module level because it is a standalone script; CLI tools call it at the point of execution — `cli/interact.py` inside `_main()` (first line of the async main), `cli/get_message_history.py` and `cli/query_state.py` inside their `if __name__ == "__main__":` blocks (the tool entry functions themselves assume logging is already initialized).

## Observability — `backend/config/observability.py`

- `langfuse_init()` creates a `Langfuse` client and does `auth_check()`; warnings on failure, no crash. Skipped when `LANGFUSE_TRACING_ENABLED` is false.
- `get_langfuse_callback_handler()` lazily creates the singleton `CallbackHandler` (delayed so dotenv has loaded first).
- `build_langfuse_config(thread_id, user_id, tags)` returns `{"callbacks": [...], "metadata": {langfuse_session_id: thread_id, ...}}` merged into every LangGraph `config` in chat_service, stream.py, CLI, and the WeChat bot.

Langfuse is the application's tracing backend; LangSmith is used only for the OpenWiki tool's own runs (see [runtime behavior](../runtime-behavior.md)).

## Related pages

- [Agent core](agent-core.md) — how the model config drives the factory
- [Tools](tools.md) — MCP registry and placeholder resolution
- [Operations](../operations.md) — runbook and fresh-setup keys

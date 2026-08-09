---
type: guide
title: Operations — Run, Configure, and Validate
description: "Runbook for the whole stack: backend, frontend, desktop, WeChat, CLI, LangGraph server, Chroma viewers; OpenAPI client regeneration; config hot-reload; and the no-tests validation strategy based on logs and tracing."
tags: [operations, runbook, validation]
---

# Operations

## Prerequisites

- Python >= 3.12, [uv](https://github.com/astral-sh/uv), Node >= 18, Ollama (local embedding server).
- `uv sync` from the repository root.
- Copy env templates: `copy .env.example .env` and `copy .env.api_key.example .env.api_key`, then fill API keys.

> **Fresh-setup warning (see [backend config](backend/config.md) for details):** `.env.example` sets only `MODEL_CONFIG_DIR` while the code reads `MODEL_CONFIG_PATH` (and `RAG_CONFIG_PATH`), so a plain copy leaves those as `None` and the backend fails at import (`open(None)`). A fresh `.env` must also define `MODEL_CONFIG_PATH`, `RAG_CONFIG_PATH`, and a correct `MCP_SERVER_DIR` (the example's `backend/core/utils/mcp/mcp_server.json` path does not exist).

## Run the stack

| Runtime | Command |
|---|---|
| Backend (dev) | `.venv\Scripts\activate; cd backend; fastapi dev` (or `fastapi dev backend/main.py` from root) |
| Frontend | `cd frontend; npm install; npm run dev` → http://localhost:5173 |
| Desktop one-click | `start-desktop.bat` or `cd desktop; npm start` (spawns backend + frontend, tray-resident) |
| WeChat bot | `.venv\Scripts\activate; python backend/wechat_bot.py` (scan QR, credentials valid 24 h) |
| CLI | `.venv\Scripts\activate; python -m backend.cli.interact` |
| LangGraph local server | `langgraph dev` |
| Chroma browser (docs) | `python view_db/view_sql.py` — note: `server-ops.md` references `view_db/start_chroma_server.py` and `view_db/view_chroma.py`, which **do not exist** in the repo; that file is stale |

## OpenAPI client regeneration

The frontend `src/api/client/` is generated:

```powershell
cd F:\index_rag\frontend; npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o src/api/client
```

Regenerate whenever backend schemas change (also documented in `server-ops.md` and `notes/api.md`).

## Configuration hot-reload

- `POST /settings/rebuild` — re-enters `init_graph()`, re-reading `model_config.yaml`, `system_prompt.txt`, `mcp_server.json`, and `subagents_config.py`.
- `PUT /settings/skills` — rewrites `skills_config.yaml` and rebuilds the graph automatically.
- `PUT /api/rag/config` — overwrites `rag_config.yaml` and reloads it at runtime.
- Editable files: `model_config.yaml`, `backend/core/prompts/system_prompt.txt`, `backend/core/mcp/mcp_server.json`, `backend/core/skill_manager/skills_config.yaml`, `backend/api/markdown_rag/rag_config.yaml`.

## Validation strategy (no automated tests)

The repository has **no first-party tests** (no pytest/test files outside `.venv`). Validation relies on:

1. **Logs** — `backend/logs/<date>/app.log` (rotating, cumulative per day) and per-run `run_<time>_<pid>.log` (TTL-cleaned). Key signatures: `Agent 编译完成` (graph up), `MCP 服务 [x] 加载成功/失败`, `Subagent 配置加载失败: ...，返回空列表` (subagent breakage), `========== 检索开始/结束` (retrieval), `模型切换中间件启动`.
2. **Langfuse traces** — enabled by default (`LANGFUSE_TRACING_ENABLED`), session-scoped by `thread_id`; check the Langfuse dashboard for run-level behavior.
3. **LangSmith runtime evidence** — the OpenWiki workflow traces its own run to the `openwiki` LangSmith project; see [runtime behavior](runtime-behavior.md) for the current sample and what to watch.
4. **Import smoke check** — `python -c "import backend.main"` from the repo root (with venv active) exercises the whole import chain, but note it touches `.env`/`.env.api_key`, attempts the Langfuse auth check, and opens the Chroma client at import time, so it needs Ollama/Langfuse reachable or configured off.
5. **Frontend type check** — `cd frontend; npm run type-check` (vue-tsc) and `npm run build` (vue-tsc --noEmit + vite build).

## Common operational workflows

- **Enable a skill**: PUT `/settings/skills` with the desired names (or edit `skills_config.yaml` + `POST /settings/rebuild`); verify the agent sees `/active_skills/<name>` via logs.
- **Ingest documents**: place `.md` in the knowledge base (file panel), then `/rag` → Process tab → preview → commit; verify via the Health panel and `GET /api/rag/collection/sunzi/stats`.
- **Inspect a conversation branch**: `GET /checkpoints/<thread_id>/inputs`, replay or fork, then `GET /chat/<thread_id>/get-messages-history?checkpoint_id=<leaf>`.
- **Reset a WeChat conversation**: send `重置` in WeChat.

## Related pages

- [Backend config](backend/config.md) — every config surface
- [Architecture overview](architecture/overview.md) — component map
- [Runtime behavior](runtime-behavior.md) — production telemetry sample

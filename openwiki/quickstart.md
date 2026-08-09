---
type: guide
title: Index RAG — Wiki Quickstart
description: "Entry point for the Index RAG wiki: repository map, wiki structure, canonical homes for key concepts, a task-routing table from intent to pages/symbols/validation, cross-system workflows, and the backlog of valid deferrals."
tags: [wiki, quickstart, index-rag]
---

# Index RAG — Wiki Quickstart

This wiki documents **Index RAG**: a DeepAgents + LangGraph knowledge-retrieval agent. A FastAPI backend compiles one `index_agent` graph, streams SSE chat to a Vue 3 frontend (plus Electron desktop shell, WeChat bot, and CLI runtimes), persists conversations to SQLite checkpoints, and ingests Markdown knowledge into Chroma for retrieval-augmented generation.

There are **no automated tests in this repository** — validation is manual runs, log inspection, and Langfuse/LangSmith traces. Every page below therefore pairs the owning code with the narrowest validation command or manual exercise.

## Repository map

| Area | Owns | Entry points |
|---|---|---|
| Backend | FastAPI composition root, graph lifecycle, chat/threads/checkpoints/files/settings/RAG APIs | `backend/main.py`, `backend/api/services/graph.py` |
| Agent core | Graph assembly, model factory, middleware, composite backend, prompts, tools, skills, subagents | `backend/core/main_agent.py`, `backend/core/assembled/*` |
| CLI | Terminal chat runtime, chat logs, state snapshots | `backend/cli/interact.py` |
| WeChat bot | WeChat message bridge into the same graph | `backend/wechat_bot.py` |
| Frontend | Vue 3 chat workspace, files browser, RAG management, settings | `frontend/src/main.ts`, `frontend/src/chat/*` |
| Desktop | Electron launcher spawning backend + frontend | `desktop/main.js` |
| Data | SQLite checkpoints/store, Chroma vector DBs, filesystem knowledge base | `.env`-driven paths |

## Wiki structure

- [Architecture overview](architecture/overview.md) — the layered system map, runtimes, stores, and data-flow invariants.
- [Backend overview](backend/overview.md) — composition root, `graph_lifespan`/`rebuild_graph` lifecycle, dual `_graph`/`_agent_ctx` globals.
- [API layer](backend/api.md) — the 7 routers with full endpoint tables, schemas, error codes.
- [Chat flow](backend/chat-flow.md) — invoke/stream/resume, the shared `_sse_stream` (10 SSE event types), attachments, HITL, rubric, and the two message-normalization paths (`langchain_result_to_response` vs `message_to_response`).
- [Agent core](backend/agent-core.md) — `create_deep_agent` assembly, model factory and the **moonshot dead-end**, dynamic model switcher, middleware chain, composite backend, system prompt.
- [Tools](backend/tools.md) — MCP-injected tools, retrieval pipeline (recall → rerank → threshold), memory tools.
- [RAG pipeline](backend/rag-pipeline.md) — ingestion (`process_files_by_path`/`process_uploaded_files`), splitter, Chroma clients, collection admin, `save_VectorStore.py` CLI.
- [Checkpoints & threads](backend/checkpoints.md) — input/leaf semantics, replay/fork, leaf computation, direct-SQL diagnostics and the WAL caveat.
- [Files & settings](backend/files-settings.md) — path confinement (both `_safe_path` variants), file CRUD error codes, settings config-file mapping.
- [Config](backend/config.md) — env layering, `.env.example` boot gaps, `model_config.yaml`/`rag_config.yaml`, hot-reload chains, logging layout and TTL cleanup, Langfuse.
- [Memory & skills](backend/memory-skills.md) — memory vector store + tools, skills config and `SkillFilteredBackend`.
- [Subagents](backend/subagents.md) — subagent loader and the currently broken `subagents_config.py` import.
- [CLI](backend/cli.md) — interactive terminal runtime, `get_message_history`, `query_state`.
- [WeChat](backend/wechat.md) — `WeChatAgentBot` behavior.
- Frontend: [overview](frontend/overview.md), [chat](frontend/chat.md), [files](frontend/files.md), [rag](frontend/rag.md), [settings](frontend/settings.md).
- [Desktop](desktop.md) — Electron launcher.
- [Operations](operations.md) — runbook: how to run backend/frontend/CLI/WeChat, regenerate the OpenAPI client, and validate changes.
- [Runtime behavior](runtime-behavior.md) — LangSmith trace evidence: what the one captured sample does and does not prove.

## Key concepts (canonical homes)

- **SSE event contract** — 10 event types, input/leaf checkpoint kinds, interrupt → resume round-trip: [chat-flow.md](backend/chat-flow.md) (backend) and [frontend/chat.md](frontend/chat.md) (consumer).
- **Checkpoint branching** — input checkpoints anchor user turns, leaf checkpoints anchor branch heads; replay vs fork; send-time `checkpoint_id` re-attachment: [checkpoints.md](backend/checkpoints.md), [frontend/chat.md](frontend/chat.md).
- **Model selection layers** — build-time `active_provider` (`get_active_llm`) vs per-request `ModelContext` (`dynamic_model_switcher` with retries + `FALLBACK_CHAIN`): [agent-core.md](backend/agent-core.md).
- **Path confinement** — `file_service._safe_path` (bare `startswith`, prefix-confusion weakness) vs `memory_and_skill_service._safe_path` (separator-bounded): [files-settings.md](backend/files-settings.md).
- **Config layering** — env over YAML for LLM settings; pure YAML for RAG; hot-reload via `rebuild_graph` or `reload_rag_config`: [config.md](backend/config.md).
- **Logging** — daily `app.log` rotation + per-run `run_HH-MM-SS_pid<pid>.log`, TTL cleanup, context fields, heartbeat filtering: [config.md](backend/config.md).
- **RAG retrieval** — module-level Chroma clients (ingestion singleton, agent retriever, orphaned MCP duplicate): [rag-pipeline.md](backend/rag-pipeline.md), [tools.md](backend/tools.md).

## Task-routing table

| Intent / change area | Wiki page | Owning entrypoints / symbols | Narrowest validation |
|---|---|---|---|
| Trace a chat turn or add an SSE event | [chat-flow.md](backend/chat-flow.md), [frontend/chat.md](frontend/chat.md) | `routers/chat.py`, `chat_service.stream_chat`, `utils/stream.py:_sse_stream`, `useChatStream` | Run backend + frontend, send a message, inspect `backend/logs/<date>/app.log` |
| Change model provider / add a provider | [agent-core.md](backend/agent-core.md), [config.md](backend/config.md) | `model_factory.get_active_llm`, `llm_settings.reload_model_config`, `model_switcher.MODEL_MAP` | Edit `model_config.yaml`, `POST /settings/rebuild`, watch startup logs; `python -c "import backend.main"` |
| Fix or enable moonshot | [agent-core.md](backend/agent-core.md) | `env_api_key.py`, `llm_settings`, `model_factory`, `model_switcher` | Four-surface checklist in the moonshot section; verify no "未知" fallback warnings in logs |
| Branching / replay / fork / thread history | [checkpoints.md](backend/checkpoints.md) | `checkpoint_service.replay_from_checkpoint`/`fork_from_checkpoint`, `thread_service` | Send a message, `GET /checkpoints/{id}/inputs`, replay, fork, compare histories |
| File CRUD or path-safety changes | [files-settings.md](backend/files-settings.md) | `file_service.*`, `memory_and_skill_service.*`, `settings_service._resolve_path` | Try `../` traversal → expect 403 `FORBIDDEN_PATH`; rename with `/` → 400 |
| Env / config boot issues | [config.md](backend/config.md) | `env_settings.py`, `llm_settings`, `rag_setting` | `python -c "import backend.main"`; check `.env` has `MODEL_CONFIG_PATH` + `RAG_CONFIG_PATH` |
| RAG ingestion / splitter / Chroma | [rag-pipeline.md](backend/rag-pipeline.md) | `rag_service.process_files_by_path`, `save_VectorStore.MarkdownSplitter` | `POST /api/rag/process` with `preview_only=true`; inspect `chunks` + preview file |
| Agent tools / retrieval tuning | [tools.md](backend/tools.md) | `rag_tool/retrieve_tool.py`, `mcp_tool()`, memory tools | `python -m backend.cli.interact`, read two-stage retrieval logs |
| Memory / skills enablement | [memory-skills.md](backend/memory-skills.md) | `settings_service.get/update_skills_status`, `SkillFilteredBackend` | `PUT /settings/skills`, verify `ls /active_skills/` filtering via agent |
| Graph assembly / middleware / backend routes | [agent-core.md](backend/agent-core.md), [backend/overview.md](backend/overview.md) | `main_agent.init_graph`, `assembled/middleware.py`, `assembled/backends.py`, `graph.rebuild_graph` | `POST /settings/rebuild`; watch "Agent 编译完成" log |
| Logging layout / TTL | [config.md](backend/config.md) | `config/logger.py:setup_logging` | Restart backend, verify `logs/<date>/app.log` + new run file; set TTL `<=0` to disable cleanup |
| CLI interaction / HITL in terminal | [cli.md](backend/cli.md) | `cli/interact.py`, `cli/runtime/stream.py` | `python -m backend.cli.interact`, answer an interrupt decision |
| WeChat bot behavior | [wechat.md](backend/wechat.md) | `wechat_bot.py:WeChatAgentBot` | `python backend/wechat_bot.py`, scan QR, send a message |
| Frontend chat / SSE rendering | [frontend/chat.md](frontend/chat.md), [frontend/overview.md](frontend/overview.md) | `useChatController`, `useChatStream`, `sseChunkHandler` | `npm run type-check`; manual chat + checkpoint branch navigation |
| Frontend files / RAG / settings UI | [frontend/files.md](frontend/files.md), [frontend/rag.md](frontend/rag.md), [frontend/settings.md](frontend/settings.md) | `useFileManager`, `useRagManager`, `SettingsView` | `npm run type-check`; exercise each page against the running backend |
| Desktop one-click startup | [desktop.md](desktop.md) | `desktop/main.js` | `npm start` in `desktop/` |
| Runtime evidence / telemetry claims | [runtime-behavior.md](runtime-behavior.md) | LangSmith dump, `openwiki/.langsmith.json` | Re-pull connector data before citing new runtime facts |

## Cross-system workflows

1. **Web chat turn**: frontend → `POST /chat/{id}/stream` → `chat_service` → `_sse_stream` → graph → tools → checkpoints → SSE events → render. See [chat-flow.md](backend/chat-flow.md) + [frontend/chat.md](frontend/chat.md) (sequence diagram included).
2. **RAG ingest + retrieve**: RAG management page → `/api/rag/process` → chunk → preview → Chroma; agent `retriever_row_doc_tool` → vector recall → rerank → threshold. See [rag-pipeline.md](backend/rag-pipeline.md) + [tools.md](backend/tools.md).
3. **Checkpoint branch round-trip**: input/leaf events → replay/fork → send-time `checkpoint_id` continuation. See [checkpoints.md](backend/checkpoints.md).
4. **Config hot reload**: write config → `POST /settings/rebuild` → `rebuild_graph` (`aexit`/`aenter`) → new graph reads configs. See [config.md](backend/config.md).
5. **WeChat turn**: message → per-user thread → attachments → same `init_graph` lifecycle. See [wechat.md](backend/wechat.md).

## Backlog (valid deferrals)

- **`knowledge-base/` content** — Obsidian vault data, not code; referenced as the filesystem store in [architecture/overview.md](architecture/overview.md) only.
- **`my-tools/` deep dive** — standalone sibling LangGraph experiment, not imported by the backend; documented briefly in [my-tools.md](my-tools.md). Deferred details unless it becomes wired into the runtime.
- **`view_db/` viewer details** — `server-ops.md` references `view_db/start_chroma_server.py` and `view_chroma.py`, which do not exist in the repo (stale docs); covered only as a runbook note in [operations.md](operations.md).

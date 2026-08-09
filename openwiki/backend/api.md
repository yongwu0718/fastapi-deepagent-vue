---
type: api
title: Backend API Layer — Routers, Schemas, Error Handling
description: Complete endpoint tables for the seven FastAPI routers (chat, threads, checkpoints, files, settings, memory-and-skill, rag-pipeline), the Pydantic schema contracts, and the centralized error-code system.
tags: [backend, api, fastapi, endpoints, schemas]
---

# Backend API Layer

All routers are registered in `backend/main.py`. Prefixes: `/chat`, `/threads` (no prefix), `/checkpoints`, `/api/files`, `/settings`, `/settings/memory-and-skill`, `/api/rag`. Every endpoint is decorated with `@handle_endpoint_errors(...)` which maps exceptions to structured `{"error_code", "detail", ...}` responses (see [error handling](#error-handling) below).

## Chat — `backend/api/routers/chat.py` (prefix `/chat`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/chat/{thread_id}` | Non-streaming chat; `ChatResponse` |
| POST | `/chat/{thread_id}/stream` | SSE streaming chat (supports `checkpoint_id`, `checkpoint_ns`, `rubric`) |
| POST | `/chat/{thread_id}/resume` | Resume an interrupted run with HITL `decisions` (SSE) |
| POST | `/chat/{thread_id}/with-files` | Non-streaming chat with PDF/DOCX attachments (multipart) |
| POST | `/chat/{thread_id}/with-files/stream` | Streaming chat with attachments (multipart, SSE) |

Request/response contracts (see [chat flow](chat-flow.md)):
- `ChatRequest`: `messages[1..]` (`role` user/assistant/system, `content` string or content-blocks list), optional `checkpoint_id`, `checkpoint_ns`, `rubric` (Loop Engineering completion condition).
- `ResumeRequest`: `decisions[1..]` of `{type: approve|reject|edit, edited_action?}`.
- `ChatResponse`: `messages[]` (`MessageResponse` with `role`, `content`, `reason_content`, `id`), `head_checkpoint_id`.

## Threads — `backend/api/routers/threads.py`

| Method | Path | Purpose |
|---|---|---|
| GET | `/chat/{thread_id}/get-messages-history` | Latest state, or a specific checkpoint's branch when `checkpoint_id` given |
| DELETE | `/chat/{thread_id}/delete-messages-history` | Delete thread (direct SQL, not graph) |
| GET | `/threads` | List all threads (SQL `list_all_threads`) |

## Checkpoints — `backend/api/routers/checkpoints.py` (prefix `/checkpoints`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/checkpoints/{thread_id}/inputs` | Paginated input/fork checkpoint history with leaf computation |
| POST | `/checkpoints/{thread_id}/replay` | Replay from a checkpoint (SSE); optional injected `messages` |
| POST | `/checkpoints/{thread_id}/fork` | Fork a new branch from a checkpoint with new `values` (SSE) |

Schemas in `backend/api/schemas/checkpoint.py`: `ReplayRequest {checkpoint_id, checkpoint_ns?, messages?}`, `ForkRequest {checkpoint_id, checkpoint_ns?, values}`, `CheckpointSummary` (config, next_nodes, input_preview, parent_checkpoint_id, source, leaf_checkpoint_id, trigger_message_id), `CheckpointHistoryResponse`. Behavior details in [checkpoints](checkpoints.md).

## Files — `backend/api/routers/files.py` (prefix `/api/files`)

Serves the knowledge-base root (`DOC_INDEX`, fallback `knowledge-base`):

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/files/list?path=` | Directory listing (dirs first, name-sorted) |
| GET | `/api/files/file?path=` | Raw file (FileResponse, preview/download) |
| GET | `/api/files/read?path=` | JSON: content, content_type, editable |
| GET | `/api/files/search?q=` | Recursive name search |
| POST | `/api/files/create-file` / `/create-directory` | Create file/dir |
| POST | `/api/files/upload?path=` | Upload to path |
| PUT | `/api/files/rename` / `/move` / `/modify` | Rename, move, overwrite content |
| DELETE | `/api/files/delete` | Recursive delete |

All paths are validated by `_safe_path()` against `ROOT_DIR` (traversal guard; 403 `FORBIDDEN_PATH`). Editable-extension allowlist governs `editable` flag. See [files & settings services](files-settings.md).

## Settings — `backend/api/routers/settings.py` (prefix `/settings`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/settings/model-config/read?path=key` | Read one mapped config file (`model`, `prompt`, `mcp`, `skills_config`) |
| PUT | `/settings/model-config/write` | Overwrite that file |
| GET | `/settings/skills` | Skill list + enabled state (scans dirs for `SKILL.md`) |
| PUT | `/settings/skills` | Update enabled list and **rebuild the graph** |
| POST | `/settings/rebuild` | Rebuild the graph from config files |

The memory-and-skill router (`/settings/memory-and-skill`, in `memory_and_skill.py`) mirrors the files router but with a `type` query (`memory` or `skills`) selecting the root (`MEMORY_DIR` / `SKILLS_DIR`) — same CRUD surface: list/file/read/search/create-file/create-directory/upload/rename/move/modify/delete.

## RAG pipeline — `backend/api/routers/rag_pipeline.py` (prefix `/api/rag`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/rag/process` | Process `.md` files by server path; `preview_only` supported |
| POST | `/api/rag/process/upload` | Process uploaded `.md` files (multipart); `preview_only` |
| POST | `/api/rag/delete` | Delete documents by ID list |
| GET | `/api/rag/health` | Vector-store health |
| GET/PUT | `/api/rag/config` | Read/overwrite `rag_config.yaml` (auto-reload) |
| GET | `/api/rag/collections` | List Chroma collections |
| GET | `/api/rag/collection/{name}/stats` | Stats (count, non-empty rate, avg length, dims, metadata coverage); `sample_limit` 100..100000 |
| GET | `/api/rag/collection/{name}/documents` | Paginated docs (ID, content, metadata) |
| POST | `/api/rag/collection/{name}/delete-docs` | Batch delete by IDs |
| POST | `/api/rag/collection/{name}/clear` | Clear all docs in collection |
| DELETE | `/api/rag/collection/{name}` | Drop the collection |

Schemas in `backend/api/schemas/rag_pipeline.py` (13 KB) define `RAGProcessRequest/Response` (chunk details, preview paths), `RAGFullConfigModel` (splitter + hnsw + collection), `CollectionStatsResponse`, etc. Service behavior in [RAG pipeline](rag-pipeline.md).

## Schemas — `backend/api/schemas/`

| File | Contents |
|---|---|
| `request.py` | `Message`, `ChatRequest` |
| `response.py` | `MessageResponse`, `ChatResponse`, `StreamResponse` (SSE payload with `type` union: text, reasoning, tool_call, tool_result, error, done, interrupt, checkpoint, rubric, image) |
| `interrupt.py` | `Decision`, `ResumeRequest` |
| `checkpoint.py` | replay/fork requests, `CheckpointSummary`, history response |
| `files.py` | create/rename/move/modify/delete requests |
| `rag_pipeline.py` | RAG process/config/collection models |
| `error.py` | generic error response |
| `settings.py` | `SkillsUpdateRequest` |

## Error handling

- `backend/api/utils/exceptions.py` defines the `ErrorCode` enum (INTERNAL_ERROR, GRAPH_NOT_INITIALIZED, THREAD_*, CHECKPOINT_*, CHAT_*, STREAM_INTERNAL_ERROR, RAG_*, FILE_*/PATH_* etc.) and `AppException(HTTPException)` with subclasses `NotFoundException` (404), `InternalErrorException` (500), `UnavailableException` (503).
- `backend/api/utils/error_handlers.py` `register_exception_handlers(app)` installs global handlers (AppException → error_code JSON; framework errors → mapped codes via `_STATUS_TO_ERROR_CODE`).
- The `@handle_endpoint_errors` decorator logs `log_msg` and converts any exception into the router's declared `ErrorCode` without leaking stack traces to clients.

## Related pages

- [Chat flow](chat-flow.md) — service implementation behind the chat endpoints
- [Checkpoints](checkpoints.md) — branch/replay/fork semantics
- [Files & settings services](files-settings.md) — path-safety and file mapping
- [RAG pipeline](rag-pipeline.md) — ingestion and collection management

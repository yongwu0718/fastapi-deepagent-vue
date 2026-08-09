---
type: component
title: Agent Tools — MCP Injection, Retrieval, Memory, Shell and Code Interpreter
description: "The full tool inventory available to the compiled agent: MCP servers loaded from mcp_server.json (math, WebSearch, lark), the two-stage retrieval tool, the five memory tools, plus shell/filesystem backends and the quickjs code interpreter."
tags: [backend, tools, mcp, rag, memory]
---

# Agent Tools

The compiled graph receives `tools = [*mcp_tools, retriever_row_doc_tool, save_memory, delete_memory, search_memory, get_memory, list_memory_keys]` plus the tools added by middleware (`FilesystemMiddleware` shell/file tools, quickjs `CodeInterpreterMiddleware` tool, and optionally the manual summarization tool which is disabled). All external tools are injected via MCP — there is no hardcoded tool registry (commit history: "将所有tool通过mcp进行注入，没有硬编码tool", 2026-07-19).

## MCP tool loading — `backend/core/mcp/mcp_tool.py`

`mcp_tool()` (async, called at each graph build):

1. Reads `backend/core/mcp/mcp_server.json` (note: path is relative to the module file, NOT the `MCP_SERVER_DIR` env var — see [config](config.md)).
2. Recursively substitutes `{VAR}` placeholders — built-ins first (`PYTHON_EXECUTABLE`, `MCP_SERVER_DIR`), then env vars; unresolved placeholders are kept as-is.
3. Warns on deprecated `sse` transports (registry currently uses `stdio` and `http`).
4. Loads each server via `MultiServerMCPClient({name: config})` → `client.get_tools()`; a failing server logs a warning and is skipped (per-server isolation), so tool availability depends on env secrets being present (`DASHSCOPE_API_KEY` for WebSearch, `App_ID`/`App_Secret` for lark).

| Server | Transport | Tools | Depends on |
|---|---|---|---|
| `math` | stdio | `add`, `multiply` (FastMCP server in `local_mcp.py`) | Python env only |
| `WebSearch` | http (streamable) | Aliyun web search MCP | `DASHSCOPE_API_KEY` |
| `lark-mcp` | stdio (`npx -y @larksuiteoapi/lark-mcp`) | Feishu calendar preset | `App_ID`, `App_Secret`, node/npx |

`backend/core/mcp/fastmcp_search.py` and the `memory_tool.py`/`retrieve_tool.py` FastMCP servers exist as standalone MCP servers (stdlib `mcp.run()`), but the **compiled graph does not use them**: `mcp_tool()` only loads servers listed in `mcp_server.json`, and the retrieval/memory tools reach the graph directly via `rag_tool/` imports, not through MCP.

## Two-stage retrieval — `backend/core/rag_tool/retrieve_tool.py`

`retriever_row_doc_tool(question)` → `retrieve_with_rerank_text(question, rerank_threshold=0.5, initial_k=50)`:

1. **Recall**: `_vectorstore.similarity_search(question, k=50)` against Chroma collection `sunzi` (module-level `Chroma` opened at import; embedding via Ollama).
2. **Rerank + filter**: `rerank_model.compress_documents(docs, question)` (DashScope `gte-rerank-v2`, top_n=10); keeps docs with `relevance_score >= 0.5`.
3. **Fallbacks** (source-grounded): rerank failure → degrade to vector order (`docs[:top_n]`); no doc above threshold → return the single top reranked doc with a warning; empty recall → `{"documents": [], "error": "未召回任何文档。"}`.
4. Returns JSON: `{"documents": [{content, metadata}], "question", "error}`.

Every stage is timed via `_timed()` and logged at INFO — retrieval latency is observable in `backend/logs/`.

## Memory tools — `backend/core/rag_tool/memory.py` (MemoryStore)

Five tools over a dedicated Chroma collection (`memory`, same persist dir):

| Tool | Behavior |
|---|---|
| `save_memory(key, value)` | upsert document; `content` becomes page_content, everything else packed into JSON metadata |
| `search_memory(query, k=5, threshold=0.4)` | `similarity_search_with_score(k*2)`, keeps rows with distance ≤ threshold (lower = closer) |
| `delete_memory(key)` | `adelete(ids=[key])` |
| `get_memory(key)` | exact fetch by ID, unpacks metadata JSON |
| `list_memory_keys(page_size=100, max_keys=1000)` | paginated ID listing |

`filter_complex_metadata()` serializes dict/list metadata values to JSON so Chroma accepts them. HNSW config for memory: cosine, ef_construction 200, max_neighbors 32, ef_search 200.

## Shell / filesystem / code tools

- `FilesystemMiddleware` (DeepAgents) exposes shell `execute` + file tools routed through the [CompositeBackend](agent-core.md) (`/memory/`, `/active_skills/`, `/knowledge/` virtual routes; default LocalShellBackend rooted at `WORKSPACE_DIR` with merged PATH).
- `CodeInterpreterMiddleware` (langchain_quickjs) exposes a JS sandbox tool; the billing subagent prompt mandates using it for all arithmetic, but the subagent itself is currently inactive (see [subagents](subagents.md)).

## Runtime usage evidence

Observed per-tool usage from the LangSmith sample: **none** — the single sampled trace (project `openwiki`, error bucket) failed at the model-call step before any tool could be invoked, so this pull provides no per-tool call counts, latencies, or token costs. See [runtime behavior](../runtime-behavior.md) for the full scoped statement.

## Related pages

- [Agent core](agent-core.md) — middleware that adds shell/code tools
- [RAG pipeline](rag-pipeline.md) — how documents get into the `sunzi` collection
- [Memory & skills](memory-skills.md) — the skills backend routes
- [Runtime behavior](../runtime-behavior.md) — runtime evidence register

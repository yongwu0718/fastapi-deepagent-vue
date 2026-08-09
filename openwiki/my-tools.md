---
type: component
title: my-tools — Sibling Standalone Agent Experiment
description: "A separate, self-contained LangGraph agent tree (own config, tools, graph) that is never imported by the backend — treat as scratch/experiment code when changing the main agent."
tags: [my-tools, experiment, langgraph]
---

# my-tools — Standalone Experiment Tree

`my-tools/` is a **sibling, self-contained agent project** that predates or parallels the main backend. Grep across `backend/` finds no importers of `my-tools.*`, so it does not participate in any runtime of the web/CLI/WeChat paths.

## Contents

| Path | What it is |
|---|---|
| `agent/graph_compile.py` | its own `init_graph()` — a small StateGraph (call_llm → tools → call_llm) with its own `config/env.py`, `config/model_config.py` (llm_ali + embeddings), `config/logger.py`, `tools/calculator.py`, `tools/chroma_memory.py`, `tools/memory_tool.py` |
| `agent/nodes/nodes.py` | LLM node factory mirroring `backend/core/subagent/langgraph_subagent/nodes.py` |
| `agent/checkpoint_logic/` | standalone scripts: `input-checkpoints.py`, `replay-graph.py`, `fork-graph.py`, `state-history.py` — exploratory checkpoint experiments |
| `agent/logic_continue/call_tool.py` | continuation experiment |
| `agent/interact.py` | terminal loop for this graph |
| `bilibili_load.py`, `pdf_load.py`, `pdf-a.py`, `image-ocr.py`, `clean.py` | standalone utility scripts (duplicate `clean.py` with `backend/rag_pipeline/clean_file.py`) |
| `billing.db` | SQLite bill database (also duplicated as `my-tools/agent/billing.db`) |
| `skill/langchain/`, `skill/my-chat/` | skill prototypes (my-chat has a 19 KB SKILL.md) |

## Why it matters to agents

- Do not confuse this tree with the production agent: changes here have no effect on the backend.
- The checkpoint experiment scripts here may be useful reference for the semantics now implemented in `backend/api/services/checkpoint_service.py`, but the production code is authoritative.
- `my-tools/clean.py` and `backend/rag_pipeline/clean_file.py` are near-duplicates; changes to document cleaning should go to the backend copy that the CLI uses.

## Related pages

- [Backend overview](backend/overview.md) — the production agent assembly
- [Backend checkpoints](backend/checkpoints.md) — production checkpoint services

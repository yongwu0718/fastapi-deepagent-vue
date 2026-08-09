---
type: component
title: Subagents — Loader, Config, and Stale Import Paths
description: "How subagents are hot-loaded (subagent_loader + subagents_config.py), the intended bill-analyzer subagent, and the stale imports that currently make subagent loading fail silently to an empty list."
tags: [backend, subagents, deepagents]
---

# Subagents

## Intended design

`backend/memory_skill/skill/subagents/scripts/`:

- `subagent_loader.py` — `load_subagents()` hot-reloads `subagents_config.py` via `importlib` (removes the cached module, executes it from disk) every time the graph is built. Mirrors the `mcp_tool()` pattern: config/loader separation, per-item failure isolation, zero-downtime reload. **On any exception it logs a warning and returns `[]`** — a failed config does not crash the agent.
- `subagents_config.py` — defines `bill_analyzer` (name `bill-analyzer`): a personal-finance analyzer subagent with `tools=[analyze_billing, analyze_monthly, analyze_expense, analyze_monthly_categories, save_bill]` and `model=llm_ali` (evaluator model differs from the main agent's DeepSeek), plus `system_prompt` describing the analysis workflow.

`create_deep_agent(subagents=subagents_config)` is called in `main_agent.py`; DeepAgents exposes subagents to the main agent as delegatable tools.

## Current state: stale imports break loading

Two import chains are broken against the actual tree:

1. `subagents_config.py` does `from backend.core.utils import (analyze_billing, analyze_monthly, analyze_expense, analyze_monthly_categories, save_bill)` — but **`backend/core/utils` does not exist**. The real functions live in `backend/memory_skill/skill/billing_analyze/scripts/billing/analyze_billing.py` (`analyze_billing` at line 214) plus sibling `clean_alipay_bill.py`/`clean_wechat_bill.py`/`common.py` modules and the billing skill's scripts.
2. `backend/core/subagent/langgraph_subagent/graph_compile.py` imports `backend.core.subagent.bill_subagent.billing` (also nonexistent). `rag_subagent/rag_factory.py` (a vendored-looking copy of `deepagents` agent assembly) and `langgraph_subagent/` (a small StateGraph billing agent with its own prompt/nodes) are **orphaned** — grep finds no importers anywhere in `backend/`.

Consequences:

- `load_subagents()` swallows the `ModuleNotFoundError` and returns `[]`, so the compiled `index_agent` runs with **zero subagents** and the bill-analyzer is not available to users, despite `skills_config.yaml` enabling `subagents` and `billing_analyze`.
- The orphaned `langgraph_subagent/` graph code (billing analysis with an `eval` sandbox mandate, `analyze_monthly` three-tier expense model) is dead code that documents the original intent.

## What changing this area requires

To re-enable the bill-analyzer subagent:

1. Fix `subagents_config.py` imports to point at the real billing modules (e.g. the `billing_analyze/scripts/billing/` package), or introduce a `backend/core/utils` package re-exporting them.
2. Optionally delete the orphaned `langgraph_subagent/` + `rag_subagent/` trees or wire them into the loader.
3. Rebuild the graph (`POST /settings/rebuild`) and verify via the log line `Subagent 配置加载完成，共 N 个` — the current observable signature is the warning `Subagent 配置加载失败: ...，返回空列表`.

There is no test coverage for the loader; the log line is the primary validation signal.

## Related pages

- [Backend overview](overview.md) — where `load_subagents()` is invoked
- [Memory & skills](memory-skills.md) — the billing_analyze skill and SKILL.MD mismatch
- [Agent core](agent-core.md) — the main agent assembly

---
okf_version: "0.1"
---

# Files

- [Desktop Shell — Electron Orchestrator](desktop.md) - The Electron wrapper that spawns the FastAPI backend and Vite frontend as subprocesses, waits for readiness, shows a tray-resident window, and cleans up child processes and ports on exit.
- [my-tools — Sibling Standalone Agent Experiment](my-tools.md) - A separate, self-contained LangGraph agent tree (own config, tools, graph) that is never imported by the backend — treat as scratch/experiment code when changing the main agent.
- [Operations — Run, Configure, and Validate](operations.md) - Runbook for the whole stack: backend, frontend, desktop, WeChat, CLI, LangGraph server, Chroma viewers; OpenAPI client regeneration; config hot-reload; and the no-tests validation strategy based on logs and tracing.
- [Index RAG — Wiki Quickstart](quickstart.md) - Entry point for the Index RAG wiki: repository map, wiki structure, canonical homes for key concepts, a task-routing table from intent to pages/symbols/validation, cross-system workflows, and the backlog of valid deferrals.
- [Runtime Behavior — LangSmith Evidence for This Repository](runtime-behavior.md) - Consolidated production telemetry from the LangSmith connector pull: one error trace from the OpenWiki CLI agent (model-name typo 400), middleware timing, sample-bias caveats, and what it means for agents working here.

# Directories

- [architecture](architecture/)
- [backend](backend/)
- [frontend](frontend/)

---
type: component
title: Memory Rules and Skills System — /memory, /active_skills, SkillFilteredBackend
description: "The agent's memory rule file (AGENT.md), the skills directory tree with SKILL.md conventions, skills_config.yaml enablement, SkillFilteredBackend filtering, and the SKILL.MD naming mismatch that hides billing_analyze."
tags: [backend, skills, memory, filesystem]
---

# Memory Rules and Skills System

## Memory rule file

`create_deep_agent` receives `memory=["/AGENT.md"]`, which maps through the composite backend's filesystem to `backend/memory_skill/memory/AGENT.md`. That file is currently **empty** (0 bytes), so the agent loads no memory rules from it. The `memory` config is a DeepAgents "memory rule" mechanism (AGENTS-style rules the agent loads at startup), distinct from the vector **memory store** (the five `MemoryStore` tools in [tools](tools.md)).

## Skills directory tree

`backend/memory_skill/skill/` holds one directory per skill, each with a `SKILL.md` (front-matter `name`/`description` + workflow) and often `references/`, `assets/`, `scripts/`:

- Standard skills: `fastapi`, `fastapi-best-practices`, `fastapi-debug-guides`, `fastapi-security`, `fastapi-testing`, `vue-*` family, `docker-*` family, `gonghao-baowen-writing`, `subagents`, `sunzi-bingfa`, `task-planner`, `vocab-tutor`.
- `billing_analyze` uses `SKILL.MD` (capitalized extension, 14 KB) with `scripts/billing/*.py` analysis modules and a `ledger_server.py` Streamlit ledger — see the [subagents](subagents.md) page for how its functions are wired.

The DeepAgents `skills=["/active_skills/"]` config makes the agent load skill sources from the `/active_skills/` virtual route, which is the `SkillFilteredBackend`-wrapped filesystem rooted at `SKILLS_DIR`.

## Enable/disable — `skills_config.yaml` + `SkillFilteredBackend`

- `backend/core/skill_manager/skills_config.yaml` holds `enabled:` names (currently billing_analyze, fastapi, gonghao-baowen-writing, subagents, sunzi-bingfa, task-planner, vocab-tutor).
- `SkillFilteredBackend` (`backend/core/skill_manager/filtered_backend.py`) wraps the skills `FilesystemBackend` and filters `ls`/`als` results: a directory whose basename is not in `enabled` is hidden from the agent. All other backend methods pass through.
- `backend/api/services/settings_service.py` `get_skills_status()` scans `SKILLS_DIR` for directories containing `SKILL.md` (exact name — see mismatch below) and compares against the config; `update_skills_status()` validates names against disk, writes the YAML, and the router then calls `rebuild_graph()` so the new junction takes effect.

### Naming mismatch (SKILL.MD vs SKILL.md)

`billing_analyze`'s file is `SKILL.MD`. `settings_service` and the skills scan only recognize `SKILL.md`, so `billing_analyze` is **invisible to both the settings UI skill list and the enabled-state check** even though it is listed in `skills_config.yaml`. The DeepAgents skills loader has its own conventions; the practical effect is that this skill's directory is not uniformly discoverable through the repo's own tooling. When changing this area, keep both the config entry and the filename case consistent.

## How the agent experiences skills

1. The agent lists `/active_skills/` → only enabled directories appear.
2. Per the system prompt, the agent reads a skill's `SKILL.md` once per session (counts against its message budget) and applies the workflow.
3. The system prompt also instructs the agent to translate the virtual path `/active_skills/` to the local path `F:\index_rag\backend\memory_skill\skill\` before running shell commands against it.

## Related pages

- [Agent core](agent-core.md) — CompositeBackend routes and system prompt
- [Tools](tools.md) — the vector memory store (distinct from the memory rule file)
- [Subagents](subagents.md) — the `subagents` skill and billing functions
- [Frontend settings](../frontend/settings.md) — the skills manager UI

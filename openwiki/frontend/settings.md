---
type: component
title: Frontend Settings — Six-Tab Configuration Console
description: "The /settings page with exactly six tabs (model, prompts, mcp, memory, skill-files, skill-manage), the model config form including the dead moonshot provider surface, and the skills enable/disable manager."
tags: [frontend, settings, configuration]
---

# Frontend Settings

`src/settings/` implements the `/settings` route. `SettingsView.vue` defines **exactly six tabs** (verified at lines 16-25):

1. **model** — `ModelConfigForm.vue` (17 KB)
2. **prompts** — `ConfigEditor.vue` over the system prompt file
3. **mcp** — `ConfigEditor.vue` over `mcp_server.json`
4. **memory** — memory file manager
5. **skill-files** — skills file manager
6. **skill-manage** — `SkillManager.vue` enable/disable

`ConfigEditor.vue` is a generic YAML/Markdown editor mapped to the settings service keys (`model` → `MODEL_CONFIG_PATH`, `prompt` → `SYSTEM_PROMPT_PATH`, `mcp` → `MCP_SERVER_PATH`, `skills_config` → `SKILLS_CONFIG_PATH`).

## ModelConfigForm — provider forms and the moonshot gap

`ModelConfigForm.vue` renders per-provider form sections (DeepSeek, Aliyun, Ollama, OpenAI, **Moonshot**) and writes the chosen `active_provider` + provider fields into `model_config.yaml`. The Moonshot section includes `model` and `thinking` fields (lines 110-113, 182-183, 377-381).

**Important: the moonshot provider is configured-but-unused.** `backend/core/models/llm_settings.py` reads no moonshot keys, `model_factory._PROVIDER_FACTORIES` maps only deepseek/ali/ollama/openai, and `model_switcher.MODEL_MAP` has no moonshot entry. Selecting Moonshot in this form writes config that takes no effect — `get_active_llm()` logs a warning and silently falls back to deepseek (see [backend config](../backend/config.md) and [agent core](../backend/agent-core.md)). Editing this form is safe (it only writes YAML) but choosing moonshot will not switch the runtime model.

## SkillManager

`SkillManager.vue` lists skills via `GET /settings/skills` and PUTs the enabled list to `PUT /settings/skills`, which rewrites `skills_config.yaml` and triggers a graph rebuild. Note that `billing_analyze` is invisible here because its file is named `SKILL.MD`, not `SKILL.md` (see [backend memory & skills](../backend/memory-skills.md)).

## FileManager

The memory/skill file tabs reuse `FileManager.vue` (13 KB) against `/settings/memory-and-skill/*?type=memory|skills` — CRUD over `MEMORY_DIR` and `SKILLS_DIR`.

## Related pages

- [Backend files & settings](../backend/files-settings.md) — services behind these tabs
- [Backend config](../backend/config.md) — the files being edited and env mapping
- [Backend agent core](../backend/agent-core.md) — how active provider is resolved

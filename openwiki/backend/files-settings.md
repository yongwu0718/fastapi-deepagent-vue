---
type: component
title: File Management and Settings Services — Path Safety and Config File Mapping
description: "The knowledge-base file service and memory/skills file service (safe path resolution, CRUD, search, editable types) plus the settings service that maps named config keys to files and manages skill enablement."
tags: [backend, files, settings, security]
---

# File Management and Settings Services

## Knowledge-base file service — `backend/api/services/file_service.py`

Root: `DOC_INDEX` env or fallback `Path(_PROJECT_ROOT).parent.parent / "knowledge-base"` (i.e. the repo's `knowledge-base/`).

- `_safe_path(sub_path)`: `full_path = (ROOT_DIR / sub_path).resolve()` then rejects with 403 `FORBIDDEN_PATH` when `str(full_path).startswith(str(ROOT_DIR))` is false. Note the check is a bare `str.startswith` with **no separator appended**, so a sibling whose path shares the root's string prefix (e.g. root `/data/knowledge-base` vs sibling `/data/knowledge-base-extra`) passes the check — a known prefix-confusion weakness. Normal `../` traversal is still blocked because `.resolve()` collapses the traversal before the prefix test.
- `list_directory(path)` — dirs-first, name-sorted listing with size/modified.
- `get_file_path` / `read_file_content` — returns `{path, content, content_type, size, editable}`; images (png/jpg/jpeg/gif/webp/svg/avif/bmp) return content_type `image` with empty content and `editable=false`; un-decodable binaries return content_type `binary`, `editable=false`; `editable` is true only when the suffix is in the allowlist below.
- CRUD + error codes: `create_file` (409 `FILE_ALREADY_EXISTS` when target exists), `create_directory` (409 `DIR_ALREADY_EXISTS`), `upload_file` (overwrite), `rename_path`, `move_path`, `modify_file_content` (overwrite), `delete_path` (recursive `shutil.rmtree` for directories). Missing targets raise `PATH_NOT_FOUND`; a listed path that is not a directory raises 400 `NOT_A_DIRECTORY`; rename/move onto an existing name raises 409 `FILE_ALREADY_EXISTS`. `rename_path` rejects a `new_name` containing `/` or `\` with 400 `INVALID_OPERATION` ("新名称不能包含路径分隔符") so a rename can never relocate the entry into another directory.
- `search_files(q)` recursively matches names; result items include a `path` field (relative path), unlike `list_directory` items which only carry `name/type/size/modified`.
- Editable allowlist: `.md .txt .py .js .ts .html .css .json .xml .yaml .yml .toml .cfg .ini .env .sh .bat .sql .csv .log .vue .jsx .tsx .java .go .rs .cpp .c .h .rb .php .swift .kt`.

## Memory & skills file service — `backend/api/services/memory_and_skill_service.py`

Same CRUD surface, parameterized by `type`:

- `_ROOTS["memory"] = MEMORY_DIR`, `_ROOTS["skills"] = SKILLS_DIR`.
- `_safe_path(type, sub_path)` appends a path separator to **both** sides before comparing — `(str(full_path) + sep).startswith(root_str + sep)` with `sep` chosen from the root's own separator flavor — so containment is confined to the exact root and the root itself passes (`root/` is a prefix of `root/`); this closes the prefix-confusion hole that `file_service._safe_path`'s bare `startswith` leaves open.
- The router `/settings/memory-and-skill/*` adds the `type` query (`memory`|`skills`) to every operation.
- Response-shape difference: `memory_and_skill_service.list_directory` items include a `path` field per item (name/type/path/size/modified), while `file_service.list_directory` items do not; both services expose the same CRUD operations otherwise.

## Settings service — `backend/api/services/settings_service.py`

- `_FILE_PATHS` maps frontend keys to resolved paths from env: `model` → `MODEL_CONFIG_PATH`, `prompt` → `SYSTEM_PROMPT_PATH`, `mcp` → `MCP_SERVER_PATH`, `skills_config` → `SKILLS_CONFIG_PATH`. Unmapped keys → 400 `FORBIDDEN_PATH`. Note the `mcp` mapping is only correct when `MCP_SERVER_DIR` points at the real `backend/core/mcp/mcp_server.json` — the `.env.example` value is stale (see [config](config.md)).
- `_resolve_path(key)` looks the key up in `_FILE_PATHS`; keys not configured from `.env` raise 400 `FORBIDDEN_PATH` ("未配置的文件"). `read_config_file(key)` / `write_config_file(key, content)` read/overwrite only those allowlisted files (`.yaml .yml .json .txt .md .toml .cfg .ini .py .js .ts .html .css .xml` are editable; binary files are returned non-editable).
- Skills status: `get_skills_status()` scans `SKILLS_DIR` for dirs containing `SKILL.md` and compares to the enabled list; `update_skills_status(enabled)` filters against disk-valid names, writes `skills_config.yaml` via `yaml.dump`, and the router then triggers `rebuild_graph()`.

## Security invariants

- All file paths cross a containment check before any filesystem operation; traversal attempts are logged (`[安全] 禁止访问`) and return 403.
- The settings service never exposes arbitrary paths — only the four env-mapped config files.

## Related pages

- [API layer](api.md) — endpoint tables
- [Frontend files](../frontend/files.md) — the browser UI
- [Frontend settings](../frontend/settings.md) — the settings UI
- [Config](config.md) — env path mapping and the MCP_SERVER_DIR staleness

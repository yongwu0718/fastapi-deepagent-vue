---
type: component
title: Frontend Files — Knowledge-Base File Browser
description: "The file management panel inside the chat layout: directory tree and breadcrumbs, Markdown/text/image/PDF preview, CRUD operations, drag-and-drop and paste upload, and per-feature composables."
tags: [frontend, files, browser]
---

# Frontend Files

`src/files/` implements the left-side file browser inside the chat layout, talking to `/api/files/*` (knowledge-base root, see [backend files & settings](../backend/files-settings.md)).

## Components

| File | Responsibility |
|---|---|
| `FileBrowser.vue` (22 KB) | main browser UI: tree/list, breadcrumbs, context actions |
| `core/useFileState.ts` | directory listing state, current path |
| `core/useFilePersistence.ts` | last-visited path persistence |
| `features/useFileDirectory.ts` | directory navigation |
| `features/useFileOps.ts` | create/rename/move/delete operations |
| `features/useFileTabs.ts` | open-file tabs (preview stack) |
| `features/useFileSearch.ts` | name search |
| `features/useFileSplit.ts` | split view handling |
| `preview/`, `rendering/`, `dialogs/`, `layout/` | preview renderers (Markdown / text / image / PDF), confirm dialogs, panel layout |

## Behavior

- Listings come from `GET /api/files/list?path=`, file content from `GET /api/files/read?path=` (JSON with `editable` flag) or `GET /api/files/file` (raw download/preview).
- Uploads: `POST /api/files/upload?path=` (multipart) triggered by drag-and-drop or paste; downloads use the raw file endpoint.
- Writes (`modify`, `create-file`, `rename`, `move`, `delete`) map one-to-one to the backend routes; destructive ops show confirmation dialogs.
- The file manager also serves as the document store for the RAG pipeline — users place `.md` files here, then use the RAG page to ingest them.

## Related pages

- [Backend files & settings](../backend/files-settings.md) — the service + path-safety rules
- [Frontend overview](overview.md) — layout hosting this panel
- [Frontend rag](rag.md) — ingestion of files placed here

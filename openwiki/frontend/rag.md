---
type: component
title: Frontend RAG — Vector Store Management UI
description: "The /rag page: four tabs (Process, Browse, Config, Health) for preview-then-commit ingestion, Chroma collection browsing, live rag_config.yaml editing, and vector store health monitoring."
tags: [frontend, rag, chroma]
---

# Frontend RAG

`src/rag/` implements the `/rag` route — the vector store management console.

## Tabs and composables

| Tab | View | Composables | Backend |
|---|---|---|---|
| Process | `ProcessTab.vue` — upload or path ingestion, preview chunks table, confirm commit | `useRagManager`, `useRagProcess`, `useRagUpload` | `POST /api/rag/process`, `POST /api/rag/process/upload?preview_only=` |
| Browse | `BrowseTab.vue` — collection documents browsing | `useRagBrowse` | `GET /api/rag/collections`, `/collection/{name}/documents`, `/stats`, `delete-docs`, `clear`, `DELETE collection` |
| Config | `ConfigTab.vue` — edit `rag_config.yaml` online | `useRagConfig` | `GET/PUT /api/rag/config` |
| Health | `HealthPanel.vue` — collection status panel (10 s auto-refresh) | `useRagHealth` | `GET /api/rag/health` |

`useRagTabs.ts` manages tab state; `useRagManager.ts` (13 KB) is the central controller: it drives the two-step workflow (preview → confirm), collects per-file chunk details (index, header path, length, split type), and calls commit only after user confirmation.

## The preview → confirm workflow

1. User picks `.md` files (drag-drop/multipart) or server paths (JSON mode), sets `preview_only=true` → backend returns per-file chunk detail tables.
2. User reviews chunk quality (header paths, content preview, lengths) in `ProcessTab`.
3. "确认入库" re-submits with `preview_only=false` → backend writes chunks to Chroma.

This UI is the primary ingestion path — see [backend RAG pipeline](../backend/rag-pipeline.md) for the server-side semantics and the `rag_config.yaml` fields the Config tab edits.

## Related pages

- [Backend RAG pipeline](../backend/rag-pipeline.md) — endpoints and chunking
- [Frontend overview](overview.md) — routing
- [Frontend files](files.md) — where source `.md` files live

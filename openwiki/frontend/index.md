# Files

- [Frontend Chat — Controller, SSE Streaming, HITL Approval, Checkpoint Branch UI, Tool Cards](chat.md) - The chat workspace: useChatController orchestration, useChatStream + SSE chunk handler (10 event types), approval cards for HITL, checkpoint retry/fork branch navigation, and tool call visualization.
- [Frontend Files — Knowledge-Base File Browser](files.md) - The file management panel inside the chat layout: directory tree and breadcrumbs, Markdown/text/image/PDF preview, CRUD operations, drag-and-drop and paste upload, and per-feature composables.
- [Frontend Overview — Vue 3 Architecture, Routing, API Client, Shared Components](overview.md) - How the Vue 3 + TypeScript frontend is organized: hash router with chat/settings/rag routes, the generated hey-api OpenAPI client, shared components (Markdown, Toasts, logger), and the layout/sidebar system.
- [Frontend RAG — Vector Store Management UI](rag.md) - The /rag page: four tabs (Process, Browse, Config, Health) for preview-then-commit ingestion, Chroma collection browsing, live rag_config.yaml editing, and vector store health monitoring.
- [Frontend Settings — Six-Tab Configuration Console](settings.md) - The /settings page with exactly six tabs (model, prompts, mcp, memory, skill-files, skill-manage), the model config form including the dead moonshot provider surface, and the skills enable/disable manager.

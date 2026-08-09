---
type: component
title: Frontend Chat — Controller, SSE Streaming, HITL Approval, Checkpoint Branch UI, Tool Cards
description: "The chat workspace: useChatController orchestration, useChatStream + SSE chunk handler (10 event types), approval cards for HITL, checkpoint retry/fork branch navigation, and tool call visualization."
tags: [frontend, chat, sse, checkpoints, hitl]
---

# Frontend Chat

## Module map — `src/chat/`

| Path | Responsibility |
|---|---|
| `core/useChatController.ts` | orchestration: state, stream, checkpoints, history, titles, scroll, errors |
| `core/useChatState.ts` | reactive chat state (messages, streaming content, interrupts, pending tool calls) |
| `core/useChatStream.ts` | SSE communication entrypoints (`sendMessage`, `resumeChat`, `replayCheckpoint`, `forkFromCheckpoint`, `cancelRequest`) |
| `core/sse/sseChunkHandler.ts` | chunk type dispatch (the 10 event types), tool-args parsing, checkpoint binding |
| `core/sse/sseRequests.ts` | unified SSE POST (`doSseRequest` JSON, `doSseFormDataRequest` multipart) over the generated client |
| `core/sse/resetStreamingState.ts` | state reset between runs |
| `core/ChatView.vue`, `ChatHeader.vue`, `ChatInput.vue`, `ChatMessages.vue`, `ChatReason.vue` | UI composition |
| `approval/ApprovalCard.vue` | HITL decision UI (approve / reject / edit) |
| `checkpoints/useCheckpoints.ts` | input-checkpoint pool, branch map, `resolveCheckpoint` by msg id / content |
| `tools/ToolCallCard.vue`, `ToolMessageCard.vue`, `useToolMessages.ts` | tool-call visualization + shared state for the right sidebar |

## Streaming contract (mirrors backend)

`useChatStream` opens `POST /chat/{thread_id}/stream` with the generated client's SSE support and feeds events to `createSseChunkHandler`, which handles:

- `reasoning` → `streamingReasoning` (shown in `ChatReason.vue`)
- `text` → `streamingContent`
- `tool_call` → builds/merges `pendingToolCalls` (`parseToolArgs` recovers partial JSON args; non-object JSON wraps as `{items}` / `{value}` / `{raw}`)
- `tool_result` → appended to the active tool call's `result`
- `checkpoint` → **input kind** binds `_checkpointId`/`_parentCheckpointId` to the latest user message; **leaf kind** binds `_leafCheckpointId` to the latest assistant message. A deferred binding mechanism (`applyPendingLeaf`) handles leaf-before-done ordering.
- `interrupt` → sets `showInterrupt`/`interruptData`; user decides in `ApprovalCard`, then `resumeChat` POSTs `/chat/{id}/resume` with `HITLResponse.decisions`.
- `rubric` → shown as Loop Engineering progress (iteration count)
- `error` → toast (deduplicated via `lastErrorMsg`), `done` → finalize assistant message + `applyPendingLeaf`

**Send-time branch continuation:** `sendMessage()` re-attaches the last assistant message's `_leafCheckpointId` as `checkpoint_id` in the request body — for both `POST /chat/{thread_id}/stream` (JSON) and `POST /chat/{thread_id}/with-files/stream` (FormData `messages` JSON). It scans `state.messages` in reverse for the last `role === 'assistant'` message that carries `_leafCheckpointId` and posts that id (spread as `...(checkpointId && { checkpoint_id: checkpointId })`). This is what makes a follow-up turn continue along the currently selected branch (after a fork or replay) instead of the tree root — distinct from the refresh-time re-binding, which only restores `_leafCheckpointId` from `head_checkpoint_id`/cache for display.

`cancelRequest()` aborts the AbortController and packages partial stream content into a final assistant message (mirrors the `done` logic, including `applyPendingLeaf()` so the leaf checkpoint is bound to the truncated assistant message before teardown).

## Retry / fork / branch navigation — `checkpoints/useCheckpoints.ts`

- `loadCheckpoints()` fetches `GET /checkpoints/{thread_id}/inputs` and builds a branch map keyed by `input` checkpoints with `leaf_checkpoint_id` targets; the chat header exposes retry (replay from the input checkpoint) and fork (new branch from `parent_checkpoint_id`).
- Refresh recovery: server messages are re-bound to checkpoints — ID-first (`_msgId` ↔ `trigger_message_id`), content-match fallback via `resolveCheckpoint` — and the branch head from `ChatResponse.head_checkpoint_id` or the cached leaf id restores `_leafCheckpointId`.
- Branch switching loads the selected leaf's history via `GET /chat/{thread_id}/get-messages-history?checkpoint_id=<leaf>`.
- History rendering runs `mergeConsecutiveReasoningMessages` (helper in `src/api/chat.ts`; see [frontend overview](overview.md)) so consecutive reasoning-only assistant messages are merged into one — the render layer (`ChatMessages.vue`) passes `skipToolMessages=true` so tool rows do not break the reasoning chain, while the data layer (`useChatController`, `useChatHistory`) uses the default `false`.

## Attachment upload — `src/upload/useFileUpload.ts`, `ContentBlocksPreview.vue`

Files are converted to base64 `ContentBlock`s (`type: image` / `type: file`) client-side; `doSseFormDataRequest` posts `{messages: JSON, files}` to `/chat/{id}/with-files/stream`; `ContentBlocksPreview` shows what will be attached.

## Related pages

- [Backend chat flow](../backend/chat-flow.md) — server-side SSE event generation
- [Backend checkpoints](../backend/checkpoints.md) — input/leaf semantics and replay/fork services
- [Frontend overview](overview.md) — layout that hosts this workspace

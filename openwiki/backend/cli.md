---
type: component
title: CLI — Terminal Interaction, Streaming, Chat Logs, State Snapshots
description: "The command-line agent runtime: interactive loop with attachments, stream chunk handling, HITL decisions in the terminal, per-thread chat logs, and state/query helpers."
tags: [backend, cli, terminal]
---

# CLI

## Entry — `backend/cli/interact.py`

Run with `python -m backend.cli.interact` (or the package console entry; `main(thread_id)` wraps `_main` with `asyncio.run`). Behavior:

- Creates or reuses a `thread_id` (default `uuid4().hex`), calls `setup_logging()` (standalone scripts must do this manually), and enters `async with init_graph()` — the **same** graph lifecycle as the web backend, so the CLI shares checkpoints/store with web threads when given the same `thread_id`.
- `config` includes Langfuse callbacks with tag `interactive-cli`.
- Loads existing state via `index_agent.aget_state(config)`; if messages exist it prints the count and continues from the checkpoint ("从断点继续记录").
- Attachments: leading tokens that are existing files with supported extensions (`SUPPORTED_EXTENSIONS`) are extracted (pdfplumber/MarkItDown via `FILE_EXTRACTORS`) and appended as `[附件 N: name]` text; supports multiple file paths before the question.
- Streams with `astream(stream_mode=["messages", "updates", "checkpoints"], subgraphs=True, version="v2")`:
  - `messages` chunks → `backend/cli/runtime/stream.py` `StreamProcessor._handle_message_chunk` prints reasoning (gray), text, tool calls per source label (`main`/`subagent`).
  - `checkpoints` chunks → prints checkpoint info.
  - `updates` chunks with `__interrupt__` → `_handle_updates_chunk` returns a `Command(resume=...)` built from `get_user_decision()` — terminal HITL: prints each action with its allowed decisions, reads a number, supports `edit` with JSON args; invalid choice defaults to `reject`.
- After each turn, appends newly added messages to a per-thread Markdown log via `append_chat_log()` (`backend/cli/runtime/chat_log.py`) at `CHAT_LOG_DIR/<thread_id>.md`.
- `exit`/`quit` ends the loop; the context manager closes SQLite connections.

## Support modules — `backend/cli/runtime/`

| File | Purpose |
|---|---|
| `stream.py` | terminal `StreamProcessor` (message chunk rendering, checkpoint info, `get_user_decision`, `_handle_updates_chunk`) |
| `chat_log.py` | `append_chat_log(MD_FILE, new_messages)` — appends formatted conversation to a Markdown file |
| `save_state.py` | snapshot helpers (`SAVE_STATE_DIR`) |

## Query helpers — `backend/cli/`

- `get_message_history.py` — `print_history(thread_id, checkpoint_id)` enters `init_graph()`, calls `graph.aget_state({"configurable": {"thread_id", "checkpoint_id"}})`, prints the message count, then writes a Markdown chat log: the title is the first `HumanMessage` content sanitized by `_first_human_title` (`_sanitize_filename` strips Windows-illegal characters `\ / : * ? " < > | \r \n \t`, trims dots, truncates to 10 chars; falls back to `thread_id[:10]`) and the file is `CHAT_LOG_DIR/<title>_<YYYYMMDD_HHMMSS>.md` written via `write_chat_log()` (`backend/cli/runtime/chat_log.py`). Hard-asserts `CHAT_LOG_DIR` is configured.
- `query_state.py` — `query_state(thread_id, checkpoint_id)` enters `init_graph()`, calls `graph.aget_state(...)`, prints message count, pending nodes (`state.next`), interrupt count (`state.interrupts`), and snapshot time (`state.created_at`), then saves a full snapshot JSON via `save_snapshot_to_json()` (`backend/cli/runtime/save_state.py`, which serializes the snapshot through `snapshot_to_dict()`: values with messages serialized per-message, next/config/metadata/created_at/parent_config/tasks/interrupts) to `./snapshot_<thread_id[:8]>_<timestamp>.json` in the current working directory.
- Both scripts call `setup_logging()` inside their `if __name__ == "__main__":` blocks before `asyncio.run(...)` — they are standalone entry points, so logging must be initialized explicitly (see [config](config.md)).

## Related pages

- [Backend overview](overview.md) — shared `init_graph` lifecycle
- [Chat flow](chat-flow.md) — same SSE/stream semantics in terminal form
- [Operations](../operations.md) — run commands

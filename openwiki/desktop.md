---
type: component
title: Desktop Shell — Electron Orchestrator
description: "The Electron wrapper that spawns the FastAPI backend and Vite frontend as subprocesses, waits for readiness, shows a tray-resident window, and cleans up child processes and ports on exit."
tags: [desktop, electron]
---

# Desktop Shell

`desktop/main.js` is a minimal Electron main process (no renderer code of its own — it loads the Vite dev server URL). It is the "one-click" launcher documented in the README and `start-desktop.bat`.

## Startup sequence

1. **Preflight**: verifies `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` exists and `frontend/node_modules` is present; otherwise shows an error dialog.
2. **Port cleanup** (Windows): kills any process listening on ports 8000/5173 via `netstat -ano | findstr` + `taskkill /F`.
3. **Backend**: spawns the venv python running the FastAPI app; waits until stdout/stderr contains the readiness marker (log text) with `waitForStdoutMark`, falling back to HTTP polling `waitForReady(8000)`.
4. **Frontend**: spawns `npm run dev` (npm.cmd on Windows), waits for readiness on port 5173.
5. Opens the Electron `BrowserWindow` pointed at `http://localhost:5173`; a `Tray` keeps the app resident when the window closes.
6. On quit, all child processes are killed and ports cleaned.

## Key facts for agents

- The desktop shell **is not a separate runtime** for the agent — it is an orchestration layer; the actual agent lives in the spawned backend process.
- `start-desktop.bat` mirrors the port cleanup and first-run Electron install (with the npmmirror `ELECTRON_MIRROR` env).
- There is no production build path wired here: it always runs the Vite dev server (`npm start` → dev), so source edits hot-reload.

## Related pages

- [Backend overview](backend/overview.md) — the spawned backend
- [Frontend overview](frontend/overview.md) — the spawned frontend
- [Operations](operations.md) — startup commands

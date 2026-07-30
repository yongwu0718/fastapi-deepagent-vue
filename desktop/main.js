/**
 * Index RAG 桌面壳 — Electron 主进程
 *
 * 职责：
 *  1. 启动 Python FastAPI 后端（子进程）
 *  2. 启动 Vue Vite 前端开发服务器（子进程）
 *  3. 等待两者就绪后打开桌面窗口
 *  4. 系统托盘常驻，关闭窗口不退出
 *  5. 退出时清理所有子进程
 *
 * 前置条件：
 *  - 项目根目录存在 .venv（Python 虚拟环境）
 *  - frontend/node_modules 已安装
 */

const { app, BrowserWindow, Tray, Menu, dialog, nativeImage } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');

// ── 常量 ─────────────────────────────────────────────
const PROJECT_ROOT = path.resolve(__dirname, '..');
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 5173;
const READY_CHECK_INTERVAL = 1000; // 1 秒轮询一次
const IS_WIN = process.platform === 'win32';

// ── 全局状态 ─────────────────────────────────────────
let mainWindow = null;
let tray = null;
let backendProcess = null;
let frontendProcess = null;

// ── 工具函数 ─────────────────────────────────────────

/** 优雅日志 */
function log(tag, ...args) {
  const ts = new Date().toLocaleTimeString();
  console.log(`[${ts}] [${tag}]`, ...args);
}

/** 获取 Python 可执行文件路径 */
function getPythonExe() {
  if (IS_WIN) {
    return path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe');
  }
  return path.join(PROJECT_ROOT, '.venv', 'bin', 'python');
}

/** 获取 npm 可执行文件路径 */
function getNpmExe() {
  return IS_WIN ? 'npm.cmd' : 'npm';
}

/** HTTP 健康检查轮询（无限等待，直到就绪） */
function waitForReady(port) {
  return new Promise((resolve) => {
    const check = () => {
      const req = http.get(`http://127.0.0.1:${port}`, () => {
        req.destroy();
        resolve();
      });
      req.on('error', () => {
        req.destroy();
        setTimeout(check, READY_CHECK_INTERVAL);
      });
      req.setTimeout(2000, () => {
        req.destroy();
        setTimeout(check, READY_CHECK_INTERVAL);
      });
    };
    check();
  });
}

/** 通过 stdout 内容判断就绪（更可靠，避免 IPv4/IPv6 不匹配） */
function waitForStdoutMark(childProc, marker) {
  return new Promise((resolve) => {
    let buffer = '';
    const onData = (data) => {
      buffer += data.toString();
      if (buffer.includes(marker)) {
        childProc.stdout.removeListener('data', onData);
        childProc.stderr.removeListener('data', onData);
        resolve();
      }
    };
    childProc.stdout.on('data', onData);
    childProc.stderr.on('data', onData);
  });
}

/** 清理端口上已有的进程（Windows） */
function killPortProcess(port) {
  if (!IS_WIN) return;
  try {
    const output = execSync(`netstat -ano | findstr :${port} | findstr LISTENING`, {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'ignore'],
    });
    const lines = output.trim().split('\n');
    for (const line of lines) {
      const parts = line.trim().split(/\s+/);
      const pid = parts[parts.length - 1];
      if (pid && !isNaN(pid)) {
        log('Cleanup', `Killing old process on port ${port} (PID ${pid})`);
        try {
          execSync(`taskkill /PID ${pid} /F`, { stdio: 'ignore' });
        } catch (_) {}
      }
    }
  } catch (_) {
    // port is free, that's fine
  }
}

/** 前置检查 */
function runPreflightChecks() {
  const errors = [];

  // 检查 .venv 是否存在
  if (!fs.existsSync(getPythonExe())) {
    errors.push(
      '未找到 Python 虚拟环境。\n\n请在项目根目录执行：\n  uv sync'
    );
  }

  // 检查 frontend/node_modules 是否存在
  const frontendNodeModules = path.join(PROJECT_ROOT, 'frontend', 'node_modules');
  if (!fs.existsSync(frontendNodeModules)) {
    errors.push(
      '未找到前端依赖。\n\n请在 frontend 目录执行：\n  npm install'
    );
  }

  if (errors.length > 0) {
    dialog.showErrorBox('环境检查失败', errors.join('\n\n'));
    return false;
  }
  return true;
}

// ── 启动子进程 ───────────────────────────────────────

/** 启动 Python FastAPI 后端 — 返回 Promise，stdout 出现 marker 时 resolve */
function startBackend(marker) {
  return new Promise((resolve, reject) => {
    log('Backend', 'Starting Python backend...');
    const pythonExe = getPythonExe();
    let buffer = '';

    backendProcess = spawn(pythonExe, [
      '-m', 'uvicorn',
      'backend.main:app',
      '--host', '127.0.0.1',
      '--port', String(BACKEND_PORT),
      '--reload',
    ], {
      cwd: PROJECT_ROOT,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
      shell: false,
    });

    const onData = (data) => {
      const text = data.toString();
      buffer += text;
      log('Backend', text.trimEnd());
      if (buffer.includes(marker)) {
        resolve();
      }
    };

    backendProcess.stdout.on('data', onData);
    backendProcess.stderr.on('data', onData);

    backendProcess.on('error', (err) => {
      log('Backend', `Process error: ${err.message}`);
      reject(err);
    });

    backendProcess.on('close', (code) => {
      log('Backend', `Process exited with code ${code}`);
      backendProcess = null;
    });
  });
}

/** 启动 Vue Vite 前端 — 返回 Promise，stdout 出现 marker 时 resolve */
function startFrontend(marker) {
  return new Promise((resolve, reject) => {
    log('Frontend', 'Starting Vite dev server...');
    const npmExe = getNpmExe();
    let buffer = '';

    frontendProcess = spawn(npmExe, ['run', 'dev', '--', '--port', String(FRONTEND_PORT)], {
      cwd: path.join(PROJECT_ROOT, 'frontend'),
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
      shell: IS_WIN,
    });

    const onData = (data) => {
      const text = data.toString();
      buffer += text;
      log('Frontend', text.trimEnd());
      if (buffer.includes(marker)) {
        resolve();
      }
    };

    frontendProcess.stdout.on('data', onData);
    frontendProcess.stderr.on('data', onData);

    frontendProcess.on('error', (err) => {
      log('Frontend', `Process error: ${err.message}`);
      reject(err);
    });

    frontendProcess.on('close', (code) => {
      log('Frontend', `Process exited with code ${code}`);
      frontendProcess = null;
    });
  });
}

// ── 窗口与托盘 ───────────────────────────────────────

/** 创建主窗口 */
function createWindow() {
  log('Window', 'Creating window...');
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 500,
    title: 'Index RAG',
    show: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.webContents.on('did-finish-load', () => {
    log('Window', 'Page loaded successfully');
  });

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    log('Window', `Page load failed: ${errorDescription} (${errorCode})`);
  });

  // 加载 Vite 开发服务器
  const url = `http://localhost:${FRONTEND_PORT}`;
  log('Window', `Loading ${url}`);
  mainWindow.loadURL(url);

  // 关闭窗口 → 收起到托盘
  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      log('Window', '窗口已最小化到系统托盘');
    }
  });

  // 窗口关闭后清理引用
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/** 创建系统托盘 */
function createTray() {
  // 创建一个简单的托盘图标（16x16 透明像素作为占位符）
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon.resize({ width: 16, height: 16 }));

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示主窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        } else {
          createWindow();
        }
      },
    },
    { type: 'separator' },
    {
      label: '开发模式',
      enabled: false,
    },
    {
      label: `  后端: http://localhost:${BACKEND_PORT}`,
      click: () => { /* 可按需扩展 */ },
    },
    {
      label: `  前端: http://localhost:${FRONTEND_PORT}`,
      click: () => { /* 可按需扩展 */ },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setToolTip('Index RAG');
  tray.setContextMenu(contextMenu);

  // 双击托盘图标显示窗口
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    } else {
      createWindow();
    }
  });
}

// ── 清理 ────────────────────────────────────────────

/** 杀死进程树（Windows 需要递归杀子进程） */
function killProcess(proc, label) {
  if (!proc) return;
  try {
    if (IS_WIN) {
      // Windows: 按 PID 杀进程树
      spawn('taskkill', ['/PID', String(proc.pid), '/T', '/F'], { stdio: 'ignore' });
    } else {
      proc.kill('SIGTERM');
    }
    log(label, '已终止');
  } catch (e) {
    // 忽略
  }
}

function cleanup() {
  killProcess(backendProcess, 'Backend');
  killProcess(frontendProcess, 'Frontend');
  backendProcess = null;
  frontendProcess = null;
}

// ── 应用生命周期 ─────────────────────────────────────

app.whenReady().then(async () => {
  app.isQuitting = false;

  // 1. 前置检查
  if (!runPreflightChecks()) {
    app.quit();
    return;
  }

  // 2. 创建托盘（显示在启动期间）
  createTray();

  // 3. 清理旧端口，启动后端
  killPortProcess(BACKEND_PORT);
  await startBackend('Application startup complete');
  log('Ready', `Backend ready -> http://localhost:${BACKEND_PORT}`);

  // 4. 清理旧端口，启动前端
  killPortProcess(FRONTEND_PORT);
  await startFrontend('ready in');
  log('Ready', `Frontend ready -> http://localhost:${FRONTEND_PORT}`);

  // 5. Open main window
  log('Ready', 'All services ready, opening window...');
  createWindow();
});

// macOS: 点击 Dock 图标重新显示窗口
app.on('activate', () => {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  } else {
    createWindow();
  }
});

// 所有窗口关闭时不做任何事（因为关闭=收起托盘）
app.on('window-all-closed', () => {
  // 不调用 app.quit()
});

// 退出前清理
app.on('before-quit', () => {
  app.isQuitting = true;
  cleanup();
});

// 异常退出兜底
process.on('exit', cleanup);
process.on('SIGINT', () => { app.quit(); });
process.on('SIGTERM', () => { app.quit(); });

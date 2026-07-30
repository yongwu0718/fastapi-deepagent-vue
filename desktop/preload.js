/**
 * Index RAG 桌面壳 — Preload 脚本
 *
 * 通过 contextBridge 向渲染进程暴露安全的 API。
 * 目前主要是信息传递，后续可扩展 IPC 通道。
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  /** 获取当前平台 */
  platform: process.platform,

  /** 是否运行在 Electron 环境中（前端可据此做适配） */
  isElectron: true,

  /** 获取后端端口号 */
  backendPort: 8000,

  /** 获取前端端口号 */
  frontendPort: 5173,
});

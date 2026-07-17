import { readonly } from 'vue'
import { createFileState, createFileComputed } from './core/useFileState'
import type { FileTab } from './core/useFileState'
import { createFilePersistence } from './core/useFilePersistence'
import { createFileSearch } from './features/useFileSearch'
import { createFileOps } from './features/useFileOps'
import { createFileDirectory } from './features/useFileDirectory'
import { createFileTabs } from './features/useFileTabs'
import { createFileSplit } from './features/useFileSplit'

export type { FileTab }

export function useFileManager() {
  // ── 1. 状态 + 计算属性 ──
  const state = createFileState()
  const computed = createFileComputed(state)

  // ── 2. _scheduleSave 初始为空（迟到绑定） ──
  const scheduleSaveRef = { fn: () => {} }

  // ── 3. 各模块 ──
  const dir = createFileDirectory(state, () => scheduleSaveRef.fn())
  const tabs = createFileTabs(state, () => scheduleSaveRef.fn())

  // ── 4. 持久化（需要 loadDirectory / openFile） ──
  const persist = createFilePersistence(state, computed, dir.loadDirectory, tabs.openFile)

  // ── 5. 迟到注入 _scheduleSave ──
  scheduleSaveRef.fn = persist._scheduleSave

  // ── 6. 其余模块 ──
  const ops = createFileOps(state, () => dir.loadDirectory(), tabs.closeTab)
  const split = createFileSplit(state, tabs.closeTab)
  const search = createFileSearch(state)

  // ── 7. selectEntry：目录走 navigateTo，文件走 openFile ──
  async function selectEntry(entry: { name: string; path: string; type: string }) {
    if (entry.type === 'directory') {
      await dir.navigateTo(entry.path)
    } else {
      await tabs.openFile(entry.path)
    }
  }

  return {
    // 状态
    currentPath: readonly(state.currentPath),
    entries: readonly(state.entries),
    loading: readonly(state.loading),

    // 标签页
    openTabs: state.openTabs,
    activeTabId: readonly(state.activeTabId),
    activeTab: computed.activeTab,

    // 分屏
    splitMode: readonly(state.splitMode),
    activePane: state.activePane,
    leftActiveTabId: readonly(state.leftActiveTabId),
    rightActiveTabId: readonly(state.rightActiveTabId),
    leftTabs: computed.leftTabs,
    rightTabs: computed.rightTabs,
    leftActiveTab: computed.leftActiveTab,
    rightActiveTab: computed.rightActiveTab,

    // 选中/文件内容
    selectedEntry: computed.selectedEntry,
    fileContent: computed.fileContent,
    fileUrl: computed.fileUrl,
    fileContentType: computed.fileContentType,
    fileContentLoading: computed.fileContentLoading,

    // 计算
    breadcrumbs: computed.breadcrumbs,
    parentPath: computed.parentPath,
    fileCount: computed.fileCount,
    dirCount: computed.dirCount,

    // 搜索
    searchQuery: readonly(state.searchQuery),
    searchLoading: readonly(state.searchLoading),
    filteredEntries: computed.filteredEntries,
    setSearch: search.setSearch,
    clearSearch: search.clearSearch,

    // 目录
    loadDirectory: dir.loadDirectory,
    navigateTo: dir.navigateTo,
    goUp: dir.goUp,
    refresh: dir.refresh,

    // 标签
    selectEntry,
    readFile: tabs.openFile,
    openFile: tabs.openFile,
    closeTab: tabs.closeTab,
    switchTab: tabs.switchTab,

    // CRUD
    createFile: ops.createFile,
    createDirectory: ops.createDirectory,
    uploadFile: ops.uploadFile,
    renameEntry: ops.renameEntry,
    moveEntry: ops.moveEntry,
    saveFile: ops.saveFile,
    deleteEntry: ops.deleteEntry,

    // 工具
    clearSelection: tabs.clearSelection,
    isFileOpen: tabs.isFileOpen,

    // 分屏
    splitToggle: split.splitToggle,
    moveTabToPane: split.moveTabToPane,

    // 持久化
    restoreState: persist.restoreState,
  }
}

/** 模块级单例 */
let instance: ReturnType<typeof useFileManager> | null = null

export function getFileManager() {
  if (!instance) instance = useFileManager()
  return instance
}

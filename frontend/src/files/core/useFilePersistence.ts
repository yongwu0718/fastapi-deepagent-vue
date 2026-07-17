const LS_FILE_STATE_KEY = 'file_manager_state_v1'

export function createFilePersistence(
  _state: any,
  _computed: any,
  _loadDirectory: (path?: string) => Promise<void>,
  _openFile: (path: string) => Promise<void>,
) {
  let _restoring = false
  let _saveTimer: ReturnType<typeof setTimeout> | null = null

  function _scheduleSave() {
    if (_restoring) return
    if (_saveTimer) clearTimeout(_saveTimer)
    _saveTimer = setTimeout(() => _doSave(), 300)
  }

  function _doSave() {
    const s = _state
    const c = _computed
    const activeTabPath = c.activeTab.value?.entry.path ?? null
    const state = {
      currentPath: s.currentPath.value,
      tabs: s.openTabs.value.map((t: any) => ({ path: t.entry.path, pane: t.pane })),
      splitMode: s.splitMode.value,
      activePane: s.activePane.value,
      activePath: activeTabPath,
      activePathLeft: c.leftActiveTab.value?.entry.path ?? null,
      activePathRight: c.rightActiveTab.value?.entry.path ?? null,
    }
    try { localStorage.setItem(LS_FILE_STATE_KEY, JSON.stringify(state)) } catch { /* 忽略 */ }
  }

  async function restoreState(): Promise<boolean> {
    const raw = localStorage.getItem(LS_FILE_STATE_KEY)
    if (!raw) return false

    let saved: any
    try { saved = JSON.parse(raw) } catch { return false }

    const s = _state

    if (!saved.tabs || saved.tabs.length === 0) {
      if (saved.currentPath) await _loadDirectory(saved.currentPath)
      return true
    }

    _restoring = true
    try {
      if (saved.currentPath) {
        s.currentPath.value = saved.currentPath
        await _loadDirectory(saved.currentPath)
      }

      if (saved.splitMode && saved.tabs.length > 0) {
        s.splitMode.value = true
        s.activePane.value = saved.activePane || 'left'

        for (const tab of saved.tabs.filter((t: any) => t.pane === 'left')) {
          s.activePane.value = 'left'
          try { await _openFile(tab.path) } catch { /* skip */ }
        }
        for (const tab of saved.tabs.filter((t: any) => t.pane === 'right')) {
          s.activePane.value = 'right'
          try { await _openFile(tab.path) } catch { /* skip */ }
        }

        if (saved.activePathLeft) {
          const tab = s.openTabs.value.find((t: any) => t.entry.path === saved.activePathLeft && t.pane === 'left')
          if (tab) s.leftActiveTabId.value = tab.id
        }
        if (saved.activePathRight) {
          const tab = s.openTabs.value.find((t: any) => t.entry.path === saved.activePathRight && t.pane === 'right')
          if (tab) s.rightActiveTabId.value = tab.id
        }
        s.activePane.value = saved.activePane || 'left'
      } else if (saved.tabs.length > 0) {
        s.splitMode.value = false
        for (const tab of saved.tabs) {
          try { await _openFile(tab.path) } catch { /* skip */ }
        }
        if (saved.activePath) {
          const tab = s.openTabs.value.find((t: any) => t.entry.path === saved.activePath)
          if (tab) s.activeTabId.value = tab.id
        }
      }
      return true
    } finally {
      _restoring = false
    }
  }

  function resetPersistenceFlag() { _restoring = false }

  return { _scheduleSave, _doSave, restoreState, resetPersistenceFlag }
}

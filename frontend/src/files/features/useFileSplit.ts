export function createFileSplit(_state: any, _closeTab: (tabId: string) => void) {
  function splitToggle() {
    if (_state.splitMode.value) {
      const rightTabIds = _state.openTabs.value.filter((t: any) => t.pane === 'right').map((t: any) => t.id)
      for (const tid of rightTabIds) _closeTab(tid)
      _state.splitMode.value = false
      _state.activePane.value = 'left'
      if (_state.leftActiveTabId.value && _state.openTabs.value.length > 0) {
        _state.activeTabId.value = _state.leftActiveTabId.value
      } else if (_state.openTabs.value.length > 0) {
        _state.activeTabId.value = _state.openTabs.value[0].id
      } else {
        _state.activeTabId.value = ''
      }
      _state.leftActiveTabId.value = ''
      _state.rightActiveTabId.value = ''
    } else {
      _state.splitMode.value = true
      _state.activePane.value = 'right'
      _state.leftActiveTabId.value = _state.activeTabId.value
      _state.rightActiveTabId.value = ''
      for (const tab of _state.openTabs.value) tab.pane = 'left'
    }
  }

  function moveTabToPane(tabId: string, targetPane: 'left' | 'right') {
    const tab = _state.openTabs.value.find((t: any) => t.id === tabId)
    if (!tab || tab.pane === targetPane) return

    const oldPane = tab.pane
    tab.pane = targetPane

    if (oldPane === 'left' && _state.leftActiveTabId.value === tabId) {
      const remaining = _state.openTabs.value.filter((t: any) => t.pane === 'left')
      _state.leftActiveTabId.value = remaining.length > 0 ? remaining[remaining.length - 1].id : ''
    } else if (oldPane === 'right' && _state.rightActiveTabId.value === tabId) {
      const remaining = _state.openTabs.value.filter((t: any) => t.pane === 'right')
      _state.rightActiveTabId.value = remaining.length > 0 ? remaining[remaining.length - 1].id : ''
    }

    if (targetPane === 'left') _state.leftActiveTabId.value = tabId
    else _state.rightActiveTabId.value = tabId
    _state.activePane.value = targetPane
  }

  return { splitToggle, moveTabToPane }
}

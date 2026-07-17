import {
  readFileEndpointApiFilesReadGet,
  getFileEndpointApiFilesFileGet,
} from '@/api/client/sdk.gen'
import { normalizeReadResponse, isBinaryFile, isIframePreviewable, isPreviewableImage } from '@/api/files'
import type { RawReadResponse } from '@/api/files'
import { createLogger } from '@/shared/useLogger'
import { toast } from '@/shared/useToast'

const log = createLogger('[FileManager]')

export function createFileTabs(_state: any, _scheduleSave: () => void) {
  async function _readFileToTab(tab: any, path: string) {
    tab.contentLoading = true
    tab.fileUrl = ''
    tab.contentType = ''
    try {
      const fileName = path.split('/').pop() ?? path
      if (isBinaryFile(fileName)) {
        const result = await getFileEndpointApiFilesFileGet({ query: { path } })
        const blob = result.data as Blob
        if (tab.fileUrl && tab.fileUrl.startsWith('blob:')) URL.revokeObjectURL(tab.fileUrl)
        tab.fileUrl = URL.createObjectURL(blob)
        tab.content = ''
        tab.contentType = isPreviewableImage(fileName) ? 'image'
          : isIframePreviewable(fileName) ? 'pdf' : 'binary'
      } else {
        const result = await readFileEndpointApiFilesReadGet({ query: { path } })
        const data = result.data as RawReadResponse
        if (data) {
          const normalized = normalizeReadResponse(data)
          tab.content = normalized.content
          tab.contentType = 'text'
          tab.entry.editable = normalized.editable
          const listEntry = _state.entries.value.find((e: FileEntry) => e.path === path)
          if (listEntry) listEntry.editable = normalized.editable
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '读取文件失败'
      log.error('读取文件失败', err)
      toast.error('读取文件失败', msg)
    } finally {
      tab.contentLoading = false
    }
  }

  async function openFile(path: string) {
    const existing = _state.openTabs.value.find((t: any) => t.entry.path === path)
    if (existing) {
      if (_state.splitMode.value) {
        if (existing.pane === _state.activePane.value) {
          if (_state.activePane.value === 'left') _state.leftActiveTabId.value = existing.id
          else _state.rightActiveTabId.value = existing.id
          return
        }
      } else {
        _state.activeTabId.value = existing.id
        return
      }
    }

    const fileName = path.split('/').pop() ?? path
    const tab = {
      id: _state._genTabId(),
      entry: { name: fileName, path, type: 'file' as const, size: 0, modified: '' },
      content: '', contentType: '', fileUrl: '', contentLoading: false,
      pane: _state.splitMode.value ? _state.activePane.value : 'left',
    }

    _state.openTabs.value = [..._state.openTabs.value, tab]

    if (_state.splitMode.value) {
      if (_state.activePane.value === 'left') _state.leftActiveTabId.value = tab.id
      else _state.rightActiveTabId.value = tab.id
    } else {
      _state.activeTabId.value = tab.id
    }

    const reactiveTab = _state.openTabs.value.find((t: any) => t.id === tab.id)
    await _readFileToTab(reactiveTab, path)
    _scheduleSave()
  }

  function closeTab(tabId: string) {
    const idx = _state.openTabs.value.findIndex((t: any) => t.id === tabId)
    if (idx === -1) return
    const tab = _state.openTabs.value[idx]
    if (tab.fileUrl && tab.fileUrl.startsWith('blob:')) URL.revokeObjectURL(tab.fileUrl)

    _state.openTabs.value = _state.openTabs.value.filter((t: any) => t.id !== tabId)

    if (_state.splitMode.value && tab.pane === 'left' && _state.leftActiveTabId.value === tabId) {
      const remaining = _state.openTabs.value.filter((t: any) => t.pane === 'left')
      if (remaining.length > 0) {
        const leftTabs = _state.openTabs.value.filter((t: any) => t.pane === 'left')
        const oldIdx = leftTabs.findIndex((t: any) => t.id === tabId)
        _state.leftActiveTabId.value = remaining[Math.min(oldIdx, remaining.length - 1)].id
      } else {
        _state.leftActiveTabId.value = ''
        if (_state.activePane.value === 'left') _state.activePane.value = 'right'
      }
    } else if (_state.splitMode.value && tab.pane === 'right' && _state.rightActiveTabId.value === tabId) {
      const remaining = _state.openTabs.value.filter((t: any) => t.pane === 'right')
      if (remaining.length > 0) {
        const rightTabs = _state.openTabs.value.filter((t: any) => t.pane === 'right')
        const oldIdx = rightTabs.findIndex((t: any) => t.id === tabId)
        _state.rightActiveTabId.value = remaining[Math.min(oldIdx, remaining.length - 1)].id
      } else {
        _state.rightActiveTabId.value = ''
        if (_state.activePane.value === 'right') _state.activePane.value = 'left'
      }
    }

    if (_state.splitMode.value && _state.openTabs.value.length === 0) {
      _state.splitMode.value = false
    }

    if (!_state.splitMode.value && _state.activeTabId.value === tabId) {
      if (_state.openTabs.value.length > 0) {
        _state.activeTabId.value = _state.openTabs.value[Math.min(idx, _state.openTabs.value.length - 1)].id
      } else {
        _state.activeTabId.value = ''
      }
    }
    _scheduleSave()
  }

  function switchTab(tabId: string) {
    if (_state.openTabs.value.some((t: any) => t.id === tabId)) {
      _state.activeTabId.value = tabId
    }
  }

  function clearSelection() {
    if (_state.splitMode.value) {
      const tabId = _state.activePane.value === 'left' ? _state.leftActiveTabId.value : _state.rightActiveTabId.value
      if (tabId) closeTab(tabId)
    } else {
      if (_state.activeTabId.value) closeTab(_state.activeTabId.value)
    }
    _scheduleSave()
  }

  function isFileOpen(path: string): boolean {
    return _state.openTabs.value.some((t: any) => t.entry.path === path)
  }

  return { _readFileToTab, openFile, closeTab, switchTab, clearSelection, isFileOpen }
}

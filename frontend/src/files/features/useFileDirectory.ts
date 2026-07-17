import { listDirectoryEndpointApiFilesListGet } from '@/api/client/sdk.gen'
import { normalizeListResponse, type FileEntry } from '@/api/files'
import type { RawListResponse } from '@/api/files'
import { createLogger } from '@/shared/useLogger'
import { toast } from '@/shared/useToast'

const log = createLogger('[FileManager]')

export function createFileDirectory(_state: any, _scheduleSave: () => void) {
  async function loadDirectory(path?: string) {
    const targetPath = path ?? _state.currentPath.value
    _state.loading.value = true
    try {
      const result = await listDirectoryEndpointApiFilesListGet(
        targetPath ? { query: { path: targetPath } } : undefined,
      )
      const data = result.data as RawListResponse
      if (data?.items) {
        const normalized = normalizeListResponse(data)
        _state.entries.value = normalized.entries
        _state.currentPath.value = normalized.path
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '加载目录失败'
      log.error('加载目录失败', err)
      toast.error('加载目录失败', msg)
    } finally {
      _state.loading.value = false
      _scheduleSave()
    }
  }

  async function navigateTo(path: string) {
    if (!_state.splitMode.value) _state.activeTabId.value = ''
    await loadDirectory(path)
  }

  async function goUp() {
    if (_state.currentPath.value) {
      const parts = _state.currentPath.value.split('/')
      if (parts.length <= 1) await navigateTo('')
      else await navigateTo(parts.slice(0, -1).join('/'))
    }
  }

  async function refresh() {
    await loadDirectory()
  }

  return { loadDirectory, navigateTo, goUp, refresh }
}

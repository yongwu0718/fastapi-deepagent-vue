import { searchFilesEndpointApiFilesSearchGet } from '@/api/client/sdk.gen'
import type { FileEntry } from '@/api/files'
import { createLogger } from '@/shared/useLogger'

const log = createLogger('[FileManager]')

interface RawSearchItem {
  name: string
  type: 'dir' | 'file'
  size: number | null
  modified: string
  path: string
}

interface RawSearchResponse {
  query: string
  results: RawSearchItem[]
}

function normalizeSearchItem(raw: RawSearchItem): FileEntry {
  return {
    name: raw.name,
    path: raw.path,
    type: raw.type === 'dir' ? 'directory' : 'file',
    size: raw.size ?? 0,
    modified: raw.modified,
  }
}

export function createFileSearch(_state: any) {
  async function _searchApi(query: string) {
    if (!query.trim()) { _state.searchResults.value = []; return }
    _state.searchLoading.value = true
    try {
      const res = await searchFilesEndpointApiFilesSearchGet({ query: { q: query } })
      const data = res.data as RawSearchResponse
      _state.searchResults.value = data?.results?.map(normalizeSearchItem) ?? []
    } catch (err) {
      log.error('搜索失败', err)
      _state.searchResults.value = []
    } finally {
      _state.searchLoading.value = false
    }
  }

  function setSearch(query: string) {
    _state.searchQuery.value = query
    if (_state._searchTimer) clearTimeout(_state._searchTimer)
    if (!query.trim()) { _state.searchResults.value = []; return }
    _state._searchTimer = setTimeout(() => _searchApi(query), 300)
  }

  function clearSearch() {
    _state.searchQuery.value = ''
    _state.searchResults.value = []
    if (_state._searchTimer) clearTimeout(_state._searchTimer)
  }

  return { setSearch, clearSearch }
}

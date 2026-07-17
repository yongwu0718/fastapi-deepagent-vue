import { ref, computed } from 'vue'
import type { FileEntry } from '@/api/files'

// ── localStorage 持久化类型 ──
export interface PersistedTab {
  path: string
  pane: 'left' | 'right'
}

export interface PersistedState {
  currentPath: string
  tabs: PersistedTab[]
  splitMode: boolean
  activePane: 'left' | 'right'
  activePath: string | null
  activePathLeft: string | null
  activePathRight: string | null
}

/** 文件标签页 */
export interface FileTab {
  id: string
  entry: FileEntry
  content: string
  contentType: string
  fileUrl: string
  contentLoading: boolean
  pane: 'left' | 'right'
}

interface FileState {
  // 目录
  currentPath: ReturnType<typeof ref<string>>
  entries: ReturnType<typeof ref<FileEntry[]>>
  loading: ReturnType<typeof ref<boolean>>
  // 标签页
  openTabs: ReturnType<typeof ref<FileTab[]>>
  activeTabId: ReturnType<typeof ref<string>>
  // 分屏
  splitMode: ReturnType<typeof ref<boolean>>
  activePane: ReturnType<typeof ref<'left' | 'right'>>
  leftActiveTabId: ReturnType<typeof ref<string>>
  rightActiveTabId: ReturnType<typeof ref<string>>
  // 搜索
  searchQuery: ReturnType<typeof ref<string>>
  searchResults: ReturnType<typeof ref<FileEntry[]>>
  searchLoading: ReturnType<typeof ref<boolean>>
  // ID 计数器
  _tabIdCounter: number
  _genTabId: () => string
  // 搜索计时器
  _searchTimer: ReturnType<typeof setTimeout> | null
}

export function createFileState(): FileState {
  const currentPath = ref('')
  const entries = ref<FileEntry[]>([])
  const loading = ref(false)

  const openTabs = ref<FileTab[]>([])
  const activeTabId = ref('')

  const splitMode = ref(false)
  const activePane = ref<'left' | 'right'>('left')
  const leftActiveTabId = ref('')
  const rightActiveTabId = ref('')

  const searchQuery = ref('')
  const searchResults = ref<FileEntry[]>([])
  const searchLoading = ref(false)

  let _tabIdCounter = 0
  function _genTabId(): string {
    return `tab_${Date.now()}_${++_tabIdCounter}`
  }

  return {
    currentPath, entries, loading,
    openTabs, activeTabId,
    splitMode, activePane, leftActiveTabId, rightActiveTabId,
    searchQuery, searchResults, searchLoading,
    _tabIdCounter, _genTabId, _searchTimer: null,
  }
}

// ── 计算属性（纯函数，不依赖 ref 之外的副作用） ──

export function createFileComputed(s: FileState) {
  const leftTabs = computed(() => s.openTabs.value.filter((t) => t.pane === 'left'))
  const rightTabs = computed(() => s.openTabs.value.filter((t) => t.pane === 'right'))

  const leftActiveTab = computed(() =>
    s.openTabs.value.find((t) => t.id === s.leftActiveTabId.value && t.pane === 'left') ?? null,
  )
  const rightActiveTab = computed(() =>
    s.openTabs.value.find((t) => t.id === s.rightActiveTabId.value && t.pane === 'right') ?? null,
  )

  const activeTab = computed(() => {
    if (s.splitMode.value) {
      const tabId = s.activePane.value === 'left' ? s.leftActiveTabId.value : s.rightActiveTabId.value
      if (!tabId) return null
      return s.openTabs.value.find((t) => t.id === tabId) ?? null
    }
    return s.openTabs.value.find((t) => t.id === s.activeTabId.value) ?? null
  })

  const selectedEntry = computed<FileEntry | null>(() => activeTab.value?.entry ?? null)
  const fileContent = computed(() => activeTab.value?.content ?? '')
  const fileUrl = computed(() => activeTab.value?.fileUrl ?? '')
  const fileContentType = computed(() => activeTab.value?.contentType ?? '')
  const fileContentLoading = computed(() => activeTab.value?.contentLoading ?? false)

  const breadcrumbs = computed(() => {
    if (!s.currentPath.value) return [{ label: 'index', path: '' }]
    const parts = s.currentPath.value.split('/')
    const crumbs: { label: string; path: string }[] = [{ label: 'index', path: '' }]
    let acc = ''
    for (const part of parts) {
      acc = acc ? `${acc}/${part}` : part
      crumbs.push({ label: part, path: acc })
    }
    return crumbs
  })

  const parentPath = computed(() => {
    if (!s.currentPath.value) return null
    const parts = s.currentPath.value.split('/')
    if (parts.length <= 1) return ''
    return parts.slice(0, -1).join('/')
  })

  const filteredEntries = computed(() => {
    if (!s.searchQuery.value.trim()) return s.entries.value
    return s.searchResults.value
  })

  const fileCount = computed(() => filteredEntries.value.filter((e) => e.type === 'file').length)
  const dirCount = computed(() => filteredEntries.value.filter((e) => e.type === 'directory').length)

  return {
    leftTabs, rightTabs, leftActiveTab, rightActiveTab,
    activeTab, selectedEntry, fileContent, fileUrl, fileContentType, fileContentLoading,
    breadcrumbs, parentPath, filteredEntries, fileCount, dirCount,
  }
}

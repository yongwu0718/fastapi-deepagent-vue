import { ref, computed, readonly } from 'vue'
import {
  listDirectoryEndpointApiFilesListGet,
  readFileEndpointApiFilesReadGet,
  getFileEndpointApiFilesFileGet,
  createFileEndpointApiFilesCreateFilePost,
  createDirectoryEndpointApiFilesCreateDirectoryPost,
  uploadFileEndpointApiFilesUploadPost,
  renameEndpointApiFilesRenamePut,
  moveEndpointApiFilesMovePut,
  modifyFileEndpointApiFilesModifyPut,
  deleteEndpointApiFilesDeleteDelete,
  searchFilesEndpointApiFilesSearchGet,
} from '@/api/client/sdk.gen'
import type {
  FileEntry,
  RawListResponse,
  RawReadResponse,
} from '@/api/files'
import {
  normalizeListResponse,
  normalizeReadResponse,
  isBinaryFile,
  isIframePreviewable,
  isPreviewableImage,
} from '@/api/files'
import { createLogger } from '@/shared/useLogger'
import { toast } from '@/shared/useToast'

const log = createLogger('[FileManager]')

/** 后端搜索 API 返回的原始条目 */
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

/** 文件标签页 */
export interface FileTab {
  id: string
  entry: FileEntry
  content: string
  contentType: string
  fileUrl: string
  contentLoading: boolean
  /** 所属窗格：分屏时区分左右 */
  pane: 'left' | 'right'
}

export function useFileManager() {
  // ── 目录状态 ──
  const currentPath = ref('')
  const entries = ref<FileEntry[]>([])
  const loading = ref(false)

  // ── 标签页管理 ──
  const openTabs = ref<FileTab[]>([])
  const activeTabId = ref('')

  // ── 分屏模式 ──
  const splitMode = ref(false)
  const activePane = ref<'left' | 'right'>('left')
  const leftActiveTabId = ref('')
  const rightActiveTabId = ref('')

  let _tabIdCounter = 0
  function _genTabId(): string {
    return `tab_${Date.now()}_${++_tabIdCounter}`
  }

  /** 左窗格标签列表 */
  const leftTabs = computed(() =>
    openTabs.value.filter((t) => t.pane === 'left'),
  )
  /** 右窗格标签列表 */
  const rightTabs = computed(() =>
    openTabs.value.filter((t) => t.pane === 'right'),
  )

  /** 左窗格活跃标签 */
  const leftActiveTab = computed(() =>
    openTabs.value.find((t) => t.id === leftActiveTabId.value && t.pane === 'left') ?? null,
  )
  /** 右窗格活跃标签 */
  const rightActiveTab = computed(() =>
    openTabs.value.find((t) => t.id === rightActiveTabId.value && t.pane === 'right') ?? null,
  )

  /** 活跃标签（分屏时返回聚焦窗格的活跃标签） */
  const activeTab = computed(() => {
    if (splitMode.value) {
      const tabId =
        activePane.value === 'left' ? leftActiveTabId.value : rightActiveTabId.value
      if (!tabId) return null
      return openTabs.value.find((t) => t.id === tabId) ?? null
    }
    return openTabs.value.find((t) => t.id === activeTabId.value) ?? null
  })

  /** 选中条目 — 从活跃标签派生 */
  const selectedEntry = computed<FileEntry | null>(() => activeTab.value?.entry ?? null)

  /** 文件内容 — 从活跃标签派生 */
  const fileContent = computed(() => activeTab.value?.content ?? '')

  /** 二进制文件的预览 URL */
  const fileUrl = computed(() => activeTab.value?.fileUrl ?? '')

  /** 文件内容类型 */
  const fileContentType = computed(() => activeTab.value?.contentType ?? '')

  /** 文件内容加载中 */
  const fileContentLoading = computed(() => activeTab.value?.contentLoading ?? false)

  // ── 计算 ──
  const breadcrumbs = computed(() => {
    if (!currentPath.value) return [{ label: 'index', path: '' }]
    const parts = currentPath.value.split('/')
    const crumbs: { label: string; path: string }[] = [{ label: 'index', path: '' }]
    let acc = ''
    for (const part of parts) {
      acc = acc ? `${acc}/${part}` : part
      crumbs.push({ label: part, path: acc })
    }
    return crumbs
  })

  const parentPath = computed(() => {
    if (!currentPath.value) return null
    const parts = currentPath.value.split('/')
    if (parts.length <= 1) return ''
    return parts.slice(0, -1).join('/')
  })

  // ── 搜索 ──
  const searchQuery = ref('')
  const searchResults = ref<FileEntry[]>([])
  const searchLoading = ref(false)

  const filteredEntries = computed(() => {
    if (!searchQuery.value.trim()) return entries.value
    return searchResults.value
  })

  let searchTimer: ReturnType<typeof setTimeout> | null = null

  async function searchFilesApi(query: string) {
    if (!query.trim()) {
      searchResults.value = []
      return
    }
    searchLoading.value = true
    try {
      const res = await searchFilesEndpointApiFilesSearchGet({ query: { q: query } })
      const data = res.data as RawSearchResponse
      if (data?.results) {
        searchResults.value = data.results.map(normalizeSearchItem)
      } else {
        searchResults.value = []
      }
    } catch (err) {
      log.error('搜索失败', err)
      searchResults.value = []
    } finally {
      searchLoading.value = false
    }
  }

  function setSearch(query: string) {
    searchQuery.value = query
    if (searchTimer) clearTimeout(searchTimer)
    if (!query.trim()) {
      searchResults.value = []
      return
    }
    searchTimer = setTimeout(() => searchFilesApi(query), 300)
  }

  function clearSearch() {
    searchQuery.value = ''
    searchResults.value = []
    if (searchTimer) clearTimeout(searchTimer)
  }

  const fileCount = computed(() => filteredEntries.value.filter((e) => e.type === 'file').length)
  const dirCount = computed(() => filteredEntries.value.filter((e) => e.type === 'directory').length)

  // ── 操作 ──

  /** 加载指定目录下的文件列表 */
  async function loadDirectory(path?: string) {
    const targetPath = path ?? currentPath.value
    loading.value = true
    log.debug('加载目录', { path: targetPath })

    try {
      const result = await listDirectoryEndpointApiFilesListGet(
        targetPath ? { query: { path: targetPath } } : undefined,
      )
      const data = result.data as RawListResponse
      if (data?.items) {
        const normalized = normalizeListResponse(data)
        entries.value = normalized.entries
        currentPath.value = normalized.path
        log.info(`已加载 ${normalized.entries.length} 个条目`, { path: targetPath })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '加载目录失败'
      log.error('加载目录失败', err)
      toast.error('加载目录失败', msg)
    } finally {
      loading.value = false
    }
  }

  /** 进入子目录 */
  async function navigateTo(path: string) {
    // 取消活跃标签（返回列表视图），仅在单屏模式下
    if (!splitMode.value) {
      activeTabId.value = ''
    }
    await loadDirectory(path)
  }

  /** 返回上级目录 */
  async function goUp() {
    if (parentPath.value !== null) {
      await navigateTo(parentPath.value)
    }
  }

  // ── 标签页操作 ──

  /** 读取文件内容到指定标签 */
  async function _readFileToTab(tab: FileTab, path: string) {
    tab.contentLoading = true
    tab.fileUrl = ''
    tab.contentType = ''
    log.debug('读取文件', { path })

    try {
      const fileName = path.split('/').pop() ?? path
      if (isBinaryFile(fileName)) {
        const result = await getFileEndpointApiFilesFileGet({ query: { path } })
        const blob = result.data as Blob
        if (tab.fileUrl && tab.fileUrl.startsWith('blob:')) {
          URL.revokeObjectURL(tab.fileUrl)
        }
        tab.fileUrl = URL.createObjectURL(blob)
        tab.content = ''

        if (isPreviewableImage(fileName)) {
          tab.contentType = 'image'
        } else if (isIframePreviewable(fileName)) {
          tab.contentType = 'pdf'
        } else {
          tab.contentType = 'binary'
        }
        log.info('二进制文件已加载', { path, type: tab.contentType })
      } else {
        const result = await readFileEndpointApiFilesReadGet({ query: { path } })
        const data = result.data as RawReadResponse
        if (data) {
          const normalized = normalizeReadResponse(data)
          tab.content = normalized.content
          tab.contentType = 'text'
          // 同步更新标签条目和列表条目的 editable 信息
          tab.entry.editable = normalized.editable
          const listEntry = entries.value.find((e) => e.path === path)
          if (listEntry) {
            listEntry.editable = normalized.editable
          }
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

  /** 打开文件（新建或激活已有标签） */
  async function openFile(path: string) {
    // 检查是否已打开
    const existing = openTabs.value.find((t) => t.entry.path === path)
    if (existing) {
      if (splitMode.value) {
        // 已在聚焦窗格中打开 → 直接激活
        if (existing.pane === activePane.value) {
          if (activePane.value === 'left') {
            leftActiveTabId.value = existing.id
          } else {
            rightActiveTabId.value = existing.id
          }
          return
        }
        // 在另一窗格 → 允许新建副本
      } else {
        activeTabId.value = existing.id
        return
      }
    }

    // 创建新标签
    const fileName = path.split('/').pop() ?? path
    const tab: FileTab = {
      id: _genTabId(),
      entry: {
        name: fileName,
        path,
        type: 'file',
        size: 0,
        modified: '',
      },
      content: '',
      contentType: '',
      fileUrl: '',
      contentLoading: false,
      pane: splitMode.value ? activePane.value : 'left',
    }
    openTabs.value = [...openTabs.value, tab]

    if (splitMode.value) {
      if (activePane.value === 'left') {
        leftActiveTabId.value = tab.id
      } else {
        rightActiveTabId.value = tab.id
      }
    } else {
      activeTabId.value = tab.id
    }

    // 必须通过 reactive 数组拿到 Proxy 版本再修改，否则 Vue 不会追踪变更
    const reactiveTab = openTabs.value.find((t) => t.id === tab.id)!
    await _readFileToTab(reactiveTab, path)
  }

  /** 关闭标签 */
  function closeTab(tabId: string) {
    const idx = openTabs.value.findIndex((t) => t.id === tabId)
    if (idx === -1) return

    const tab = openTabs.value[idx]
    // 清理 blob URL
    if (tab.fileUrl && tab.fileUrl.startsWith('blob:')) {
      URL.revokeObjectURL(tab.fileUrl)
    }

    openTabs.value = openTabs.value.filter((t) => t.id !== tabId)

    // 如果关闭的是活跃标签，切换到相邻标签或清空
    if (splitMode.value) {
      if (tab.pane === 'left' && leftActiveTabId.value === tabId) {
        const remaining = openTabs.value.filter((t) => t.pane === 'left')
        if (remaining.length > 0) {
          const newIdx = Math.min(
            leftTabs.value.findIndex((t) => t.id === tabId),
            remaining.length - 1,
          )
          leftActiveTabId.value = remaining[newIdx].id
        } else {
          leftActiveTabId.value = ''
          if (activePane.value === 'left') {
            activePane.value = 'right'
          }
        }
      } else if (tab.pane === 'right' && rightActiveTabId.value === tabId) {
        const remaining = openTabs.value.filter((t) => t.pane === 'right')
        if (remaining.length > 0) {
          const newIdx = Math.min(
            rightTabs.value.findIndex((t) => t.id === tabId),
            remaining.length - 1,
          )
          rightActiveTabId.value = remaining[newIdx].id
        } else {
          rightActiveTabId.value = ''
          if (activePane.value === 'right') {
            activePane.value = 'left'
          }
        }
      }
      // 无标签时退出分屏
      if (openTabs.value.length === 0) {
        splitMode.value = false
      }
    } else {
      if (activeTabId.value === tabId) {
        if (openTabs.value.length > 0) {
          const newIdx = Math.min(idx, openTabs.value.length - 1)
          activeTabId.value = openTabs.value[newIdx].id
        } else {
          activeTabId.value = ''
        }
      }
    }
  }

  /** 切换到指定标签 */
  function switchTab(tabId: string) {
    if (openTabs.value.some((t) => t.id === tabId)) {
      activeTabId.value = tabId
    }
  }

  /** 选中条目（目录进入，文件打开标签） */
  async function selectEntry(entry: FileEntry) {
    if (entry.type === 'directory') {
      await navigateTo(entry.path)
    } else {
      await openFile(entry.path)
    }
  }

  /** 读取文件内容（兼容旧 API，内部走 openFile） */
  async function readFile(path: string) {
    await openFile(path)
  }

  /** 创建新文件 */
  async function createFile(path: string, content?: string) {
    loading.value = true
    log.debug('创建文件', { path })

    try {
      await createFileEndpointApiFilesCreateFilePost({
        body: { path, content: content ?? '' },
      })
      toast.success('文件已创建', path)
      await loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '创建文件失败'
      log.error('创建文件失败', err)
      toast.error('创建文件失败', msg)
    } finally {
      loading.value = false
    }
  }

  /** 创建新目录 */
  async function createDirectory(path: string) {
    loading.value = true
    log.debug('创建目录', { path })

    try {
      await createDirectoryEndpointApiFilesCreateDirectoryPost({
        body: { path },
      })
      toast.success('目录已创建', path)
      await loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '创建目录失败'
      log.error('创建目录失败', err)
      toast.error('创建目录失败', msg)
    } finally {
      loading.value = false
    }
  }

  /** 上传文件到当前目录 */
  async function uploadFile(file: File, targetPath?: string) {
    loading.value = true
    const destPath = targetPath ?? `${currentPath.value ? currentPath.value + '/' : ''}${file.name}`
    log.debug('上传文件', { source: file.name, dest: destPath })

    try {
      await uploadFileEndpointApiFilesUploadPost({
        body: { file },
        query: { path: destPath },
      })
      toast.success('文件已上传', destPath)
      await loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '上传文件失败'
      log.error('上传文件失败', err)
      toast.error('上传文件失败', msg)
    } finally {
      loading.value = false
    }
  }

  /** 重命名文件/目录 */
  async function renameEntry(path: string, newName: string) {
    loading.value = true
    log.debug('重命名', { path, newName })

    try {
      await renameEndpointApiFilesRenamePut({
        body: { path, new_name: newName },
      })
      toast.success('已重命名', newName)
      await loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '重命名失败'
      log.error('重命名失败', err)
      toast.error('重命名失败', msg)
    } finally {
      loading.value = false
    }
  }

  /** 移动文件/目录 */
  async function moveEntry(path: string, targetDir: string) {
    loading.value = true
    log.debug('移动', { path, targetDir })

    try {
      await moveEndpointApiFilesMovePut({
        body: { path, target_dir: targetDir },
      })
      toast.success('已移动', path)
      await loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '移动失败'
      log.error('移动失败', err)
      toast.error('移动失败', msg)
    } finally {
      loading.value = false
    }
  }

  /** 保存文件内容（修改文件） */
  async function saveFile(path: string, content: string) {
    loading.value = true
    log.debug('保存文件', { path })

    try {
      await modifyFileEndpointApiFilesModifyPut({
        body: { path, content },
      })
      toast.success('文件已保存', path)
      // 更新所有标签中属于该文件的内容
      for (const tab of openTabs.value) {
        if (tab.entry.path === path) {
          tab.content = content
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '保存文件失败'
      log.error('保存文件失败', err)
      toast.error('保存文件失败', msg)
    } finally {
      loading.value = false
    }
  }

  /** 删除文件/目录 */
  async function deleteEntry(path: string) {
    loading.value = true
    log.debug('删除', { path })

    try {
      await deleteEndpointApiFilesDeleteDelete({
        body: { path },
      })
      toast.success('已删除', path)
      // 关闭所有涉及该路径的标签（精确匹配 + 子路径前缀匹配）
      const toClose = openTabs.value.filter(
        (t) => t.entry.path === path || t.entry.path.startsWith(path + '/'),
      )
      for (const tab of toClose) {
        closeTab(tab.id)
      }
      await loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '删除失败'
      log.error('删除失败', err)
      toast.error('删除失败', msg)
    } finally {
      loading.value = false
    }
  }

  /** 刷新当前目录 */
  async function refresh() {
    await loadDirectory()
  }

  /** 清除选中（关闭活跃标签，返回列表） */
  function clearSelection() {
    if (splitMode.value) {
      const tabId =
        activePane.value === 'left' ? leftActiveTabId.value : rightActiveTabId.value
      if (tabId) {
        closeTab(tabId)
      }
    } else {
      if (activeTabId.value) {
        closeTab(activeTabId.value)
      }
    }
  }

  /** 开启/关闭分屏模式 */
  function splitToggle() {
    if (splitMode.value) {
      // 退出分屏：关闭所有右窗格标签，左窗格标签转为普通标签
      const rightTabIds = openTabs.value
        .filter((t) => t.pane === 'right')
        .map((t) => t.id)
      for (const tid of rightTabIds) {
        closeTab(tid)
      }
      splitMode.value = false
      activePane.value = 'left'
      // 恢复单屏模式的活跃标签
      if (leftActiveTabId.value && openTabs.value.length > 0) {
        activeTabId.value = leftActiveTabId.value
      } else if (openTabs.value.length > 0) {
        activeTabId.value = openTabs.value[0].id
      } else {
        activeTabId.value = ''
      }
      leftActiveTabId.value = ''
      rightActiveTabId.value = ''
    } else {
      // 进入分屏
      splitMode.value = true
      activePane.value = 'right'
      leftActiveTabId.value = activeTabId.value
      rightActiveTabId.value = ''
      // 所有现有标签归左窗格
      for (const tab of openTabs.value) {
        tab.pane = 'left'
      }
    }
  }

  /** 移动标签到指定窗格 */
  function moveTabToPane(tabId: string, targetPane: 'left' | 'right') {
    const tab = openTabs.value.find((t) => t.id === tabId)
    if (!tab || tab.pane === targetPane) return

    const oldPane = tab.pane
    tab.pane = targetPane

    // 清空旧窗格活跃标记
    if (oldPane === 'left' && leftActiveTabId.value === tabId) {
      const remaining = openTabs.value.filter((t) => t.pane === 'left')
      leftActiveTabId.value = remaining.length > 0 ? remaining[remaining.length - 1].id : ''
    } else if (oldPane === 'right' && rightActiveTabId.value === tabId) {
      const remaining = openTabs.value.filter((t) => t.pane === 'right')
      rightActiveTabId.value = remaining.length > 0 ? remaining[remaining.length - 1].id : ''
    }

    // 在目标窗格中激活
    if (targetPane === 'left') {
      leftActiveTabId.value = tabId
    } else {
      rightActiveTabId.value = tabId
    }
    activePane.value = targetPane
  }

  // ── 检查文件是否已在标签中打开 ──
  function isFileOpen(path: string): boolean {
    return openTabs.value.some((t) => t.entry.path === path)
  }

  return {
    // 状态（只读）
    currentPath: readonly(currentPath),
    entries: readonly(entries),
    loading: readonly(loading),

    // 标签页
    openTabs,
    activeTabId: readonly(activeTabId),
    activeTab,

    // 分屏模式
    splitMode: readonly(splitMode),
    activePane,
    leftActiveTabId: readonly(leftActiveTabId),
    rightActiveTabId: readonly(rightActiveTabId),
    leftTabs,
    rightTabs,
    leftActiveTab,
    rightActiveTab,

    // 选中条目 / 文件内容（从活跃标签派生）
    selectedEntry,
    fileContent,
    fileUrl,
    fileContentType,
    fileContentLoading,

    // 计算
    breadcrumbs,
    parentPath,
    fileCount,
    dirCount,

    // 搜索
    searchQuery: readonly(searchQuery),
    searchLoading: readonly(searchLoading),
    filteredEntries,
    setSearch,
    clearSearch,

    // 操作
    loadDirectory,
    navigateTo,
    goUp,
    selectEntry,
    readFile,
    openFile,
    closeTab,
    switchTab,
    createFile,
    createDirectory,
    uploadFile,
    renameEntry,
    moveEntry,
    saveFile,
    deleteEntry,
    refresh,
    clearSelection,
    isFileOpen,
    // 分屏操作
    splitToggle,
    moveTabToPane,
  }
}

/** 模块级单例 */
let instance: ReturnType<typeof useFileManager> | null = null

export function getFileManager() {
  if (!instance) {
    instance = useFileManager()
  }
  return instance
}

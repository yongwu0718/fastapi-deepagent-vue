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

export function useFileManager() {
  // ── 状态 ──
  const currentPath = ref('')
  const entries = ref<FileEntry[]>([])
  const loading = ref(false)

  // 选中的条目
  const selectedEntry = ref<FileEntry | null>(null)
  // 已读取的文件内容（文本文件用）
  const fileContent = ref('')
  const fileContentLoading = ref(false)
  // 二进制文件的预览 URL（PDF/图片等）
  const fileUrl = ref('')
  // 文件内容类型：'text' | 'binary' | 'image' | 'pdf' | ''
  const fileContentType = ref('')

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
    selectedEntry.value = null
    fileContent.value = ''
    fileUrl.value = ''
    fileContentType.value = ''
    await loadDirectory(path)
  }

  /** 返回上级目录 */
  async function goUp() {
    if (parentPath.value !== null) {
      await navigateTo(parentPath.value)
    }
  }

  /** 读取文件内容 */
  async function readFile(path: string) {
    fileContentLoading.value = true
    fileUrl.value = ''
    fileContentType.value = ''
    log.debug('读取文件', { path })

    try {
      // 根据扩展名判断是否为二进制文件
      const fileName = path.split('/').pop() ?? path
      if (isBinaryFile(fileName)) {
        // 二进制文件：通过 SDK 调用 /api/files/file 端点
        // SDK 的 parseAs: 'auto' 会自动按 Content-Type (application/pdf, image/png 等)
        // 匹配为 blob，result.data 即为 Blob 对象
        const result = await getFileEndpointApiFilesFileGet({ query: { path } })
        const blob = result.data as Blob
        // 释放旧 URL
        if (fileUrl.value) {
          URL.revokeObjectURL(fileUrl.value)
        }
        fileUrl.value = URL.createObjectURL(blob)
        fileContent.value = ''

        // 根据类型标记
        if (isPreviewableImage(fileName)) {
          fileContentType.value = 'image'
        } else if (isIframePreviewable(fileName)) {
          fileContentType.value = 'pdf'
        } else {
          fileContentType.value = 'binary'
        }
        log.info('二进制文件已加载', { path, type: fileContentType.value })
      } else {
        // 文本文件：使用 /api/files/read 端点
        const result = await readFileEndpointApiFilesReadGet({ query: { path } })
        const data = result.data as RawReadResponse
        if (data) {
          const normalized = normalizeReadResponse(data)
          fileContent.value = normalized.content
          fileContentType.value = 'text'
          // 同步更新条目的 editable 信息
          const entry = entries.value.find((e) => e.path === path)
          if (entry) {
            entry.editable = normalized.editable
          }
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '读取文件失败'
      log.error('读取文件失败', err)
      toast.error('读取文件失败', msg)
    } finally {
      fileContentLoading.value = false
    }
  }

  /** 选中条目（目录进入，文件读取） */
  async function selectEntry(entry: FileEntry) {
    selectedEntry.value = entry
    if (entry.type === 'directory') {
      await navigateTo(entry.path)
    } else {
      await readFile(entry.path)
    }
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
      fileContent.value = content
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
      if (selectedEntry.value?.path === path) {
        selectedEntry.value = null
        fileContent.value = ''
        if (fileUrl.value) {
          URL.revokeObjectURL(fileUrl.value)
        }
        fileUrl.value = ''
        fileContentType.value = ''
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

  /** 清除选中 */
  function clearSelection() {
    selectedEntry.value = null
    fileContent.value = ''
    if (fileUrl.value) {
      URL.revokeObjectURL(fileUrl.value)
    }
    fileUrl.value = ''
    fileContentType.value = ''
  }

  return {
    // 状态（只读）
    currentPath: readonly(currentPath),
    entries: readonly(entries),
    loading: readonly(loading),
    selectedEntry: readonly(selectedEntry),
    fileContent: readonly(fileContent),
    fileUrl: readonly(fileUrl),
    fileContentType: readonly(fileContentType),
    fileContentLoading: readonly(fileContentLoading),

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
    createFile,
    createDirectory,
    uploadFile,
    renameEntry,
    moveEntry,
    saveFile,
    deleteEntry,
    refresh,
    clearSelection,
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

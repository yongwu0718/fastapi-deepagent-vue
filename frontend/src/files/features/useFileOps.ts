import {
  createFileEndpointApiFilesCreateFilePost,
  createDirectoryEndpointApiFilesCreateDirectoryPost,
  uploadFileEndpointApiFilesUploadPost,
  renameEndpointApiFilesRenamePut,
  moveEndpointApiFilesMovePut,
  modifyFileEndpointApiFilesModifyPut,
  deleteEndpointApiFilesDeleteDelete,
} from '@/api/client/sdk.gen'
import { createLogger } from '@/shared/useLogger'
import { toast } from '@/shared/useToast'

const log = createLogger('[FileManager]')

export function createFileOps(
  _state: any,
  _loadDirectory: () => Promise<void>,
  _closeTab: (tabId: string) => void,
) {
  async function createFile(path: string, content?: string) {
    _state.loading.value = true
    try {
      await createFileEndpointApiFilesCreateFilePost({ body: { path, content: content ?? '' } })
      toast.success('文件已创建', path)
      await _loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '创建文件失败'
      log.error('创建文件失败', err)
      toast.error('创建文件失败', msg)
    } finally { _state.loading.value = false }
  }

  async function createDirectory(path: string) {
    _state.loading.value = true
    try {
      await createDirectoryEndpointApiFilesCreateDirectoryPost({ body: { path } })
      toast.success('目录已创建', path)
      await _loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '创建目录失败'
      log.error('创建目录失败', err)
      toast.error('创建目录失败', msg)
    } finally { _state.loading.value = false }
  }

  async function uploadFile(file: File, targetPath?: string) {
    _state.loading.value = true
    const destPath = targetPath ?? `${_state.currentPath.value ? _state.currentPath.value + '/' : ''}${file.name}`
    try {
      await uploadFileEndpointApiFilesUploadPost({ body: { file }, query: { path: destPath } })
      toast.success('文件已上传', destPath)
      await _loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '上传文件失败'
      log.error('上传文件失败', err)
      toast.error('上传文件失败', msg)
    } finally { _state.loading.value = false }
  }

  async function renameEntry(path: string, newName: string) {
    _state.loading.value = true
    try {
      await renameEndpointApiFilesRenamePut({ body: { path, new_name: newName } })
      toast.success('已重命名', newName)
      await _loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '重命名失败'
      log.error('重命名失败', err)
      toast.error('重命名失败', msg)
    } finally { _state.loading.value = false }
  }

  async function moveEntry(path: string, targetDir: string) {
    _state.loading.value = true
    try {
      await moveEndpointApiFilesMovePut({ body: { path, target_dir: targetDir } })
      toast.success('已移动', path)
      await _loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '移动失败'
      log.error('移动失败', err)
      toast.error('移动失败', msg)
    } finally { _state.loading.value = false }
  }

  async function saveFile(path: string, content: string) {
    _state.loading.value = true
    try {
      await modifyFileEndpointApiFilesModifyPut({ body: { path, content } })
      toast.success('文件已保存', path)
      for (const tab of _state.openTabs.value) {
        if ((tab as any).entry.path === path) (tab as any).content = content
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '保存文件失败'
      log.error('保存文件失败', err)
      toast.error('保存文件失败', msg)
    } finally { _state.loading.value = false }
  }

  async function deleteEntry(path: string) {
    _state.loading.value = true
    try {
      await deleteEndpointApiFilesDeleteDelete({ body: { path } })
      toast.success('已删除', path)
      const toClose = _state.openTabs.value.filter(
        (t: any) => t.entry.path === path || t.entry.path.startsWith(path + '/'),
      )
      for (const tab of toClose as any[]) _closeTab(tab.id)
      await _loadDirectory()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '删除失败'
      log.error('删除失败', err)
      toast.error('删除失败', msg)
    } finally { _state.loading.value = false }
  }

  return { createFile, createDirectory, uploadFile, renameEntry, moveEntry, saveFile, deleteEntry }
}

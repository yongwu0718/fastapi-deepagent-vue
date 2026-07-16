<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  listDirectoryEndpointSettingsMemoryAndSkillListGet,
  readFileEndpointSettingsMemoryAndSkillReadGet,
  createFileEndpointSettingsMemoryAndSkillCreateFilePost,
  modifyFileEndpointSettingsMemoryAndSkillModifyPut,
  deleteEndpointSettingsMemoryAndSkillDeleteDelete,
  uploadFileEndpointSettingsMemoryAndSkillUploadPost,
  createDirectoryEndpointSettingsMemoryAndSkillCreateDirectoryPost,
} from '@/api/client/sdk.gen'

const props = defineProps<{
  type: 'memory' | 'skills'
  label: string
}>()

interface FileItem {
  name: string
  type: 'file' | 'directory'
  path: string
}

const items = ref<FileItem[]>([])
const loading = ref(false)
const currentPath = ref('')
const loadError = ref('')

const editing = ref(false)
const editFilename = ref('')
const editContent = ref('')
const editStatus = ref('')
const isNew = ref(false)

const parentPath = ref<string | null>(null)

/** 根据列表条目构造完整文件路径（补齐当前子目录前缀） */
function fileFullPath(item: FileItem) {
  const prefix = currentPath.value ? currentPath.value + '/' : ''
  return prefix + item.path
}

function calcParent(path: string): string | null {
  if (!path) return null
  const parts = path.split('/').filter(Boolean)
  if (parts.length === 0) return null
  parts.pop()
  return parts.join('/') || '' // "" 表示上级是根目录
}

async function loadDir(dir: string = '') {
  console.log('loadDir 调用 | dir=', dir || '(根)')
  loading.value = true
  loadError.value = ''
  try {
    const res = await listDirectoryEndpointSettingsMemoryAndSkillListGet({
      query: { type: props.type, path: dir },
    })
    const raw = (res.data as any)?.items
    console.log('loadDir 成功 | dir=', dir || '(根)', 'items=', raw?.length ?? 0)
    currentPath.value = dir
    parentPath.value = calcParent(dir)
    items.value = raw ?? []
  } catch (e: any) {
    console.error('loadDir 失败 | dir=', dir || '(根)', 'error=', e)
    items.value = []
    loadError.value = '加载失败: ' + (e?.body?.detail ?? String(e))
  } finally {
    loading.value = false
  }
}

function navigateTo(dir: string) {
  editing.value = false
  loadDir(dir)
}

function goUp() {
  if (parentPath.value !== null) {
    navigateTo(parentPath.value)
  }
}

async function openFile(item: FileItem) {
  if (item.type === 'directory') {
    await loadDir(fileFullPath(item))
    return
  }
  loading.value = true
  try {
    const res = await readFileEndpointSettingsMemoryAndSkillReadGet({
      query: { type: props.type, path: fileFullPath(item) },
    })
    editFilename.value = item.path
    editContent.value = (res.data as any)?.content ?? ''
    isNew.value = false
    editing.value = true
  } catch {
    editStatus.value = '读取失败'
  } finally {
    loading.value = false
  }
}

const uploadInput = ref<HTMLInputElement | null>(null)
const folderInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const uploadMsg = ref('')

// 上传文件夹时只上传这些类型的文件
const ALLOWED_EXTENSIONS = [
  '.md', '.txt', '.py', '.yaml', '.yml', '.json', '.toml',
  '.js', '.ts', '.html', '.css', '.xml', '.cfg', '.ini',
  '.env', '.sh', '.bat', '.ps1', '.sql',
]

function triggerUpload() {
  uploadInput.value?.click()
}

async function handleUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploading.value = true
  try {
    await uploadFileEndpointSettingsMemoryAndSkillUploadPost({
      body: { file },
      query: {
        type: props.type,
        path: currentPath.value ? currentPath.value + '/' + file.name : file.name,
      },
    })
    await loadDir(currentPath.value)
  } catch (err: any) {
    alert('上传失败: ' + (err?.body?.detail ?? String(err)))
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function triggerFolderUpload() {
  folderInput.value?.click()
}

async function handleFolderUpload(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  // 过滤：只保留指定类型的文件
  const allFiles = Array.from(input.files)
  const files = allFiles.filter((f) => {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase()
    return ALLOWED_EXTENSIONS.includes(ext)
  })
  const skipped = allFiles.length - files.length
  if (files.length === 0) {
    alert('所选文件夹中没有可上传的文件类型')
    input.value = ''
    return
  }

  uploading.value = true
  uploadMsg.value = ''

  const total = files.length

  // 收集所有需要创建的目录（去重）
  const dirs = new Set<string>()
  for (let i = 0; i < files.length; i++) {
    const relativePath = files[i].webkitRelativePath
    const dir = relativePath.substring(0, relativePath.lastIndexOf('/'))
    if (dir) dirs.add(dir)
  }

  try {
    // 先创建所有目录
    for (const dir of dirs) {
      const fullDir = currentPath.value ? currentPath.value + '/' + dir : dir
      try {
        await createDirectoryEndpointSettingsMemoryAndSkillCreateDirectoryPost({
          body: { path: fullDir },
          query: { type: props.type },
        })
      } catch (_) {
        // 目录可能已存在，忽略
      }
    }

    // 逐个上传文件
    let done = 0
    for (let i = 0; i < total; i++) {
      const file = files[i]
      const relativePath = file.webkitRelativePath
      const targetPath = currentPath.value
        ? currentPath.value + '/' + relativePath
        : relativePath
      uploadMsg.value = `上传中 ${done + 1}/${total}...`
      try {
        await uploadFileEndpointSettingsMemoryAndSkillUploadPost({
          body: { file },
          query: { type: props.type, path: targetPath },
        })
        done++
      } catch (err: any) {
        console.error('上传失败:', relativePath, err)
      }
    }
    uploadMsg.value = `完成 ${done}/${total}` + (skipped > 0 ? ` (已跳过 ${skipped} 个其他文件)` : '')
    await loadDir(currentPath.value)
  } catch (err: any) {
    alert('文件夹上传失败: ' + (err?.body?.detail ?? String(err)))
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function newFile() {
  editFilename.value = ''
  editContent.value = ''
  isNew.value = true
  editStatus.value = ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  editStatus.value = ''
}

async function saveFile() {
  if (!editFilename.value.trim()) {
    editStatus.value = '请输入文件名'
    return
  }
  editStatus.value = ''
  try {
    const filePath = currentPath.value ? currentPath.value + '/' + editFilename.value : editFilename.value
    if (isNew.value) {
      await createFileEndpointSettingsMemoryAndSkillCreateFilePost({
        body: { path: filePath, content: editContent.value },
        query: { type: props.type },
      })
    } else {
      await modifyFileEndpointSettingsMemoryAndSkillModifyPut({
        body: { path: filePath, content: editContent.value },
        query: { type: props.type },
      })
    }
    editStatus.value = '已保存 ✓'
    editing.value = false
    await loadDir(currentPath.value)
  } catch (e: any) {
    editStatus.value = '保存失败: ' + (e?.body?.detail ?? String(e))
  }
}

async function deleteFile(item: FileItem) {
  if (!confirm(`确定删除 ${item.path}？`)) return
  try {
    await deleteEndpointSettingsMemoryAndSkillDeleteDelete({
      body: { path: fileFullPath(item) },
      query: { type: props.type },
    })
    await loadDir(currentPath.value)
  } catch (e: any) {
    alert('删除失败: ' + (e?.body?.detail ?? String(e)))
  }
}

onMounted(() => loadDir())
</script>

<template>
  <div class="file-panel">
    <div class="file-toolbar">
      <div class="file-nav">
        <button class="nav-btn" :disabled="parentPath === null" @click="goUp">← 上级</button>
        <span class="current-path">/{{ type }}{{ currentPath ? '/' + currentPath : '' }}</span>
      </div>
      <div class="file-actions">
        <span v-if="uploadMsg" class="upload-msg">{{ uploadMsg }}</span>
        <button class="new-btn" @click="newFile" v-if="!editing">+ 新建文件</button>
        <button class="upload-btn" @click="triggerUpload" v-if="!editing" :disabled="uploading">
          上传
        </button>
        <button class="upload-btn" @click="triggerFolderUpload" v-if="!editing" :disabled="uploading">
          上传文件夹
        </button>
      </div>
    </div>

    <input
      ref="uploadInput"
      type="file"
      class="upload-input"
      @change="handleUpload"
    />
    <input
      ref="folderInput"
      type="file"
      class="upload-input"
      webkitdirectory
      directory
      @change="handleFolderUpload"
    />

    <div v-if="editing" class="edit-area">
      <div class="edit-header">
        <input
          v-model="editFilename"
          class="filename-input"
          placeholder="文件路径，如 notes/todo.md"
        />
        <div class="edit-actions">
          <span v-if="editStatus" class="edit-status">{{ editStatus }}</span>
          <button class="action-btn cancel" @click="cancelEdit">取消</button>
          <button class="action-btn save" @click="saveFile">保存</button>
        </div>
      </div>
      <textarea v-model="editContent" class="edit-textarea" spellcheck="false" />
    </div>

    <div v-else class="file-list">
      <div v-if="loading" class="list-loading">加载中...</div>
      <div v-else-if="loadError" class="list-error">{{ loadError }}</div>
      <div v-else-if="items.length === 0" class="list-empty">目录为空</div>
      <div
        v-for="item in items"
        :key="item.path"
        class="file-item"
        :class="{ 'is-dir': item.type === 'directory' }"
        @click="openFile(item)"
      >
        <span class="item-icon">{{ item.type === 'directory' ? '📁' : '📄' }}</span>
        <span class="item-name">{{ item.name }}</span>
        <button
          class="delete-btn"
          @click.stop="deleteFile(item)"
          title="删除"
        >✕</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-panel { display: flex; flex-direction: column; height: 100%; }
.file-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; background: #fff; border-bottom: 1px solid #e2e8f0; }
.file-nav { display: flex; align-items: center; gap: 8px; }
.nav-btn { padding: 3px 10px; border: 1px solid #cbd5e1; border-radius: 4px; background: #fff; font-size: 13px; cursor: pointer; }
.nav-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.current-path { font-size: 13px; color: #64748b; font-family: monospace; }
.file-actions { display: flex; align-items: center; gap: 6px; }
.new-btn { padding: 5px 14px; border: none; border-radius: 5px; background: #2563eb; color: #fff; font-size: 13px; cursor: pointer; }
.upload-btn { padding: 5px 14px; border: 1px solid #cbd5e1; border-radius: 5px; background: #fff; color: #475569; font-size: 13px; cursor: pointer; }
.upload-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.upload-btn:hover:not(:disabled) { background: #f1f5f9; }
.upload-msg { font-size: 12px; color: #2563eb; white-space: nowrap; }
.upload-input { display: none; }
.file-list { flex: 1; overflow-y: auto; padding: 4px 0; }
.list-loading, .list-empty, .list-error { text-align: center; padding: 40px; color: #94a3b8; font-size: 14px; }
.list-error { color: #ef4444; }
.file-item { display: flex; align-items: center; gap: 8px; padding: 8px 16px; cursor: pointer; border-bottom: 1px solid #f1f5f9; transition: background 0.1s; }
.file-item:hover { background: #f8fafc; }
.item-icon { font-size: 16px; }
.item-name { flex: 1; font-size: 13px; color: #334155; }
.is-dir .item-name { font-weight: 500; color: #2563eb; }
.delete-btn { padding: 2px 6px; border: none; background: none; color: #94a3b8; font-size: 14px; cursor: pointer; border-radius: 3px; opacity: 0; transition: all 0.15s; }
.file-item:hover .delete-btn { opacity: 1; }
.delete-btn:hover { background: #fee2e2; color: #ef4444; }
.edit-area { flex: 1; display: flex; flex-direction: column; }
.edit-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; background: #fff; border-bottom: 1px solid #e2e8f0; }
.filename-input { flex: 1; padding: 5px 10px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px; font-family: monospace; }
.edit-actions { display: flex; align-items: center; gap: 8px; margin-left: 12px; }
.edit-status { font-size: 12px; color: #059669; }
.action-btn { padding: 4px 12px; border: none; border-radius: 4px; font-size: 13px; cursor: pointer; }
.action-btn.cancel { background: #f1f5f9; color: #64748b; }
.action-btn.save { background: #16a34a; color: #fff; }
.edit-textarea { flex: 1; width: 100%; padding: 16px; border: none; resize: none; font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 13px; line-height: 1.6; background: #1e1e2e; color: #cdd6f4; outline: none; }
</style>

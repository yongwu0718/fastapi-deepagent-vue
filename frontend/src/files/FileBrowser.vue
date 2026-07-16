<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getFileManager } from './useFileManager'
import type { FileEntry } from '@/api/files'
import FileCreateDialog from './FileCreateDialog.vue'
import FileRenameDialog from './FileRenameDialog.vue'
import FileDeleteDialog from './FileDeleteDialog.vue'
import FilePreview from './FilePreview.vue'

const fm = getFileManager()

// ── 搜索 ──
const searchText = ref('')

// ── 对话框状态 ──
const showCreateDialog = ref(false)
const createMode = ref<'file' | 'directory'>('file')

const renameTarget = ref<FileEntry | null>(null)
const deleteTarget = ref<FileEntry | null>(null)

// 文件上传 input
const uploadInput = ref<HTMLInputElement | null>(null)

// ── FilePreview 引用 ──
const previewRef = ref<InstanceType<typeof FilePreview> | null>(null)

// ── 预览模式本地计算（不依赖 previewRef，避免 template ref 时序问题） ──
const isMarkdown = computed(() =>
  fm.selectedEntry.value?.name.toLowerCase().endsWith('.md') ?? false,
)

const textExts = ['txt', 'md', 'json', 'xml', 'yml', 'yaml', 'toml', 'ini', 'cfg',
  'csv', 'tsv', 'log', 'html', 'css', 'js', 'ts', 'py', 'java', 'go', 'rs', 'c',
  'cpp', 'h', 'sh', 'bat', 'ps1', 'env', 'gitignore', 'editorconfig', 'vue', 'jsx', 'tsx']

const isTextEditable = computed(() => {
  const entry = fm.selectedEntry.value
  if (!entry) return false
  if (entry.editable) return true
  const ext = entry.name.split('.').pop()?.toLowerCase()
  return !!(ext && textExts.includes(ext))
})

const isText = computed(() =>
  fm.fileContentType.value === 'text' || fm.fileContentType.value === '',
)

const isBinary = computed(() =>
  fm.fileContentType.value === 'binary' && !isPdf.value && !isImage.value,
)

const isPdf = computed(() => fm.fileContentType.value === 'pdf')
const isImage = computed(() => fm.fileContentType.value === 'image')

// Markdown 编辑模式（与 FilePreview 内部 isEditing 同步）
const isEditing = ref(false)

// 切换文件时重置编辑模式
watch(
  () => fm.selectedEntry.value?.path,
  () => { isEditing.value = false },
)

// ── 操作 ──

function goTo(path: string) {
  fm.navigateTo(path)
}

function onEntryClick(entry: FileEntry) {
  fm.selectEntry(entry)
}

function openCreateFile() {
  createMode.value = 'file'
  showCreateDialog.value = true
}

function openCreateDir() {
  createMode.value = 'directory'
  showCreateDialog.value = true
}

function onUploadClick() {
  uploadInput.value?.click()
}

async function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  await fm.uploadFile(file)
  input.value = ''
}

function onRename(entry: FileEntry) {
  renameTarget.value = entry
}

function onDelete(entry: FileEntry) {
  deleteTarget.value = entry
}

async function onRenameConfirm(newName: string) {
  if (!renameTarget.value) return
  await fm.renameEntry(renameTarget.value.path, newName)
  renameTarget.value = null
}

async function onDeleteConfirm() {
  if (!deleteTarget.value) return
  await fm.deleteEntry(deleteTarget.value.path)
  deleteTarget.value = null
}

async function onCreateConfirm(path: string, content?: string) {
  if (createMode.value === 'file') {
    await fm.createFile(path, content)
  } else {
    await fm.createDirectory(path)
  }
  showCreateDialog.value = false
}

function closePreview() {
  fm.clearSelection()
  isEditing.value = false
}

// ── 预览模式操作 ──
function onPreviewSave() {
  previewRef.value?.handleSave()
  // .md 文件保存后切回预览
  if (isMarkdown.value) {
    isEditing.value = false
  }
}

function onPreviewCopy() {
  previewRef.value?.handleCopy()
}

function onPreviewToggleEdit() {
  previewRef.value?.toggleEdit()
  // 同步编辑状态
  isEditing.value = previewRef.value?.isEditing ?? false
}

function onPreviewDownload() {
  previewRef.value?.handleDownload()
}

// ── 拖拽文件到目录：移动文件 ──
const dragOverDir = ref<string | null>(null)

function onDirDragOver(e: DragEvent, dirPath: string) {
  if (!dragSourcePath.value) return
  e.preventDefault()
  e.dataTransfer!.dropEffect = 'move'
  dragOverDir.value = dirPath
}

function onDirDragLeave() {
  dragOverDir.value = null
}

async function onDirDrop(e: DragEvent, dirPath: string) {
  e.preventDefault()
  dragOverDir.value = null
  if (!dragSourcePath.value) return
  await fm.moveEntry(dragSourcePath.value, dirPath)
  dragSourcePath.value = ''
}

// ── 格式化文件大小 ──
// ── 拖拽文件路径到对话框 ──
const dragSourcePath = ref('')

function onDragStart(e: DragEvent, entry: FileEntry) {
  if (entry.type !== 'file') return
  dragSourcePath.value = entry.path
  e.dataTransfer?.setData('text/plain', `/knowledge/${entry.path}`)
  e.dataTransfer!.effectAllowed = 'copyMove'
}

function fmtSize(bytes: number): string {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function fmtTime(iso: string): string {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    return d.toLocaleString()
  } catch {
    return iso
  }
}
</script>

<template>
  <div class="file-browser">
    <!-- 列表模式：统一头部 = 工具栏 + 面包屑 + 状态 -->
    <div v-if="!fm.selectedEntry.value" class="fb-header">
      <div class="fb-header-left">
        <button class="fb-btn" title="刷新" @click="fm.refresh()" :disabled="fm.loading.value">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
        </button>
        <!-- 面包屑 -->
        <template v-for="(item, idx) in fm.breadcrumbs.value" :key="item.path">
          <span v-if="idx > 0" class="fb-bc-sep">/</span>
          <button class="fb-bc-item" :class="{ active: idx === fm.breadcrumbs.value.length - 1 }" @click="goTo(item.path)">{{ item.label }}</button>
        </template>
        <!-- 状态 -->
        <span class="fb-inline-status">
          <span v-if="fm.loading.value" class="fb-loading-indicator">加载中...</span>
          <span v-else-if="fm.searchLoading.value" class="fb-loading-indicator">搜索中...</span>
          <span v-else-if="fm.searchQuery.value">{{ fm.filteredEntries.value.length }} 个匹配</span>
          <span v-else>{{ fm.fileCount.value }} 文件, {{ fm.dirCount.value }} 目录</span>
        </span>
      </div>
      <div class="fb-header-right">
        <div class="fb-search">
          <svg class="fb-search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <input v-model="searchText" type="text" class="fb-search-input" placeholder="搜索..." @input="fm.setSearch(searchText)" />
          <button v-if="fm.searchQuery.value" class="fb-search-clear" @click="searchText = ''; fm.clearSearch()" title="清除搜索">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        <button class="fb-btn fb-btn-primary" @click="openCreateFile">新建</button>
        <button class="fb-btn" @click="openCreateDir">目录</button>
        <button class="fb-btn" @click="onUploadClick">上传</button>
        <input ref="uploadInput" type="file" class="fb-upload-input" @change="onFileSelected" />
      </div>
    </div>

    <!-- 预览模式：统一头部 -->
    <div v-else class="fb-header fb-header--preview">
      <button class="fb-btn" @click="closePreview" title="返回">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5"/><polyline points="12 19 5 12 12 5"/></svg>
      </button>
      <span class="fb-preview-title">{{ fm.selectedEntry.value.name }}</span>
      <!-- Markdown: 编辑/预览切换 -->
      <template v-if="isMarkdown && isTextEditable && isText">
        <button v-if="isEditing" class="fb-btn" @click="onPreviewToggleEdit">预览</button>
        <button v-else class="fb-btn" @click="onPreviewToggleEdit">编辑</button>
        <button class="fb-btn" @click="onPreviewCopy">{{ previewRef?.copied ? '已复制' : '复制' }}</button>
        <button v-if="isEditing" class="fb-btn fb-btn-primary" @click="onPreviewSave" :disabled="fm.fileContentLoading.value">保存</button>
      </template>
      <!-- 普通可编辑文本 -->
      <template v-else-if="isTextEditable && isText">
        <button class="fb-btn" @click="onPreviewCopy">{{ previewRef?.copied ? '已复制' : '复制' }}</button>
        <button class="fb-btn fb-btn-primary" @click="onPreviewSave" :disabled="fm.fileContentLoading.value">保存</button>
      </template>
      <!-- 只读文本 -->
      <button v-else-if="isText" class="fb-btn" @click="onPreviewCopy">{{ previewRef?.copied ? '已复制' : '复制' }}</button>
      <!-- 二进制 -->
      <button v-if="isBinary || isPdf || isImage" class="fb-btn" @click="onPreviewDownload" :disabled="!fm.fileUrl.value">下载</button>
    </div>

    <!-- 文件列表 -->
    <div class="fb-list" v-if="!fm.selectedEntry.value">
      <!-- 返回上级 -->
      <div
        v-if="!fm.searchQuery.value && fm.parentPath.value !== null"
        class="fb-entry fb-entry-up"
        :class="{ 'fb-entry--drop-target': dragOverDir === fm.parentPath.value }"
        @click="fm.goUp()"
        @dragover="fm.parentPath.value !== null && onDirDragOver($event, fm.parentPath.value!)"
        @dragleave="onDirDragLeave()"
        @drop="fm.parentPath.value !== null && onDirDrop($event, fm.parentPath.value!)"
      >
        <svg class="fb-entry-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5l-7 7 7 7"/><path d="M4 12h16"/></svg>
        <span class="fb-entry-name">..</span>
      </div>

      <!-- 条目 -->
      <div
        v-for="entry in fm.filteredEntries.value"
        :key="entry.path"
        class="fb-entry"
        :class="{
          'fb-entry-dir': entry.type === 'directory',
          'fb-entry--draggable': entry.type === 'file',
          'fb-entry--drop-target': entry.type === 'directory' && dragOverDir === entry.path,
        }"
        :draggable="entry.type === 'file'"
        @dragover="entry.type === 'directory' && onDirDragOver($event, entry.path)"
        @dragleave="entry.type === 'directory' && onDirDragLeave()"
        @drop="entry.type === 'directory' && onDirDrop($event, entry.path)"
        @click="onEntryClick(entry)"
        @dragstart="onDragStart($event, entry)"
      >
        <!-- 图标 -->
        <svg v-if="entry.type === 'directory'" class="fb-entry-icon fb-icon-dir" width="16" height="16" viewBox="0 0 24 24" fill="var(--accent)" stroke="var(--accent)" stroke-width="1.5">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        </svg>
        <svg v-else class="fb-entry-icon fb-icon-file" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>
        </svg>

        <!-- 名称 -->
        <span class="fb-entry-name">{{ entry.name }}</span>

        <!-- 搜索模式下显示路径 -->
        <span v-if="fm.searchQuery.value" class="fb-entry-path">{{ entry.path }}</span>

        <!-- 大小 -->
        <span class="fb-entry-size" v-if="entry.type === 'file'">{{ fmtSize(entry.size) }}</span>

        <!-- 时间 -->
        <span class="fb-entry-time">{{ fmtTime(entry.modified) }}</span>

        <!-- 操作 -->
        <div class="fb-entry-actions" @click.stop>
          <button class="fb-action-btn" title="重命名" @click="onRename(entry)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="fb-action-btn fb-action-danger" title="删除" @click="onDelete(entry)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!fm.loading.value && fm.filteredEntries.value.length === 0" class="fb-empty">
        <p v-if="fm.searchQuery.value">未找到匹配 "{{ fm.searchQuery.value }}" 的文件</p>
        <p v-else>此目录为空</p>
      </div>
    </div>

    <!-- 文件预览/编辑器 -->
    <FilePreview
      ref="previewRef"
      v-if="fm.selectedEntry.value"
      :entry="fm.selectedEntry.value"
      :content="fm.fileContent.value"
      :content-type="fm.fileContentType.value"
      :file-url="fm.fileUrl.value"
      :loading="fm.fileContentLoading.value"
      @save="(c: string) => fm.selectedEntry.value && fm.saveFile(fm.selectedEntry.value.path, c)"
    />

    <!-- 对话框 -->
    <FileCreateDialog
      v-if="showCreateDialog"
      :mode="createMode"
      :current-path="fm.currentPath.value"
      @confirm="onCreateConfirm"
      @cancel="showCreateDialog = false"
    />

    <FileRenameDialog
      v-if="renameTarget"
      :entry="renameTarget"
      @confirm="onRenameConfirm"
      @cancel="renameTarget = null"
    />

    <FileDeleteDialog
      v-if="deleteTarget"
      :entry="deleteTarget"
      @confirm="onDeleteConfirm"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<style scoped>
.file-browser {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ── 统一头部 ── */
.fb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px 6px 12px;
  border-bottom: 1px solid var(--border, #e5e4e7);
  gap: 8px;
  flex-shrink: 0;
  min-height: 36px;
}

.fb-header--preview {
  justify-content: flex-start;
}

.fb-header-left,
.fb-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
}

.fb-header-right {
  flex-shrink: 0;
}

.fb-preview-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-h, #08060d);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 内联面包屑 ── */
.fb-bc-sep {
  font-size: 12px;
  color: var(--text-m, #9b8eaa);
  flex-shrink: 0;
}

.fb-bc-item {
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-m, #9b8eaa);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}

.fb-bc-item:hover {
  color: var(--text-h, #08060d);
  background: var(--bg-hover, #f5f3f7);
}

.fb-bc-item.active {
  color: var(--text-h, #08060d);
  font-weight: 600;
}

/* ── 内联状态 ── */
.fb-inline-status {
  font-size: 11px;
  color: var(--text-m, #9b8eaa);
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: 4px;
}

.fb-loading-indicator {
  animation: fb-pulse 1.5s ease-in-out infinite;
}

@keyframes fb-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ── 按钮 ── */
.fb-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 5px;
  background: var(--bg, #fff);
  color: var(--text, #6b6375);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  flex-shrink: 0;
}

.fb-btn:hover {
  background: var(--bg-hover, #f5f3f7);
  border-color: var(--accent, #aa3bff);
  color: var(--text-h, #08060d);
}

.fb-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fb-btn-primary {
  background: var(--accent, #aa3bff);
  color: #fff;
  border-color: var(--accent, #aa3bff);
}

.fb-btn-primary:hover {
  background: var(--accent-hover, #9333ea);
  color: #fff;
}

.fb-upload-input {
  display: none;
}

/* ── 文件列表 ── */
.fb-list {
  flex: 1;
  overflow-y: auto;
}

.fb-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px 8px 14px;
  cursor: pointer;
  transition: background 0.12s;
  border-bottom: 1px solid var(--border-subtle, #f0edf3);
}

.fb-entry:hover {
  background: var(--bg-hover, #f5f3f7);
}

.fb-entry-up {
  color: var(--text-m, #9b8eaa);
  font-weight: 500;
}

.fb-entry--draggable {
  cursor: grab;
}

.fb-entry--draggable:active {
  cursor: grabbing;
}

.fb-entry--drop-target {
  background: rgba(170, 59, 255, 0.08);
  outline: 2px dashed var(--accent, #aa3bff);
  outline-offset: -2px;
}

.fb-entry-icon {
  flex-shrink: 0;
}

.fb-icon-dir {
  color: var(--accent, #aa3bff);
}

.fb-icon-file {
  color: var(--text-m, #9b8eaa);
}

.fb-entry-name {
  flex: 1;
  font-size: 13px;
  color: var(--text-h, #08060d);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.fb-entry-path {
  flex: 0 0 auto;
  font-size: 10px;
  color: var(--text-m, #9b8eaa);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fb-entry-size {
  font-size: 11px;
  color: var(--text-m, #9b8eaa);
  flex-shrink: 0;
  min-width: 55px;
  text-align: right;
}

.fb-entry-time {
  font-size: 11px;
  color: var(--text-m, #9b8eaa);
  flex-shrink: 0;
  min-width: 100px;
  display: none;
}

@media (min-width: 480px) {
  .fb-entry-time {
    display: block;
  }
}

.fb-entry-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.12s;
}

.fb-entry:hover .fb-entry-actions {
  opacity: 1;
}

.fb-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-m, #9b8eaa);
  cursor: pointer;
  transition: all 0.12s;
}

.fb-action-btn:hover {
  background: var(--bg, #fff);
  color: var(--text-h, #08060d);
}

.fb-action-danger:hover {
  color: #ef4444;
  background: #fef2f2;
}

/* ── 空状态 ── */
.fb-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  color: var(--text-m, #9b8eaa);
  font-size: 13px;
}

/* ── 搜索框 ── */
.fb-search {
  display: flex;
  align-items: center;
  position: relative;
}

.fb-search-icon {
  position: absolute;
  left: 8px;
  color: var(--text-m, #9b8eaa);
  pointer-events: none;
}

.fb-search-input {
  width: 120px;
  padding: 4px 24px 4px 24px;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 5px;
  font-size: 11px;
  font-family: inherit;
  outline: none;
  background: var(--bg, #fff);
  color: var(--text-h, #08060d);
  transition: border-color 0.15s, width 0.2s;
}

.fb-search-input:focus {
  border-color: var(--accent, #aa3bff);
  box-shadow: 0 0 0 2px rgba(170, 59, 255, 0.12);
  width: 150px;
}

.fb-search-input::placeholder {
  color: var(--text-m, #9b8eaa);
}

.fb-search-clear {
  position: absolute;
  right: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-m, #9b8eaa);
  cursor: pointer;
  transition: all 0.12s;
}

.fb-search-clear:hover {
  background: var(--bg-hover, #f5f3f7);
  color: var(--text-h, #08060d);
}
</style>

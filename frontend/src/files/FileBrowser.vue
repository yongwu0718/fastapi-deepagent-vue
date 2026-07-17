<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getFileManager } from './useFileManager'
import type { FileEntry } from '@/api/files'
import FileCreateDialog from './dialogs/FileCreateDialog.vue'
import FileRenameDialog from './dialogs/FileRenameDialog.vue'
import FileDeleteDialog from './dialogs/FileDeleteDialog.vue'
import FilePreview from './preview/FilePreview.vue'
import FileList from './layout/FileList.vue'
import FileTabs from './layout/FileTabs.vue'
import SplitFileView from './layout/SplitFileView.vue'

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
const singlePreviewRef = ref<InstanceType<typeof FilePreview> | null>(null)
const splitViewRef = ref<InstanceType<typeof SplitFileView> | null>(null)

/** 当前活跃窗格的 FilePreview 引用 */
const previewRef = computed(() => {
  if (fm.splitMode.value && splitViewRef.value) {
    return fm.activePane.value === 'left'
      ? splitViewRef.value.leftPreviewRef
      : splitViewRef.value.rightPreviewRef
  }
  return singlePreviewRef.value
})

// ── 预览模式本地计算 ──
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

watch(
  () => fm.selectedEntry.value?.path,
  () => { isEditing.value = false },
)

// ── 大纲 ──
function scrollToHeading(id: string) {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

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

// ── 预览模式操作 ──
function onPreviewSave() {
  previewRef.value?.handleSave()
  if (isMarkdown.value) {
    isEditing.value = false
  }
}

function onPreviewCopy() {
  previewRef.value?.handleCopy()
}

function onPreviewToggleEdit() {
  previewRef.value?.toggleEdit()
  isEditing.value = previewRef.value?.isEditing ?? false
}

function onPreviewDownload() {
  previewRef.value?.handleDownload()
}

// ── 拖拽 ──
const dragSourcePath = ref('')

async function onMoveEntry(params: { sourcePath: string; targetDir: string }) {
  await fm.moveEntry(params.sourcePath, params.targetDir)
  dragSourcePath.value = ''
}

function onBreadcrumbDragStart(e: DragEvent, path: string) {
  e.dataTransfer?.setData('text/plain', `/knowledge/${path}`)
  e.dataTransfer!.effectAllowed = 'copy'
}
</script>

<template>
  <div class="file-browser">
    <!-- 头部 -->
    <div class="fb-header">
      <div class="fb-header-left">
        <button class="fb-btn" title="刷新" @click="fm.refresh()" :disabled="fm.loading.value">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
        </button>
        <template v-for="(item, idx) in fm.breadcrumbs.value" :key="item.path">
          <span v-if="idx > 0" class="fb-bc-sep">/</span>
          <button
            class="fb-bc-item"
            :class="{ active: idx === fm.breadcrumbs.value.length - 1 }"
            :draggable="item.path !== ''"
            @dragstart="onBreadcrumbDragStart($event, item.path)"
            @click="goTo(item.path)"
          >{{ item.label }}</button>
        </template>
        <span class="fb-inline-status">
          <span v-if="fm.loading.value" class="fb-loading-indicator">加载中...</span>
          <span v-else-if="fm.searchLoading.value" class="fb-loading-indicator">搜索中...</span>
          <span v-else-if="fm.searchQuery.value">{{ fm.filteredEntries.value.length }} 个匹配</span>
          <span v-else>{{ fm.fileCount.value }} 文件, {{ fm.dirCount.value }} 目录</span>
        </span>
      </div>
      <div class="fb-header-right">
        <template v-if="fm.activeTab.value">
          <template v-if="isMarkdown && isTextEditable && isText">
            <button v-if="isEditing" class="fb-btn" @click="onPreviewToggleEdit">预览</button>
            <button v-else class="fb-btn" @click="onPreviewToggleEdit">编辑</button>
            <button class="fb-btn" @click="onPreviewCopy">{{ previewRef?.copied ? '已复制' : '复制' }}</button>
            <button v-if="isEditing" class="fb-btn fb-btn-primary" @click="onPreviewSave" :disabled="fm.fileContentLoading.value">保存</button>
          </template>
          <template v-else-if="isTextEditable && isText">
            <button class="fb-btn" @click="onPreviewCopy">{{ previewRef?.copied ? '已复制' : '复制' }}</button>
            <button class="fb-btn fb-btn-primary" @click="onPreviewSave" :disabled="fm.fileContentLoading.value">保存</button>
          </template>
          <button v-else-if="isText" class="fb-btn" @click="onPreviewCopy">{{ previewRef?.copied ? '已复制' : '复制' }}</button>
          <button v-if="isBinary || isPdf || isImage" class="fb-btn" @click="onPreviewDownload" :disabled="!fm.fileUrl.value">下载</button>
        </template>
        <div v-if="!fm.activeTab.value" class="fb-search">
          <svg class="fb-search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <input v-model="searchText" type="text" class="fb-search-input" placeholder="搜索..." @input="fm.setSearch(searchText)" />
          <button v-if="fm.searchQuery.value" class="fb-search-clear" @click="searchText = ''; fm.clearSearch()" title="清除搜索">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        <button
          v-if="fm.openTabs.value.length > 0"
          class="fb-btn"
          :class="{ 'fb-btn-active': fm.splitMode.value }"
          @click="fm.splitToggle()"
          :title="fm.splitMode.value ? '退出分屏' : '分屏'"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="8" height="18" rx="1"/>
            <rect x="13" y="3" width="8" height="18" rx="1"/>
          </svg>
        </button>
        <button class="fb-btn fb-btn-primary" @click="openCreateFile">新建</button>
        <button class="fb-btn" @click="openCreateDir">目录</button>
        <button class="fb-btn" @click="onUploadClick">上传</button>
        <input ref="uploadInput" type="file" class="fb-upload-input" @change="onFileSelected" />
      </div>
    </div>

    <!-- ==================== 单屏模式 ==================== -->
    <template v-if="!fm.splitMode.value">
      <div v-if="fm.openTabs.value.length > 0" class="fb-tabs">
        <FileTabs
          :tabs="fm.openTabs.value"
          :active-tab-id="fm.activeTabId.value"
          :focused="true"
          pane="left"
          empty-text=""
          @switch-tab="fm.switchTab"
          @close-tab="fm.closeTab"
        />
        <button
          v-if="previewRef?.outline?.length"
          class="fb-tabs-outline-btn"
          :class="{ active: previewRef?.showOutline }"
          @click="previewRef!.showOutline = !previewRef!.showOutline"
          title="大纲"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>
            <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
          </svg>
        </button>
      </div>

      <div class="fb-content">
        <FileList
          v-if="!fm.activeTab.value"
          :entries="fm.filteredEntries.value"
          :loading="fm.loading.value"
          :search-query="fm.searchQuery.value"
          :search-loading="fm.searchLoading.value"
          :parent-path="fm.parentPath.value"
          :drag-source-path="dragSourcePath"
          :is-file-open="fm.isFileOpen"
          @entry-click="onEntryClick"
          @rename="onRename"
          @delete="onDelete"
          @go-up="fm.goUp()"
          @move-entry="onMoveEntry"
          @update:drag-source-path="dragSourcePath = $event"
        />
        <FilePreview
          v-if="fm.activeTab.value"
          ref="singlePreviewRef"
          :key="fm.activeTabId.value"
          :entry="fm.activeTab.value.entry"
          :content="fm.fileContent.value"
          :content-type="fm.fileContentType.value"
          :file-url="fm.fileUrl.value"
          :loading="fm.fileContentLoading.value"
          @save="(c: string) => fm.activeTab.value && fm.saveFile(fm.activeTab.value.entry.path, c)"
        />
      </div>
    </template>

    <!-- ==================== 分屏模式 ==================== -->
    <SplitFileView
      v-else
      ref="splitViewRef"
      @rename="onRename"
      @delete="onDelete"
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

    <!-- 大纲 -->
    <div
      v-if="previewRef?.showOutline && previewRef?.outline?.length"
      class="fb-outline-panel"
    >
      <div class="fb-outline-header">
        <span>大纲</span>
        <button class="fb-outline-close" @click="previewRef!.showOutline = false">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      </div>
      <div class="fb-outline-list">
        <button
          v-for="(item, idx) in previewRef.outline"
          :key="idx"
          class="fb-outline-item"
          :style="{ paddingLeft: 12 + (item.level - 1) * 14 + 'px' }"
          :class="{ 'fb-outline-item--h1': item.level === 1 }"
          @click="scrollToHeading(item.id)"
        >
          {{ item.text }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-browser {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

/* ── 头部 ── */
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

/* ── 标签栏容器 ── */
.fb-tabs {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border, #e5e4e7);
  background: var(--bg-subtle, #faf8fc);
  overflow: hidden;
}

/* ── 大纲按钮 ── */
.fb-tabs-outline-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  margin-right: 6px;
  flex-shrink: 0;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: var(--text-m, #9b8eaa);
  cursor: pointer;
  transition: all 0.12s;
}

.fb-tabs-outline-btn:hover {
  background: var(--bg-hover, #f5f3f7);
  color: var(--text-h, #08060d);
}

.fb-tabs-outline-btn.active {
  color: var(--accent, #aa3bff);
  border-color: var(--accent, #aa3bff);
}

/* ── 内容区域 ── */
.fb-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── 面包屑 ── */
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

.fb-btn-active {
  background: var(--accent, #aa3bff);
  color: #fff;
  border-color: var(--accent, #aa3bff);
}

.fb-btn-active:hover {
  background: var(--accent-hover, #9333ea);
  color: #fff;
}

.fb-upload-input {
  display: none;
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

/* ── 大纲 ── */
.fb-outline-panel {
  position: absolute;
  top: 40px;
  right: 8px;
  z-index: 30;
  width: 220px;
  max-height: calc(100% - 80px);
  background: var(--bg, #fff);
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.fb-outline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-subtle, #f0edf3);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-h, #08060d);
  flex-shrink: 0;
}

.fb-outline-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-m, #9b8eaa);
  cursor: pointer;
  transition: all 0.12s;
}

.fb-outline-close:hover {
  background: var(--bg-hover, #f5f3f7);
  color: var(--text-h, #08060d);
}

.fb-outline-list {
  overflow-y: auto;
  padding: 4px 0;
  flex: 1;
}

.fb-outline-item {
  display: block;
  width: 100%;
  padding: 5px 12px;
  border: none;
  background: transparent;
  color: var(--text, #6b6375);
  font-size: 12px;
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fb-outline-item:hover {
  background: var(--bg-hover, #f5f3f7);
  color: var(--accent, #aa3bff);
}

.fb-outline-item--h1 {
  font-weight: 600;
  color: var(--text-h, #08060d);
}
</style>

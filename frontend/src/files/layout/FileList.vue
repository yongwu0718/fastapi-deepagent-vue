<script setup lang="ts">
import { ref } from 'vue'
import type { FileEntry } from '@/api/files'

const props = defineProps<{
  entries: FileEntry[]
  loading: boolean
  searchQuery: string
  searchLoading: boolean
  parentPath: string | null
  dragSourcePath: string
  isFileOpen: (path: string) => boolean
}>()

const emit = defineEmits<{
  'entry-click': [entry: FileEntry]
  rename: [entry: FileEntry]
  delete: [entry: FileEntry]
  'go-up': []
  'move-entry': [params: { sourcePath: string; targetDir: string }]
  'update:dragSourcePath': [path: string]
}>()

// ── 本地拖拽状态 ──
const dragOverDir = ref<string | null>(null)

function onDirDragOver(e: DragEvent, dirPath: string) {
  if (!props.dragSourcePath) return
  e.preventDefault()
  e.dataTransfer!.dropEffect = 'move'
  dragOverDir.value = dirPath
}

function onDirDragLeave() {
  dragOverDir.value = null
}

function onDirDrop(e: DragEvent, dirPath: string) {
  e.preventDefault()
  dragOverDir.value = null
  if (!props.dragSourcePath) return
  emit('move-entry', { sourcePath: props.dragSourcePath, targetDir: dirPath })
  emit('update:dragSourcePath', '')
}

function onDragStart(e: DragEvent, entry: FileEntry) {
  if (entry.type !== 'file') return
  emit('update:dragSourcePath', entry.path)
  e.dataTransfer?.setData('text/plain', `/knowledge/${entry.path}`)
  e.dataTransfer!.effectAllowed = 'copyMove'
}

// ── 格式化 ──
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
  <div class="fb-list">
    <!-- 返回上级 -->
    <div
      v-if="!searchQuery && parentPath !== null"
      class="fb-entry fb-entry-up"
      :class="{ 'fb-entry--drop-target': dragOverDir === parentPath }"
      @click="emit('go-up')"
      @dragover="parentPath !== null && onDirDragOver($event, parentPath!)"
      @dragleave="onDirDragLeave()"
      @drop="parentPath !== null && onDirDrop($event, parentPath!)"
    >
      <svg class="fb-entry-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5l-7 7 7 7"/><path d="M4 12h16"/></svg>
      <span class="fb-entry-name">..</span>
    </div>

    <!-- 条目 -->
    <div
      v-for="entry in entries"
      :key="entry.path"
      class="fb-entry"
      :class="{
        'fb-entry-dir': entry.type === 'directory',
        'fb-entry--draggable': entry.type === 'file',
        'fb-entry--drop-target': entry.type === 'directory' && dragOverDir === entry.path,
        'fb-entry--open': entry.type === 'file' && isFileOpen(entry.path),
      }"
      :draggable="entry.type === 'file'"
      @dragover="entry.type === 'directory' && onDirDragOver($event, entry.path)"
      @dragleave="entry.type === 'directory' && onDirDragLeave()"
      @drop="entry.type === 'directory' && onDirDrop($event, entry.path)"
      @click="emit('entry-click', entry)"
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

      <!-- 已在标签中打开的标记 -->
      <span v-if="entry.type === 'file' && isFileOpen(entry.path)" class="fb-entry-tag" title="已在标签页中打开">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
      </span>

      <!-- 搜索模式下显示路径 -->
      <span v-if="searchQuery" class="fb-entry-path">{{ entry.path }}</span>

      <!-- 大小 -->
      <span class="fb-entry-size" v-if="entry.type === 'file'">{{ fmtSize(entry.size) }}</span>

      <!-- 时间 -->
      <span class="fb-entry-time">{{ fmtTime(entry.modified) }}</span>

      <!-- 操作 -->
      <div class="fb-entry-actions" @click.stop>
        <button class="fb-action-btn" title="重命名" @click="emit('rename', entry)">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </button>
        <button class="fb-action-btn fb-action-danger" title="删除" @click="emit('delete', entry)">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && entries.length === 0" class="fb-empty">
      <p v-if="searchQuery">未找到匹配 "{{ searchQuery }}" 的文件</p>
      <p v-else>此目录为空</p>
    </div>
  </div>
</template>

<style scoped>
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

.fb-entry--open {
  background: rgba(170, 59, 255, 0.04);
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

.fb-entry-tag {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  color: var(--accent, #aa3bff);
  opacity: 0.7;
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
</style>

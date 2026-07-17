<script setup lang="ts">
import { ref } from 'vue'
import type { FileTab } from '../useFileManager'

const props = defineProps<{
  tabs: FileTab[]
  activeTabId: string
  focused: boolean
  emptyText: string
  /** 当前所属窗格，用于跨窗格拖拽移动 */
  pane: 'left' | 'right'
}>()

const emit = defineEmits<{
  'switch-tab': [tabId: string]
  'close-tab': [tabId: string]
  activate: []
  'move-tab': [tabId: string, targetPane: 'left' | 'right']
}>()

/** 自定义 MIME 类型，标记拖拽的是标签页 */
const TAB_MIME = 'application/x-file-tab-id'

const dragOver = ref(false)

function onTabDragStart(e: DragEvent, tab: FileTab) {
  // 拖到聊天对话框：写入文件路径
  e.dataTransfer?.setData('text/plain', `/knowledge/${tab.entry.path}`)
  // 拖到另一窗格的标签栏：写入 tab id
  e.dataTransfer?.setData(TAB_MIME, tab.id)
  e.dataTransfer!.effectAllowed = 'copyMove'
}

function onTabBarDragOver(e: DragEvent) {
  // 只接受携带标签 ID 的拖拽
  if (!e.dataTransfer?.types.includes(TAB_MIME)) return
  // 防止拖回自身窗格（可选：允许则注释掉）
  e.preventDefault()
  dragOver.value = true
}

function onTabBarDragLeave() {
  dragOver.value = false
}

function onTabBarDrop(e: DragEvent) {
  dragOver.value = false
  const tabId = e.dataTransfer?.getData(TAB_MIME)
  if (!tabId) return
  e.preventDefault()
  // 目标窗格就是当前组件所属窗格
  emit('move-tab', tabId, props.pane)
}
</script>

<template>
  <div
    class="ft-tabs-bar"
    :class="{
      'ft-tabs-bar--focused': focused,
      'ft-tabs-bar--drag-over': dragOver,
    }"
    @mousedown="emit('activate')"
    @dragover="onTabBarDragOver"
    @dragleave="onTabBarDragLeave"
    @drop="onTabBarDrop"
  >
    <button
      v-for="tab in tabs"
      :key="tab.id"
      class="ft-tab"
      :class="{ active: tab.id === activeTabId }"
      :title="tab.entry.path"
      draggable="true"
      @dragstart="onTabDragStart($event, tab)"
      @click="emit('switch-tab', tab.id)"
    >
      <svg class="ft-tab-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>
      </svg>
      <span class="ft-tab-name">{{ tab.entry.name }}</span>
      <span v-if="tab.contentLoading" class="ft-tab-loading">...</span>
      <span
        class="ft-tab-close"
        role="button"
        @click.stop="emit('close-tab', tab.id)"
        title="关闭"
      >
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
      </span>
    </button>
    <span v-if="tabs.length === 0" class="ft-tabs-empty">{{ emptyText }}</span>
  </div>
</template>

<style scoped>
.ft-tabs-bar {
  display: flex;
  align-items: center;
  gap: 2px;
  overflow-x: auto;
  scrollbar-width: none;
  padding: 2px 4px;
  flex: 1;
  min-height: 32px;
  border-bottom: 2px solid transparent;
  transition: border-color 0.15s, background 0.15s;
}

.ft-tabs-bar::-webkit-scrollbar {
  display: none;
}

.ft-tabs-bar--focused {
  border-bottom-color: var(--accent, #aa3bff);
}

.ft-tabs-bar--drag-over {
  background: rgba(170, 59, 255, 0.06);
  border-bottom-color: var(--accent, #aa3bff);
}

.ft-tab {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 8px 5px 10px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: var(--text-m, #9b8eaa);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  max-width: 160px;
  transition: all 0.12s;
}

.ft-tab:hover {
  background: var(--bg-hover, #f5f3f7);
  color: var(--text-h, #08060d);
}

.ft-tab.active {
  background: var(--bg, #fff);
  color: var(--text-h, #08060d);
  border-color: var(--border, #e5e4e7);
  border-bottom-color: var(--bg, #fff);
  margin-bottom: -1px;
  border-radius: 4px 4px 0 0;
}

.ft-tab-icon {
  flex-shrink: 0;
  opacity: 0.6;
}

.ft-tab-name {
  overflow: hidden;
  text-overflow: ellipsis;
}

.ft-tab-loading {
  font-size: 10px;
  animation: ft-pulse 1.5s ease-in-out infinite;
  flex-shrink: 0;
}

.ft-tab-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 3px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.12s, background 0.12s;
}

.ft-tab:hover .ft-tab-close,
.ft-tab.active .ft-tab-close {
  opacity: 0.7;
}

.ft-tab-close:hover {
  opacity: 1 !important;
  background: var(--bg-hover, #f5f3f7);
  color: var(--text-h, #08060d);
}

.ft-tabs-empty {
  font-size: 11px;
  color: var(--text-m, #9b8eaa);
  padding: 0 8px;
  white-space: nowrap;
}

@keyframes ft-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>

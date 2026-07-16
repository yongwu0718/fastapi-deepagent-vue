<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToolMessages } from '@/chat/tools/useToolMessages'
import { useOutlineItems } from '@/chat/core/useContentNav'
import { useSidebarResize } from './useSidebarResize'
import ToolsTab from './ToolsTab.vue'
import OutlineTab from './OutlineTab.vue'
import DetailsTab from './DetailsTab.vue'

defineProps<{
  isOpen: boolean
}>()

const { sidebarWidth, isResizing, rootRef, onResizeStart } = useSidebarResize()

// ── Tab 栏 ──
type TabId = 'tools' | 'details' | 'outline'
const activeTab = ref<TabId>('tools')
const tabs: { id: TabId; label: string }[] = [
  { id: 'tools', label: '工具调用' },
  { id: 'outline', label: '大纲' },
  { id: 'details', label: '详情' },
]

// ── Tab badge 计数 ──
const { toolCallCount } = useToolMessages()
const { outlineItems } = useOutlineItems()
const outlineCount = computed(() => outlineItems.value.length)
</script>

<template>
  <div
    ref="rootRef"
    class="right-sidebar"
    :class="{ open: isOpen, resizing: isResizing }"
    :style="isOpen ? { width: sidebarWidth + 'px' } : {}"
  >
    <!-- 拖拽手柄 -->
    <div class="resize-handle" @mousedown="onResizeStart">
      <div class="resize-handle-line" />
    </div>
    <div class="right-sidebar-inner" :style="{ width: sidebarWidth + 'px' }">
      <!-- 头部 -->
      <div class="right-sidebar-header">
        <h3 class="right-sidebar-title">详情面板</h3>
      </div>

      <!-- Tab 栏 -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['tab-btn', { active: activeTab === tab.id }]"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
          <span v-if="tab.id === 'tools' && toolCallCount" class="tab-badge">
            {{ toolCallCount }}
          </span>
          <span v-if="tab.id === 'outline' && outlineCount" class="tab-badge">
            {{ outlineCount }}
          </span>
        </button>
      </div>

      <!-- 内容区 -->
      <div class="right-sidebar-body">
        <ToolsTab v-if="activeTab === 'tools'" />
        <OutlineTab v-if="activeTab === 'outline'" />
        <DetailsTab v-if="activeTab === 'details'" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.right-sidebar {
  width: 0;
  flex-shrink: 0;
  overflow: hidden;
  border-left: 1px solid var(--border, #e5e4e7);
  background: var(--bg, #fff);
  position: relative;
}

.right-sidebar:not(.resizing) {
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.right-sidebar-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ── 拖拽手柄 ── */
.resize-handle {
  position: absolute;
  left: -4px;
  top: 0;
  bottom: 0;
  width: 10px;
  z-index: 20;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
}

.resize-handle-line {
  width: 3px;
  height: 40px;
  border-radius: 2px;
  background: transparent;
  transition: background 0.15s;
}

.resize-handle:hover .resize-handle-line,
.right-sidebar.resizing .resize-handle-line {
  background: var(--accent, #aa3bff);
  opacity: 0.5;
}

/* ── 头部 ── */
.right-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border, #e5e4e7);
}

.right-sidebar-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-h, #08060d);
}

/* ── Tab 栏 ── */
.tab-bar {
  display: flex;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border, #e5e4e7);
  padding: 0 12px;
  gap: 0;
}

.tab-btn {
  position: relative;
  padding: 10px 16px;
  border: none;
  background: transparent;
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  color: var(--text, #6b6375);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: color 0.15s;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.tab-btn:hover {
  color: var(--text-h, #08060d);
}

.tab-btn.active {
  color: var(--accent, #aa3bff);
  border-bottom-color: var(--accent, #aa3bff);
}

.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 600;
  background: var(--accent, #aa3bff);
  color: #fff;
}

/* ── 内容区 ── */
.right-sidebar-body {
  flex: 1;
  overflow-y: auto;
}
</style>

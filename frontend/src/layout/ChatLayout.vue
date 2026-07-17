<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useChatHistory } from '@/threads/useChatHistory'
import { useToolMessages } from '@/chat/tools/useToolMessages'
import ChatSidebar from '@/threads/ChatSidebar.vue'
import ChatView from '@/chat/core/ChatView.vue'
import RightSidebar from '@/sidebar/RightSidebar.vue'
import FileBrowser from '@/files/FileBrowser.vue'
import { getFileManager } from '@/files/useFileManager'
import { useFilePanelResize } from './useFilePanelResize'

const {
  threads,
  activeThreadId,
  threadsLoading,
  loadThreads,
  createThread,
  selectThread,
  deleteThread,
  updateThreadTitle,
} = useChatHistory()

// 页面加载时从后端拉取线程列表
onMounted(() => loadThreads())

/** 侧边栏开关 */
const sidebarOpen = ref(true)
const {
  panelWidth: sidebarWidth,
  isResizing: sidebarResizing,
  rootRef: sidebarRef,
  onResizeStart: onSidebarResize,
} = useFilePanelResize(300)

// ── 文件面板持久化 ──
const LS_FILE_PANEL_OPEN = 'chat_file_panel_open'

/** 左侧文件面板开关 — 从 localStorage 恢复上次状态 */
const filePanelOpen = ref(localStorage.getItem(LS_FILE_PANEL_OPEN) === 'true')

watch(filePanelOpen, (open) => {
  localStorage.setItem(LS_FILE_PANEL_OPEN, String(open))
})

const {
  panelWidth: filePanelWidth,
  isResizing: fileResizing,
  rootRef: filePanelRef,
  onResizeStart: onFilePanelResize,
  onResizeStartLeft: onFilePanelResizeLeft,
} = useFilePanelResize()

/** 右侧详情面板开关 */
const rightSidebarOpen = ref(false)

/** 聊天是否已开始 */
const chatStarted = ref(false)

// ── 当流式工具调用到来时，自动展开右侧栏 ──
const { shouldAutoOpenSidebar, consumeAutoOpenSidebar } = useToolMessages()
watch(shouldAutoOpenSidebar, (val) => {
  if (val && consumeAutoOpenSidebar()) {
    rightSidebarOpen.value = true
  }
})

// ── 文件面板初始化：首次打开时恢复持久化状态或加载根目录 ──
const fm = getFileManager()

async function initFilePanel() {
  if (fm.entries.value.length > 0) return // 已初始化
  const restored = await fm.restoreState()
  if (!restored) {
    fm.loadDirectory()
  }
}

watch(filePanelOpen, async (open) => {
  if (open) {
    await initFilePanel()
  }
})

// 如果刷新前文件面板是打开的，onMounted 时恢复
onMounted(async () => {
  if (filePanelOpen.value) {
    await initFilePanel()
  }
})

function handleCreateThread() {
  createThread()
}

function handleSelectThread(id: string) {
  selectThread(id)
}

function handleToggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function handleToggleFilePanel() {
  filePanelOpen.value = !filePanelOpen.value
}

function handleToggleRightSidebar() {
  rightSidebarOpen.value = !rightSidebarOpen.value
}

function handleChatStarted(started: boolean) {
  chatStarted.value = started
}

function handleUpdateTitle(threadId: string, title: string) {
  updateThreadTitle(threadId, title)
}
</script>

<template>
  <div class="chat-layout">
    <!-- 侧边栏面板 -->
    <div
      ref="sidebarRef"
      class="sidebar-wrapper"
      :class="{ collapsed: !sidebarOpen, resizing: sidebarResizing }"
      :style="sidebarOpen ? { width: sidebarWidth + 'px' } : {}"
    >
      <div class="sidebar-inner" :style="{ width: sidebarWidth + 'px' }">
        <ChatSidebar
          :threads="threads"
          :active-thread-id="activeThreadId"
          :threads-loading="threadsLoading"
          @select="handleSelectThread"
          @create="handleCreateThread"
          @delete="deleteThread"
          @toggle="handleToggleSidebar"
        />
      </div>
      <!-- 拖拽手柄 -->
      <div class="sidebar-resize-handle">
        <div class="resize-handle-line" @mousedown="onSidebarResize" />
      </div>
    </div>

    <!-- 左侧文件管理面板 -->
    <div
      ref="filePanelRef"
      class="file-panel-wrapper"
      :class="{ collapsed: !filePanelOpen, resizing: fileResizing }"
      :style="filePanelOpen ? { width: filePanelWidth + 'px' } : {}"
    >
      <!-- 左侧拖拽手柄 -->
      <div class="file-panel-resize-handle file-panel-resize-handle--left">
        <div class="resize-handle-line" @mousedown="onFilePanelResizeLeft" />
      </div>
      <div class="file-panel-inner" :style="{ width: filePanelWidth + 'px' }">
        <FileBrowser />
      </div>
      <!-- 右侧拖拽手柄 -->
      <div class="file-panel-resize-handle file-panel-resize-handle--right">
        <div class="resize-handle-line" @mousedown="onFilePanelResize" />
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="main-content">
      <ChatView
        :thread-id="activeThreadId"
        :chat-started="chatStarted"
        :sidebar-open="sidebarOpen"
        :file-panel-open="filePanelOpen"
        :right-sidebar-open="rightSidebarOpen"
        @create-thread="handleCreateThread"
        @toggle-sidebar="handleToggleSidebar"
        @toggle-file-panel="handleToggleFilePanel"
        @toggle-right-sidebar="handleToggleRightSidebar"
        @chat-started="handleChatStarted"
        @update-title="handleUpdateTitle"
      />
    </div>

    <!-- 右侧详情抽屉面板 -->
    <RightSidebar :is-open="rightSidebarOpen" />
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  height: 100svh;
  width: 100%;
  overflow: hidden;
  background: var(--bg, #fff);
}

.sidebar-wrapper {
  flex-shrink: 0;
  overflow: hidden;
  position: relative;
}

.sidebar-wrapper:not(.resizing) {
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-wrapper.collapsed {
  width: 0 !important;
}

.sidebar-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── 侧边栏拖拽手柄 ── */
.sidebar-resize-handle {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 12px;
  z-index: 20;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.sidebar-resize-handle .resize-handle-line {
  width: 3px;
  height: 40px;
  border-radius: 2px;
  background: transparent;
  pointer-events: auto;
  /* 扩展点击区域 */
  padding: 0 6px;
  margin: 0 -6px;
  background-clip: content-box;
  transition: background 0.15s;
}

.sidebar-resize-handle .resize-handle-line:hover,
.sidebar-wrapper.resizing .sidebar-resize-handle .resize-handle-line {
  background: var(--accent, #aa3bff);
  opacity: 0.5;
}

.file-panel-wrapper {
  flex-shrink: 0;
  overflow: hidden;
  border-right: 1px solid var(--border, #e5e4e7);
  background: var(--bg, #fff);
  position: relative;
}

.file-panel-wrapper:not(.resizing) {
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.file-panel-wrapper.collapsed {
  width: 0 !important;
  border-right: none;
}

/* ── 拖拽手柄 ── */
.file-panel-resize-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 12px;
  z-index: 20;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.file-panel-resize-handle--right {
  right: 0;
}

.file-panel-resize-handle--left {
  left: 0;
}

.file-panel-resize-handle .resize-handle-line {
  width: 3px;
  height: 40px;
  border-radius: 2px;
  background: transparent;
  pointer-events: auto;
  /* 扩展点击区域 */
  padding: 0 6px;
  margin: 0 -6px;
  background-clip: content-box;
  transition: background 0.15s;
}

.file-panel-resize-handle .resize-handle-line:hover,
.file-panel-wrapper.resizing .file-panel-resize-handle .resize-handle-line {
  background: var(--accent, #aa3bff);
  opacity: 0.5;
}

.file-panel-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>

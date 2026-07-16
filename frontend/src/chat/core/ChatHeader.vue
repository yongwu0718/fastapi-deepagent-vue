<script setup lang="ts">
import { useRouter } from 'vue-router'
import AgentLogo from '@/shared/AgentLogo.vue'

defineProps<{
  hasMessages: boolean
  loading: boolean
  sidebarOpen: boolean
  filePanelOpen: boolean
  rightSidebarOpen: boolean
}>()

const emit = defineEmits<{
  toggleSidebar: []
  toggleFilePanel: []
  toggleRightSidebar: []
  createThread: []
}>()

const router = useRouter()

function goSettings() {
  router.push({ name: 'settings' })
}

function goRag() {
  router.push({ name: 'rag' })
}
</script>

<template>
  <!-- 空白状态头部 -->
  <header v-if="!hasMessages && !loading" class="chat-header chat-header--empty">
    <button
      class="header-sidebar-btn"
      :title="sidebarOpen ? '关闭侧边栏' : '打开侧边栏'"
      @click="emit('toggleSidebar')"
    >
      <svg v-if="!sidebarOpen" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="15" y1="3" x2="15" y2="21" />
        <line x1="9" y1="9" x2="9" y2="15" />
      </svg>
      <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="9" y1="3" x2="9" y2="21" />
        <line x1="15" y1="9" x2="15" y2="15" />
      </svg>
    </button>
    <button
      class="header-sidebar-btn"
      :title="filePanelOpen ? '关闭文件面板' : '打开文件面板'"
      @click="emit('toggleFilePanel')"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      </svg>
    </button>
    <div class="header-spacer" />
    <button
      class="header-settings-btn"
      title="向量库管理 (RAG)"
      @click="goRag"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
      </svg>
    </button>
    <button
      class="header-settings-btn"
      title="设置"
      @click="goSettings"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    </button>
    <button
      class="header-sidebar-btn"
      :title="rightSidebarOpen ? '关闭详情面板' : '打开详情面板'"
      @click="emit('toggleRightSidebar')"
    >
      <svg v-if="!rightSidebarOpen" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="9" y1="3" x2="9" y2="21" />
        <line x1="15" y1="9" x2="15" y2="15" />
      </svg>
      <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="15" y1="3" x2="15" y2="21" />
        <line x1="9" y1="9" x2="9" y2="15" />
      </svg>
    </button>
  </header>

  <!-- 聊天中完整头部 -->
  <header v-else class="chat-header chat-header--full">
    <div class="header-left">
      <button
        class="header-sidebar-btn"
        :title="sidebarOpen ? '关闭侧边栏' : '打开侧边栏'"
        @click="emit('toggleSidebar')"
      >
        <svg v-if="!sidebarOpen" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <line x1="15" y1="3" x2="15" y2="21" />
          <line x1="9" y1="9" x2="9" y2="15" />
        </svg>
        <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <line x1="9" y1="3" x2="9" y2="21" />
          <line x1="15" y1="9" x2="15" y2="15" />
        </svg>
      </button>
      <button
        class="header-sidebar-btn"
        :title="filePanelOpen ? '关闭文件面板' : '打开文件面板'"
        @click="emit('toggleFilePanel')"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
      </button>
      <button class="header-logo-btn" title="新建对话" @click="emit('createThread')">
        <AgentLogo :size="28" />
        <span class="header-title">Agent Chat</span>
      </button>
    </div>
    <div class="header-right">
      <button
        class="header-settings-btn"
        title="向量库管理 (RAG)"
        @click="goRag"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <ellipse cx="12" cy="5" rx="9" ry="3" />
          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        </svg>
      </button>
      <button
        class="header-settings-btn"
        title="设置"
        @click="goSettings"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      </button>
      <button
        class="header-sidebar-btn"
        :title="rightSidebarOpen ? '关闭详情面板' : '打开详情面板'"
        @click="emit('toggleRightSidebar')"
      >
        <svg v-if="!rightSidebarOpen" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <line x1="9" y1="3" x2="9" y2="21" />
          <line x1="15" y1="9" x2="15" y2="15" />
        </svg>
        <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <line x1="15" y1="3" x2="15" y2="21" />
          <line x1="9" y1="9" x2="9" y2="15" />
        </svg>
      </button>
      <button class="header-new-btn" title="新建对话" @click="emit('createThread')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 5v14" />
          <path d="M5 12h14" />
        </svg>
      </button>
    </div>
    <div class="header-gradient" />
  </header>
</template>

<style scoped>
.chat-header {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  flex-shrink: 0;
}

.chat-header--empty {
  justify-content: flex-start;
  padding: 10px 16px;
}

.chat-header--full {
  justify-content: space-between;
  max-width: var(--chat-max-width, 100%);
  margin: 0 auto;
  width: 100%;
  padding-left: 0;
  padding-right: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-sidebar-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid var(--border, #e5e4e7);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text, #6b6375);
  transition: background 0.15s;
  flex-shrink: 0;
}

.header-sidebar-btn:hover {
  background: var(--code-bg, #f4f3ec);
}

.header-spacer {
  flex: 1;
}

.header-logo-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s;
}

.header-logo-btn:hover {
  background: var(--code-bg, #f4f3ec);
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-h, #08060d);
  margin: 0;
  letter-spacing: -0.02em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-settings-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid var(--border, #e5e4e7);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text, #6b6375);
  transition: background 0.15s;
  flex-shrink: 0;
}
.header-settings-btn:hover {
  background: var(--code-bg, #f4f3ec);
  color: var(--accent, #aa3bff);
}

.header-new-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--border, #e5e4e7);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text, #6b6375);
  transition: background 0.15s, color 0.15s;
}

.header-new-btn:hover {
  background: var(--code-bg, #f4f3ec);
  color: var(--accent, #aa3bff);
}

.header-gradient {
  position: absolute;
  inset-inline: 0;
  top: 100%;
  height: 20px;
  background: linear-gradient(to bottom, var(--bg, #fff), transparent);
  pointer-events: none;
}
</style>

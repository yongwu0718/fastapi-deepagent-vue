<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ChatThread } from './useChatHistory'
import type { Message } from '@/api/chat'
import { getContentText } from '@/api/chat'

const LS_MSG_CACHE_PREFIX = 'chat_msgs_'

const props = defineProps<{
  threads: readonly ChatThread[]
  activeThreadId: string | null
  threadsLoading?: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  create: []
  delete: [id: string]
  toggle: []
}>()

const sortedThreads = computed(() =>
  [...props.threads].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  ),
)

function formatDate(iso: string): string {
  const date = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days} 天前`
  return date.toLocaleDateString()
}

function threadSnippet(thread: ChatThread): string {
  return thread.title || '新对话'
}

// ── 搜索 ──
const searchQuery = ref('')

/** 从 localStorage 读取线程消息缓存 */
function getCachedMessages(threadId: string): Message[] | null {
  try {
    const raw = localStorage.getItem(LS_MSG_CACHE_PREFIX + threadId)
    if (raw) return JSON.parse(raw)
  } catch { /* 忽略 */ }
  return null
}

const filteredThreads = computed(() => {
  const q = searchQuery.value.trim()
  if (!q) return sortedThreads.value

  try {
    const regex = new RegExp(q, 'i')
    return sortedThreads.value.filter((thread) => {
      if (regex.test(thread.title)) return true
      const cached = getCachedMessages(thread.id)
      if (!cached) return false
      return cached.some((msg) => regex.test(getContentText(msg.content)))
    })
  } catch {
    // 正则语法错误时，降级为普通字符串匹配
    const lower = q.toLowerCase()
    return sortedThreads.value.filter((thread) => {
      if (thread.title.toLowerCase().includes(lower)) return true
      const cached = getCachedMessages(thread.id)
      if (!cached) return false
      return cached.some((msg) => getContentText(msg.content).toLowerCase().includes(lower))
    })
  }
})

function clearSearch() {
  searchQuery.value = ''
}
</script>

<template>
  <aside class="sidebar-desktop">
    <!-- 头部 -->
    <div class="sidebar-header">
      <h1 class="sidebar-title">Thread History</h1>
    </div>

    <!-- 搜索栏 -->
    <div class="sidebar-search">
      <svg class="sidebar-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input
        v-model="searchQuery"
        class="sidebar-search-input"
        type="text"
        placeholder="搜索对话."
      />
      <button
        v-if="searchQuery"
        class="sidebar-search-clear"
        title="清除搜索"
        @click="clearSearch"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>

    <!-- 线程列表 / 骨架屏 -->
    <div v-if="threadsLoading" class="sidebar-list">
      <div
        v-for="i in 20"
        :key="'skeleton-' + i"
        class="sidebar-skeleton"
      />
    </div>
    <div v-else class="sidebar-list">
      <div
        v-for="thread in filteredThreads"
        :key="thread.id"
        :class="['sidebar-item', { active: thread.id === activeThreadId }]"
        role="button"
        tabindex="0"
        @click="emit('select', thread.id)"
        @keydown.enter="emit('select', thread.id)"
        @keydown.space.prevent="emit('select', thread.id)"
      >
        <p class="sidebar-item-text">{{ threadSnippet(thread) }}</p>
        <span class="sidebar-item-meta">{{ formatDate(thread.createdAt) }}</span>
        <button
          class="sidebar-item-delete"
          title="删除"
          @click.stop="emit('delete', thread.id)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div v-if="threads.length === 0" class="sidebar-empty">
        暂无对话历史
      </div>
      <div v-else-if="searchQuery && filteredThreads.length === 0" class="sidebar-empty">
        未找到匹配的对话
      </div>
    </div>

    <!-- 底部新建按钮 -->
    <div class="sidebar-footer">
      <button class="sidebar-new-btn" @click="emit('create')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        <span>新建对话</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar-desktop {
  width: 300px;
  height: 100%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border, #e5e4e7);
  background: var(--bg, #fff);
  overflow: hidden;
  box-shadow: inset -4px 0 6px -4px rgba(0, 0, 0, 0.04);
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border, #e5e4e7);
  flex-shrink: 0;
}

.sidebar-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-h, #08060d);
  margin: 0;
  letter-spacing: -0.02em;
}

/* ── 搜索栏 ── */
.sidebar-search {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border, #e5e4e7);
  flex-shrink: 0;
}

.sidebar-search-icon {
  color: var(--text, #6b6375);
  opacity: 0.5;
  flex-shrink: 0;
}

.sidebar-search-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font: inherit;
  font-size: 13px;
  color: var(--text-h, #08060d);
  padding: 4px 0;
}

.sidebar-search-input::placeholder {
  color: var(--text, #6b6375);
  opacity: 0.5;
}

.sidebar-search-clear {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text, #6b6375);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  opacity: 0.5;
  transition: opacity 0.15s, background 0.15s;
}

.sidebar-search-clear:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.06);
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--text, #6b6375);
  transition: background 0.15s;
}

.sidebar-item:hover {
  background: var(--code-bg, #f4f3ec);
}

.sidebar-item:focus-visible {
  outline: 2px solid var(--accent, #aa3bff);
  outline-offset: -2px;
}

.sidebar-item.active {
  background: var(--accent-bg, rgba(170, 59, 255, 0.1));
  color: var(--accent, #aa3bff);
}

.sidebar-item.active .sidebar-item-text {
  color: var(--accent, #aa3bff);
}

.sidebar-item-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 400;
  margin: 0;
  color: var(--text-h, #08060d);
}

.sidebar-item-meta {
  font-size: 11px;
  color: var(--text, #6b6375);
  opacity: 0.6;
  flex-shrink: 0;
}

.sidebar-item-delete {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text, #6b6375);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
  flex-shrink: 0;
}

.sidebar-item:hover .sidebar-item-delete {
  opacity: 1;
}

.sidebar-item-delete:hover {
  background: rgba(220, 38, 38, 0.1);
  color: #dc2626;
}

.sidebar-empty {
  padding: 24px 12px;
  text-align: center;
  font-size: 13px;
  color: var(--text, #6b6375);
  opacity: 0.6;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border, #e5e4e7);
  flex-shrink: 0;
}

.sidebar-new-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border, #e5e4e7);
  background: transparent;
  color: var(--text-h, #08060d);
  transition: background 0.15s, border-color 0.15s;
}

.sidebar-new-btn:hover {
  background: var(--code-bg, #f4f3ec);
  border-color: var(--accent, #aa3bff);
}

/* ── 骨架屏 ── */
.sidebar-skeleton {
  height: 44px;
  width: 100%;
  border-radius: 8px;
  background: var(--code-bg, #f4f3ec);
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

/* ── 滚动条 ── */
.sidebar-list::-webkit-scrollbar {
  width: 4px;
}

.sidebar-list::-webkit-scrollbar-thumb {
  border-radius: 9999px;
  background: rgba(0, 0, 0, 0.15);
}

.sidebar-list::-webkit-scrollbar-track {
  background: transparent;
}
</style>

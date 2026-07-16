<script setup lang="ts">
import { ref, computed, toRef, onMounted, onUnmounted } from 'vue'
import { useChatController } from './useChatController'
import { useContentNav } from './useContentNav'
import ChatHeader from './ChatHeader.vue'
import ChatMessages from './ChatMessages.vue'
import ChatInput from './ChatInput.vue'
import AgentLogo from '@/shared/AgentLogo.vue'
import ScrollToBottom from '@/shared/ScrollToBottom.vue'
import ApprovalCard from '@/chat/approval/ApprovalCard.vue'
import type { HITLDecision, HITLRequest, HITLResponse } from '@/api/chat'
import { loggerChat } from '@/shared/useLogger'

const props = defineProps<{
  threadId: string | null
  chatStarted: boolean
  sidebarOpen: boolean
  filePanelOpen: boolean
  rightSidebarOpen: boolean
}>()

const emit = defineEmits<{
  createThread: []
  toggleSidebar: []
  toggleFilePanel: []
  toggleRightSidebar: []
  chatStarted: [started: boolean]
  updateTitle: [threadId: string, title: string]
}>()

const threadIdRef = toRef(props, 'threadId')
const ctrl = useChatController(threadIdRef, {
  createThread: () => emit('createThread'),
  chatStarted: (val) => emit('chatStarted', val),
  updateTitle: (tid, title) => emit('updateTitle', tid, title),
})

// 模板 refs（必须在组件自身 setup 中声明）
const messagesRef = ref<InstanceType<typeof ChatMessages> | null>(null)

function onScrollToBottom() {
  ctrl.handleScrollToBottom(messagesRef.value)
}

function onResume(decisions: HITLDecision[]) {
  loggerChat.debug('onResume called', { decisionCount: decisions.length })
  ctrl.resumeChat(decisions)
}

function onCancelInterrupt() {
  ctrl.showInterrupt.value = false
  ctrl.interruptData.value = null
}

/** 解析中断负载为结构化数据 */
const parsedInterrupt = computed<HITLRequest | null>(() => {
  const data = ctrl.interruptData.value
  if (!data) return null
  try {
    const obj = typeof data === 'string' ? JSON.parse(data) : data
    if (obj && obj.action_requests?.length) return obj as HITLRequest
  } catch { /* 解析失败，回退 */ }
  return null
})

// 大纲数据同步到模块级共享状态（供 RightSidebar 读取）
useContentNav(ctrl.messages, ctrl.streamingContent)

// ── 对话宽度自由拖拽缩放 ──
const DEFAULT_MAX_WIDTH = '48rem'
const MIN_WIDTH_REM = 24

function getSavedWidth(): string {
  try {
    const saved = localStorage.getItem('chat_max_width')
    if (saved) return saved
  } catch { /* ignore */ }
  return DEFAULT_MAX_WIDTH
}

function saveWidth(val: string) {
  try {
    localStorage.setItem('chat_max_width', val)
  } catch { /* ignore */ }
}

const chatMaxWidth = ref(getSavedWidth())
const isDragging = ref(false)
const resizeHandleRef = ref<HTMLElement | null>(null)
const chatViewRef = ref<HTMLElement | null>(null)

function onDrag(e: MouseEvent) {
  if (!isDragging.value) return
  const container = chatViewRef.value
  if (!container) return
  const rect = container.getBoundingClientRect()
  const newWidthPx = e.clientX - rect.left
  const newWidthRem = newWidthPx / 16
  const maxWidthRem = rect.width / 16
  const clamped = Math.max(MIN_WIDTH_REM, Math.min(newWidthRem, maxWidthRem))
  chatMaxWidth.value = `${Math.round(clamped)}rem`
}

function startDrag(e: MouseEvent) {
  e.preventDefault()
  isDragging.value = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function stopDrag() {
  if (!isDragging.value) return
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  saveWidth(chatMaxWidth.value)
}

onUnmounted(() => {
  // 清理可能残留的事件监听
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
})
</script>

<template>
  <div ref="chatViewRef" class="chat-view" :style="{ '--chat-max-width': chatMaxWidth }">
    <ChatHeader
      :has-messages="ctrl.hasMessages.value"
      :loading="ctrl.loading.value"
      :sidebar-open="sidebarOpen"
      :file-panel-open="filePanelOpen"
      :right-sidebar-open="rightSidebarOpen"
      @toggle-sidebar="emit('toggleSidebar')"
      @toggle-file-panel="emit('toggleFilePanel')"
      @toggle-right-sidebar="emit('toggleRightSidebar')"
      @create-thread="emit('createThread')"
    />

    <div class="chat-content" :class="{ 'chat-content--empty': !ctrl.hasMessages.value && !ctrl.loading.value }">
      <!-- 历史加载中 -->
      <div v-if="ctrl.historyLoading.value" class="chat-empty">
        <div class="empty-logo">
          <div class="history-spinner" />
        </div>
        <h1 class="empty-title">加载对话中.</h1>
      </div>

      <!-- 空白状态 -->
      <div v-else-if="ctrl.showWelcome.value" class="chat-empty">
        <div class="empty-logo">
          <AgentLogo :size="48" />
        </div>
        <h1 class="empty-title">Agent Chat</h1>
        <p class="empty-desc">基于 RAG 的知识检索增强对话系统，支持文件上传与工具调用</p>
        <!-- 欢迎页居中输入框 -->
        <div class="empty-input">
          <ChatInput
            :loading="ctrl.loading.value"
            @send="ctrl.sendMessage"
            @cancel="ctrl.cancelRequest"
          />
        </div>
      </div>

      <!-- 消息列表 -->
      <div
        v-if="ctrl.hasMessages.value || ctrl.loading.value"
        class="chat-messages-wrapper"
        @scroll="ctrl.onMessagesScroll"
      >
        <ChatMessages
          ref="messagesRef"
          :messages="ctrl.messages.value"
          :streaming-content="ctrl.streamingContent.value"
          :streaming-reasoning="ctrl.streamingReasoning.value"
          :loading="ctrl.loading.value"
          :first-token-received="ctrl.firstTokenReceived.value"
          :show-interrupt="ctrl.showInterrupt.value"
          :interrupt-data="ctrl.interruptData.value"
          :retrying-message-index="ctrl.retryingMessageIndex.value"
          :forking-message-index="ctrl.forkingMessageIndex.value"
          :fork-editing-index="ctrl.forkEditingIndex.value"
          :fork-editing-draft="ctrl.forkEditingDraft.value"
          :branch-map="ctrl.branchMap.value"
          :branch-switching-index="ctrl.branchSwitchingIndex.value"
          @retry="(index: number) => ctrl.retryUserMessage(index)"
          @fork-edit="(index: number) => ctrl.startForkEdit(index)"
          @fork-cancel="ctrl.cancelForkEdit()"
          @fork-submit="(payload) => ctrl.submitForkEdit(payload)"
          @switch-branch="(msgIndex: number, leafCid: string) => ctrl.switchToBranch(msgIndex, leafCid)"
        />
      </div>

      <!-- 错误提示 -->
      <div v-if="ctrl.localError.value" class="chat-error">
        <span>{{ ctrl.localError.value }}</span>
        <button class="chat-error-close" @click="ctrl.clearError">✕</button>
      </div>

      <!-- 底部输入区（有消息时才显示） -->
      <div v-if="ctrl.hasMessages.value || ctrl.loading.value" class="chat-footer">
        <ScrollToBottom :visible="ctrl.showScrollButton.value" @click="onScrollToBottom" />
        <ChatInput
          :loading="ctrl.loading.value"
          @send="ctrl.sendMessage"
          @cancel="ctrl.cancelRequest"
        />
      </div>

      <!-- 中断审批卡片（覆盖整个 chat-content） -->
      <ApprovalCard
        v-if="ctrl.showInterrupt.value && parsedInterrupt"
        :action-requests="parsedInterrupt.action_requests"
        :review-configs="parsedInterrupt.review_configs"
        :loading="ctrl.loading.value"
        @respond="(response: HITLResponse) => onResume(response.decisions)"
        @cancel="onCancelInterrupt"
      />

      <!-- 拖拽缩放手柄（有消息时显示） -->
      <div
        v-if="ctrl.hasMessages.value || ctrl.loading.value"
        ref="resizeHandleRef"
        class="chat-resize-handle"
        :class="{ 'chat-resize-handle--active': isDragging }"
      >
        <div class="chat-resize-grip" @mousedown="startDrag" />
      </div>

    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  background: var(--bg, #fff);
}

/* ── 内容区域 ── */
.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.chat-content--empty {
  justify-content: flex-end;
}

.chat-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  margin-top: -10vh;
}

.empty-logo {
  margin-bottom: 16px;
  opacity: 0.9;
}

.empty-title {
  font: 600 28px/1.2 var(--heading, system-ui);
  color: var(--text-h, #08060d);
  margin: 0 0 8px;
  letter-spacing: -0.02em;
}

.empty-desc {
  font-size: 14px;
  color: var(--text, #6b6375);
  margin: 0;
  text-align: center;
  max-width: 360px;
}

/* ── 欢迎页居中输入框 ── */
.empty-input {
  margin-top: 32px;
  width: 100%;
  max-width: 32rem;
}

/* ── 消息滚动区 ── */
.chat-messages-wrapper {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 16px;
}

.chat-messages-wrapper::-webkit-scrollbar {
  width: 6px;
}

.chat-messages-wrapper::-webkit-scrollbar-thumb {
  border-radius: 9999px;
  background: rgba(0, 0, 0, 0.15);
}

.chat-messages-wrapper::-webkit-scrollbar-track {
  background: transparent;
}

/* ── 错误 ── */
.chat-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  font-size: 13px;
  color: #dc2626;
  background: rgba(220, 38, 38, 0.06);
  flex-shrink: 0;
}

.chat-error-close {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: #dc2626;
  opacity: 0.6;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-error-close:hover {
  opacity: 1;
}

/* ── 输入区容器 ── */
.chat-footer {
  position: relative;
  flex-shrink: 0;
  margin-bottom: 0;
}

/* ── 历史加载 spinner ── */
.history-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border, #e5e4e7);
  border-top-color: var(--accent, #aa3bff);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── 拖拽缩放手柄 ── */
.chat-resize-handle {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 20px;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none; /* 不拦截滚动条点击 */
}

.chat-resize-grip {
  width: 6px;
  height: 56px;
  border-radius: 3px;
  background: var(--border, #e5e4e7);
  transition: background 0.15s, height 0.15s, opacity 0.2s;
  opacity: 0;
  cursor: col-resize;
  pointer-events: auto; /* 仅 grip 响应拖拽 */
}

.chat-content:hover .chat-resize-grip,
.chat-resize-handle--active .chat-resize-grip {
  opacity: 1;
}

.chat-resize-grip:hover,
.chat-resize-handle--active .chat-resize-grip {
  background: var(--accent, #aa3bff);
  height: 72px;
}
</style>

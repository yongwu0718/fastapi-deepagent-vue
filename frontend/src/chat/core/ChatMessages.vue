<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import type { Message } from '@/api/chat'
import { DO_NOT_RENDER_ID_PREFIX } from './useChatState'
import ChatReason from './ChatReason.vue'
import Markdown from '@/shared/Markdown.vue'
import type { SiblingBranch } from '@/chat/checkpoints/useCheckpoints'

const props = defineProps<{
  messages: readonly Message[]
  streamingContent: string
  streamingReasoning: string
  loading: boolean
  firstTokenReceived: boolean
  showInterrupt: boolean
  interruptData: unknown
  /** 当前正在重试的消息索引（用于按钮 loading/disabled） */
  retryingMessageIndex?: number | null
  /** 当前正在分支的消息索引（用于按钮 loading/disabled） */
  forkingMessageIndex?: number | null
  /** 当前正在 fork 编辑态的消息索引（用于显示内联编辑器） */
  forkEditingIndex?: number | null
  /** fork 编辑框的初始内容（由父组件同步） */
  forkEditingDraft?: string
  /** 分支信息：msgIndex → { branches, currentIndex } */
  branchMap?: Map<number, { branches: SiblingBranch[]; currentIndex: number }>
  /** 当前正在切换分支的消息索引 */
  branchSwitchingIndex?: number | null
}>()

const emit = defineEmits<{
  /** 重试指定索引处的用户消息 */
  retry: [index: number]
  /** 进入 fork 编辑态（展示内联编辑器） */
  forkEdit: [index: number]
  /** 取消 fork 编辑 */
  forkCancel: []
  /** 提交 fork：携带编辑后的内容 */
  forkSubmit: [payload: { index: number; content: string }]
  /** 切换分支：msgIndex + 目标叶子检查点 ID */
  switchBranch: [msgIndex: number, targetLeafCid: string]
}>()

/** fork 编辑草稿（本地状态，编辑过程中维护，避免每次按键都触发父级更新） */
const editDraft = ref('')
const editTextareaRef = ref<HTMLTextAreaElement | null>(null)

function getBranchInfo(index: number): { branches: SiblingBranch[]; currentIndex: number } | null {
  return props.branchMap?.get(index) ?? null
}

/** 预计算每条消息的分支信息，避免模板中复杂调用 */
const branchInfoByIndex = computed(() => {
  return props.messages.map((_, i) => getBranchInfo(i))
})

/** 进入编辑态时，把父级传入的初始草稿同步到本地 ref，并自动聚焦 */
watch(
  () => [props.forkEditingIndex, props.forkEditingDraft] as const,
  ([idx, draft]) => {
    if (idx === null || idx === undefined) {
      editDraft.value = ''
      return
    }
    editDraft.value = draft ?? ''
    nextTick(() => {
      const el = editTextareaRef.value
      if (el && typeof el.focus === 'function') {
        el.focus()
        const len = (el as HTMLTextAreaElement).value.length
        ;(el as HTMLTextAreaElement).setSelectionRange(len, len)
      }
    })
  },
  { immediate: true },
)

const listRef = ref<HTMLElement | null>(null)

const hasStreamingReasoning = computed(() => props.streamingReasoning.length > 0)
const hasStreamingText = computed(() => props.streamingContent.length > 0)
const isReasoningPhase = computed(() => hasStreamingReasoning.value && !hasStreamingText.value)
const isStreaming = computed(() => hasStreamingReasoning.value || hasStreamingText.value)

/** 是否有中断负载（决定显示简单提示还是审批卡片） */
const hasInterruptPayload = computed(() => {
  if (!props.interruptData) return false
  try {
    const data = typeof props.interruptData === 'string'
      ? JSON.parse(props.interruptData)
      : props.interruptData
    return !!(data?.action_requests?.length)
  } catch { return false }
})

/** 复制状态：记录当前已复制的消息索引 */
const copiedIndex = ref<number | null>(null)

/** 复制消息内容到剪贴板 */
async function copyMessage(index: number, content: string) {
  try {
    await navigator.clipboard.writeText(content)
  } catch {
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = content
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
  }
  copiedIndex.value = index
  setTimeout(() => {
    if (copiedIndex.value === index) {
      copiedIndex.value = null
    }
  }, 2000)
}

/** ── 长消息折叠 ── */
const FOLD_CHAR_THRESHOLD = 500
const FOLD_PREVIEW_CHARS = 300
const expandedMessages = ref<Set<number>>(new Set())

function isFolded(index: number, content: string, role: string): boolean {
  return role === 'user' && content.length > FOLD_CHAR_THRESHOLD && !expandedMessages.value.has(index)
}

function toggleFold(index: number) {
  const s = new Set(expandedMessages.value)
  if (s.has(index)) {
    s.delete(index)
  } else {
    s.add(index)
  }
  expandedMessages.value = s
}

function getFoldPreview(content: string): string {
  return content.slice(0, FOLD_PREVIEW_CHARS) + '...'
}

function scrollToBottom() {
  const parent = listRef.value?.parentElement
  if (parent) {
    parent.scrollTo({ top: parent.scrollHeight, behavior: 'smooth' })
  }
}

defineExpose({ scrollToBottom })

watch(
  () => [
    props.messages.length,
    props.streamingContent,
    props.streamingReasoning,
  ],
  () => {
    nextTick(() => {
      const parent = listRef.value?.parentElement
      if (parent) {
        parent.scrollTo({ top: parent.scrollHeight, behavior: 'smooth' })
      }
    })
  },
)
</script>

<template>
  <div ref="listRef" class="chat-messages">
    <!-- 已完成的对话消息（过滤 DO_NOT_RENDER 前缀） -->
    <template v-for="(msg, index) in messages" :key="msg._key ?? `${index}-${msg.role}`">
      <div
        v-if="(!msg.content?.startsWith(DO_NOT_RENDER_ID_PREFIX) || msg.contentBlocks?.length) && msg.role !== 'tool'"
        :id="`msg-nav-${index}`"
        :class="['message', `message--${msg.role}`]"
      >
        <div class="message-avatar">
          {{ msg.role === 'user' ? '👤' : msg.role === 'system' ? '⚙️' : '🤖' }}
        </div>
        <div class="message-body">
          <div class="message-role">
            {{ msg.role === 'user' ? '你' : msg.role === 'system' ? '系统' : 'AI 助手' }}
          </div>

          <!-- 推理内容 -->
          <ChatReason
            v-if="msg.role === 'assistant' && msg.reasonContent"
            :reasoning="msg.reasonContent"
            :is-streaming="false"
          />

          <!-- 中断消息（仅在无内容和无多模态块时显示） -->
          <div v-if="msg.interrupt && !msg.content && !msg.contentBlocks?.length" class="interrupt-notice">
            <span class="interrupt-icon">⏸</span>
            <span>对话已中断，等待输入.</span>
          </div>

          <!-- 消息内容 / fork 编辑态 -->
          <div v-if="msg.content || msg.contentBlocks?.length" class="message-text" :class="{ 'message-text--folded': isFolded(index, msg.content, msg.role) }">
            <!-- fork 编辑中：内联编辑框（仅 user） -->
            <template v-if="msg.role === 'user' && forkEditingIndex === index">
              <textarea
                ref="editTextareaRef"
                class="fork-edit-textarea"
                rows="3"
                :value="editDraft"
                @input="(e: Event) => (editDraft = (e.target as HTMLTextAreaElement).value)"
                @keydown.enter.exact.prevent="emit('forkSubmit', { index, content: editDraft })"
                @keydown.esc.prevent="emit('forkCancel')"
                placeholder="修改该消息以创建新分支…"
              />
            </template>
            <template v-else>
              <!-- 多模态内容块（图片/文件）—— 仅 user 消息 -->
              <div v-if="msg.role === 'user' && msg.contentBlocks?.length" class="content-blocks">
                <div
                  v-for="(block, bi) in msg.contentBlocks"
                  :key="`block-${bi}`"
                  class="content-block-item"
                >
                  <img
                    v-if="block.type === 'image'"
                    :src="'data:' + block.mimeType + ';base64,' + block.data"
                    :alt="block.metadata.name || block.metadata.filename || '图片'"
                    class="content-block-image"
                    loading="lazy"
                  />
                  <div v-else class="content-block-file" :title="block.metadata.name || block.metadata.filename || '文件'">
                    <span class="file-icon">📎</span>
                    <span class="file-name">{{ block.metadata.name || block.metadata.filename || '附件' }}</span>
                  </div>
                </div>
              </div>
              <!-- 文本内容 -->
              <Markdown v-if="msg.role === 'assistant'">{{ msg.content }}</Markdown>
              <template v-else-if="isFolded(index, msg.content, msg.role)">{{ getFoldPreview(msg.content) }}</template>
              <template v-else>{{ msg.content }}</template>
            </template>
          </div>

          <!-- 长消息折叠按钮（仅 user 消息，无 contentBlocks 时才按文本长度折叠） -->
          <div
            v-if="msg.role === 'user' && msg.content && !msg.contentBlocks?.length && msg.content.length > FOLD_CHAR_THRESHOLD"
            class="fold-toggle"
            @click="toggleFold(index)"
          >
            {{ isFolded(index, msg.content, msg.role) ? '展开 ▼' : '收起 ▲' }}
          </div>

          <!-- fork 编辑态操作行 -->
          <div
            v-if="msg.role === 'user' && forkEditingIndex === index"
            class="message-actions"
          >
            <button
              type="button"
              class="copy-btn fork-btn"
              :disabled="forkingMessageIndex === index"
              title="使用编辑后的内容创建新分支"
              @click="emit('forkSubmit', { index, content: editDraft })"
            >
              <span v-if="forkingMessageIndex !== index">✅ 创建分支</span>
              <span v-else>⏳ 分支中…</span>
            </button>
            <button
              type="button"
              class="copy-btn"
              title="取消编辑"
              @click="emit('forkCancel')"
            >
              <span>✖ 取消</span>
            </button>
          </div>

          <!-- 操作按钮 -->
          <div class="message-actions">
            <!-- 复制按钮 -->
            <button
              type="button"
              v-if="(msg.content || msg.contentBlocks?.length) && (msg.role === 'user' || msg.role === 'assistant')"
              class="copy-btn"
              :class="{ 'copy-btn--copied': copiedIndex === index }"
              @click="copyMessage(index, msg.content)"
            >
              <span v-if="copiedIndex === index">✓ 已复制</span>
              <span v-else>📋 复制</span>
            </button>

            <!-- 重试按钮（仅对 user 消息，有内容或多模态块时显示） -->
            <button
              type="button"
              v-if="msg.role === 'user' && (msg.content || msg.contentBlocks?.length)"
              class="copy-btn retry-btn"
              :class="{ 'retry-btn--loading': retryingMessageIndex === index }"
              :disabled="retryingMessageIndex === index || props.loading"
              :title="retryingMessageIndex === index ? '正在重试…' : '从该消息的检查点重新执行'"
              @click="emit('retry', index)"
            >
              <span v-if="retryingMessageIndex !== index">🔄 重试</span>
              <span v-else class="retry-spinner-wrap">⏳ 重试中…</span>
            </button>

            <!-- 分支按钮（仅对 user 消息，有内容或多模态块时显示） -->
            <button
              type="button"
              v-if="msg.role === 'user' && (msg.content || msg.contentBlocks?.length)"
              class="copy-btn fork-btn"
              :class="{ 'fork-btn--loading': forkingMessageIndex === index }"
              :disabled="forkingMessageIndex === index || props.loading"
              :title="forkingMessageIndex === index ? '正在创建分支…' : '编辑该消息后从其检查点创建新分支'"
              @click="emit('forkEdit', index)"
            >
              <span v-if="forkingMessageIndex !== index">🌿 分支</span>
              <span v-else class="retry-spinner-wrap">⏳ 分支中…</span>
            </button>
          </div>

          <!-- 分支切换器（user 消息有多个兄弟分支时显示） -->
          <div
            v-if="msg.role === 'user' && branchInfoByIndex[index]"
            class="branch-switcher"
          >
            <button
              type="button"
              class="branch-nav-btn"
              :disabled="branchInfoByIndex[index]!.currentIndex <= 0 || loading || branchSwitchingIndex === index"
              :title="branchInfoByIndex[index]!.currentIndex <= 0 ? '已经是第一个分支' : '上一个分支'"
              @click="emit('switchBranch', index, branchInfoByIndex[index]!.branches[branchInfoByIndex[index]!.currentIndex - 1].leafCheckpointId ?? '')"
            >
              <span>◀</span>
            </button>
            <span class="branch-indicator">
              <span v-if="branchSwitchingIndex !== index">分支 {{ branchInfoByIndex[index]!.currentIndex + 1 }}/{{ branchInfoByIndex[index]!.branches.length }}</span>
              <span v-else>⏳ 切换中.</span>
            </span>
            <button
              type="button"
              class="branch-nav-btn"
              :disabled="branchInfoByIndex[index]!.currentIndex >= branchInfoByIndex[index]!.branches.length - 1 || loading || branchSwitchingIndex === index"
              :title="branchInfoByIndex[index]!.currentIndex >= branchInfoByIndex[index]!.branches.length - 1 ? '已经是最后一个分支' : '下一个分支'"
              @click="emit('switchBranch', index, branchInfoByIndex[index]!.branches[branchInfoByIndex[index]!.currentIndex + 1].leafCheckpointId ?? '')"
            >
              <span>▶</span>
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- 加载动画（首个 token 到达前） -->
    <div
      v-if="loading && !firstTokenReceived && !isStreaming"
      class="message message--assistant"
    >
      <div class="message-avatar">🤖</div>
      <div class="message-body">
        <div class="message-role">AI 助手</div>
        <div class="loading-dots">
          <span class="dot" />
          <span class="dot" />
          <span class="dot" />
        </div>
      </div>
    </div>

    <!-- 流式输出中 -->
    <div
      v-if="isStreaming"
      class="message message--assistant"
    >
      <div class="message-avatar">🤖</div>
      <div class="message-body">
        <div class="message-role">AI 助手</div>
        <ChatReason
          v-if="hasStreamingReasoning"
          :reasoning="streamingReasoning"
          :is-streaming="isReasoningPhase"
        />
        <div v-if="hasStreamingText" class="message-text">
          <Markdown>{{ streamingContent }}</Markdown>
          <span class="cursor-blink">▍</span>
        </div>
      </div>
    </div>

    <!-- 中断提示（无审批负载时显示简单提示，审批卡片由 ChatView 层渲染） -->
    <div
      v-if="showInterrupt && !isStreaming && !loading && !hasInterruptPayload"
      class="message message--assistant"
    >
      <div class="message-avatar">🤖</div>
      <div class="message-body">
        <div class="message-role">AI 助手</div>
        <div class="interrupt-notice">
          <span class="interrupt-icon">⏸</span>
          <span>对话已中断，输入你的回复以继续.</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-messages {
  max-width: var(--chat-max-width, 48rem);
  margin: 0 auto;
  padding: 32px 0 64px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 90%;
}

.message--user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message--assistant,
.message--system {
  align-self: flex-start;
}

.message-avatar {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  background: var(--code-bg, #f4f3ec);
}

.message-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.message--user .message-body {
  align-items: flex-end;
}

.message-role {
  font-size: 12px;
  font-weight: 600;
  color: var(--text, #6b6375);
  opacity: 0.7;
}

.message-text {
  padding: 10px 16px;
  border-radius: 16px;
  line-height: 1.6;
  word-break: break-word;
}

.message--user .message-text {
  background: var(--accent, #aa3bff);
  color: #fff;
  border-bottom-right-radius: 4px;
  white-space: pre-wrap;
}

.message--assistant .message-text {
  background: var(--code-bg, #f4f3ec);
  color: var(--text-h, #08060d);
  border-bottom-left-radius: 4px;
  font-size: 15px;
}

/* ── 中断提示 ── */
.interrupt-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 10px;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.2);
  font-size: 13px;
  color: #b45309;
}

.interrupt-icon {
  font-size: 16px;
}

.cursor-blink {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

/* ── 加载动画 ── */
.loading-dots {
  display: flex;
  gap: 5px;
  padding: 12px 16px;
  background: var(--code-bg, #f4f3ec);
  border-radius: 16px;
  border-bottom-left-radius: 4px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text, #6b6375);
  opacity: 0.4;
  animation: dotPulse 1.4s ease-in-out infinite;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.85); }
  40% { opacity: 0.8; transform: scale(1); }
}

/* ── 复制按钮 ── */
.copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text, #6b6375);
  background: transparent;
  border: 1px solid var(--border, #e0dce7);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  opacity: 0;
  align-self: flex-start;
}

.message:hover .copy-btn,
.message-body:hover .copy-btn {
  opacity: 1;
}

.copy-btn:hover {
  background: var(--code-bg, #f4f3ec);
  border-color: var(--accent, #aa3bff);
  color: var(--accent, #aa3bff);
}

.copy-btn--copied {
  opacity: 1 !important;
  color: #16a34a;
  border-color: #16a34a;
  background: rgba(22, 163, 74, 0.08);
}

.message--user .copy-btn {
  align-self: flex-end;
  color: rgba(255, 255, 255, 0.7);
  border-color: rgba(255, 255, 255, 0.3);
}

.message--user .copy-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.6);
  color: #fff;
}

.message--user .copy-btn--copied {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.2);
}

/* 消息操作按钮容器 */
.message-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* ── 重试按钮 ── */
/* 与复制按钮完全共用 .copy-btn 样式：默认 opacity: 0，hover 整条消息时显示。
   这里只覆盖 disabled / loading 态，复用 .copy-btn 的颜色/边框/hover 表现。 */

.retry-btn:disabled,
.fork-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5 !important;
}

.retry-btn--loading,
.fork-btn--loading {
  pointer-events: none;
  opacity: 1 !important;
}

/* ── Fork 内联编辑框 ── */
.fork-edit-textarea {
  width: 100%;
  min-width: 280px;
  max-width: 100%;
  padding: 8px 10px;
  font: inherit;
  font-size: 14px;
  line-height: 1.5;
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 8px;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s, background 0.15s;
  white-space: pre-wrap;
  word-break: break-word;
  box-sizing: border-box;
}

.fork-edit-textarea:focus {
  border-color: #fff;
  background: rgba(255, 255, 255, 0.15);
}

.fork-edit-textarea::placeholder {
  color: rgba(255, 255, 255, 0.6);
}

/* ── 长消息折叠 ── */
.message-text--folded {
  position: relative;
  max-height: 200px;
  overflow: hidden;
}

.message-text--folded::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 60px;
  pointer-events: none;
}

.message-text--user.message-text--folded::after,
.message--user .message-text--folded::after {
  background: linear-gradient(to bottom, transparent, var(--accent, #aa3bff));
}

.message--assistant .message-text--folded::after {
  background: linear-gradient(to bottom, transparent, var(--code-bg, #f4f3ec));
}

.fold-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  margin-top: 6px;
  font-size: 12px;
  font-weight: 500;
  color: var(--accent, #aa3bff);
  background: transparent;
  border: 1px solid var(--accent, #aa3bff);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
  align-self: flex-start;
}

.fold-toggle:hover {
  background: var(--accent, #aa3bff);
  color: #fff;
}

.message--user .fold-toggle {
  align-self: flex-end;
  color: var(--accent, #aa3bff);
  border-color: var(--accent, #aa3bff);
  background: transparent;
}

.message--user .fold-toggle:hover {
  background: var(--accent, #aa3bff);
  color: #fff;
}
.branch-switcher {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-top: 6px;
  padding: 3px 8px;
  border-radius: 16px;
  background: rgba(170, 59, 255, 0.06);
  border: 1px solid rgba(170, 59, 255, 0.15);
  align-self: flex-end;
}

.branch-nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  font-size: 12px;
  line-height: 1;
  color: var(--accent, #aa3bff);
  background: transparent;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.branch-nav-btn:hover:not(:disabled) {
  background: rgba(170, 59, 255, 0.12);
}

.branch-nav-btn:disabled {
  cursor: default;
  opacity: 0.3;
}

.branch-indicator {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent, #aa3bff);
  padding: 0 4px;
  min-width: 48px;
  text-align: center;
  user-select: none;
  white-space: nowrap;
}

/* ── 多模态内容块 ── */
.content-blocks {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 6px;
}

.content-block-item {
  max-width: 320px;
  border-radius: 8px;
  overflow: hidden;
}

.content-block-image {
  display: block;
  width: 100%;
  height: auto;
  max-height: 360px;
  object-fit: contain;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.05);
}

.content-block-file {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 6px;
  font-size: 13px;
  color: inherit;
}

.content-block-file .file-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.content-block-file .file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

</style>

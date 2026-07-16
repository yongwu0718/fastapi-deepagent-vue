import { ref, type Ref } from 'vue'
import type { Message, ToolCall } from '@/api/chat'

/** 不渲染的消息 ID 前缀 */
export const DO_NOT_RENDER_ID_PREFIX = 'do-not-render-'

/** 为消息添加前端唯一 _key（若已存在则不覆盖） */
export function ensureMessageKey(msg: Message): Message {
  if (!msg._key) {
    msg._key = `${msg.role}-${crypto.randomUUID().slice(0, 8)}`
  }
  return msg
}

/**
 * 聊天纯状态管理
 * —— 只负责响应式状态的定义与基础操作，不涉及 API 通信
 */
export function useChatState() {
  // ── 核心状态 ──
  const messages: Ref<Message[]> = ref([
    { role: 'assistant', content: '你好！我是 AI 助手，有什么可以帮你的？' },
  ])
  const loading = ref(false)
  const historyLoading = ref(false)
  const error = ref<string | null>(null)

  // ── 流式状态 ──
  const streamingContent = ref('')
  const streamingReasoning = ref('')
  const firstTokenReceived = ref(false)
  const pendingToolCalls = ref<Map<string, ToolCall>>(new Map())

  // ── 功能开关 ──
  const showInterrupt = ref(false)
  const interruptData = ref<unknown>(null)

  return {
    // 状态
    messages,
    loading,
    historyLoading,
    error,
    streamingContent,
    streamingReasoning,
    firstTokenReceived,
    showInterrupt,
    interruptData,
    pendingToolCalls,
  }
}
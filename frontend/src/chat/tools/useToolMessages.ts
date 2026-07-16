import { ref, computed, watch } from 'vue'
import type { ToolCall, Message } from '@/api/chat'
import { getContentText } from '@/api/chat'

export interface ToolCallGroup {
  messageIndex: number
  messageContent: string
  toolCalls: ToolCall[]
}

/** 单条 tool 角色消息条目（来自历史加载） */
export interface ToolMessageEntry {
  messageIndex: number
  /** tool 消息的返回内容 */
  content: string
  /** 关联的工具名（从邻近 assistant toolCalls 推断） */
  toolName?: string
  /** 关联的 tool_call_id */
  toolCallId?: string
}

/** 按消息分组的工具调用（供右侧栏展示） */
const _toolCallGroups = ref<ToolCallGroup[]>([])

/** tool 角色消息列表（来自 get-messages-history） */
const _toolMessages = ref<ToolMessageEntry[]>([])

/** 流式期间的实时工具调用（从 pendingToolCalls 同步，含实时 tool_result） */
const _streamingToolCalls = ref<ToolCall[]>([])

/** 是否应自动展开右侧栏（当流式工具调用到来时触发） */
const _shouldAutoOpenSidebar = ref(false)

/** 监听流式工具调用变化 → 触发右侧栏自动展开 */
watch(_streamingToolCalls, (calls) => {
  if (calls.length > 0) {
    _shouldAutoOpenSidebar.value = true
  }
}, { deep: false })

/** 工具调用总数（assistant toolCalls + tool 消息 + 流式） */
const toolCallCount = computed(() =>
  _toolCallGroups.value.reduce((sum, g) => sum + g.toolCalls.length, 0)
  + _toolMessages.value.length
  + _streamingToolCalls.value.length,
)

/** 从 messages 中提取 toolCalls 和 tool 角色消息 */
function syncToolCalls(messages: readonly Message[]) {
  // 1. 收集 assistant 消息中的 toolCalls
  const groups: ToolCallGroup[] = []
  const assistantToolCalls: Map<number, ToolCall[]> = new Map()

  messages.forEach((msg, i) => {
    if (msg.role === 'assistant' && msg.toolCalls?.length) {
      // 提取 tool_call_id → name 映射
      const nameMap = new Map<string, string>()
      msg.toolCalls.forEach((tc) => nameMap.set(tc.id, tc.name))
      assistantToolCalls.set(i, msg.toolCalls)

      groups.push({
        messageIndex: i,
        messageContent: getContentText(msg.content).slice(0, 120),
        toolCalls: msg.toolCalls,
      })
    }
  })

  _toolCallGroups.value = groups

  // 2. 收集 tool 角色消息，就近匹配 assistant toolCalls
  const toolEntries: ToolMessageEntry[] = []
  messages.forEach((msg, i) => {
    const text = getContentText(msg.content)
    if (msg.role !== 'tool' || !text) return

    // 尝试找到最近的前一个 assistant 消息的 toolCalls 中匹配的 name
    let toolName: string | undefined
    let toolCallId: string | undefined

    // 从当前位置向前搜索最近的 assistant 消息
    for (let j = i - 1; j >= 0; j--) {
      const prev = messages[j]
      if (prev.role === 'assistant' && prev.toolCalls?.length) {
        // 取第一个未匹配的 toolCall 作为候选（按出现顺序）
        const prevEntries = toolEntries.filter((e) => e.messageIndex === i)
        const usedNames = new Set(prevEntries.map((e) => e.toolName).filter(Boolean))
        for (const tc of prev.toolCalls) {
          if (!usedNames.has(tc.name)) {
            toolName = tc.name
            toolCallId = tc.id
            break
          }
        }
        break
      }
    }

    toolEntries.push({ messageIndex: i, content: text, toolName, toolCallId })
  })

  _toolMessages.value = toolEntries
}

/**
 * 共享的工具消息状态
 * —— 跨组件使用（ChatMessages / RightSidebar / ChatView），无需 prop drilling
 */
export function useToolMessages() {
  /** 设置流式工具调用（SSE 收到 tool_call / tool_result 时调用） */
  function setStreamingToolCalls(calls: ToolCall[]) {
    _streamingToolCalls.value = calls
  }

  /** 清空流式工具调用（流结束时调用） */
  function clearStreamingToolCalls() {
    _streamingToolCalls.value = []
  }

  /** 消费自动展开信号（调用后重置为 false） */
  function consumeAutoOpenSidebar(): boolean {
    if (_shouldAutoOpenSidebar.value) {
      _shouldAutoOpenSidebar.value = false
      return true
    }
    return false
  }

  return {
    toolCallGroups: _toolCallGroups,
    toolMessages: _toolMessages,
    streamingToolCalls: _streamingToolCalls,
    toolCallCount,
    shouldAutoOpenSidebar: _shouldAutoOpenSidebar,
    syncToolCalls,
    setStreamingToolCalls,
    clearStreamingToolCalls,
    consumeAutoOpenSidebar,
  }
}
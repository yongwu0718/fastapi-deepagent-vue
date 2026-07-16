import type { useChatState } from '@/chat/core/useChatState'

type ChatState = ReturnType<typeof useChatState>

/**
 * 重置所有流式状态字段。
 *
 * 在 sendMessage / resumeChat / replayCheckpoint / forkFromCheckpoint 中
 * 共享此函数，消除 4 处重复代码。
 */
export function resetStreamingState(state: ChatState): void {
  state.loading.value = true
  state.error.value = null
  state.streamingContent.value = ''
  state.streamingReasoning.value = ''
  state.firstTokenReceived.value = false
  state.pendingToolCalls.value = new Map()
  state.showInterrupt.value = false
  state.interruptData.value = null
}

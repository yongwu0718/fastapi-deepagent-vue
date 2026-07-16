import { ref, watch, onUnmounted, type Ref } from 'vue'
import { client } from '@/api/client/client.gen'
import type { Message, StreamChunk, ContentBlock as ApiContentBlock, HITLDecision } from '@/api/chat'
import { toast } from '@/shared/useToast'
import type { useChatState } from './useChatState'
import { ensureMessageKey } from './useChatState'
import { useToolMessages } from '@/chat/tools/useToolMessages'
import { createSseChunkHandler } from './sse/sseChunkHandler'
import { doSseRequest, doSseFormDataRequest } from './sse/sseRequests'
import { resetStreamingState } from './sse/resetStreamingState'
import { loggerSSE, loggerResume } from '@/shared/useLogger'

type ChatState = ReturnType<typeof useChatState>

/**
 * SSE 流式通信（编排层）。
 *
 * 职责：组装 chunk 处理器 + 请求发起 + 状态重置，对外暴露 5 个公开方法。
 * 核心逻辑已拆分到 sse/ 子模块：
 *   - sseChunkHandler.ts → handleSseChunk / handleSseError / parseToolArgs
 *   - sseRequests.ts     → doSseRequest（统一 SSE 请求）
 *   - resetStreamingState.ts → 状态重置
 */
export function useChatStream(
  state: ChatState,
  threadId: Ref<string | null>,
  options: {
    onReplayStart?: () => void
    onReplayEnd?: () => void
  } = {},
) {
  let abortController: AbortController | null = null
  const lastErrorMsg = { current: '' }

  // ── replay / fork 模式 ──
  const isReplayMode = ref(false)
  const { onReplayStart, onReplayEnd } = options

  const { setStreamingToolCalls, clearStreamingToolCalls } = useToolMessages()

  // ── 创建共享的 chunk 处理器 ──
  const { handleSseChunk, handleSseError, applyPendingLeaf } = createSseChunkHandler(
    state,
    isReplayMode,
    {
      setStreamingToolCalls,
      clearStreamingToolCalls,
      getAbortSignal: () => abortController?.signal,
      clearAbortController: () => { abortController = null },
      lastErrorMsgRef: lastErrorMsg,
      onReplayEnd,
    },
  )

  // ── 取消请求（停止生成）──
  function cancelRequest() {
    abortController?.abort()
    abortController = null

    // 将已接收的部分流式内容打包为 assistant 消息（模拟 done 事件逻辑）
    const toolCalls = state.pendingToolCalls.value.size > 0
      ? Array.from(state.pendingToolCalls.value.values())
      : undefined

    if (state.streamingContent.value || state.streamingReasoning.value || toolCalls) {
      state.messages.value = [
        ...state.messages.value,
        ensureMessageKey({
          role: 'assistant' as const,
          content: state.streamingContent.value || '',
          reasonContent: state.streamingReasoning.value || undefined,
          toolCalls,
          interrupt: state.showInterrupt.value || undefined,
        }),
      ]
      state.streamingContent.value = ''
      state.streamingReasoning.value = ''
      state.pendingToolCalls.value = new Map()
    }
    // 与 done 事件一致：补绑 LEAF 检查点到最新 assistant
    applyPendingLeaf()

    clearStreamingToolCalls()
    state.loading.value = false

    // replay/fork 模式清理
    isReplayMode.value = false
    onReplayEnd?.()
  }

  onUnmounted(() => {
    abortController?.abort()
    abortController = null
    clearStreamingToolCalls()
  })

  // ── 错误 toast 监听 ──
  watch(state.error, (val) => {
    if (val && val !== lastErrorMsg.current) {
      lastErrorMsg.current = val
      toast.error('发生错误', val)
    }
    if (!val) lastErrorMsg.current = ''
  })

  // ── 进入 replay/fork 的公共前置逻辑 ──
  function enterReplayMode(): boolean {
    if (!threadId.value) {
      loggerSSE.warn('No threadId, aborting replay/fork')
      return false
    }
    if (state.loading.value) {
      loggerSSE.warn('Another request is in flight')
      return false
    }
    isReplayMode.value = true
    onReplayStart?.()
    resetStreamingState(state)
    clearStreamingToolCalls()
    abortController = new AbortController()
    return true
  }

  /** 发送消息（流式 SSE）。
   *  有 PDF/DOCX 附件时走 with-files/stream（FormData），
   *  纯文本时走 /stream（JSON）。 */
  async function sendMessage(content: string, contentBlocks?: ApiContentBlock[], rawFiles?: File[], rubric?: string) {
    const trimmed = content.trim()
    const hasBlocks = contentBlocks && contentBlocks.length > 0
    const hasFiles = rawFiles && rawFiles.length > 0
    if ((!trimmed && !hasBlocks) || state.loading.value) return
    if (!threadId.value) return

    // 添加用户消息
    const userMsg: Message = ensureMessageKey({ role: 'user', content: trimmed })
    if (hasBlocks) userMsg.contentBlocks = contentBlocks
    state.messages.value = [...state.messages.value, userMsg]

    resetStreamingState(state)
    clearStreamingToolCalls()
    abortController = new AbortController()

    // 存在分支时，查找最后一条 assistant 消息绑定的叶子检查点，确保新消息沿当前分支继续
    const lastAssistant = [...state.messages.value].reverse().find(
      (m) => m.role === 'assistant' && m._leafCheckpointId,
    )
    const checkpointId = lastAssistant?._leafCheckpointId

    const onEvent = (event: { data: unknown }) => handleSseChunk(event.data as StreamChunk)

    // ── 有附件 → FormData SSE 端点 ──
    if (hasFiles) {
      const messagesJson = JSON.stringify({
        messages: [{ role: 'user', content: trimmed }],
        ...(checkpointId && { checkpoint_id: checkpointId }),
      })

      await doSseFormDataRequest({
        url: '/chat/{thread_id}/with-files/stream',
        path: { thread_id: threadId.value },
        messages: messagesJson,
        files: rawFiles!,
        signal: abortController.signal,
        onSseEvent: onEvent,
        onSseError: handleSseError,
      })
      return
    }

    // ── 纯文本 → JSON SSE 端点 ──
    await doSseRequest({
      url: '/chat/{thread_id}/stream',
      path: { thread_id: threadId.value },
      body: {
        messages: [{ role: 'user', content: trimmed }],
        ...(checkpointId && { checkpoint_id: checkpointId }),
        ...(rubric && { rubric }),
      },
      signal: abortController.signal,
      onSseEvent: onEvent,
      onSseError: handleSseError,
    })
  }

  /** 恢复中断的对话 */
  async function resumeChat(decisions: HITLDecision[]) {
    if (!threadId.value) {
      loggerResume.warn('No threadId, aborting')
      return
    }

    loggerResume.info('Sending decisions', decisions)

    // 只设 loading，保持 showInterrupt=true
    state.loading.value = true
    state.streamingContent.value = ''
    state.streamingReasoning.value = ''
    state.firstTokenReceived.value = false
    state.pendingToolCalls.value = new Map()
    state.error.value = null
    clearStreamingToolCalls()

    abortController = new AbortController()
    let firstDataReceived = false

    try {
      const result = await client.sse.post({
        url: '/chat/{thread_id}/resume',
        path: { thread_id: threadId.value },
        body: { decisions },
        signal: abortController.signal,
        onSseEvent: (event) => {
          if (!firstDataReceived && state.showInterrupt.value) {
            firstDataReceived = true
            state.showInterrupt.value = false
            state.interruptData.value = null
          }
          handleSseChunk(event.data as StreamChunk)
        },
        onSseError: handleSseError,
      })

      try {
        for await (const _data of result.stream) {
          /* onSseEvent 已处理 */
        }
      } catch {
        /* onSseError 已处理 */
      }

      // 安全兜底：流结束但未收到 done 事件
      if (state.loading.value) {
        state.loading.value = false
        abortController = null
      }
    } catch (err) {
      if (abortController?.signal.aborted) return
      loggerResume.error('Failed', err)
      state.error.value = String(err)
      state.showInterrupt.value = false
      state.interruptData.value = null
      state.loading.value = false
      abortController = null
      clearStreamingToolCalls()
    }
  }

  /** 从指定检查点重放执行（重试入口），可选注入用户消息触发模型重新生成 */
  async function replayCheckpoint(
    checkpointId: string,
    checkpointNs: string = '',
    messages?: Array<{ role: string; content: string }>,
  ): Promise<boolean> {
    if (!checkpointId) {
      loggerSSE.warn('replayCheckpoint: No checkpointId, aborting')
      return false
    }
    if (!enterReplayMode()) return false

    try {
      await doSseRequest({
        url: '/checkpoints/{thread_id}/replay',
        path: { thread_id: threadId.value! },
        body: {
          thread_id: threadId.value!,
          checkpoint_id: checkpointId,
          checkpoint_ns: checkpointNs || '',
          ...(messages && { messages }),
        },
        signal: abortController!.signal,
        onSseEvent: (event) => handleSseChunk(event.data as StreamChunk),
        onSseError: handleSseError,
      })
      state.loading.value = false
      abortController = null
      return true
    } catch (err) {
      if (abortController?.signal.aborted) return false
      loggerSSE.error('replayCheckpoint failed', err)
      state.error.value = String(err)
      state.loading.value = false
      abortController = null
      clearStreamingToolCalls()
      return false
    }
  }

  /** 从指定检查点分叉执行（分支入口） */
  async function forkFromCheckpoint(
    checkpointId: string,
    forkOpts: {
      checkpointNs?: string
      values?: Record<string, unknown>
      asNode?: string | null
    } = {},
  ): Promise<boolean> {
    if (!checkpointId) {
      loggerSSE.warn('forkFromCheckpoint: No checkpointId, aborting')
      return false
    }
    if (!enterReplayMode()) return false

    try {
      await doSseRequest({
        url: '/checkpoints/{thread_id}/fork',
        path: { thread_id: threadId.value! },
        body: {
          thread_id: threadId.value!,
          checkpoint_id: checkpointId,
          checkpoint_ns: forkOpts.checkpointNs ?? '',
          values: forkOpts.values ?? {},
          as_node: forkOpts.asNode ?? null,
        },
        signal: abortController!.signal,
        onSseEvent: (event) => handleSseChunk(event.data as StreamChunk),
        onSseError: handleSseError,
      })
      state.loading.value = false
      abortController = null
      return true
    } catch (err) {
      if (abortController?.signal.aborted) return false
      loggerSSE.error('forkFromCheckpoint failed', err)
      state.error.value = String(err)
      state.loading.value = false
      abortController = null
      clearStreamingToolCalls()
      return false
    }
  }

  return { sendMessage, cancelRequest, resumeChat, replayCheckpoint, forkFromCheckpoint }
}

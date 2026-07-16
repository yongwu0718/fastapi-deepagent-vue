import { type Ref } from 'vue'
import type { StreamChunk, ToolCall } from '@/api/chat'
import { toast } from '@/shared/useToast'
import { ensureMessageKey } from '@/chat/core/useChatState'
import type { useChatState } from '@/chat/core/useChatState'
import { loggerSSE } from '@/shared/useLogger'

type ChatState = ReturnType<typeof useChatState>

/** 工具调用参数安全解析 —— 将 SSE tool_call_args 字符串解析为 Record */
export function parseToolArgs(
  rawArgs: string | undefined,
  fallback: Record<string, unknown> = {},
): Record<string, unknown> {
  if (!rawArgs) return fallback
  try {
    const parsed: unknown = JSON.parse(rawArgs)
    if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>
    }
    return Array.isArray(parsed) ? { items: parsed } : { value: parsed }
  } catch {
    return { raw: rawArgs }
  }
}

export interface SseChunkHandlerOptions {
  setStreamingToolCalls: (calls: ToolCall[]) => void
  clearStreamingToolCalls: () => void
  /** 检查是否已被取消 */
  getAbortSignal: () => AbortSignal | undefined
  /** 清空 abortController 引用 */
  clearAbortController: () => void
  /** 上次错误消息（防止重复 toast） */
  lastErrorMsgRef: { current: string }
  /** replay/fork 模式结束回调 */
  onReplayEnd?: () => void
}

/**
 * 创建 SSE chunk 处理器（handleSseChunk + handleSseError）。
 *
 * 从 useChatStream 中提取，独立为可测试模块。
 * 处理 8 种 chunk 类型：checkpoint / reasoning / text / tool_call / tool_result /
 * interrupt / user / done / error。
 */
export function createSseChunkHandler(
  state: ChatState,
  isReplayMode: Ref<boolean>,
  opts: SseChunkHandlerOptions,
) {
  const {
    setStreamingToolCalls,
    clearStreamingToolCalls,
    getAbortSignal,
    clearAbortController,
    lastErrorMsgRef,
    onReplayEnd,
  } = opts

  /** 将当前 pendingToolCalls 同步到右侧栏 */
  function syncStreamingTools() {
    const map = state.pendingToolCalls.value
    if (map.size > 0) {
      setStreamingToolCalls(Array.from(map.values()))
    }
  }

  /**
   * 待绑定的 LEAF 检查点 ID。
   *
   * 问题：SSE 事件顺序中 LEAF checkpoint 可能在 done 之前到达，此时消息数组里
   * 还没有 done 创建的最终 assistant 消息，导致 LEAF 绑定到上一轮的 assistant。
   *
   * 修复：暂存 LEAF ID，在 done 创建新 assistant 后补绑；若 done 时已有 assistant
   * 携带了该 LEAF（正常顺序），则跳过。
   */
  let pendingLeafCheckpointId: string | null = null

  /** 将待定 LEAF 检查点绑定到最新的 assistant 消息 */
  function applyPendingLeaf() {
    if (!pendingLeafCheckpointId) return
    const msgs = state.messages.value
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'assistant') {
        if (msgs[i]._leafCheckpointId === pendingLeafCheckpointId) {
          // 已绑在同一轮最新 assistant 上（正常顺序），无需补绑
          loggerSSE.debug('checkpoint LEAF already on latest', { index: i, leafCid: pendingLeafCheckpointId.slice(-12) })
        } else {
          msgs[i] = {
            ...msgs[i],
            _leafCheckpointId: pendingLeafCheckpointId,
          }
          loggerSSE.debug('checkpoint LEAF DEFERRED BIND', { index: i, leafCid: pendingLeafCheckpointId.slice(-12) })
        }
        break
      }
    }
    pendingLeafCheckpointId = null
  }

  function handleSseChunk(chunk: StreamChunk) {
    if (!chunk) return

    if (chunk.type === 'checkpoint' && chunk.content) {
      try {
        const info = JSON.parse(chunk.content) as {
          checkpoint_id: string
          parent_checkpoint_id: string | null
          kind?: 'input' | 'leaf'
        }
        const msgs = state.messages.value
        loggerSSE.debug('checkpoint received', { cid: info.checkpoint_id?.slice(-12), pcid: info.parent_checkpoint_id?.slice(-12), kind: info.kind, isReplay: isReplayMode.value })

        // input 检查点：绑定到最近一条 user 消息
        //   _checkpointId       = input 检查点自身 ID（用于重试 replay）
        //   _parentCheckpointId = 父检查点 ID（用于分支 fork）
        // 父检查点是什么就绑什么，包括 null（根 input 也绑定，标识无前驱状态）
        if (info.kind === 'input') {
          for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i].role === 'user') {
              if (msgs[i]._checkpointId) {
                loggerSSE.debug('checkpoint SKIP bind', { index: i, existingCid: msgs[i]._checkpointId?.slice(-12), content: msgs[i].content?.slice(0, 30) })
              } else {
                msgs[i] = {
                  ...msgs[i],
                  _checkpointId: info.checkpoint_id,
                  _parentCheckpointId: info.parent_checkpoint_id,
                }
                loggerSSE.debug('checkpoint BIND', { index: i, inputCid: info.checkpoint_id?.slice(-12), parentCid: info.parent_checkpoint_id?.slice(-12) ?? 'null', content: msgs[i].content?.slice(0, 30) })
              }
              break
            }
          }
        }
        // leaf 检查点：暂存待绑定，等 done 事件确定最终 assistant 后再绑定
        if (info.kind === 'leaf') {
          // 先尝试立即绑定（正常顺序：done 先到 → LEAF 后到）
          let bound = false
          for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i].role === 'assistant') {
              if (!msgs[i]._leafCheckpointId) {
                msgs[i] = {
                  ...msgs[i],
                  _leafCheckpointId: info.checkpoint_id,
                }
                loggerSSE.debug('checkpoint LEAF BIND', { index: i, leafCid: info.checkpoint_id?.slice(-12) })
              }
              bound = true
              break
            }
          }
          // 暂存以备 done 后补绑（处理 LEAF 先于 done 到达的情况）
          if (!bound || state.loading.value) {
            pendingLeafCheckpointId = info.checkpoint_id
          }
        }
      } catch { /* 解析失败不影响聊天 */ }
      return
    }

    if (!state.firstTokenReceived.value) {
      state.firstTokenReceived.value = true
    }

    if (chunk.type === 'reasoning' && chunk.content) {
      state.streamingReasoning.value += chunk.content
    } else if (chunk.type === 'text' && chunk.content) {
      state.streamingContent.value += chunk.content
    } else if (chunk.type === 'tool_call' && chunk.tool_call_id) {
      const existing = state.pendingToolCalls.value.get(chunk.tool_call_id)
      state.pendingToolCalls.value = new Map(state.pendingToolCalls.value)
      state.pendingToolCalls.value.set(chunk.tool_call_id, {
        id: chunk.tool_call_id,
        name: chunk.tool_call_name || existing?.name || 'tool',
        args: parseToolArgs(chunk.tool_call_args, existing?.args),
      })
      syncStreamingTools()
    } else if (chunk.type === 'tool_result') {
      const tcId = chunk.tool_call_id || `tool_result_${Date.now()}`
      const existing = state.pendingToolCalls.value.get(tcId)
      state.pendingToolCalls.value = new Map(state.pendingToolCalls.value)
      state.pendingToolCalls.value.set(tcId, {
        ...(existing || { id: tcId, name: 'tool', args: {} }),
        result: chunk.content || '',
      })
      syncStreamingTools()
    } else if (chunk.type === 'interrupt') {
      state.loading.value = false
      state.showInterrupt.value = true
      try {
        state.interruptData.value = chunk.content ? JSON.parse(chunk.content) : null
      } catch {
        state.interruptData.value = chunk.content
      }
    } else if (chunk.type === 'user') {
      return
    } else if (chunk.type === 'rubric') {
      // Loop Engineering 评估事件 —— RubricMiddleware 通过 stream_writer 发送
      try {
        const evalData = JSON.parse(chunk.content || '{}') as {
          type: string
          iteration: number
          result?: string
          explanation?: string
        }
        if (evalData.type === 'rubric_evaluation_start') {
          toast.info('Loop 评估', `第 ${evalData.iteration + 1} 轮评估中`)
        } else if (evalData.type === 'rubric_evaluation_end') {
          const result = evalData.result || ''
          if (result === 'satisfied') {
            toast.success('Loop 评估通过', '完成条件已满足')
          } else if (result === 'needs_revision') {
            toast.info('Loop 评估未通过', evalData.explanation || '正在改进并重试')
          } else if (result === 'failed') {
            toast.warning('Loop 评估终止', '完成条件不可判定')
          } else if (result === 'max_iterations_reached') {
            toast.warning('Loop 评估终止', '达到最大迭代次数')
          } else if (result === 'grader_error') {
            toast.error('Loop 评估异常', evalData.explanation || '评估器出错')
          }
        }
      } catch { /* 解析失败不影响聊天 */ }
    } else if (chunk.type === 'done') {
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
      // 补绑 LEAF 检查点：LEAF 可能在 done 之前到达并绑到了上一轮 assistant，
      // 此时最新的 assistant 刚刚被创建，应重新绑定到当前最新 assistant。
      applyPendingLeaf()
      clearStreamingToolCalls()
      state.loading.value = false
      clearAbortController()
      isReplayMode.value = false
      onReplayEnd?.()
    } else if (chunk.type === 'error') {
      clearStreamingToolCalls()
      state.error.value = chunk.content ?? '未知错误'
      state.loading.value = false
      clearAbortController()
      isReplayMode.value = false
      onReplayEnd?.()
    }
  }

  function handleSseError(err: unknown) {
    if (getAbortSignal()?.aborted) return
    const msg = String(err)
    state.error.value = msg
    state.loading.value = false
    clearAbortController()
    clearStreamingToolCalls()
    if (msg && msg !== lastErrorMsgRef.current) {
      lastErrorMsgRef.current = msg
      toast.error('请求失败，请重试', msg)
    }
  }

  return { handleSseChunk, handleSseError, applyPendingLeaf }
}

import { ref, computed, watch, type Ref } from 'vue'
import { useChatState } from './useChatState'
import { useChatStream } from './useChatStream'
import { useCheckpoints, type SiblingBranch } from '@/chat/checkpoints/useCheckpoints'
import { loadThreadHistory, cacheThreadMessages } from '@/threads/useChatHistory'
import { useToolMessages } from '@/chat/tools/useToolMessages'
import type { ContentBlock } from '@/upload/useFileUpload'
import { toast } from '@/shared/useToast'
import { ensureMessageKey } from './useChatState'
import { getContentText, mergeConsecutiveReasoningMessages } from '@/api/chat'
import { loggerRetry, loggerFork, loggerCheckpoint } from '@/shared/useLogger'

export interface ChatControllerCallbacks {
  createThread: () => void
  chatStarted: (started: boolean) => void
  updateTitle: (threadId: string, title: string) => void
}

/**
 * ChatView 编排逻辑
 * —— 状态管理、流式通信、线程切换、历史加载、标题更新、滚动控制、错误处理
 */
export function useChatController(
  threadId: Ref<string | null>,
  callbacks: ChatControllerCallbacks,
) {
  const state = useChatState()
  const stream = useChatStream(state, threadId)
  const checkpoints = useCheckpoints(threadId)

  const {
    messages, loading, historyLoading, error,
    streamingContent, streamingReasoning, firstTokenReceived,
    showInterrupt, interruptData,
  } = state

  const { sendMessage: streamSend, cancelRequest, resumeChat, replayCheckpoint, forkFromCheckpoint } = stream

  // ── 分支叶子持久化键 ──
  const LS_BRANCH_LEAF_KEY = 'chat_branch_leaf_'
  function persistBranchLeaf(leafCid: string | null) {
    if (!leafCid || !threadId.value) return
    localStorage.setItem(LS_BRANCH_LEAF_KEY + threadId.value, leafCid)
  }
  function loadBranchLeaf(): string | null {
    if (!threadId.value) return null
    return localStorage.getItem(LS_BRANCH_LEAF_KEY + threadId.value)
  }

  // ── 同步工具调用到共享状态（供右侧栏使用） ──
  const { syncToolCalls } = useToolMessages()
  watch(messages, (msgs) => syncToolCalls(msgs), { deep: true, immediate: true })

  // ── 消息变化时持久化到 localStorage（刷新后可恢复） ──
  watch(
    () => [messages.value, threadId.value] as const,
    async ([msgs, tid]) => {
      if (tid && msgs.length > 0) {
        cacheThreadMessages(tid, msgs)
      }
      // 持久化当前分支叶子检查点
      if (msgs.length > 0) {
        const lastAssistant = [...msgs].reverse().find((m) => m.role === 'assistant' && m._leafCheckpointId)
        if (lastAssistant?._leafCheckpointId) {
          persistBranchLeaf(lastAssistant._leafCheckpointId)
        }
      }
      // SSE 流结束后自动加载 inputs 池，使 computeBranchMap 可用
      if (
        tid &&
        msgs.some((m) => m.role === 'user' && m._checkpointId) &&
        !checkpoints.loaded.value &&
        !checkpoints.loading.value
      ) {
        checkpoints.loadCheckpoints().catch(() => {})
      }
    },
    { deep: true },
  )

  // ── 线程切换 → 加载历史消息 ──
  // immediate: true 保证页面初始化时（localStorage 恢复的 threadId）立即触发加载
  watch(threadId, (newId) => {
    cancelRequest()
    streamingContent.value = ''
    streamingReasoning.value = ''
    error.value = null
    firstTokenReceived.value = false
    state.pendingToolCalls.value = new Map()
    showInterrupt.value = false
    interruptData.value = null
    messages.value = []
    checkpoints.reset()

    if (!newId) return

    historyLoading.value = true

    // 优先恢复缓存的叶子分支
    const cachedLeaf = loadBranchLeaf()
    // 加载完整历史：不传入 checkpoint_id，避免后端只返回叶子分支的片段
    loadThreadHistory(newId)
      .then(async (serverMsgs) => {
        if (serverMsgs.length > 0) {
          messages.value = mergeConsecutiveReasoningMessages(serverMsgs.map(ensureMessageKey))
        } else {
          messages.value = [ensureMessageKey({ role: 'assistant', content: '你好！我是 AI 助手，有什么可以帮你的？' })]
        }

        // 刷新恢复：给缺失 _checkpointId 的 user 消息绑定检查点
        const needsBinding = serverMsgs.some(
          (m) => m.role === 'user' && !m._checkpointId,
        )
        if (needsBinding) {
          loggerCheckpoint.info('刷新恢复，通过 /inputs 绑定检查点')
          try {
            await checkpoints.loadCheckpoints()
            let bound = 0
            const boundMsgs = await Promise.all(
              messages.value.map(async (msg) => {
                if (msg.role !== 'user' || msg._checkpointId) return msg
                const resolved = await checkpoints.resolveCheckpointForMessage(getContentText(msg.content))
                if (resolved) {
                  bound++
                  // 与 SSE 实时绑定保持一致：
                  // _checkpointId 绑定 input 检查点自身 ID（重试用）
                  // _parentCheckpointId 绑定父检查点 ID（分支用）
                  return {
                    ...msg,
                    _checkpointId: resolved.checkpointId,
                    _parentCheckpointId: resolved.parentCheckpointId,
                  }
                }
                return msg
              }),
            )
            messages.value = boundMsgs
            if (bound > 0) {
              loggerCheckpoint.info('绑定检查点', { bound })
              cacheThreadMessages(newId, messages.value)
            }
          } catch { /* /inputs 失败不影响聊天 */ }
        }

        // 刷新恢复：用持久化的分支叶子 ID 补全 assistant 消息的 _leafCheckpointId
        if (cachedLeaf) {
          const lastAssIdx = [...messages.value].reverse().findIndex((m) => m.role === 'assistant')
          if (lastAssIdx >= 0) {
            const realIdx = messages.value.length - 1 - lastAssIdx
            const lastAss = messages.value[realIdx]
            if (!lastAss._leafCheckpointId) {
              messages.value = [
                ...messages.value.slice(0, realIdx),
                { ...lastAss, _leafCheckpointId: cachedLeaf },
                ...messages.value.slice(realIdx + 1),
              ]
              cacheThreadMessages(newId, messages.value)
              loggerCheckpoint.info('刷新后恢复叶子检查点', { index: realIdx, leafCid: cachedLeaf.slice(-12) })
            }
          }
        }
      })
      .finally(() => {
        historyLoading.value = false
      })
  }, { immediate: true })

  // ── 聊天状态 ──
  const hasMessages = computed(() => messages.value.length > 1)
  const showWelcome = computed(() => !hasMessages.value && !loading.value)

  watch(hasMessages, (val) => {
    callbacks.chatStarted(val)
  })

  // ── 自动更新线程标题 ──
  let titleUpdated = false
  watch(
    () => threadId.value,
    () => { titleUpdated = false },
  )
  watch(
    () => [messages.value.length, threadId.value] as const,
    ([len, tid]) => {
      if (titleUpdated || !tid || len < 2) return
      const firstUserMsg = messages.value.find((m) => m.role === 'user')
      if (!firstUserMsg) return
      const title = getContentText(firstUserMsg.content).slice(0, 50)
      callbacks.updateTitle(tid, title)
      titleUpdated = true
    },
  )

  // ── 消息区滚动 ──
  const showScrollButton = ref(false)

  function handleScrollToBottom(messagesRef: { scrollToBottom: () => void } | null) {
    messagesRef?.scrollToBottom()
  }

  function onMessagesScroll(event: Event) {
    const target = event.target as HTMLElement
    if (!target) return
    const threshold = 120
    const distanceFromBottom =
      target.scrollHeight - target.scrollTop - target.clientHeight
    showScrollButton.value = distanceFromBottom > threshold
  }

  // ── 发送消息（自动创建线程） ──
  async function sendMessage(content: string, contentBlocks?: ContentBlock[], rawFiles?: File[], rubric?: string) {
    if (!threadId.value) {
      callbacks.createThread()
      await new Promise((r) => setTimeout(r, 50))
    }
    streamSend(content, contentBlocks, rawFiles, rubric)
  }

  // ── 本地错误状态（可关闭） ──
  const localError = ref<string | null>(null)
  watch(error, (val) => {
    localError.value = val
  })
  function clearError() {
    localError.value = null
  }

  // ── 重试：直接用消息上绑定的 _checkpointId 触发 replay ──
  const retryingMessageIndex = ref<number | null>(null)

  /**
   * 重试指定索引处的用户消息：
   * - 优先使用 _parentCheckpointId（消息处理前的状态），从父检查点重新执行
   * - 父检查点为 null 时回退到 _checkpointId（首条消息场景）
   * - 历史消息（页面刷新恢复）缺少检查点信息时给出提示
   */
  async function retryUserMessage(index: number) {
    if (!threadId.value) {
      toast.warning('当前没有可重试的对话')
      return
    }
    const target = messages.value[index]
    if (!target || target.role !== 'user') {
      toast.warning('只能重试用户消息')
      return
    }
    if (loading.value) {
      toast.info('当前正在处理中，请稍候')
      return
    }

    const checkpointId = target._parentCheckpointId || target._checkpointId
    if (!checkpointId) {
      toast.warning('该消息缺少检查点信息', '可能是历史会话，请重新发送消息')
      return
    }
    // 使用父检查点时需要注入用户消息以触发模型重新生成
    const msgContent = target.contentBlocks?.length
      ? getContentText(target.content)
      : getContentText(target.content).trim()
    const retryMessages = target._parentCheckpointId
      ? [{ role: 'user', content: msgContent }]
      : undefined

    retryingMessageIndex.value = index
    try {
      loggerRetry.info('replay from checkpoint', {
        cid: checkpointId.slice(-12),
        hasMessages: !!retryMessages,
      })
      const ok = await replayCheckpoint(checkpointId, '', retryMessages)
      loggerRetry.info('replay done', { ok, msgCid: target._checkpointId?.slice(-12) })
      if (!ok) {
        toast.error('重试失败', '请稍后再试')
      } else {
        toast.success('已触发重试')
      }
    } catch (err) {
      loggerRetry.error('retryUserMessage 异常', err)
      toast.error('重试失败', String(err))
    } finally {
      retryingMessageIndex.value = null
    }
  }

  // ── 分支：定位到对应用户消息的检查点并触发 fork ──
  const forkingMessageIndex = ref<number | null>(null)

  // ── 分支编辑态：用户点击「🌿 分支」进入编辑，提交时连同编辑内容一起 fork ──
  const forkEditingIndex = ref<number | null>(null)
  const forkEditingDraft = ref<string>('')

  /** 进入分支编辑态：把目标消息内容预填到草稿 */
  function startForkEdit(index: number) {
    const target = messages.value[index]
    if (!target || target.role !== 'user') {
      toast.warning('只能从用户消息处创建分支')
      return
    }
    if (loading.value || forkingMessageIndex.value !== null) {
      toast.info('当前正在处理中，请稍候')
      return
    }
    forkEditingIndex.value = index
    forkEditingDraft.value = getContentText(target.content)
  }

  /** 取消分支编辑 */
  function cancelForkEdit() {
    forkEditingIndex.value = null
    forkEditingDraft.value = ''
  }

  /**
   * 提交分支编辑：用编辑后的内容 + _checkpointId 直接调后端 fork
   */
  async function submitForkEdit(payload: { index: number; content: string }) {
    const { index, content } = payload
    if (!threadId.value) {
      toast.warning('当前没有可分支的对话')
      return
    }
    const target = messages.value[index]
    if (!target || target.role !== 'user') {
      toast.warning('只能从用户消息处创建分支')
      return
    }
    if (loading.value) {
      toast.info('当前正在处理中，请稍候')
      return
    }
    const trimmed = (content ?? '').trim()
    if (!trimmed) {
      toast.warning('消息内容不能为空')
      return
    }
    // 编辑后内容与原消息完全相同 —— 与重试无异
    if (trimmed === getContentText(target.content).trim()) {
      toast.info('内容未变化', '请修改消息内容后再创建分支')
      return
    }

    // 分支使用父检查点 ID（fork base），从父状态创建新分支
    const checkpointId = target._parentCheckpointId ?? target._checkpointId
    if (!checkpointId) {
      toast.warning('该消息缺少检查点信息', '可能是历史会话，请重新发送消息')
      return
    }

    forkingMessageIndex.value = index
    try {
      loggerFork.info('fork from parent checkpoint', { pcid: target._parentCheckpointId?.slice(-12), cid: target._checkpointId?.slice(-12), content: trimmed.slice(0, 30) })
      const values = {
        messages: [
          { type: 'human', role: 'human', content: trimmed },
        ],
      }

      const ok = await forkFromCheckpoint(checkpointId, {
        checkpointNs: '',
        values,
      })
      loggerFork.info('fork done', { ok, forkCid: checkpointId?.slice(-12) })
      if (!ok) {
        toast.error('分支失败', '请稍后再试')
      } else {
        toast.success('已创建分支', '原始执行链完整保留，新分支从该检查点继续')
        forkEditingIndex.value = null
        forkEditingDraft.value = ''
      }
    } catch (err) {
      loggerFork.error('submitForkEdit 异常', err)
      toast.error('分支失败', String(err))
    } finally {
      forkingMessageIndex.value = null
    }
  }

  // ── 分支切换 ──
  const branchSwitchingIndex = ref<number | null>(null)

  /**
   * 切换到指定分支：用目标叶子检查点 ID 加载该分支的完整历史。
   * 不重新生成 AI 回复，直接读已有消息。
   */
  async function switchToBranch(
    msgIndex: number,
    targetLeafCheckpointId: string,
  ) {
    if (!threadId.value) {
      toast.warning('当前没有可切换的对话')
      return
    }
    if (loading.value) {
      toast.info('当前正在处理中，请稍候')
      return
    }

    branchSwitchingIndex.value = msgIndex
    try {
      loggerFork.info('switch branch', { leafCid: targetLeafCheckpointId.slice(-12) })
      const branchMsgs = await loadThreadHistory(threadId.value, targetLeafCheckpointId)
      if (branchMsgs.length > 0) {
        messages.value = mergeConsecutiveReasoningMessages(branchMsgs.map(ensureMessageKey))
        // 加载后补全 _checkpointId / _parentCheckpointId
        try {
          await checkpoints.loadCheckpoints()
          let bound = 0
          const boundMsgs = await Promise.all(
            messages.value.map(async (msg) => {
              if (msg.role !== 'user' || msg._checkpointId) return msg
              const resolved = await checkpoints.resolveCheckpointForMessage(getContentText(msg.content))
              if (resolved) {
                bound++
                return {
                  ...msg,
                  _checkpointId: resolved.checkpointId,
                  _parentCheckpointId: resolved.parentCheckpointId,
                }
              }
              return msg
            }),
          )
          messages.value = boundMsgs
          if (bound > 0) {
            loggerCheckpoint.info('分支切换后绑定检查点', { bound })
            cacheThreadMessages(threadId.value, messages.value)
          }
        } catch { /* 绑定失败不影响功能 */ }
        // 将分支叶子检查点绑定到最后一条 assistant 消息，确保后续 sendMessage 沿当前分支继续
        const lastAssIdx = [...messages.value].reverse().findIndex((m) => m.role === 'assistant')
        if (lastAssIdx >= 0) {
          const realIdx = messages.value.length - 1 - lastAssIdx
          messages.value = [
            ...messages.value.slice(0, realIdx),
            { ...messages.value[realIdx], _leafCheckpointId: targetLeafCheckpointId },
            ...messages.value.slice(realIdx + 1),
          ]
          cacheThreadMessages(threadId.value, messages.value)
          loggerCheckpoint.info('分支切换后绑定叶子检查点到 assistant', { index: realIdx, leafCid: targetLeafCheckpointId.slice(-12) })
        }

        persistBranchLeaf(targetLeafCheckpointId)
        toast.success('已切换分支')
      } else {
        toast.warning('该分支无历史消息')
      }
    } catch (err) {
      loggerFork.error('switchToBranch 异常', err)
      toast.error('分支切换失败', String(err))
    } finally {
      branchSwitchingIndex.value = null
    }
  }

  /**
   * 分支信息：msgIndex → { branches, currentIndex }（响应式 computed）
   *
   * 去重逻辑：同一 parentCheckpointId 下的多条连续 user 消息（如"你好"→"我是小明"）
   * 只在最后一条（实际分叉点）上显示分支按钮，前面的是顺序执行，不参与分支导航。
   */
  const branchMap = computed(() => {
    const map = new Map<number, { branches: SiblingBranch[]; currentIndex: number }>()
    if (checkpoints.checkpoints.value.length === 0) return map
    // 按 parentCheckpointId 去重：只保留每个父检查点的最后一条消息（且需有 _checkpointId，排除 fork 分支消息）
    const lastByParent = new Map<string, number>()
    messages.value.forEach((msg, idx) => {
      if (msg.role !== 'user' || !msg._parentCheckpointId || !msg._checkpointId) return
      lastByParent.set(msg._parentCheckpointId, idx)
    })
    // 只对最后一条消息构建分支信息
    lastByParent.forEach((msgIdx, parentCid) => {
      const msg = messages.value[msgIdx]
      const siblings = checkpoints.getSiblingBranches(parentCid)
      if (siblings.length === 0) return
      const currentCid = msg._checkpointId
      const currentIdx = siblings.findIndex((b) => b.checkpointId === currentCid)
      map.set(msgIdx, {
        branches: siblings,
        currentIndex: currentIdx >= 0 ? currentIdx : 0,
      })
    })
    return map
  })

  return {
    // 状态
    messages,
    loading,
    historyLoading,
    error,
    localError,
    clearError,
    streamingContent,
    streamingReasoning,
    firstTokenReceived,
    showInterrupt,
    interruptData,
    // 重试
    retryingMessageIndex,
    retryUserMessage,
    // 分支
    forkingMessageIndex,
    // 分支编辑态
    forkEditingIndex,
    forkEditingDraft,
    startForkEdit,
    cancelForkEdit,
    submitForkEdit,
    // 分支切换
    branchSwitchingIndex,
    branchMap,
    switchToBranch,
    persistBranchLeaf,
    loadBranchLeaf,
    // 计算
    hasMessages,
    showWelcome,
    // 操作
    sendMessage,
    cancelRequest,
    resumeChat,
    // 滚动
    showScrollButton,
    handleScrollToBottom,
    onMessagesScroll,
  }
}

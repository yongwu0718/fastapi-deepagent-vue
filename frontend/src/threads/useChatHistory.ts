import { ref, readonly, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  getMessagesHistoryChatThreadIdGetMessagesHistoryGet,
  listThreadsEndpointThreadsGet,
  deleteMessagesHistoryChatThreadIdDeleteMessagesHistoryDelete,
} from '@/api/client/sdk.gen'
import type { ChatResponse } from '@/api/client/types.gen'
import type { Message } from '@/api/chat'
import { normalizeContent, mergeConsecutiveReasoningMessages } from '@/api/chat'

export interface ChatThread {
  /** 线程标识，同时作为后端 API 的 thread_id (UUID) */
  id: string
  title: string
  createdAt: string
  messageCount: number
}

/** GET /threads 返回的线程项 */
interface ServerThreadItem {
  thread_id: string
  message_count: number
}

// ── localStorage 键名 ──
const LS_ACTIVE_THREAD_KEY = 'chat_active_thread_id'
const LS_MSG_CACHE_PREFIX = 'chat_msgs_'

/** 持久化当前活跃线程 ID */
function persistActiveThreadId(tid: string | null) {
  if (tid) {
    localStorage.setItem(LS_ACTIVE_THREAD_KEY, tid)
  } else {
    localStorage.removeItem(LS_ACTIVE_THREAD_KEY)
  }
}

/** 缓存线程消息到 localStorage */
export function cacheThreadMessages(tid: string, msgs: Message[]) {
  try {
    localStorage.setItem(LS_MSG_CACHE_PREFIX + tid, JSON.stringify(msgs))
  } catch { /* 忽略存储空间不足 */ }
}

/** 从 localStorage 恢复缓存的线程消息 */
function loadCachedMessages(tid: string): Message[] | null {
  try {
    const raw = localStorage.getItem(LS_MSG_CACHE_PREFIX + tid)
    if (raw) return JSON.parse(raw)
  } catch { /* 忽略解析错误 */ }
  return null
}

/**
 * 加载指定线程的历史消息
 * —— 从后端获取最新内容，同时从 localStorage 合并 checkpoint_id 信息
 * —— 后端不可用时回退到 localStorage 缓存
 * —— checkpointId 可选：传入时加载特定分支的历史
 */
export async function loadThreadHistory(
  tid: string,
  checkpointId?: string | null,
): Promise<Message[]> {
  // 先读 localStorage 缓存（包含 SSE 绑定的 _checkpointId / _parentCheckpointId / _leafCheckpointId）
  const cached = loadCachedMessages(tid)

  try {
    const query: Record<string, unknown> = {}
    if (checkpointId) query.checkpoint_id = checkpointId
    const result = await getMessagesHistoryChatThreadIdGetMessagesHistoryGet({
      path: { thread_id: tid },
      query: Object.keys(query).length > 0 ? query : undefined,
    })
    if (result.data?.messages?.length) {
      const msgs: Message[] = result.data.messages.map((m, idx) => {
        const normalized = normalizeContent(m.content)
        return {
          role: m.role as Message['role'],
          content: normalized.text,
          contentBlocks: normalized.blocks.length > 0 ? normalized.blocks : undefined,
          reasonContent: m.reason_content ?? undefined,
          // 从缓存中恢复 checkpoint 信息（按位置 + 角色 + 文本内容匹配）
          ...pickCheckpointFromCache(cached, idx, m.role, normalized.text),
        }
      })
      cacheThreadMessages(tid, msgs)
      return mergeConsecutiveReasoningMessages(msgs)
    }
  } catch {
    // 后端请求失败 → 回退到 localStorage 缓存
    if (cached && cached.length > 0) return cached
  }
  return []
}

/** 从缓存消息中按位置/内容匹配恢复 checkpoint 字段 */
function pickCheckpointFromCache(
  cached: Message[] | null,
  idx: number,
  role: string,
  content: string,
): { _checkpointId?: string | null; _parentCheckpointId?: string | null; _leafCheckpointId?: string | null } {
  if (!cached) return {}
  const candidate = cached[idx]
  // 按位置优先匹配：user 消息恢复 _checkpointId/_parentCheckpointId，assistant 消息恢复 _leafCheckpointId
  const posMatch = pickFromCandidate(candidate, role, content)
  if (posMatch) return posMatch
  // 位置不匹配时遍历查找（分支切换/消息数量变化等场景）
  const found = cached.find((m) => {
    if (m.role !== role || m.content !== content) return false
    return !!(m._checkpointId || m._leafCheckpointId)
  })
  if (found) return pickFromCandidate(found, role, content) ?? {}
  return {}
}

function pickFromCandidate(
  candidate: Message | undefined,
  role: string,
  content: string,
): { _checkpointId?: string | null; _parentCheckpointId?: string | null; _leafCheckpointId?: string | null } | null {
  if (!candidate || candidate.role !== role || candidate.content !== content) return null
  const result: { _checkpointId?: string | null; _parentCheckpointId?: string | null; _leafCheckpointId?: string | null } = {}
  if (candidate._checkpointId) {
    result._checkpointId = candidate._checkpointId
    result._parentCheckpointId = candidate._parentCheckpointId
  }
  if (candidate._leafCheckpointId) {
    result._leafCheckpointId = candidate._leafCheckpointId
  }
  return Object.keys(result).length > 0 ? result : null
}

export function useChatHistory() {
  const router = useRouter()
  const route = useRoute()

  const threads = ref<ChatThread[]>([])

  // 从 URL 路由参数初始化活跃线程 ID
  const routeThreadId =
    typeof route.params.threadId === 'string' ? route.params.threadId : null
  const activeThreadId = ref<string | null>(routeThreadId)

  const threadsLoading = ref(false)

  // ── 路由变化 → 同步到 activeThreadId（浏览器前进/后退、直接 URL 访问） ──
  watch(
    () => route.params.threadId,
    (tid) => {
      const id = typeof tid === 'string' ? tid : null
      if (id !== activeThreadId.value) {
        activeThreadId.value = id
      }
    },
  )

  // ── activeThreadId 变化 → 持久化到 localStorage ──
  watch(activeThreadId, (id) => {
    persistActiveThreadId(id)
  })

  /** 从后端加载所有线程列表 */
  async function loadThreads() {
    threadsLoading.value = true
    try {
      const result = await listThreadsEndpointThreadsGet()
      if (result.data) {
        const data = result.data as { threads: ServerThreadItem[] }
        if (data?.threads?.length) {
          // 去重：只添加本地列表中不存在的线程
          const existingIds = new Set(threads.value.map((t) => t.id))
          const serverThreads: ChatThread[] = data.threads
            .filter((t) => !existingIds.has(t.thread_id))
            .map((t) => ({
              id: t.thread_id,
              // 用 UUID 前 6 位作为唯一标识，点击加载后标题会自动更新为第一条用户消息
              title: `对话 · ${t.thread_id.slice(0, 6)}`,
              createdAt: new Date().toISOString(),
              messageCount: t.message_count,
            }))
          threads.value = [...serverThreads, ...threads.value]
        }
      }
    } catch {
      // 加载失败不阻塞，侧边栏保持当前列表
    } finally {
      threadsLoading.value = false
    }
  }

  /** 创建新线程，id 即 thread_id，每次新建生成新的 UUID */
  function createThread(): string {
    const id = crypto.randomUUID()
    const thread: ChatThread = {
      id,
      title: '新对话',
      createdAt: new Date().toISOString(),
      messageCount: 0,
    }
    threads.value = [thread, ...threads.value]
    // 立即更新本地状态（sendMessage 需要同步获取新 ID）
    activeThreadId.value = id
    // 同步到 URL
    router.push(`/chat/${id}`)
    return id
  }

  /** 选中线程 → 更新本地状态 + URL */
  function selectThread(id: string) {
    if (id === activeThreadId.value) return
    activeThreadId.value = id
    router.push(`/chat/${id}`)
  }

  /** 删除线程（先调后端删除，再移除本地） */
  async function deleteThread(id: string) {
    try {
      await deleteMessagesHistoryChatThreadIdDeleteMessagesHistoryDelete({ path: { thread_id: id } })
    } catch {
      // 后端删除失败不阻塞前端移除
    }
    // 清理 localStorage 缓存
    localStorage.removeItem(LS_MSG_CACHE_PREFIX + id)
    threads.value = threads.value.filter((t) => t.id !== id)
    if (activeThreadId.value === id) {
      const nextId = threads.value[0]?.id ?? null
      activeThreadId.value = nextId
      if (nextId) {
        router.push(`/chat/${nextId}`)
      } else {
        router.push('/')
      }
    }
  }

  /** 更新线程标题 */
  function updateThreadTitle(id: string, title: string) {
    const thread = threads.value.find((t) => t.id === id)
    if (thread) thread.title = title
  }

  return {
    threads: readonly(threads),
    activeThreadId: readonly(activeThreadId),
    threadsLoading: readonly(threadsLoading),
    loadThreads,
    createThread,
    selectThread,
    deleteThread,
    updateThreadTitle,
  }
}

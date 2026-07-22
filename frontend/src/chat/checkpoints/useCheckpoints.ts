import { ref, type Ref } from 'vue'
import {
  getInputCheckpointsCheckpointsThreadIdInputsGet,
} from '@/api/client/sdk.gen'
import type { CheckpointSummary } from '@/api/client/types.gen'
import { loggerCheckpoint } from '@/shared/useLogger'

/** 兄弟分支项 —— 同一 parent 下的每个 input 检查点 */
export interface SiblingBranch {
  /** input 检查点自身 ID */
  checkpointId: string
  /** 叶子检查点 ID（用于加载完整分支历史） */
  leafCheckpointId: string | null
  /** 用户输入预览 */
  inputPreview: string | null
  /** 来源：input（原始） / fork（重试） */
  source: string
}

/**
 * 检查点池管理 —— 拉取与绑定。
 *
 * 绑定策略：优先通过 LangChain 消息 id（trigger_message_id ↔ _msgId）做权威 O(1) 绑定；
 * 消息无 id 时（旧数据）回退内容匹配兜底。
 */
export function useCheckpoints(threadId: Ref<string | null>) {
  const checkpoints = ref<CheckpointSummary[]>([])
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref<string | null>(null)

  async function loadCheckpoints(): Promise<CheckpointSummary[]> {
    const tid = threadId.value
    if (!tid) { checkpoints.value = []; loaded.value = true; return checkpoints.value }
    loading.value = true
    error.value = null
    try {
      const result = await getInputCheckpointsCheckpointsThreadIdInputsGet({
        path: { thread_id: tid },
        query: { limit: 200, offset: 0 },
      })
      checkpoints.value = result.data?.checkpoints ?? []
      loaded.value = true
      return checkpoints.value
    } catch (err) {
      loggerCheckpoint.error('加载检查点列表失败', err)
      error.value = String(err)
      loaded.value = true
      return []
    } finally {
      loading.value = false
    }
  }

  function extractCheckpointId(summary: CheckpointSummary): string | null {
    const config = summary.config
    if (!config || typeof config !== 'object') return null
    const c = (config as { configurable?: { checkpoint_id?: unknown } }).configurable
    if (c && typeof c === 'object' && typeof c.checkpoint_id === 'string' && c.checkpoint_id.length > 0) {
      return c.checkpoint_id
    }
    try {
      const m = JSON.stringify(config).match(/"checkpoint_id"\s*:\s*"([^"]+)"/)
      if (m?.[1]) return m[1]
    } catch { /* ignore */ }
    return null
  }

  function extractCheckpointNs(summary: CheckpointSummary): string {
    const config = summary.config
    if (!config || typeof config !== 'object') return ''
    const c = (config as { configurable?: { checkpoint_ns?: unknown } }).configurable
    if (c && typeof c === 'object' && typeof c.checkpoint_ns === 'string') return c.checkpoint_ns
    return ''
  }

  /**
   * 构建 trigger_message_id → 检查点信息的字典（O(1) 权威绑定）。
   * key = 触发此检查点的 LangChain 消息 id。
   * trigger_message_id 为 null/undefined 的检查点（如 resume 产生）自动跳过。
   */
  function buildIdMap(): Map<string, { checkpointId: string | null; parentCheckpointId: string | null }> {
    const map = new Map<string, { checkpointId: string | null; parentCheckpointId: string | null }>()
    for (const cp of checkpoints.value) {
      if (!cp.trigger_message_id) continue
      map.set(cp.trigger_message_id, {
        checkpointId: extractCheckpointId(cp),
        parentCheckpointId: cp.parent_checkpoint_id ?? null,
      })
    }
    return map
  }

  /** 内容匹配（仅用作旧消息无 _msgId 时的兜底）。 */
  function matchByContent(
    userMessage: string,
    pool: CheckpointSummary[] = checkpoints.value,
  ): CheckpointSummary | null {
    const text = (userMessage || '').trim()
    if (!text || pool.length === 0) return null
    const n = (s: string) => s.replace(/\s+/g, ' ').trim()
    const t = n(text)
    return pool.find((s) => s.input_preview && n(s.input_preview) === t)
      || pool.find((s) => s.input_preview && t.startsWith(n(s.input_preview)))
      || pool.find((s) => s.input_preview && n(s.input_preview).startsWith(t))
      || pool.find((s) => s.input_preview && t.includes(n(s.input_preview)))
      || null
  }

  /**
   * 绑定检查点到消息。
   * - 优先：通过 msgId 在 idMap 中 O(1) 查找（权威绑定）
   * - 兜底：通过用户消息文本内容匹配（旧消息）
   */
  function resolveCheckpoint(
    msgId: string | undefined,
    userMessage: string,
  ): { checkpointId: string | null; parentCheckpointId: string | null } | null {
    if (!loaded.value || checkpoints.value.length === 0) return null
    if (msgId) {
      const idMap = buildIdMap()
      if (idMap.has(msgId)) return { checkpointId: idMap.get(msgId)!.checkpointId, parentCheckpointId: idMap.get(msgId)!.parentCheckpointId }
    }
    const hit = matchByContent(userMessage)
    if (!hit) return null
    return { checkpointId: extractCheckpointId(hit), parentCheckpointId: hit.parent_checkpoint_id ?? null }
  }

  const lastMatched = ref<CheckpointSummary | null>(null)

  function getSiblingBranches(parentCheckpointId: string | null | undefined): SiblingBranch[] {
    if (!parentCheckpointId || checkpoints.value.length === 0) return []
    const siblings = checkpoints.value.filter(
      (cp) => cp.parent_checkpoint_id === parentCheckpointId && cp.source !== 'fork',
    )
    if (siblings.length <= 1) return []
    return siblings.map((cp) => ({
        checkpointId: extractCheckpointId(cp) ?? '',
        leafCheckpointId: cp.leaf_checkpoint_id ?? null,
        inputPreview: cp.input_preview ?? null,
        source: cp.source ?? '',
      })).sort((a, b) => {
        if (a.source === 'input' && b.source !== 'input') return -1
        if (a.source !== 'input' && b.source === 'input') return 1
        return 0
      })
  }

  function reset() {
    checkpoints.value = []
    loaded.value = false
    lastMatched.value = null
    error.value = null
  }

  return {
    checkpoints, loading, loaded, error, lastMatched,
    loadCheckpoints, extractCheckpointId, extractCheckpointNs,
    buildIdMap, resolveCheckpoint, getSiblingBranches, reset,
  }
}
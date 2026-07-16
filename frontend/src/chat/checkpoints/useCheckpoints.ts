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
 * 检查点池管理 —— 拉取与匹配
 *
 * 后端 LangGraph 在每次用户消息进入时都会生成一个 source=="input" 的检查点。
 * 前端通过 GET /checkpoints/{thread_id}/inputs 拉取池子，按 input_preview 与
 * 具体的用户消息做匹配，匹配到后从 config.configurable.checkpoint_id 中拿到
 * 准确的检查点 ID，再调用 POST /checkpoints/{thread_id}/replay 触发重试。
 *
 * 匹配策略（按优先级）：
 * 1) 完全相等（preview 是消息的截断形式）
 * 2) 消息内容以 preview 开头（preview 是消息前 80 字符）
 * 3) preview 以消息内容开头（消息是 preview 的截断，常见于用户编辑过的内容）
 * 4) 双向包含的兜底匹配
 */
export function useCheckpoints(threadId: Ref<string | null>) {
  const checkpoints = ref<CheckpointSummary[]>([])
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref<string | null>(null)

  /** 拉取当前线程的全部 input 检查点（覆盖式） */
  async function loadCheckpoints(): Promise<CheckpointSummary[]> {
    const tid = threadId.value
    if (!tid) {
      checkpoints.value = []
      loaded.value = true
      return checkpoints.value
    }
    loading.value = true
    error.value = null
    try {
      const result = await getInputCheckpointsCheckpointsThreadIdInputsGet({
        path: { thread_id: tid },
        query: { limit: 200, offset: 0 },
      })
      if (result.data?.checkpoints) {
        checkpoints.value = result.data.checkpoints
      } else {
        checkpoints.value = []
      }
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

  /**
   * 提取 checkpoint_id —— 后端 CheckpointSummary.config 是
   * `{ configurable: { thread_id, checkpoint_id, checkpoint_ns } }`。
   * 使用正则严格匹配 checkpoint_id 字段，避免误读其他字段。
   */
  function extractCheckpointId(summary: CheckpointSummary): string | null {
    const config = summary.config
    if (!config || typeof config !== 'object') return null
    // 直接定位：config.configurable.checkpoint_id
    const configurable = (config as { configurable?: { checkpoint_id?: unknown } })
      .configurable
    if (configurable && typeof configurable === 'object') {
      const raw = configurable.checkpoint_id
      if (typeof raw === 'string' && raw.length > 0) return raw
    }
    // 兜底：序列化后再用正则匹配，避免类型漂移
    try {
      const serialized = JSON.stringify(config)
      // 匹配 "checkpoint_id":"." 或 "checkpoint_id": "." 的字符串值
      const m = serialized.match(/"checkpoint_id"\s*:\s*"([^"]+)"/)
      if (m && m[1]) return m[1]
    } catch {
      /* ignore */
    }
    return null
  }

  /**
   * 抽取 checkpoint_ns（子图场景）
   */
  function extractCheckpointNs(summary: CheckpointSummary): string {
    const config = summary.config
    if (!config || typeof config !== 'object') return ''
    const configurable = (config as { configurable?: { checkpoint_ns?: unknown } })
      .configurable
    if (configurable && typeof configurable === 'object') {
      const raw = configurable.checkpoint_ns
      if (typeof raw === 'string') return raw
    }
    return ''
  }

  /**
   * 在已有池子中按用户消息内容匹配检查点
   * —— 返回首个满足任一匹配规则的 CheckpointSummary
   *
   * 匹配规则按优先级（用于从池子中定位"该 user 消息对应的检查点"）：
   *   1) 完全相等（preview == 原消息内容）
   *   2) 消息以 preview 开头（preview 是消息的截断，最常见）
   *   3) preview 以消息开头（消息是 preview 的截断）
   *   4) 双向包含的兜底
   *
   * 注意：必须用"原消息"匹配，而非编辑后的内容 —— 因为 input 检查点池里
   * 只会有原消息对应的 input_preview。
   */
  function matchCheckpointByContent(
    userMessage: string,
    pool: CheckpointSummary[] = checkpoints.value,
  ): CheckpointSummary | null {
    const text = (userMessage || '').trim()
    if (!text || pool.length === 0) return null

    // 0) 规范化：去掉多余空白（preview 是字符串，可能含换行/连续空格）
    const normalize = (s: string) => s.replace(/\s+/g, ' ').trim()
    const textN = normalize(text)

    // 1) 完全相等（normalize 后）
    let hit = pool.find((s) => s.input_preview && normalize(s.input_preview) === textN)
    if (hit) return hit
    // 2) preview 以前 80 字截断 → 消息以 preview 开头
    hit = pool.find((s) => s.input_preview && textN.startsWith(normalize(s.input_preview)))
    if (hit) return hit
    // 3) 消息被截断 → preview 以消息开头
    hit = pool.find((s) => s.input_preview && normalize(s.input_preview).startsWith(textN))
    if (hit) return hit
    // 4) 双向包含（normalize 后）
    hit = pool.find(
      (s) => s.input_preview && textN.includes(normalize(s.input_preview)),
    )
    if (hit) return hit
    return null
  }

  /**
   * 端到端：按线程 + 消息内容拉取并匹配，返回可用于 replay / fork 的检查点信息
   * - 未匹配到时返回 null
   * - 命中后将摘要信息暴露到最近匹配，便于 UI 高亮
   *
   * 关键：必须传"原始 user 消息内容"去匹配，而非编辑后的内容。
   * 池子里的 input_preview 是该消息首次进入时的内容，编辑后的内容不会出现在池中。
   *
   * 返回值与 SSE 实时绑定路径（sseChunkHandler.ts）保持一致：
   *   - checkpointId       = input 检查点自身 ID（重试 replay 从该 input 重新执行）
   *   - parentCheckpointId = 父检查点 ID（分支 fork 从父状态创建新分支）
   *   - 普通消息：parent 为上一轮叶子状态，replay/fork 从该状态继续
   *   - 根 input（首条消息）：parent 为 null，表示无前驱状态，不可 fork
   */
  const lastMatched = ref<CheckpointSummary | null>(null)

  /**
   * 按 parent_checkpoint_id 分组，返回同 parent 下的所有兄弟分支。
   * 用于分支切换 UI：同一 user 消息的多个不同后续路径（不同的 user input）。
   *
   * @param parentCheckpointId - 某条 user 消息的 _parentCheckpointId
   * @returns 兄弟分支列表，按 source 排序。null 或 <=1 时返回空数组。
   */
  function getSiblingBranches(parentCheckpointId: string | null | undefined): SiblingBranch[] {
    if (!parentCheckpointId || checkpoints.value.length === 0) return []
    const siblings = checkpoints.value.filter(
      (cp) => cp.parent_checkpoint_id === parentCheckpointId && cp.source !== 'fork',
    )
    if (siblings.length <= 1) return []
    return siblings
      .map((cp) => ({
        checkpointId: extractCheckpointId(cp) ?? '',
        leafCheckpointId: cp.leaf_checkpoint_id ?? null,
        inputPreview: cp.input_preview ?? null,
        source: cp.source ?? '',
      }))
      .sort((a, b) => {
        if (a.source === 'input' && b.source !== 'input') return -1
        if (a.source !== 'input' && b.source === 'input') return 1
        return 0
      })
  }

  async function resolveCheckpointForMessage(
    userMessage: string,
  ): Promise<{
    checkpointId: string | null       // input 检查点自身 ID（用于重试 replay）
    parentCheckpointId: string | null // 父检查点 ID（用于分支 fork）
    checkpointNs: string
  } | null> {
    // 池子为空时拉一次；已有则复用，调用方可在外部主动 invalidate
    if (!loaded.value || checkpoints.value.length === 0) {
      await loadCheckpoints()
    }
    const hit = matchCheckpointByContent(userMessage)
    lastMatched.value = hit
    if (!hit) return null
    return {
      checkpointId: extractCheckpointId(hit),
      parentCheckpointId: hit.parent_checkpoint_id ?? null,
      checkpointNs: extractCheckpointNs(hit),
    }
  }

  function reset() {
    checkpoints.value = []
    loaded.value = false
    lastMatched.value = null
    error.value = null
  }

  return {
    checkpoints,
    loading,
    loaded,
    error,
    lastMatched,
    loadCheckpoints,
    extractCheckpointId,
    extractCheckpointNs,
    matchCheckpointByContent,
    resolveCheckpointForMessage,
    getSiblingBranches,
    reset,
  }
}
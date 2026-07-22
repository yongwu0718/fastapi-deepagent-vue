type MessageRole = 'user' | 'assistant' | 'system' | 'tool'

/** 多模态内容块类型（图片/文件） */
export interface ContentBlock {
  type: 'image' | 'file'
  mimeType: string
  data: string // base64（不含前缀）
  metadata: {
    name?: string
    filename?: string
  }
}

/** 工具调用 */
export interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  result?: string
}

/** 聊天消息 */
export interface Message {
  role: MessageRole
  content: string
  reasonContent?: string
  /** 多模态内容块（图片/PDF） */
  contentBlocks?: ContentBlock[]
  /** 工具调用列表 */
  toolCalls?: ToolCall[]
  /** 是否中断 */
  interrupt?: boolean
  /**
   * 绑定的检查点 ID（用于重试 replay）。
   * 绑定的是 input 检查点自身的 ID：
   *   - 重试时从该 input 检查点重新执行
   *   - 根 input（首条消息）：为 null，表示无前驱状态，不可重试
   * SSE 实时绑定与 /inputs 兜底绑定均遵循此语义。
   */
  _checkpointId?: string | null
  /**
   * 父检查点 ID（用于分支 fork）。
   * 绑定的是 input 检查点的 parent_checkpoint_id（fork base）：
   *   - 分支时从父状态创建新分支
   *   - 根 input（首条消息）：为 null，表示无前驱状态，不可分支
   */
  _parentCheckpointId?: string | null
  /**
   * 叶子检查点 ID（用于分支切换导航）。
   * 来自 SSE kind='leaf' 的 checkpoint 事件，绑定到 assistant 消息。
   * 分支切换时用该 ID 调 get-messages-history 加载完整分支历史。
   */
  _leafCheckpointId?: string | null
  /** 前端内部 key，保证 v-for 稳定性 */
  _key?: string
  /**
   * LangChain 消息唯一 ID（来自后端 MessageResponse.id）。
   * 用于刷新恢复时权威绑定消息与检查点（替代内容匹配）。
   */
  _msgId?: string
}

/** 流式响应的 chunk 类型 */
export interface StreamChunk {
  type: 'text' | 'reasoning' | 'tool_call' | 'tool_result' | 'done' | 'error' | 'interrupt' | 'checkpoint' | 'user' | 'rubric'
  content?: string
  /** 工具调用相关 */
  tool_call_id?: string
  tool_call_name?: string
  tool_call_args?: string
  done: boolean
}

/** ── HITL 中断相关类型 ── */

/** 待审批的动作请求 */
export interface ActionRequest {
  name: string
  args: Record<string, unknown>
  description?: string
}

/** 审批规则配置 */
export interface ReviewConfig {
  action_name: string
  allowed_decisions: string[]
}

/** SSE 中断事件解析后的负载 */
export interface HITLRequest {
  action_requests: ActionRequest[]
  review_configs: ReviewConfig[]
}

/** 用户对单个动作的决策 */
export interface HITLDecision {
  type: 'approve' | 'reject' | 'edit'
  /** 拒绝原因（type=reject 时可选） */
  message?: string
  /** 编辑后的动作（type=edit 时） */
  edited_action?: {
    name: string
    args: Record<string, unknown>
  }
}

/** 用户决策集合，用于调用 /resume 端点 */
export interface HITLResponse {
  decisions: HITLDecision[]
}

// ─── 多模态 content 辅助函数 ───

/**
 * 从消息 content 中提取纯文本。
 * content 可能是 string（纯文本）或 Array<content_block>（多模态），
 * 本函数始终返回纯文本字符串。
 */
export function getContentText(content: string | Array<{ type?: string; text?: string; [key: string]: unknown }> | undefined | null): string {
  if (!content) return ''
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .filter((block) => block.type === 'text' && typeof block.text === 'string')
      .map((block) => block.text as string)
      .join('')
  }
  return ''
}

/**
 * 从消息 content 中提取多模态块（image / file 等非文本块）。
 */
export function getContentBlocks(content: string | Array<{ type?: string; [key: string]: unknown }> | undefined | null): ContentBlock[] {
  if (!content || typeof content === 'string') return []
  if (Array.isArray(content)) {
    return content
      .filter((block) => block.type === 'image' || block.type === 'file')
      .map((block) => ({
        type: (block.type as 'image' | 'file') ?? 'file',
        mimeType: (block.mime_type as string) ?? (block.mimeType as string) ?? 'application/octet-stream',
        data: (block.data as string) ?? '',
        metadata: {
          name: (block.name as string) ?? (block.filename as string),
          filename: (block.filename as string) ?? (block.name as string),
        },
      }))
  }
  return []
}

/**
 * 将 API 返回的 content（string | Array）标准化为 { text, blocks }。
 * 用于从 MessageResponse → Message 的桥接层。
 */
export function normalizeContent(content: string | Array<{ [key: string]: unknown }> | undefined | null): {
  text: string
  blocks: ContentBlock[]
} {
  return {
    text: getContentText(content),
    blocks: getContentBlocks(content),
  }
}

/**
 * 判断消息是否有多模态内容（文本为空但有图片/文件）。
 */
export function hasContentBlocksOnly(content: string | Array<{ [key: string]: unknown }> | undefined | null): boolean {
  return getContentText(content).length === 0 && getContentBlocks(content).length > 0
}

/**
 * 合并连续的纯推理 assistant 消息。
 *
 * 如果多条连续的 assistant 消息都只有 reasonContent 而没有实际文本内容（content 为空且无 contentBlocks），
 * 则将它们的推理内容合并为一条消息，避免历史列表中显示多条空消息。
 *
 * @param msgs - 原始消息数组
 * @param skipToolMessages - 是否在处理时将 tool 角色消息视为透明（不中断连续推理链），
 *   但 tool 消息仍保留在结果数组中。渲染层传 true，数据层传 false（默认）。
 */
export function mergeConsecutiveReasoningMessages(
  msgs: Message[],
  skipToolMessages = false,
): Message[] {
  if (!msgs || msgs.length === 0) return msgs

  const result: Message[] = []
  let pending: string[] = []

  for (let i = 0; i < msgs.length; i++) {
    const msg = msgs[i]
    const isReasoningOnly =
      msg.role === 'assistant' &&
      !msg.content &&
      !msg.contentBlocks?.length &&
      !!msg.reasonContent
    const isTool = msg.role === 'tool'

    if (isReasoningOnly) {
      pending.push(msg.reasonContent!)
    } else if (skipToolMessages && isTool) {
      // 渲染层：tool 消息不打断推理链，但仍保留在结果中（索引不变，由模板 v-if 隐藏）
      result.push(msg)
    } else {
      // 刷新缓存的推理消息
      if (pending.length > 0) {
        result.push({
          role: 'assistant',
          content: '',
          reasonContent: pending.join('\n\n---\n\n'),
        })
        pending = []
      }
      result.push(msg)
    }
  }

  // 末尾的纯推理消息
  if (pending.length > 0) {
    result.push({
      role: 'assistant',
      content: '',
      reasonContent: pending.join('\n\n---\n\n'),
    })
  }

  return result
}

import { client } from '@/api/client/client.gen'
import { formDataBodySerializer } from '@/api/client/core/bodySerializer.gen'

/**
 * 统一 SSE 请求发起逻辑（JSON 请求体）。
 *
 * 消除原 doStreamRequest / doReplayRequest / doForkRequest 三处结构相同的重复代码。
 */
export async function doSseRequest<TBody = unknown>(options: {
  url: string
  path: Record<string, string>
  body: TBody
  signal: AbortSignal
  onSseEvent: (event: { data: unknown }) => void
  onSseError: (err: unknown) => void
}): Promise<void> {
  const { url, path, body, signal, onSseEvent, onSseError } = options

  const result = await client.sse.post({
    url: url as '/chat/{thread_id}/stream',
    path,
    body: body as Record<string, unknown>,
    signal,
    onSseEvent,
    onSseError,
  })

  // 消费 AsyncGenerator（事件已在 onSseEvent 中处理）
  ;(async () => {
    try {
      for await (const _data of result.stream) {
        /* onSseEvent 已处理 */
      }
    } catch {
      /* onSseError 已处理 */
    }
  })()
}

/**
 * FormData SSE 请求（用于带附件的 with-files/stream 端点）。
 *
 * body 构造为 { messages: string, files: File[] }，
 * 由 formDataBodySerializer 序列化为 multipart/form-data。
 */
export async function doSseFormDataRequest(options: {
  url: string
  path: Record<string, string>
  messages: string
  files: File[]
  signal: AbortSignal
  onSseEvent: (event: { data: unknown }) => void
  onSseError: (err: unknown) => void
}): Promise<void> {
  const { url, path, messages, files, signal, onSseEvent, onSseError } = options

  const result = await client.sse.post({
    ...formDataBodySerializer,
    url: url as '/chat/{thread_id}/with-files/stream',
    path,
    body: { messages, files },
    signal,
    onSseEvent,
    onSseError,
    headers: { 'Content-Type': null },
  })

  // 消费 AsyncGenerator
  ;(async () => {
    try {
      for await (const _data of result.stream) {
        /* onSseEvent 已处理 */
      }
    } catch {
      /* onSseError 已处理 */
    }
  })()
}

import { ref, readonly, onUnmounted } from 'vue'
import { toast } from '@/shared/useToast'

/** 支持的文件类型 */
export const SUPPORTED_FILE_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

export interface ContentBlock {
  type: 'image' | 'file'
  mimeType: string
  data: string // base64（不含 data:.;base64, 前缀）
  metadata: {
    name?: string
    filename?: string
  }
}

/** 将 File 转为 base64（不含前缀） */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      const result = reader.result as string
      resolve(result.split(',')[1]) // 去掉 data:.;base64, 前缀
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

/** 将 File 转为 ContentBlock */
async function fileToContentBlock(file: File): Promise<ContentBlock> {
  const supportedImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

  if (!SUPPORTED_FILE_TYPES.includes(file.type)) {
    const msg = `不支持的文件类型: ${file.type}。支持的类型: ${SUPPORTED_FILE_TYPES.join(', ')}`
    toast.error(msg)
    throw new Error(msg)
  }

  const data = await fileToBase64(file)

  if (supportedImageTypes.includes(file.type)) {
    return {
      type: 'image',
      mimeType: file.type,
      data,
      metadata: { name: file.name },
    }
  }

  // PDF
  return {
    type: 'file',
    mimeType: 'application/pdf',
    data,
    metadata: { filename: file.name },
  }
}

/** 检查文件是否重复 */
function isDuplicate(file: File, blocks: ContentBlock[]): boolean {
  return blocks.some((block) => {
    if (block.type === 'file' && file.type === 'application/pdf') {
      return block.metadata.filename === file.name
    }
    if (block.type === 'image' && file.type.startsWith('image/')) {
      return block.metadata.name === file.name
    }
    return false
  })
}

export function useFileUpload() {
  const contentBlocks = ref<ContentBlock[]>([])
  /** 原始 File 对象（与 contentBlocks 索引一一对应），供 FormData 附件端点使用 */
  const rawFiles = ref<File[]>([])
  const dragOver = ref(false)
  const dragCounter = ref(0)

  /** 文件输入 onChange 处理 */
  async function handleFileUpload(e: Event) {
    const input = e.target as HTMLInputElement
    const files = input.files
    if (!files?.length) return

    const newBlocks = [...contentBlocks.value]
    const newRawFiles = [...rawFiles.value]
    for (const file of Array.from(files)) {
      if (!SUPPORTED_FILE_TYPES.includes(file.type)) {
        toast.error(`不支持的文件类型: ${file.type}`)
        continue
      }
      if (isDuplicate(file, newBlocks)) {
        toast.warning('文件已存在', file.name)
        continue
      }
      try {
        const block = await fileToContentBlock(file)
        newBlocks.push(block)
        newRawFiles.push(file)
      } catch {
        // 已在 fileToContentBlock 中 toast
      }
    }
    contentBlocks.value = newBlocks
    rawFiles.value = newRawFiles
    // 重置 input 以允许重复选择同一个文件
    input.value = ''
  }

  /** 粘贴事件处理 */
  async function handlePaste(e: ClipboardEvent) {
    const items = e.clipboardData?.items
    if (!items) return

    for (const item of Array.from(items)) {
      if (item.kind !== 'file') continue
      const file = item.getAsFile()
      if (!file) continue
      if (!SUPPORTED_FILE_TYPES.includes(file.type)) continue
      if (isDuplicate(file, contentBlocks.value)) {
        toast.warning('文件已存在', file.name)
        continue
      }
      e.preventDefault()
      try {
        const block = await fileToContentBlock(file)
        contentBlocks.value = [...contentBlocks.value, block]
        rawFiles.value = [...rawFiles.value, file]
      } catch {
        // handled
      }
    }
  }

  /** 删除某个内容块 */
  function removeBlock(idx: number) {
    contentBlocks.value = contentBlocks.value.filter((_, i) => i !== idx)
    rawFiles.value = rawFiles.value.filter((_, i) => i !== idx)
  }

  /** 清空所有内容块 */
  function resetBlocks() {
    contentBlocks.value = []
    rawFiles.value = []
  }

  // ── 全局拖拽 ──
  function onDragEnter(e: DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    dragCounter.value++
    // 检查是否包含文件
    if (e.dataTransfer?.types.includes('Files')) {
      dragOver.value = true
    }
  }

  function onDragLeave(e: DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    dragCounter.value--
    if (dragCounter.value === 0) {
      dragOver.value = false
    }
  }

  async function onDrop(e: DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    dragOver.value = false
    dragCounter.value = 0

    const files = e.dataTransfer?.files
    if (!files?.length) return

    const newBlocks = [...contentBlocks.value]
    const newRawFiles = [...rawFiles.value]
    for (const file of Array.from(files)) {
      if (!SUPPORTED_FILE_TYPES.includes(file.type)) {
        toast.error(`不支持的文件类型: ${file.type}`)
        continue
      }
      if (isDuplicate(file, newBlocks)) {
        toast.warning('文件已存在', file.name)
        continue
      }
      try {
        const block = await fileToContentBlock(file)
        newBlocks.push(block)
        newRawFiles.push(file)
      } catch {
        // handled
      }
    }
    contentBlocks.value = newBlocks
    rawFiles.value = newRawFiles
  }

  /** 阻止默认拖拽行为（具名函数，确保 add/remove 引用一致） */
  function onDragOver(e: DragEvent) {
    e.preventDefault()
  }

  /** 全局拖拽事件是否已挂载（防止重复注册） */
  let eventsAttached = false

  // 挂载全局拖拽事件（仅首次调用时注册）
  if (typeof window !== 'undefined' && !eventsAttached) {
    eventsAttached = true
    window.addEventListener('dragenter', onDragEnter)
    window.addEventListener('dragleave', onDragLeave)
    window.addEventListener('dragover', onDragOver)
    window.addEventListener('drop', onDrop)
  }

  // 清理：仅在组件卸载且没有其他实例时移除
  onUnmounted(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('dragenter', onDragEnter)
      window.removeEventListener('dragleave', onDragLeave)
      window.removeEventListener('dragover', onDragOver)
      window.removeEventListener('drop', onDrop)
      eventsAttached = false
    }
  })

  return {
    contentBlocks: readonly(contentBlocks),
    rawFiles: readonly(rawFiles),
    dragOver: readonly(dragOver),
    handleFileUpload,
    handlePaste,
    removeBlock,
    resetBlocks,
  }
}

import { ref } from 'vue'
import { toast } from '@/shared/useToast'

export interface UploadItem {
  file: File
  name: string
  size: number
}

export function useRagUpload() {
  const uploadItems = ref<UploadItem[]>([])
  const dragOverDrop = ref(false)
  let dragCounterDrop = 0

  function addFiles(files: File[]) {
    for (const f of files) {
      if (!f.name.endsWith('.md')) {
        toast.warning(`跳过非 Markdown 文件: ${f.name}`)
        continue
      }
      if (uploadItems.value.some((u) => u.name === f.name)) {
        toast.warning(`文件已存在: ${f.name}`)
        continue
      }
      uploadItems.value.push({ file: f, name: f.name, size: f.size })
    }
  }

  function handleFileInput(e: Event) {
    const input = e.target as HTMLInputElement
    const files = input.files
    if (!files?.length) return
    addFiles(Array.from(files))
    input.value = ''
  }

  function removeUploadItem(idx: number) {
    uploadItems.value.splice(idx, 1)
  }

  function onDropZoneEnter(e: DragEvent) {
    e.preventDefault()
    dragCounterDrop++
    if (e.dataTransfer?.types.includes('Files')) dragOverDrop.value = true
  }

  function onDropZoneLeave(e: DragEvent) {
    e.preventDefault()
    dragCounterDrop--
    if (dragCounterDrop <= 0) { dragOverDrop.value = false; dragCounterDrop = 0 }
  }

  function onDropZoneOver(e: DragEvent) { e.preventDefault() }

  function onDropZone(e: DragEvent) {
    e.preventDefault()
    dragOverDrop.value = false
    dragCounterDrop = 0
    const files = e.dataTransfer?.files
    if (files?.length) addFiles(Array.from(files))
  }

  function clearUploadItems() {
    uploadItems.value = []
  }

  return {
    uploadItems,
    dragOverDrop,
    handleFileInput,
    removeUploadItem,
    onDropZoneEnter,
    onDropZoneLeave,
    onDropZoneOver,
    onDropZone,
    clearUploadItems,
  }
}

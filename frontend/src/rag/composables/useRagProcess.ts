import { ref, computed, reactive, type Ref } from 'vue'
import type { useRagManager } from './useRagManager'
import type { UploadItem } from './useRagUpload'

export function useRagProcess(rag: ReturnType<typeof useRagManager>, uploadItems: Ref<UploadItem[]>) {
  const processFilesInput = ref('')
  const previewDir = ref('')
  const parsedFiles = computed(() =>
    processFilesInput.value
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean)
  )
  const isPreviewMode = ref(false)

  const expandedChunks = reactive<Set<string>>(new Set())

  function toggleChunks(filename: string) {
    if (expandedChunks.has(filename)) {
      expandedChunks.delete(filename)
    } else {
      expandedChunks.add(filename)
    }
  }

  function handleProcess() {
    isPreviewMode.value = true
    if (uploadItems.value.length) {
      rag.processUploadedFiles(
        uploadItems.value.map((u) => u.file),
        previewDir.value || null,
        true,
      )
      return
    }
    rag.processFiles(parsedFiles.value, previewDir.value || null, true)
  }

  function handleConfirmSave() {
    isPreviewMode.value = false
    rag.confirmSave(
      parsedFiles.value,
      uploadItems.value.map((u) => u.file),
      previewDir.value || null,
    )
  }

  function clearProcessForm() {
    processFilesInput.value = ''
    previewDir.value = ''
    rag.processResult.value = null
    uploadItems.value = []
    expandedChunks.clear()
    isPreviewMode.value = false
  }

  return {
    processFilesInput,
    previewDir,
    parsedFiles,
    isPreviewMode,
    expandedChunks,
    toggleChunks,
    handleProcess,
    handleConfirmSave,
    clearProcessForm,
  }
}

import { ref, computed } from 'vue'
import type { useRagManager } from './useRagManager'

export function useRagBrowse(rag: ReturnType<typeof useRagManager>) {
  const deleteDocsInput = ref('')
  const docsToDelete = computed(() =>
    deleteDocsInput.value
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean)
  )
  const showClearConfirm = ref(false)
  const showDeleteColConfirm = ref(false)

  function handleBrowseCollectionChange(name: string) {
    rag.selectCollection(name)
  }

  function handleBrowsePageChange(page: number) {
    if (rag.selectedCollection.value) {
      rag.fetchDocuments(rag.selectedCollection.value, page, rag.browsePageSize.value)
    }
  }

  function handleDeleteDocs() {
    if (!rag.selectedCollection.value || !docsToDelete.value.length) return
    rag.deleteDocsFromCollection(rag.selectedCollection.value, docsToDelete.value)
    deleteDocsInput.value = ''
    showClearConfirm.value = false
    showDeleteColConfirm.value = false
  }

  function handleDeleteSingleDoc(docId: string) {
    if (!rag.selectedCollection.value) return
    rag.deleteDocsFromCollection(rag.selectedCollection.value, [docId])
  }

  function handleClearCollection() {
    if (!rag.selectedCollection.value) return
    showClearConfirm.value = true
  }

  function confirmClearCollection() {
    if (!rag.selectedCollection.value) return
    rag.clearCollectionAction(rag.selectedCollection.value)
    showClearConfirm.value = false
  }

  function handleDeleteCollection() {
    if (!rag.selectedCollection.value) return
    showDeleteColConfirm.value = true
  }

  function confirmDeleteCollection() {
    if (!rag.selectedCollection.value) return
    rag.deleteCollectionAction(rag.selectedCollection.value)
    showDeleteColConfirm.value = false
  }

  return {
    deleteDocsInput,
    docsToDelete,
    showClearConfirm,
    showDeleteColConfirm,
    handleBrowseCollectionChange,
    handleBrowsePageChange,
    handleDeleteDocs,
    handleDeleteSingleDoc,
    handleClearCollection,
    confirmClearCollection,
    handleDeleteCollection,
    confirmDeleteCollection,
  }
}

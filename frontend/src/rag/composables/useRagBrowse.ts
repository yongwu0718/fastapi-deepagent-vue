import { ref } from 'vue'
import type { useRagManager } from './useRagManager'

export function useRagBrowse(rag: ReturnType<typeof useRagManager>) {
  const deleteConfirmDocId = ref<string | null>(null)
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

  function handleDeleteSingleDoc(docId: string) {
    if (!rag.selectedCollection.value) return
    deleteConfirmDocId.value = docId
  }

  function confirmDeleteSingleDoc() {
    if (!rag.selectedCollection.value || !deleteConfirmDocId.value) return
    rag.deleteDocsFromCollection(rag.selectedCollection.value, [deleteConfirmDocId.value])
    deleteConfirmDocId.value = null
  }

  function cancelDeleteSingleDoc() {
    deleteConfirmDocId.value = null
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
    deleteConfirmDocId,
    showClearConfirm,
    showDeleteColConfirm,
    handleBrowseCollectionChange,
    handleBrowsePageChange,
    handleDeleteSingleDoc,
    confirmDeleteSingleDoc,
    cancelDeleteSingleDoc,
    handleClearCollection,
    confirmClearCollection,
    handleDeleteCollection,
    confirmDeleteCollection,
  }
}

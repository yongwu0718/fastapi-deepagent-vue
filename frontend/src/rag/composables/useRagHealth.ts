import { ref, onMounted, onUnmounted } from 'vue'
import type { useRagManager } from './useRagManager'

export function useRagHealth(rag: ReturnType<typeof useRagManager>) {
  const autoRefresh = ref(true)
  let refreshTimer: ReturnType<typeof setInterval> | null = null

  function startAutoRefresh() {
    stopAutoRefresh()
    if (autoRefresh.value) {
      refreshTimer = setInterval(() => rag.fetchHealth(), 10_000)
    }
  }

  function stopAutoRefresh() {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  function toggleAutoRefresh() {
    autoRefresh.value = !autoRefresh.value
    if (autoRefresh.value) {
      startAutoRefresh()
    } else {
      stopAutoRefresh()
    }
  }

  onMounted(() => {
    rag.fetchHealth()
    startAutoRefresh()
  })

  onUnmounted(() => {
    stopAutoRefresh()
  })

  return { autoRefresh, startAutoRefresh, stopAutoRefresh, toggleAutoRefresh }
}

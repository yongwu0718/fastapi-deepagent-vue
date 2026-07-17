import { ref } from 'vue'
import type { useRagManager } from './useRagManager'

export type TabKey = 'process' | 'config' | 'browse'

export function useRagTabs(rag: ReturnType<typeof useRagManager>) {
  const activeTab = ref<TabKey>('process')

  async function switchTab(key: TabKey) {
    activeTab.value = key
    if (key === 'config' && !rag.configLoaded.value && !rag.configLoading.value) {
      // 触发配置加载（由 useRagConfig 注入 handleLoadConfig 后执行）
      onSwitchToConfig?.()
    }
    if (key === 'browse' && !rag.collections.value && !rag.collectionsLoading.value) {
      rag.fetchCollections()
    }
  }

  // 可注入的回调，由 useRagConfig 注册
  let onSwitchToConfig: (() => void) | null = null
  function registerConfigLoader(fn: () => void) {
    onSwitchToConfig = fn
  }

  return { activeTab, switchTab, registerConfigLoader }
}

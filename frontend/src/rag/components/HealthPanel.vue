<script setup lang="ts">
import type { useRagManager } from '../composables/useRagManager'

defineProps<{
  rag: ReturnType<typeof useRagManager>
  autoRefresh: boolean
}>()

defineEmits<{
  (e: 'toggleAutoRefresh'): void
  (e: 'refresh'): void
}>()
</script>

<template>
  <aside class="health-panel">
    <div class="panel-header">
      <h2>健康状态</h2>
      <div class="health-actions">
        <label class="auto-refresh-label" title="每10秒自动刷新">
          <input
            type="checkbox"
            :checked="autoRefresh"
            @change="$emit('toggleAutoRefresh')"
          />
          自动刷新
        </label>
        <button
          class="refresh-btn"
          :disabled="rag.healthLoading.value"
          @click="$emit('refresh')"
        >
          {{ rag.healthLoading.value ? '刷新中...' : '🔄 刷新' }}
        </button>
      </div>
    </div>

    <div v-if="rag.healthLoading.value && !rag.health.value" class="health-skeleton">
      <div v-for="i in 5" :key="i" class="skeleton-row">
        <div class="skeleton-label" />
        <div class="skeleton-value" />
      </div>
    </div>

    <div v-else-if="rag.healthError.value" class="health-error">
      <p>{{ rag.healthError.value }}</p>
    </div>

    <div v-else-if="rag.health.value" class="health-items">
      <div class="health-item">
        <span class="item-label">集合名称</span>
        <span class="item-value">{{ rag.health.value.collection_name }}</span>
      </div>
      <div class="health-item">
        <span class="item-label">文档块数</span>
        <span class="item-value highlight">{{ rag.health.value.collection_count.toLocaleString() }}</span>
      </div>
      <div class="health-item">
        <span class="item-label">嵌入模型</span>
        <span class="item-value">{{ rag.health.value.embedding_model }}</span>
      </div>
      <div class="health-item">
        <span class="item-label">嵌入服务</span>
        <span class="item-value mono">{{ rag.health.value.embedding_base_url }}</span>
      </div>
      <div class="health-item">
        <span class="item-label">持久化目录</span>
        <span class="item-value mono">{{ rag.health.value.persist_directory }}</span>
      </div>
    </div>

    <div v-else class="health-empty">暂无健康数据</div>
  </aside>
</template>

<style scoped>
.health-panel {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 20px;
  background: #fff;
  border-right: 1px solid #e2e8f0;
  overflow-y: auto;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}
.panel-header h2 { font-size: 15px; font-weight: 600; margin: 0; }
.health-actions { display: flex; align-items: center; gap: 8px; }
.auto-refresh-label {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: #64748b; cursor: pointer; user-select: none;
}
.refresh-btn {
  padding: 3px 10px; border: 1px solid #cbd5e1; border-radius: 5px;
  background: #fff; font-size: 12px; color: #475569; cursor: pointer; white-space: nowrap;
}
.refresh-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.refresh-btn:hover:not(:disabled) { background: #f1f5f9; }
.health-skeleton { display: flex; flex-direction: column; gap: 10px; }
.skeleton-row { display: flex; justify-content: space-between; align-items: center; }
.skeleton-label { width: 60px; height: 14px; background: #e2e8f0; border-radius: 3px; animation: pulse 1.5s infinite; }
.skeleton-value { width: 120px; height: 14px; background: #e2e8f0; border-radius: 3px; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.health-error {
  padding: 12px; background: #fef2f2; border: 1px solid #fecaca;
  border-radius: 6px; color: #dc2626; font-size: 13px;
}
.health-items { display: flex; flex-direction: column; gap: 2px; }
.health-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 9px 0; border-bottom: 1px solid #f1f5f9;
}
.item-label { font-size: 13px; color: #64748b; flex-shrink: 0; }
.item-value { font-size: 13px; color: #1e293b; text-align: right; word-break: break-all; }
.item-value.highlight { font-weight: 700; color: #2563eb; font-size: 16px; }
.item-value.mono { font-family: 'JetBrains Mono','Fira Code','Consolas',monospace; font-size: 11px; }
.health-empty { padding: 20px 0; text-align: center; color: #94a3b8; font-size: 13px; }
</style>

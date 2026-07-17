<script setup lang="ts">
import type { useRagManager } from '../composables/useRagManager'

defineProps<{
  rag: ReturnType<typeof useRagManager>
  deleteDocsInput: string
  docsToDelete: string[]
  showClearConfirm: boolean
  showDeleteColConfirm: boolean
}>()

defineEmits<{
  (e: 'update:deleteDocsInput', v: string): void
  (e: 'selectCollection', name: string): void
  (e: 'refreshCollections'): void
  (e: 'refreshStats'): void
  (e: 'pageChange', page: number): void
  (e: 'deleteDocs'): void
  (e: 'deleteSingleDoc', id: string): void
  (e: 'clearCollection'): void
  (e: 'confirmClear'): void
  (e: 'cancelClear'): void
  (e: 'deleteCollection'): void
  (e: 'confirmDeleteCol'): void
  (e: 'cancelDeleteCol'): void
}>()
</script>

<template>
  <div class="tab-content">
    <!-- 集合选择 -->
    <div class="form-group">
      <label class="form-label">选择集合</label>
      <div class="browse-col-select-row">
        <select
          class="form-input browse-select"
          :disabled="rag.collectionsLoading.value"
          :value="rag.selectedCollection.value"
          @change="$emit('selectCollection', ($event.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>-- 请选择集合 --</option>
          <option v-for="col in rag.collections.value?.collections ?? []" :key="col.name" :value="col.name">
            {{ col.name }} ({{ col.count }} 条)
          </option>
        </select>
        <button class="action-btn secondary" :disabled="rag.collectionsLoading.value" @click="$emit('refreshCollections')">
          {{ rag.collectionsLoading.value ? '刷新中...' : '🔄 刷新' }}
        </button>
      </div>
    </div>

    <!-- 统计面板 -->
    <fieldset v-if="rag.selectedCollection.value" class="config-section">
      <legend>
        统计面板
        <button class="action-btn secondary refresh-stats-btn" :disabled="rag.statsLoading.value" @click="$emit('refreshStats')">
          {{ rag.statsLoading.value ? '统计中...' : '刷新统计' }}
        </button>
      </legend>
      <div v-if="rag.statsLoading.value" class="config-loading">正在统计...</div>
      <div v-else-if="rag.collectionStats.value" class="stats-grid">
        <div class="stats-item"><span class="stats-label">总文档数</span><span class="stats-value">{{ rag.collectionStats.value.total_count.toLocaleString() }}</span></div>
        <div class="stats-item"><span class="stats-label">采样文档数</span><span class="stats-value">{{ rag.collectionStats.value.sampled_count.toLocaleString() }}</span></div>
        <div class="stats-item"><span class="stats-label">非空率</span><span class="stats-value">{{ rag.collectionStats.value.empty_rate }}</span></div>
        <div class="stats-item"><span class="stats-label">平均长度</span><span class="stats-value">{{ rag.collectionStats.value.avg_doc_length.toFixed(0) }} 字符</span></div>
        <div class="stats-item"><span class="stats-label">向量维度</span><span class="stats-value">{{ rag.collectionStats.value.vector_dimension ?? 'N/A' }}</span></div>
        <div class="stats-item"><span class="stats-label">空文档数</span><span class="stats-value">{{ rag.collectionStats.value.empty_count }}</span></div>
      </div>
      <div v-if="rag.collectionStats.value?.metadata_coverage?.length" class="meta-coverage-section">
        <h4 class="meta-title">元数据字段覆盖率</h4>
        <table class="meta-table">
          <thead><tr><th>字段名</th><th>出现次数</th><th>覆盖率</th></tr></thead>
          <tbody>
            <tr v-for="(item, mi) in rag.collectionStats.value.metadata_coverage" :key="mi">
              <td><code>{{ item.field }}</code></td>
              <td>{{ item.count }}</td>
              <td>{{ item.coverage }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </fieldset>

    <!-- 文档列表 -->
    <fieldset v-if="rag.selectedCollection.value" class="config-section">
      <legend>文档列表 <span class="legend-sub">(共 {{ rag.documents.value?.total ?? 0 }} 条)</span></legend>
      <div v-if="rag.docsLoading.value" class="config-loading">正在加载...</div>
      <div v-else-if="rag.documents.value?.documents?.length" class="docs-table-wrap">
        <table class="docs-table">
          <thead><tr><th class="docs-col-idx">#</th><th class="docs-col-id">文档 ID</th><th class="docs-col-content">内容预览</th><th class="docs-col-meta">元数据</th><th class="docs-col-action">操作</th></tr></thead>
          <tbody>
            <tr v-for="(doc, idx) in rag.documents.value.documents" :key="doc.id">
              <td class="docs-col-idx">{{ (rag.browsePage.value - 1) * rag.browsePageSize.value + idx + 1 }}</td>
              <td class="docs-col-id"><code>{{ doc.id }}</code></td>
              <td class="docs-col-content"><div class="doc-content-preview">{{ doc.document?.slice(0, 300) ?? 'N/A' }}{{ (doc.document?.length ?? 0) > 300 ? '...' : '' }}</div></td>
              <td class="docs-col-meta">
                <div v-if="doc.metadata && Object.keys(doc.metadata).length" class="meta-tags">
                  <span v-for="(val, key) in doc.metadata" :key="key" class="meta-tag" :title="`${key}: ${val}`">{{ key }}</span>
                </div>
                <span v-else class="text-muted">—</span>
              </td>
              <td class="docs-col-action">
                <button class="row-delete-btn" :disabled="rag.browseActionLoading.value" :title="`删除 ${doc.id}`" @click="$emit('deleteSingleDoc', doc.id)">✕</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="pagination">
          <span class="page-info">第 {{ rag.browsePage.value }} / {{ Math.max(1, Math.ceil((rag.documents.value?.total ?? 0) / rag.browsePageSize.value)) }} 页</span>
          <div class="page-btns">
            <button class="page-btn" :disabled="rag.browsePage.value <= 1" @click="$emit('pageChange', rag.browsePage.value - 1)">上一页</button>
            <button class="page-btn" :disabled="rag.browsePage.value * rag.browsePageSize.value >= (rag.documents.value?.total ?? 0)" @click="$emit('pageChange', rag.browsePage.value + 1)">下一页</button>
          </div>
        </div>
      </div>
      <div v-else class="health-empty">该集合为空</div>
    </fieldset>

    <!-- 操作 -->
    <fieldset v-if="rag.selectedCollection.value" class="config-section">
      <legend>操作</legend>
      <div class="browse-action-group">
        <h4 class="action-title">删除文档</h4>
        <div class="form-group mb-sm">
          <textarea class="form-textarea" rows="3" placeholder="输入要删除的文档 ID（每行一个，或以逗号分隔）" :disabled="rag.browseActionLoading.value" :value="deleteDocsInput" @input="$emit('update:deleteDocsInput', ($event.target as HTMLTextAreaElement).value)" />
        </div>
        <button class="action-btn danger" :disabled="rag.browseActionLoading.value || docsToDelete.length === 0" @click="$emit('deleteDocs')">
          {{ rag.browseActionLoading.value ? '操作中...' : `删除 ${docsToDelete.length} 个文档` }}
        </button>
      </div>

      <hr />

      <div class="browse-action-group">
        <h4 class="action-title danger-title">清空集合</h4>
        <p class="action-desc">删除集合中所有文档，集合结构保留</p>
        <template v-if="!showClearConfirm">
          <button class="action-btn danger" :disabled="rag.browseActionLoading.value" @click="$emit('clearCollection')">🧹 清空集合</button>
        </template>
        <template v-else>
          <p class="confirm-text">⚠️ 确认清空？此操作不可恢复！</p>
          <div class="confirm-btns">
            <button class="action-btn danger" :disabled="rag.browseActionLoading.value" @click="$emit('confirmClear')">✅ 确认清空</button>
            <button class="action-btn secondary" :disabled="rag.browseActionLoading.value" @click="$emit('cancelClear')">❌ 取消</button>
          </div>
        </template>
      </div>

      <hr />

      <div class="browse-action-group">
        <h4 class="action-title danger-title">删除整个集合</h4>
        <p class="action-desc">永久删除集合及所有数据</p>
        <template v-if="!showDeleteColConfirm">
          <button class="action-btn danger" :disabled="rag.browseActionLoading.value" @click="$emit('deleteCollection')">🗑️ 删除集合</button>
        </template>
        <template v-else>
          <p class="confirm-text">⚠️ 确认删除整个集合？此操作不可恢复！</p>
          <div class="confirm-btns">
            <button class="action-btn danger" :disabled="rag.browseActionLoading.value" @click="$emit('confirmDeleteCol')">✅ 确认删除</button>
            <button class="action-btn secondary" :disabled="rag.browseActionLoading.value" @click="$emit('cancelDeleteCol')">❌ 取消</button>
          </div>
        </template>
      </div>
    </fieldset>

    <div v-if="!rag.selectedCollection.value && !rag.collectionsLoading.value" class="health-empty">
      <template v-if="rag.collections.value?.collections?.length">请选择一个集合开始浏览</template>
      <template v-else>数据库中没有找到任何集合，请先在配置管理中检查 ChromaDB 路径</template>
    </div>
  </div>
</template>

<style scoped>
.tab-content { flex: 1; overflow-y: auto; padding-right: 4px; }
.form-group { margin-bottom: 16px; }
.mb-sm { margin-bottom: 8px; }
.form-label { display: flex; align-items: baseline; gap: 8px; font-size: 13px; font-weight: 500; color: #334155; margin-bottom: 6px; }
.form-textarea, .form-input {
  width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px;
  font-size: 13px; font-family: inherit; color: #1e293b; background: #fff; transition: border-color .15s; box-sizing: border-box;
}
.form-input { max-width: 500px; }
.browse-col-select-row { display: flex; gap: 10px; align-items: center; }
.browse-select { flex: 1; }
.config-section { border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 0 0 16px; background: #fff; }
.config-section legend { font-size: 14px; font-weight: 600; color: #334155; padding: 0 8px; }
.legend-sub { font-weight: 400; font-size: 12px; color: #94a3b8; margin-left: 8px; }
.config-loading { padding: 20px; color: #64748b; font-size: 13px; text-align: center; }
.health-empty { padding: 20px 0; text-align: center; color: #94a3b8; font-size: 13px; }
/* 按钮 */
.action-btn {
  padding: 8px 20px; border: none; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all .15s;
}
.action-btn:disabled { opacity: .6; cursor: not-allowed; }
.action-btn.secondary { background: #fff; color: #475569; border: 1px solid #cbd5e1; }
.action-btn.secondary:hover:not(:disabled) { background: #f1f5f9; }
.action-btn.danger { background: #dc2626; color: #fff; }
.action-btn.danger:hover:not(:disabled) { background: #b91c1c; }
.refresh-stats-btn { margin-left: 12px; padding: 2px 10px !important; font-size: 11px !important; }
/* 统计 */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.stats-item { padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; display: flex; flex-direction: column; gap: 4px; }
.stats-label { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: .5px; }
.stats-value { font-size: 18px; font-weight: 700; color: #1e293b; }
.meta-coverage-section { margin-top: 8px; }
.meta-title { font-size: 13px; color: #475569; margin: 12px 0 8px; }
.meta-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.meta-table th { text-align: left; padding: 5px 8px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; color: #64748b; font-weight: 500; }
.meta-table td { padding: 4px 8px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.meta-table code { font-family: 'JetBrains Mono','Fira Code','Consolas',monospace; font-size: 11px; }
/* 文档表格 */
.docs-table-wrap { overflow-x: auto; }
.docs-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.docs-table th { text-align: left; padding: 6px 8px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; color: #64748b; font-weight: 500; white-space: nowrap; font-size: 11px; }
.docs-table td { padding: 5px 8px; border-bottom: 1px solid #f1f5f9; color: #334155; vertical-align: top; }
.docs-table tbody tr:hover { background: #f8fafc; }
.docs-col-idx { width: 30px; text-align: center; color: #94a3b8; }
.docs-col-id { max-width: 200px; }
.docs-col-id code { font-family: 'JetBrains Mono','Fira Code','Consolas',monospace; font-size: 10px; word-break: break-all; }
.docs-col-content { min-width: 200px; }
.doc-content-preview { max-width: 400px; max-height: 60px; overflow-y: auto; font-size: 11px; color: #475569; white-space: pre-wrap; word-break: break-all; line-height: 1.4; }
.docs-col-meta { max-width: 180px; }
.docs-col-action { width: 36px; text-align: center; }
.row-delete-btn { width: 24px; height: 24px; border: none; border-radius: 4px; background: none; color: #94a3b8; font-size: 14px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; transition: all .15s; }
.row-delete-btn:hover:not(:disabled) { background: #fee2e2; color: #dc2626; }
.row-delete-btn:disabled { opacity: .4; cursor: not-allowed; }
.meta-tags { display: flex; flex-wrap: wrap; gap: 3px; }
.meta-tag { display: inline-block; padding: 1px 6px; background: #eff6ff; color: #2563eb; border-radius: 3px; font-size: 10px; font-family: monospace; white-space: nowrap; }
.text-muted { color: #cbd5e1; }
.pagination { display: flex; align-items: center; justify-content: space-between; padding: 10px 0 4px; }
.page-info { font-size: 12px; color: #64748b; }
.page-btns { display: flex; gap: 6px; }
.page-btn { padding: 4px 12px; border: 1px solid #cbd5e1; border-radius: 4px; background: #fff; font-size: 12px; color: #475569; cursor: pointer; }
.page-btn:hover:not(:disabled) { background: #f1f5f9; color: #2563eb; }
.page-btn:disabled { opacity: .5; cursor: not-allowed; }
/* 操作区 */
.browse-action-group { margin-bottom: 4px; }
.action-title { font-size: 13px; color: #475569; margin: 0 0 8px; }
.action-title.danger-title { color: #dc2626; margin: 0 0 4px; }
.action-desc { font-size: 12px; color: #64748b; margin: 0 0 8px; }
.confirm-text { color: #dc2626; font-size: 13px; font-weight: 600; margin: 0 0 8px; }
.confirm-btns { display: flex; gap: 8px; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 16px 0; }
</style>

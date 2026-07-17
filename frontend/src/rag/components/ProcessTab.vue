<script setup lang="ts">
import type { useRagManager } from '../composables/useRagManager'
import type { UploadItem } from '../composables/useRagUpload'

defineProps<{
  rag: ReturnType<typeof useRagManager>
  processFilesInput: string
  previewDir: string
  parsedFiles: string[]
  isPreviewMode: boolean
  expandedChunks: Set<string>
  uploadItems: UploadItem[]
  dragOverDrop: boolean
}>()

defineEmits<{
  (e: 'update:processFilesInput', v: string): void
  (e: 'update:previewDir', v: string): void
  (e: 'process'): void
  (e: 'confirmSave'): void
  (e: 'clear'): void
  (e: 'toggleChunks', filename: string): void
  (e: 'fileInput', ev: Event): void
  (e: 'removeUpload', idx: number): void
  (e: 'clearUpload'): void
  (e: 'pathInputChange'): void
  (e: 'dropZoneEnter', ev: DragEvent): void
  (e: 'dropZoneLeave', ev: DragEvent): void
  (e: 'dropZoneOver', ev: DragEvent): void
  (e: 'dropZone', ev: DragEvent): void
}>()
</script>

<template>
  <div class="tab-content">
    <!-- 文件上传 -->
    <fieldset class="config-section upload-section" :class="{ 'mode-disabled': processFilesInput.trim() !== '' }">
      <legend>拖拽上传</legend>
      <div
        class="drop-zone"
        :class="{ 'drop-zone--over': dragOverDrop }"
        @dragenter="$emit('dropZoneEnter', $event)"
        @dragleave="$emit('dropZoneLeave', $event)"
        @dragover="$emit('dropZoneOver', $event)"
        @drop="$emit('dropZone', $event)"
      >
        <template v-if="processFilesInput.trim()">
          <p class="drop-hint muted">已填写路径，上传已禁用</p>
        </template>
        <template v-else>
          <p class="drop-hint">拖拽 .md 文件到此处，或点击选择</p>
          <label class="file-select-btn">
            选择文件
            <input
              type="file" accept=".md" multiple class="file-input-hidden"
              :disabled="rag.processing.value"
              @change="$emit('fileInput', $event)"
            />
          </label>
        </template>
      </div>

      <div v-if="uploadItems.length" class="upload-list">
        <div v-for="(item, idx) in uploadItems" :key="item.name + idx" class="upload-item">
          <span class="upload-name">{{ item.name }}</span>
          <span class="upload-size">{{ (item.size / 1024).toFixed(1) }} KB</span>
          <button class="upload-remove" :disabled="rag.processing.value" @click="$emit('removeUpload', idx)">✕</button>
        </div>
        <div class="upload-actions">
          <button class="action-btn secondary" :disabled="rag.processing.value" @click="$emit('clearUpload')">清空列表</button>
        </div>
      </div>
    </fieldset>

    <div class="form-group">
      <label class="form-label">
        服务器文件路径
        <span class="form-hint">
          <template v-if="uploadItems.length">已有文件加入，路径已禁用</template>
          <template v-else>手动填写服务器上已有的 .md 文件路径（每行一个）</template>
        </span>
      </label>
      <textarea
        class="form-textarea" rows="6"
        placeholder="例如：&#10;F:\index_rag\knowledge-base\doc1.md&#10;F:\index_rag\knowledge-base\doc2.md"
        :disabled="rag.processing.value || uploadItems.length > 0"
        :value="processFilesInput"
        @input="$emit('update:processFilesInput', ($event.target as HTMLTextAreaElement).value)"
        @keyup="$emit('pathInputChange')"
      />
    </div>

    <div class="form-group">
      <label class="form-label">预览输出目录 <span class="form-hint">可选，留空使用默认配置</span></label>
      <input
        class="form-input" type="text"
        placeholder="可选，如：F:\index_rag\data\previews"
        :disabled="rag.processing.value"
        :value="previewDir"
        @input="$emit('update:previewDir', ($event.target as HTMLInputElement).value)"
      />
    </div>

    <div class="form-actions">
      <button
        v-if="!rag.processResult.value"
        class="action-btn primary"
        :disabled="rag.processing.value || (parsedFiles.length === 0 && !uploadItems.length)"
        @click="$emit('process')"
      >
        {{ rag.processing.value ? '处理中...' : `预览分块 (${uploadItems.length || parsedFiles.length} 个文件)` }}
      </button>
      <button
        v-if="isPreviewMode && rag.processResult.value && !rag.processing.value"
        class="action-btn primary"
        @click="$emit('confirmSave')"
      >
        确认入库 ({{ rag.processResult.value.total_chunks }} 个分块)
      </button>
      <button class="action-btn secondary" :disabled="rag.processing.value" @click="$emit('clear')">清空</button>
    </div>

    <!-- 处理结果 -->
    <div v-if="rag.processResult.value" class="result-panel" :class="isPreviewMode ? 'warning' : 'success'">
      <h3>{{ isPreviewMode ? '分块预览' : '处理结果' }}</h3>
      <p v-if="isPreviewMode" class="preview-hint">分块预览中，尚未写入向量库。确认分块质量后可点击下方"确认入库"。</p>
      <div class="result-summary">
        <div class="result-stat"><span class="stat-num">{{ rag.processResult.value.total_files }}</span><span class="stat-label">总文件</span></div>
        <div class="result-stat success"><span class="stat-num">{{ rag.processResult.value.success_count }}</span><span class="stat-label">成功</span></div>
        <div v-if="rag.processResult.value.failed_count" class="result-stat error"><span class="stat-num">{{ rag.processResult.value.failed_count }}</span><span class="stat-label">失败</span></div>
        <div class="result-stat"><span class="stat-num">{{ rag.processResult.value.total_chunks }}</span><span class="stat-label">总分块</span></div>
      </div>
      <div class="result-meta">向量库当前文档块总数：<strong>{{ rag.processResult.value.collection_count.toLocaleString() }}</strong></div>

      <ul v-if="rag.processResult.value.results?.length" class="result-detail-list">
        <li v-for="r in rag.processResult.value.results" :key="r.filename" class="result-detail-item" :class="r.status">
          <div class="detail-header" @click="$emit('toggleChunks', r.filename)">
            <span class="detail-expand">{{ expandedChunks.has(r.filename) ? '▾' : '▸' }}</span>
            <span class="detail-path">{{ r.filename }}</span>
            <span class="detail-chunks">{{ r.chunks_count }} chunks</span>
            <span v-if="r.error" class="detail-error">{{ r.error }}</span>
          </div>
          <div v-if="expandedChunks.has(r.filename) && r.chunks?.length" class="chunk-table-wrap">
            <table class="chunk-table">
              <thead>
                <tr><th class="col-idx">#</th><th class="col-header-path">标题路径</th><th class="col-preview">内容预览</th><th class="col-len">长度</th><th class="col-type">类型</th></tr>
              </thead>
              <tbody>
                <tr v-for="c in r.chunks" :key="c.index" :class="{ 'is-char-split': c.is_char_split }">
                  <td class="col-idx">{{ c.index }}</td>
                  <td class="col-header-path"><span v-if="c.header_path" class="header-path-text">{{ c.header_path }}</span><span v-else class="text-muted">—</span></td>
                  <td class="col-preview"><code class="chunk-preview-code">{{ c.preview }}</code></td>
                  <td class="col-len">{{ c.content_length }}</td>
                  <td class="col-type"><span v-if="c.is_char_split" class="badge badge--char-split">二次切分</span><span v-else class="badge badge--header">标题切分</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.tab-content { flex: 1; overflow-y: auto; padding-right: 4px; }
/* 表单 */
.form-group { margin-bottom: 16px; }
.form-label { display: flex; align-items: baseline; gap: 8px; font-size: 13px; font-weight: 500; color: #334155; margin-bottom: 6px; }
.form-hint { font-weight: 400; color: #94a3b8; font-size: 12px; }
.form-textarea, .form-input {
  width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px;
  font-size: 13px; font-family: inherit; color: #1e293b; background: #fff; transition: border-color .15s; box-sizing: border-box;
}
.form-textarea:focus, .form-input:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
.form-textarea:disabled, .form-input:disabled { background: #f8fafc; color: #94a3b8; }
.form-input { max-width: 500px; }
.form-actions { display: flex; gap: 10px; margin-bottom: 20px; }
.action-btn {
  padding: 8px 20px; border: none; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all .15s;
}
.action-btn:disabled { opacity: .6; cursor: not-allowed; }
.action-btn.primary { background: #2563eb; color: #fff; }
.action-btn.primary:hover:not(:disabled) { background: #1d4ed8; }
.action-btn.secondary { background: #fff; color: #475569; border: 1px solid #cbd5e1; }
.action-btn.secondary:hover:not(:disabled) { background: #f1f5f9; }
/* 上传区 */
.config-section { border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 0 0 16px; background: #fff; }
.config-section legend { font-size: 14px; font-weight: 600; color: #334155; padding: 0 8px; }
.upload-section { margin-bottom: 16px; }
.upload-section.mode-disabled { opacity: .45; pointer-events: none; }
.drop-zone { border: 2px dashed #cbd5e1; border-radius: 8px; padding: 24px; text-align: center; transition: all .2s; }
.drop-zone--over { border-color: #2563eb; background: #eff6ff; }
.drop-hint { margin: 0 0 12px; font-size: 13px; color: #94a3b8; }
.drop-hint.muted { color: #94a3b8; font-style: italic; }
.file-select-btn {
  display: inline-block; padding: 6px 16px; border: 1px solid #cbd5e1; border-radius: 6px;
  background: #fff; font-size: 13px; color: #475569; cursor: pointer; transition: all .15s;
}
.file-select-btn:hover { background: #f1f5f9; color: #2563eb; }
.file-input-hidden { display: none; }
.upload-list { margin-top: 12px; display: flex; flex-direction: column; gap: 4px; max-height: 200px; overflow-y: auto; }
.upload-item { display: flex; align-items: center; gap: 8px; padding: 5px 8px; border-radius: 4px; font-size: 12px; background: #eff6ff; }
.upload-name { flex: 1; font-family: monospace; font-size: 12px; color: #334155; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.upload-size { flex-shrink: 0; font-size: 11px; color: #64748b; }
.upload-remove { flex-shrink: 0; width: 20px; height: 20px; border: none; border-radius: 4px; background: none; color: #94a3b8; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.upload-remove:hover { background: #fee2e2; color: #dc2626; }
.upload-actions { margin-top: 10px; display: flex; gap: 8px; }
/* 结果面板 */
.result-panel { padding: 16px; border-radius: 8px; margin-top: 8px; }
.result-panel.success { background: #f0fdf4; border: 1px solid #bbf7d0; }
.result-panel.warning { background: #fffbeb; border: 1px solid #fde68a; }
.result-panel.warning h3 { color: #92400e; }
.result-panel h3 { margin: 0 0 12px; font-size: 14px; font-weight: 600; color: #166534; }
.preview-hint { margin: 0 0 12px; font-size: 12px; color: #a16207; background: #fef3c7; padding: 6px 10px; border-radius: 4px; border-left: 3px solid #f59e0b; }
.result-summary { display: flex; gap: 24px; margin-bottom: 12px; }
.result-stat { display: flex; flex-direction: column; align-items: center; }
.stat-num { font-size: 22px; font-weight: 700; color: #334155; }
.result-stat.success .stat-num { color: #16a34a; }
.result-stat.error .stat-num { color: #dc2626; }
.stat-label { font-size: 11px; color: #64748b; margin-top: 2px; }
.result-meta { font-size: 13px; color: #475569; margin-bottom: 12px; }
.result-detail-list { list-style: none; margin: 0; padding: 0; border-top: 1px solid #d1fae5; padding-top: 10px; }
.result-detail-item { display: flex; flex-direction: column; padding: 4px 0; font-size: 12px; border-bottom: 1px solid #ecfdf5; }
.detail-header { display: flex; align-items: center; gap: 8px; padding: 6px 4px; cursor: pointer; border-radius: 4px; transition: background .15s; user-select: none; }
.detail-header:hover { background: #dcfce7; }
.detail-expand { flex-shrink: 0; width: 16px; text-align: center; font-size: 11px; color: #64748b; }
.detail-path { flex: 1; font-family: 'JetBrains Mono','Fira Code','Consolas',monospace; font-size: 11px; color: #334155; word-break: break-all; }
.detail-chunks { flex-shrink: 0; background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 10px; font-weight: 500; }
.detail-error { color: #dc2626; flex-shrink: 0; }
.result-detail-item.error .detail-path { color: #dc2626; }
.chunk-table-wrap { margin: 4px 0 8px 20px; overflow-x: auto; border: 1px solid #d1fae5; border-radius: 6px; background: #f0fdf4; }
.chunk-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.chunk-table th { padding: 6px 8px; text-align: left; font-weight: 600; color: #475569; background: #dcfce7; border-bottom: 1px solid #bbf7d0; white-space: nowrap; font-size: 11px; }
.chunk-table td { padding: 5px 8px; color: #334155; border-bottom: 1px solid #ecfdf5; vertical-align: top; }
.chunk-table tbody tr:last-child td { border-bottom: none; }
.chunk-table tbody tr:hover { background: #ecfdf5; }
.chunk-table tbody tr.is-char-split { background: #fffbeb; }
.col-idx { width: 32px; text-align: center; color: #94a3b8; font-weight: 500; }
.col-header-path { max-width: 180px; }
.col-preview { min-width: 200px; }
.col-len { width: 52px; text-align: right; color: #64748b; }
.col-type { width: 72px; text-align: center; }
.header-path-text { font-family: 'JetBrains Mono','Fira Code','Consolas',monospace; font-size: 10px; color: #059669; word-break: break-all; line-height: 1.4; }
.chunk-preview-code { display: block; max-width: 360px; font-family: 'JetBrains Mono','Fira Code','Consolas',monospace; font-size: 10px; color: #475569; white-space: pre-wrap; word-break: break-all; line-height: 1.5; background: none; padding: 0; }
.text-muted { color: #cbd5e1; }
.badge { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 500; white-space: nowrap; }
.badge--char-split { background: #fef3c7; color: #92400e; }
.badge--header { background: #dcfce7; color: #166534; }
</style>

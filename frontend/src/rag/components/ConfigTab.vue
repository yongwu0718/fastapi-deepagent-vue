<script setup lang="ts">
import type { useRagManager } from '../composables/useRagManager'

defineProps<{
  rag: ReturnType<typeof useRagManager>
  configForm: Record<string, any>
  configSaveMsg: string
}>()
</script>

<template>
  <div class="tab-content">
    <div v-if="rag.configLoading.value" class="config-loading">正在读取配置...</div>
    <div v-else class="config-form">
      <!-- 嵌入模型 -->
      <fieldset class="config-section">
        <legend>嵌入模型</legend>
        <div class="config-row">
          <label class="config-label">模型名称 <span class="config-hint">Ollama 嵌入模型名称</span></label>
          <input v-model="configForm.embedding.model" class="form-input" type="text" placeholder="如 nomic-embed-text" />
        </div>
        <div class="config-row">
          <label class="config-label">服务地址 <span class="config-hint">Ollama 服务地址</span></label>
          <input v-model="configForm.embedding.base_url" class="form-input" type="text" placeholder="如 http://localhost:11434" />
        </div>
      </fieldset>

      <!-- 分割器 -->
      <fieldset class="config-section">
        <legend>文档分割器</legend>
        <div class="config-row">
          <label class="config-label">标题层级 <span class="config-hint">逗号分隔，如 #,##,###</span></label>
          <input
            class="form-input" type="text" placeholder="#,##,###"
            :value="configForm.rag.splitter.headers.join(',')"
            @input="(e: any) => configForm.rag.splitter.headers = (e.target as HTMLInputElement).value.split(',').map((s: string) => s.trim()).filter(Boolean)"
          />
        </div>
        <div class="config-row config-row--inline">
          <label class="config-label">Chunk 大小</label>
          <input v-model.number="configForm.rag.splitter.chunk_size" class="form-input form-input--short" type="number" min="100" max="10000" />
        </div>
        <div class="config-row config-row--inline">
          <label class="config-label">Chunk 重叠</label>
          <input v-model.number="configForm.rag.splitter.chunk_overlap" class="form-input form-input--short" type="number" min="0" max="5000" />
        </div>
        <div class="config-row config-row--check">
          <label class="config-label">启用字符切分</label>
          <input v-model="configForm.rag.splitter.enable_char_split" type="checkbox" class="config-checkbox" />
        </div>
        <div class="config-row config-row--check">
          <label class="config-label">逐行返回</label>
          <input v-model="configForm.rag.splitter.return_each_line" type="checkbox" class="config-checkbox" />
        </div>
        <div class="config-row config-row--check">
          <label class="config-label">剥离标题行</label>
          <input v-model="configForm.rag.splitter.strip_headers" type="checkbox" class="config-checkbox" />
        </div>
      </fieldset>

      <!-- HNSW -->
      <fieldset class="config-section">
        <legend>HNSW 索引参数</legend>
        <div class="config-row config-row--inline">
          <label class="config-label">距离度量</label>
          <select v-model="configForm.rag.hnsw.space" class="form-input form-input--short">
            <option value="cosine">cosine</option>
            <option value="l2">l2</option>
            <option value="ip">ip</option>
          </select>
        </div>
        <div class="config-row config-row--inline">
          <label class="config-label">构建深度</label>
          <input v-model.number="configForm.rag.hnsw.ef_construction" class="form-input form-input--short" type="number" min="10" max="1000" />
        </div>
        <div class="config-row config-row--inline">
          <label class="config-label">最大邻居数</label>
          <input v-model.number="configForm.rag.hnsw.max_neighbors" class="form-input form-input--short" type="number" min="4" max="256" />
        </div>
        <div class="config-row config-row--inline">
          <label class="config-label">查询深度</label>
          <input v-model.number="configForm.rag.hnsw.ef_search" class="form-input form-input--short" type="number" min="10" max="1000" />
        </div>
        <div class="config-row config-row--inline">
          <label class="config-label">构建线程数</label>
          <input v-model.number="configForm.rag.hnsw.num_threads" class="form-input form-input--short" type="number" min="1" max="64" />
        </div>
        <div class="config-row config-row--inline">
          <label class="config-label">批量大小</label>
          <input v-model.number="configForm.rag.hnsw.batch_size" class="form-input form-input--short" type="number" min="1" max="10000" />
        </div>
        <div class="config-row config-row--inline">
          <label class="config-label">同步阈值</label>
          <input v-model.number="configForm.rag.hnsw.sync_threshold" class="form-input form-input--short" type="number" min="1" max="100000" />
        </div>
        <div class="config-row config-row--inline">
          <label class="config-label">扩容因子</label>
          <input v-model.number="configForm.rag.hnsw.resize_factor" class="form-input form-input--short" type="number" min="1" max="5" step="0.1" />
        </div>
      </fieldset>

      <!-- 处理参数 -->
      <fieldset class="config-section">
        <legend>处理参数</legend>
        <div class="config-row">
          <label class="config-label">预览输出目录 <span class="config-hint">分块预览文件输出路径</span></label>
          <input v-model="configForm.rag.processing.preview_output_dir" class="form-input" type="text" placeholder="留空使用默认值" />
        </div>
        <div class="config-row config-row--check">
          <label class="config-label">CLI 交互确认</label>
          <input v-model="configForm.rag.processing.enable_interactive" type="checkbox" class="config-checkbox" />
        </div>
      </fieldset>

      <!-- 集合 / 存储 -->
      <fieldset class="config-section">
        <legend>集合 / 存储</legend>
        <div class="config-row">
          <label class="config-label">集合名称 <span class="config-hint">Chroma 集合名称，修改后旧集合数据保留在磁盘</span></label>
          <input v-model="configForm.rag.collection.name" class="form-input" type="text" placeholder="如 my_collection" />
        </div>
        <div class="config-row">
          <label class="config-label">持久化目录 <span class="config-hint">向量库磁盘路径</span></label>
          <input v-model="configForm.rag.collection.persist_directory" class="form-input" type="text" placeholder="如 ./chroma_db" />
        </div>
      </fieldset>
      <p v-if="configSaveMsg" class="config-save-msg">{{ configSaveMsg }}</p>
    </div>
  </div>
</template>

<style scoped>
.tab-content { flex: 1; overflow-y: auto; padding-right: 4px; }
.config-loading { padding: 20px; color: #64748b; font-size: 13px; text-align: center; }
.config-form { display: flex; flex-direction: column; gap: 4px; }
.config-section { border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 0 0 16px; background: #fff; }
.config-section legend { font-size: 14px; font-weight: 600; color: #334155; padding: 0 8px; }
.config-row { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.config-row--inline { flex-direction: row; align-items: center; justify-content: space-between; gap: 16px; }
.config-row--inline .config-label { margin-bottom: 0; flex-shrink: 0; }
.config-row--check { flex-direction: row; align-items: center; justify-content: space-between; gap: 16px; }
.config-row--check .config-label { margin-bottom: 0; }
.config-label { font-size: 13px; font-weight: 500; color: #475569; display: flex; align-items: baseline; gap: 6px; }
.config-hint { font-weight: 400; color: #94a3b8; font-size: 11px; }
.config-checkbox { width: 18px; height: 18px; cursor: pointer; accent-color: #2563eb; }
.form-input { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; font-family: inherit; color: #1e293b; background: #fff; transition: border-color .15s; box-sizing: border-box; max-width: 500px; }
.form-input--short { width: 160px; max-width: 160px; }
.config-save-msg { margin: 0; font-size: 13px; color: #059669; }
</style>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useRagManager } from './useRagManager'
import { toast } from '@/shared/useToast'

const router = useRouter()
const rag = useRagManager()

// ── 分块预览展开状态 ──
const expandedChunks = reactive<Set<string>>(new Set())

function toggleChunks(filename: string) {
  if (expandedChunks.has(filename)) {
    expandedChunks.delete(filename)
  } else {
    expandedChunks.add(filename)
  }
}

// ── Tab 状态 ──
type TabKey = 'process' | 'delete' | 'config'
const activeTab = ref<TabKey>('process')

// ── 配置表单（对应 RagFullConfigModel 结构）──
const configForm = ref({
  embedding: { model: '', base_url: '' },
  rag: {
    splitter: {
      headers: ['#', '##', '###'],
      return_each_line: false,
      strip_headers: false,
      enable_char_split: true,
      chunk_size: 1000,
      chunk_overlap: 200,
    },
    hnsw: {
      space: 'cosine',
      ef_construction: 200,
      max_neighbors: 16,
      ef_search: 100,
      num_threads: 4,
      batch_size: 100,
      sync_threshold: 1000,
      resize_factor: 1.2,
    },
    processing: {
      preview_output_dir: '',
      enable_interactive: false,
    },
  },
})

const configSaveMsg = ref('')

function applyConfigToForm(raw: any) {
  const e = raw?.embedding ?? {}
  const s = raw?.rag?.splitter ?? {}
  const h = raw?.rag?.hnsw ?? {}
  const p = raw?.rag?.processing ?? {}
  configForm.value = {
    embedding: { model: e.model ?? '', base_url: e.base_url ?? '' },
    rag: {
      splitter: {
        headers: s.headers ?? ['#', '##', '###'],
        return_each_line: s.return_each_line ?? false,
        strip_headers: s.strip_headers ?? false,
        enable_char_split: s.enable_char_split ?? true,
        chunk_size: s.chunk_size ?? 1000,
        chunk_overlap: s.chunk_overlap ?? 200,
      },
      hnsw: {
        space: h.space ?? 'cosine',
        ef_construction: h.ef_construction ?? 200,
        max_neighbors: h.max_neighbors ?? 16,
        ef_search: h.ef_search ?? 100,
        num_threads: h.num_threads ?? 4,
        batch_size: h.batch_size ?? 100,
        sync_threshold: h.sync_threshold ?? 1000,
        resize_factor: h.resize_factor ?? 1.2,
      },
      processing: {
        preview_output_dir: p.preview_output_dir ?? '',
        enable_interactive: p.enable_interactive ?? false,
      },
    },
  }
}

function buildConfigPayload(): any {
  return {
    embedding: {
      model: configForm.value.embedding.model || undefined,
      base_url: configForm.value.embedding.base_url || undefined,
    },
    rag: {
      splitter: { ...configForm.value.rag.splitter },
      hnsw: {
        ...configForm.value.rag.hnsw,
        resize_factor: Number(configForm.value.rag.hnsw.resize_factor),
      },
      processing: {
        preview_output_dir: configForm.value.rag.processing.preview_output_dir || undefined,
        enable_interactive: configForm.value.rag.processing.enable_interactive,
      },
    },
  }
}

async function handleLoadConfig() {
  await rag.fetchConfig()
  if (rag.config.value) {
    applyConfigToForm(rag.config.value)
    configSaveMsg.value = ''
  }
}

async function handleSaveConfig() {
  configSaveMsg.value = ''
  const payload = buildConfigPayload()
  await rag.saveConfig(payload)
  if (rag.config.value) {
    configSaveMsg.value = '配置已保存，运行时已自动重载'
  }
}

// Tab 切换时自动加载配置
function switchTab(key: TabKey) {
  activeTab.value = key
  if (key === 'config' && !rag.configLoaded.value && !rag.configLoading.value) {
    handleLoadConfig()
  }
}

// ── 处理表单 ──
const processFilesInput = ref('')
const previewDir = ref('')
const parsedFiles = computed(() =>
  processFilesInput.value
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
)
const isPreviewMode = ref(false) // true=当前结果是预览（未入库）

// ── 删除表单 ──
const deleteIdsInput = ref('')
const parsedIds = computed(() =>
  deleteIdsInput.value
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
)

// ── 自动刷新 ──
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

// ── 生命周期 ──
onMounted(() => {
  rag.fetchHealth()
  startAutoRefresh()
})

// ── 导航 ──
function backToChat() {
  stopAutoRefresh()
  router.push({ name: 'chat', params: { threadId: crypto.randomUUID() } })
}

function goToSettings() {
  stopAutoRefresh()
  router.push({ name: 'settings' })
}

// ── 操作 ──
function handleProcess() {
  isPreviewMode.value = true
  // 有待上传的文件 → 走 multipart 直传处理（preview only）
  if (uploadItems.value.length) {
    rag.processUploadedFiles(
      uploadItems.value.map((u) => u.file),
      previewDir.value || null,
      true,
    )
    return
  }
  // 无上传文件 → 走 JSON 路径模式（preview only）
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

function handleDelete() {
  rag.deleteByIds(parsedIds.value)
}

function clearProcessForm() {
  processFilesInput.value = ''
  previewDir.value = ''
  rag.processResult.value = null
  uploadItems.value = []
  expandedChunks.clear()
  isPreviewMode.value = false
}

function clearDeleteForm() {
  deleteIdsInput.value = ''
  rag.deleteResult.value = null
}

// ── 文件上传区 ──
interface UploadItem {
  file: File
  name: string
  size: number
}
const uploadItems = ref<UploadItem[]>([])
const dragOverDrop = ref(false)
let dragCounterDrop = 0

function handleFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files?.length) return
  addFiles(Array.from(files))
  input.value = ''
}

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
  // 互斥：有上传文件时清空路径输入
  if (uploadItems.value.length) {
    processFilesInput.value = ''
  }
}

function removeUploadItem(idx: number) {
  uploadItems.value.splice(idx, 1)
}

// 互斥：手动填写路径时清空上传列表
function onPathInputChange() {
  if (processFilesInput.value.trim()) {
    uploadItems.value = []
  }
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
</script>

<template>
  <div class="rag-page">
    <!-- ── Header ── -->
    <header class="rag-header">
      <button class="back-btn" @click="backToChat">← 返回聊天</button>
      <h1 class="rag-title">向量库管理 (RAG)</h1>
      <button class="settings-link" @click="goToSettings">设置管理</button>
    </header>

    <!-- ── Body ── -->
    <div class="rag-body">
      <!-- 左侧健康面板 -->
      <aside class="health-panel">
        <div class="panel-header">
          <h2>健康状态</h2>
          <div class="health-actions">
            <label class="auto-refresh-label" title="每10秒自动刷新">
              <input
                type="checkbox"
                :checked="autoRefresh"
                @change="toggleAutoRefresh"
              />
              自动刷新
            </label>
            <button
              class="refresh-btn"
              :disabled="rag.healthLoading.value"
              @click="rag.fetchHealth()"
            >
              {{ rag.healthLoading.value ? '刷新中...' : '🔄 刷新' }}
            </button>
          </div>
        </div>

        <!-- 加载骨架 -->
        <div v-if="rag.healthLoading.value && !rag.health.value" class="health-skeleton">
          <div v-for="i in 5" :key="i" class="skeleton-row">
            <div class="skeleton-label" />
            <div class="skeleton-value" />
          </div>
        </div>

        <!-- 错误 -->
        <div v-else-if="rag.healthError.value" class="health-error">
          <p>{{ rag.healthError.value }}</p>
        </div>

        <!-- 健康数据 -->
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

        <!-- 空状态 -->
        <div v-else class="health-empty">
          暂无健康数据
        </div>
      </aside>

      <!-- 右侧操作区 -->
      <main class="operation-area">
        <!-- Tab 栏 -->
        <nav class="tab-bar">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'process' }"
            @click="switchTab('process')"
          >
            文件处理
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'delete' }"
            @click="switchTab('delete')"
          >
            文档删除
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'config' }"
            @click="switchTab('config')"
          >
            配置管理
          </button>
          <span class="tab-spacer" />
          <template v-if="activeTab === 'config'">
            <button
              class="tab-action-btn"
              :disabled="rag.configLoading.value || rag.configSaving.value"
              @click="handleLoadConfig"
            >
              {{ rag.configLoading.value ? '读取中...' : '读取' }}
            </button>
            <button
              class="tab-action-btn"
              :disabled="rag.configSaving.value || rag.configLoading.value"
              @click="handleSaveConfig"
            >
              {{ rag.configSaving.value ? '保存中...' : '保存' }}
            </button>
          </template>
        </nav>

        <!-- 处理 Tab -->
        <div v-if="activeTab === 'process'" class="tab-content">
          <!-- ── 文件上传区域 ── -->
          <fieldset
            class="config-section upload-section"
            :class="{ 'mode-disabled': processFilesInput.trim() !== '' }"
          >
            <legend>拖拽上传</legend>
            <div
              class="drop-zone"
              :class="{ 'drop-zone--over': dragOverDrop }"
              @dragenter="onDropZoneEnter"
              @dragleave="onDropZoneLeave"
              @dragover="onDropZoneOver"
              @drop="onDropZone"
            >
              <template v-if="processFilesInput.trim()">
                <p class="drop-hint muted">已填写路径，上传已禁用</p>
              </template>
              <template v-else>
                <p class="drop-hint">拖拽 .md 文件到此处，或点击选择</p>
                <label class="file-select-btn">
                  选择文件
                  <input
                    type="file"
                    accept=".md"
                    multiple
                    class="file-input-hidden"
                    :disabled="rag.processing.value"
                    @change="handleFileInput"
                  />
                </label>
              </template>
            </div>

            <!-- 已选文件列表 -->
            <div v-if="uploadItems.length" class="upload-list">
              <div
                v-for="(item, idx) in uploadItems"
                :key="item.name + idx"
                class="upload-item"
              >
                <span class="upload-name">{{ item.name }}</span>
                <span class="upload-size">{{ (item.size / 1024).toFixed(1) }} KB</span>
                <button
                  class="upload-remove"
                  :disabled="rag.processing.value"
                  @click="removeUploadItem(idx)"
                >
                  ✕
                </button>
              </div>
              <div class="upload-actions">
                <button
                  class="action-btn secondary"
                  :disabled="rag.processing.value"
                  @click="clearUploadItems"
                >
                  清空列表
                </button>
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
              v-model="processFilesInput"
              class="form-textarea"
              rows="6"
              placeholder="例如：&#10;F:\index_rag\knowledge-base\doc1.md&#10;F:\index_rag\knowledge-base\doc2.md"
              :disabled="rag.processing.value || uploadItems.length > 0"
              @input="onPathInputChange"
            />
          </div>

          <div class="form-group">
            <label class="form-label">
              预览输出目录
              <span class="form-hint">可选，留空使用默认配置</span>
            </label>
            <input
              v-model="previewDir"
              class="form-input"
              type="text"
              placeholder="可选，如：F:\index_rag\data\previews"
              :disabled="rag.processing.value"
            />
          </div>

          <div class="form-actions">
            <!-- 预览模式没有结果时：显示"预览分块"按钮 -->
            <button
              v-if="!rag.processResult.value"
              class="action-btn primary"
              :disabled="rag.processing.value || (parsedFiles.length === 0 && !uploadItems.length)"
              @click="handleProcess"
            >
              {{ rag.processing.value ? '处理中...' : `预览分块 (${uploadItems.length || parsedFiles.length} 个文件)` }}
            </button>
            <!-- 预览模式有结果时：显示"确认入库"按钮 -->
            <button
              v-if="isPreviewMode && rag.processResult.value && !rag.processing.value"
              class="action-btn primary"
              @click="handleConfirmSave"
            >
              确认入库 ({{ rag.processResult.value.total_chunks }} 个分块)
            </button>
            <button
              class="action-btn secondary"
              :disabled="rag.processing.value"
              @click="clearProcessForm"
            >
              清空
            </button>
          </div>

          <!-- 处理结果 -->
          <div v-if="rag.processResult.value" class="result-panel" :class="isPreviewMode ? 'warning' : 'success'">
            <h3>{{ isPreviewMode ? '分块预览' : '处理结果' }}</h3>
            <p v-if="isPreviewMode" class="preview-hint">分块预览中，尚未写入向量库。确认分块质量后可点击下方"确认入库"。</p>
            <div class="result-summary">
              <div class="result-stat">
                <span class="stat-num">{{ rag.processResult.value.total_files }}</span>
                <span class="stat-label">总文件</span>
              </div>
              <div class="result-stat success">
                <span class="stat-num">{{ rag.processResult.value.success_count }}</span>
                <span class="stat-label">成功</span>
              </div>
              <div class="result-stat error" v-if="rag.processResult.value.failed_count">
                <span class="stat-num">{{ rag.processResult.value.failed_count }}</span>
                <span class="stat-label">失败</span>
              </div>
              <div class="result-stat">
                <span class="stat-num">{{ rag.processResult.value.total_chunks }}</span>
                <span class="stat-label">总分块</span>
              </div>
            </div>
            <div class="result-meta">
              向量库当前文档块总数：<strong>{{ rag.processResult.value.collection_count.toLocaleString() }}</strong>
            </div>
            <!-- 逐文件详情（含分块预览） -->
            <ul v-if="rag.processResult.value.results?.length" class="result-detail-list">
              <li
                v-for="r in rag.processResult.value.results"
                :key="r.filename"
                class="result-detail-item"
                :class="r.status"
              >
                <div class="detail-header" @click="toggleChunks(r.filename)">
                  <span class="detail-expand">{{ expandedChunks.has(r.filename) ? '▾' : '▸' }}</span>
                  <span class="detail-path">{{ r.filename }}</span>
                  <span class="detail-chunks">{{ r.chunks_count }} chunks</span>
                  <span v-if="r.error" class="detail-error">{{ r.error }}</span>
                </div>
                <!-- 分块预览表格 -->
                <div v-if="expandedChunks.has(r.filename) && r.chunks?.length" class="chunk-table-wrap">
                  <table class="chunk-table">
                    <thead>
                      <tr>
                        <th class="col-idx">#</th>
                        <th class="col-header-path">标题路径</th>
                        <th class="col-preview">内容预览</th>
                        <th class="col-len">长度</th>
                        <th class="col-type">类型</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="c in r.chunks" :key="c.index" :class="{ 'is-char-split': c.is_char_split }">
                        <td class="col-idx">{{ c.index }}</td>
                        <td class="col-header-path">
                          <span v-if="c.header_path" class="header-path-text">{{ c.header_path }}</span>
                          <span v-else class="text-muted">—</span>
                        </td>
                        <td class="col-preview">
                          <code class="chunk-preview-code">{{ c.preview }}</code>
                        </td>
                        <td class="col-len">{{ c.content_length }}</td>
                        <td class="col-type">
                          <span v-if="c.is_char_split" class="badge badge--char-split">二次切分</span>
                          <span v-else class="badge badge--header">标题切分</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </li>
            </ul>
          </div>
        </div>

        <!-- 删除 Tab -->
        <div v-if="activeTab === 'delete'" class="tab-content">
          <div class="form-group">
            <label class="form-label">
              文档 ID 列表
              <span class="form-hint">每行一个 ID，或以逗号分隔</span>
            </label>
            <textarea
              v-model="deleteIdsInput"
              class="form-textarea"
              rows="6"
              placeholder="例如：&#10;doc1_chunk_0&#10;doc1_chunk_1&#10;doc2_chunk_0"
              :disabled="rag.deleting.value"
            />
          </div>

          <div class="form-actions">
            <button
              class="action-btn danger"
              :disabled="rag.deleting.value || parsedIds.length === 0"
              @click="handleDelete"
            >
              {{ rag.deleting.value ? '删除中...' : `确认删除 (${parsedIds.length} 个文档)` }}
            </button>
            <button
              class="action-btn secondary"
              :disabled="rag.deleting.value"
              @click="clearDeleteForm"
            >
              清空
            </button>
          </div>

          <!-- 删除结果 -->
          <div v-if="rag.deleteResult.value" class="result-panel success">
            <h3>删除结果</h3>
            <div class="result-summary">
              <div class="result-stat success">
                <span class="stat-num">{{ rag.deleteResult.value.deleted_count }}</span>
                <span class="stat-label">已删除</span>
              </div>
              <div class="result-stat">
                <span class="stat-num">{{ rag.deleteResult.value.collection_count.toLocaleString() }}</span>
                <span class="stat-label">剩余文档块</span>
              </div>
            </div>
            <p v-if="rag.deleteResult.value.message" class="result-msg">
              {{ rag.deleteResult.value.message }}
            </p>
          </div>
        </div>

        <!-- 配置 Tab -->
        <div v-if="activeTab === 'config'" class="tab-content">
          <!-- 加载中 -->
          <div v-if="rag.configLoading.value" class="config-loading">
            正在读取配置...
          </div>

          <!-- 配置表单 -->
          <div v-else class="config-form">
            <!-- Section: 嵌入模型 -->
            <fieldset class="config-section">
              <legend>嵌入模型</legend>
              <div class="config-row">
                <label class="config-label">
                  模型名称
                  <span class="config-hint">Ollama 嵌入模型名称</span>
                </label>
                <input
                  v-model="configForm.embedding.model"
                  class="form-input"
                  type="text"
                  placeholder="如 nomic-embed-text"
                />
              </div>
              <div class="config-row">
                <label class="config-label">
                  服务地址
                  <span class="config-hint">Ollama 服务地址</span>
                </label>
                <input
                  v-model="configForm.embedding.base_url"
                  class="form-input"
                  type="text"
                  placeholder="如 http://localhost:11434"
                />
              </div>
            </fieldset>

            <!-- Section: 分割器 -->
            <fieldset class="config-section">
              <legend>文档分割器</legend>
              <div class="config-row">
                <label class="config-label">
                  标题层级
                  <span class="config-hint">逗号分隔，如 #,##,###</span>
                </label>
                <input
                  class="form-input"
                  type="text"
                  placeholder="#,##,###"
                  :value="configForm.rag.splitter.headers.join(',')"
                  @input="(e: any) => {
                    configForm.rag.splitter.headers = (e.target as HTMLInputElement).value.split(',').map((s: string) => s.trim()).filter(Boolean)
                  }"
                />
              </div>
              <div class="config-row config-row--inline">
                <label class="config-label">Chunk 大小</label>
                <input
                  v-model.number="configForm.rag.splitter.chunk_size"
                  class="form-input form-input--short"
                  type="number"
                  min="100"
                  max="10000"
                />
              </div>
              <div class="config-row config-row--inline">
                <label class="config-label">Chunk 重叠</label>
                <input
                  v-model.number="configForm.rag.splitter.chunk_overlap"
                  class="form-input form-input--short"
                  type="number"
                  min="0"
                  max="5000"
                />
              </div>
              <div class="config-row config-row--check">
                <label class="config-label">启用字符切分</label>
                <input
                  v-model="configForm.rag.splitter.enable_char_split"
                  type="checkbox"
                  class="config-checkbox"
                />
              </div>
              <div class="config-row config-row--check">
                <label class="config-label">逐行返回</label>
                <input
                  v-model="configForm.rag.splitter.return_each_line"
                  type="checkbox"
                  class="config-checkbox"
                />
              </div>
              <div class="config-row config-row--check">
                <label class="config-label">剥离标题行</label>
                <input
                  v-model="configForm.rag.splitter.strip_headers"
                  type="checkbox"
                  class="config-checkbox"
                />
              </div>
            </fieldset>

            <!-- Section: HNSW 索引 -->
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
                <input
                  v-model.number="configForm.rag.hnsw.ef_construction"
                  class="form-input form-input--short"
                  type="number"
                  min="10"
                  max="1000"
                />
              </div>
              <div class="config-row config-row--inline">
                <label class="config-label">最大邻居数</label>
                <input
                  v-model.number="configForm.rag.hnsw.max_neighbors"
                  class="form-input form-input--short"
                  type="number"
                  min="4"
                  max="256"
                />
              </div>
              <div class="config-row config-row--inline">
                <label class="config-label">查询深度</label>
                <input
                  v-model.number="configForm.rag.hnsw.ef_search"
                  class="form-input form-input--short"
                  type="number"
                  min="10"
                  max="1000"
                />
              </div>
              <div class="config-row config-row--inline">
                <label class="config-label">构建线程数</label>
                <input
                  v-model.number="configForm.rag.hnsw.num_threads"
                  class="form-input form-input--short"
                  type="number"
                  min="1"
                  max="64"
                />
              </div>
              <div class="config-row config-row--inline">
                <label class="config-label">批量大小</label>
                <input
                  v-model.number="configForm.rag.hnsw.batch_size"
                  class="form-input form-input--short"
                  type="number"
                  min="1"
                  max="10000"
                />
              </div>
              <div class="config-row config-row--inline">
                <label class="config-label">同步阈值</label>
                <input
                  v-model.number="configForm.rag.hnsw.sync_threshold"
                  class="form-input form-input--short"
                  type="number"
                  min="1"
                  max="100000"
                />
              </div>
              <div class="config-row config-row--inline">
                <label class="config-label">扩容因子</label>
                <input
                  v-model.number="configForm.rag.hnsw.resize_factor"
                  class="form-input form-input--short"
                  type="number"
                  min="1"
                  max="5"
                  step="0.1"
                />
              </div>
            </fieldset>

            <!-- Section: 处理参数 -->
            <fieldset class="config-section">
              <legend>处理参数</legend>
              <div class="config-row">
                <label class="config-label">
                  预览输出目录
                  <span class="config-hint">分块预览文件输出路径</span>
                </label>
                <input
                  v-model="configForm.rag.processing.preview_output_dir"
                  class="form-input"
                  type="text"
                  placeholder="留空使用默认值"
                />
              </div>
              <div class="config-row config-row--check">
                <label class="config-label">CLI 交互确认</label>
                <input
                  v-model="configForm.rag.processing.enable_interactive"
                  type="checkbox"
                  class="config-checkbox"
                />
              </div>
            </fieldset>
            <p v-if="configSaveMsg" class="config-save-msg">{{ configSaveMsg }}</p>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
/* ── 页面布局 ── */
.rag-page {
  display: flex;
  flex-direction: column;
  height: 100svh;
  background: #f8f9fa;
}

/* ── Header ── */
.rag-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.rag-title {
  flex: 1;
  font-size: 17px;
  font-weight: 600;
  margin: 0;
}

.back-btn,
.settings-link {
  padding: 5px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  color: #475569;
}
.back-btn:hover,
.settings-link:hover {
  background: #f1f5f9;
}

/* ── Body ── */
.rag-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* ── 左侧健康面板 ── */
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

.panel-header h2 {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
}

.health-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.auto-refresh-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #64748b;
  cursor: pointer;
  user-select: none;
}

.refresh-btn {
  padding: 3px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 5px;
  background: #fff;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  white-space: nowrap;
}
.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.refresh-btn:hover:not(:disabled) {
  background: #f1f5f9;
}

/* ── 健康数据 ── */
.health-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.health-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 9px 0;
  border-bottom: 1px solid #f1f5f9;
}

.item-label {
  font-size: 13px;
  color: #64748b;
  flex-shrink: 0;
}

.item-value {
  font-size: 13px;
  color: #1e293b;
  text-align: right;
  word-break: break-all;
}

.item-value.highlight {
  font-weight: 700;
  color: #2563eb;
  font-size: 16px;
}

.item-value.mono {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 11px;
}

/* ── 骨架屏 ── */
.health-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.skeleton-label {
  width: 60px;
  height: 14px;
  background: #e2e8f0;
  border-radius: 3px;
  animation: pulse 1.5s infinite;
}

.skeleton-value {
  width: 120px;
  height: 14px;
  background: #e2e8f0;
  border-radius: 3px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.health-error {
  padding: 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 13px;
}

.health-empty {
  padding: 20px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

/* ── 右侧操作区 ── */
.operation-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  padding: 20px;
}

.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e2e8f0;
}

.tab-btn {
  padding: 8px 20px;
  border: none;
  background: none;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.15s;
}
.tab-btn:hover {
  color: #334155;
}
.tab-btn.active {
  color: #2563eb;
  font-weight: 600;
  border-bottom-color: #2563eb;
}

.tab-spacer {
  flex: 1;
}

.tab-action-btn {
  padding: 3px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #fff;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  white-space: nowrap;
  margin-bottom: -2px;
  transition: all 0.15s;
}

.tab-action-btn:hover:not(:disabled) {
  background: #f1f5f9;
  color: #2563eb;
}

.tab-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

/* ── 表单 ── */
.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 6px;
}

.form-hint {
  font-weight: 400;
  color: #94a3b8;
  font-size: 12px;
}

.form-textarea,
.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  color: #1e293b;
  background: #fff;
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.form-textarea:focus,
.form-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-textarea:disabled,
.form-input:disabled {
  background: #f8fafc;
  color: #94a3b8;
}

.form-input {
  max-width: 500px;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.action-btn {
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-btn.primary {
  background: #2563eb;
  color: #fff;
}
.action-btn.primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.action-btn.danger {
  background: #dc2626;
  color: #fff;
}
.action-btn.danger:hover:not(:disabled) {
  background: #b91c1c;
}

.action-btn.secondary {
  background: #fff;
  color: #475569;
  border: 1px solid #cbd5e1;
}
.action-btn.secondary:hover:not(:disabled) {
  background: #f1f5f9;
}

/* ── 结果面板 ── */
.result-panel {
  padding: 16px;
  border-radius: 8px;
  margin-top: 8px;
}

.result-panel.success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.result-panel.warning {
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.result-panel.warning h3 {
  color: #92400e;
}

.preview-hint {
  margin: 0 0 12px 0;
  font-size: 12px;
  color: #a16207;
  background: #fef3c7;
  padding: 6px 10px;
  border-radius: 4px;
  border-left: 3px solid #f59e0b;
}

.result-panel h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #166534;
}

.result-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
}

.result-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: #334155;
}

.result-stat.success .stat-num {
  color: #16a34a;
}

.result-stat.error .stat-num {
  color: #dc2626;
}

.stat-label {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.result-meta {
  font-size: 13px;
  color: #475569;
  margin-bottom: 12px;
}

.result-msg {
  font-size: 13px;
  color: #475569;
  margin: 0;
}

/* ── 逐文件详情 ── */
.result-detail-list {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid #d1fae5;
  padding-top: 10px;
}

.result-detail-item {
  display: flex;
  flex-direction: column;
  padding: 4px 0;
  font-size: 12px;
  border-bottom: 1px solid #ecfdf5;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s;
  user-select: none;
}

.detail-header:hover {
  background: #dcfce7;
}

.detail-expand {
  flex-shrink: 0;
  width: 16px;
  text-align: center;
  font-size: 11px;
  color: #64748b;
}

.detail-path {
  flex: 1;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 11px;
  color: #334155;
  word-break: break-all;
}

.detail-chunks {
  flex-shrink: 0;
  background: #dcfce7;
  color: #166534;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.detail-error {
  color: #dc2626;
  flex-shrink: 0;
}

.result-detail-item.error .detail-path {
  color: #dc2626;
}

/* ── 分块预览表格 ── */
.chunk-table-wrap {
  margin: 4px 0 8px 20px;
  overflow-x: auto;
  border: 1px solid #d1fae5;
  border-radius: 6px;
  background: #f0fdf4;
}

.chunk-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.chunk-table th {
  padding: 6px 8px;
  text-align: left;
  font-weight: 600;
  color: #475569;
  background: #dcfce7;
  border-bottom: 1px solid #bbf7d0;
  white-space: nowrap;
  font-size: 11px;
}

.chunk-table td {
  padding: 5px 8px;
  color: #334155;
  border-bottom: 1px solid #ecfdf5;
  vertical-align: top;
}

.chunk-table tbody tr:last-child td {
  border-bottom: none;
}

.chunk-table tbody tr:hover {
  background: #ecfdf5;
}

.chunk-table tbody tr.is-char-split {
  background: #fffbeb;
}

.col-idx {
  width: 32px;
  text-align: center;
  color: #94a3b8;
  font-weight: 500;
}

.col-header-path {
  max-width: 180px;
}

.col-preview {
  min-width: 200px;
}

.col-len {
  width: 52px;
  text-align: right;
  color: #64748b;
}

.col-type {
  width: 72px;
  text-align: center;
}

.header-path-text {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 10px;
  color: #059669;
  word-break: break-all;
  line-height: 1.4;
}

.chunk-preview-code {
  display: block;
  max-width: 360px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 10px;
  color: #475569;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
  background: none;
  padding: 0;
}

.text-muted {
  color: #cbd5e1;
}

.badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}

.badge--char-split {
  background: #fef3c7;
  color: #92400e;
}

.badge--header {
  background: #dcfce7;
  color: #166534;
}

/* ── 配置管理 ── */
.config-loading {
  padding: 20px;
  color: #64748b;
  font-size: 13px;
  text-align: center;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-section {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  margin: 0 0 16px 0;
  background: #fff;
}

.config-section legend {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  padding: 0 8px;
}

.config-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.config-row--inline {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.config-row--inline .config-label {
  margin-bottom: 0;
  flex-shrink: 0;
}

.config-row--check {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.config-row--check .config-label {
  margin-bottom: 0;
}

.config-label {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.config-hint {
  font-weight: 400;
  color: #94a3b8;
  font-size: 11px;
}

.config-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #2563eb;
}

.form-input--short {
  width: 160px;
  max-width: 160px;
}

.config-save-msg {
  margin: 0;
  font-size: 13px;
  color: #059669;
}

/* ── 文件上传 ── */
.upload-section {
  margin-bottom: 16px;
}

.upload-section.mode-disabled {
  opacity: 0.45;
  pointer-events: none;
}

.drop-hint.muted {
  color: #94a3b8;
  font-style: italic;
}

.drop-zone {
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  padding: 24px;
  text-align: center;
  transition: all 0.2s;
}

.drop-zone--over {
  border-color: #2563eb;
  background: #eff6ff;
}

.drop-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: #94a3b8;
}

.file-select-btn {
  display: inline-block;
  padding: 6px 16px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s;
}
.file-select-btn:hover {
  background: #f1f5f9;
  color: #2563eb;
}

.file-input-hidden {
  display: none;
}

.upload-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.upload-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 4px;
  font-size: 12px;
  background: #eff6ff;
}

.upload-name {
  flex: 1;
  font-family: monospace;
  font-size: 12px;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-size {
  flex-shrink: 0;
  font-size: 11px;
  color: #64748b;
}

.upload-remove {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 4px;
  background: none;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.upload-remove:hover {
  background: #fee2e2;
  color: #dc2626;
}

.upload-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}
</style>

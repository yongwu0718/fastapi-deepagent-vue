<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { load as yamlLoad, dump as yamlDump } from 'js-yaml'

const props = defineProps<{
  load: () => Promise<string>
  save: (content: string) => Promise<void>
}>()

// ── 可选厂商列表 ──
const PROVIDER_OPTIONS = [
  { key: 'deepseek', label: 'DeepSeek', icon: '🤖' },
  { key: 'ali', label: 'Aliyun', icon: '☁️' },
  { key: 'openai', label: 'OpenAI', icon: '🔷' },
  { key: 'ollama', label: 'Ollama', icon: '🦙' },
] as const

// ── 表单数据 ──
interface ProviderForm {
  base_url?: string
  model?: string
  // deepseek 专属
  json_model?: string
  reasoning_effort?: string
  extra_body?: string  // JSON 文本
  json_kwargs?: string  // JSON 文本
  // ollama 专属
  reasoning?: string
  // aliyun 专属
  enable_thinking?: boolean
  // moonshot 专属
  thinking?: boolean
  // embedding 专属（base_url + model 共用）
  // reranker 专属
  top_n?: number
}

const activeProvider = ref('deepseek')
const deepseek = ref<ProviderForm>({})
const ollama = ref<ProviderForm>({})
const aliyun = ref<ProviderForm>({})
const openai = ref<ProviderForm>({})
const moonshot = ref<ProviderForm>({})
const embedding = ref<ProviderForm>({})
const reranker = ref<ProviderForm>({})

const loading = ref(false)
const saving = ref(false)
const status = ref('')
const error = ref('')

// ── YAML ↔ Form ──
function yamlToForm(yamlStr: string) {
  let parsed: Record<string, any> = {}
  try {
    parsed = (yamlLoad(yamlStr) as Record<string, any>) ?? {}
  } catch {
    error.value = 'YAML 解析失败，请检查配置格式'
    return
  }

  // active_provider
  activeProvider.value = parsed.active_provider || 'deepseek'

  function pick(target: ProviderForm, source: Record<string, any>) {
    if (!source) return
    target.model = source.model ?? ''
    target.base_url = source.base_url ?? ''
  }

  // deepseek
  if (parsed.deepseek) {
    const d = parsed.deepseek
    deepseek.value = {
      base_url: d.base_url ?? '',
      model: d.model ?? '',
      json_model: d.json_model ?? '',
      reasoning_effort: d.reasoning_effort ?? '',
      extra_body: d.extra_body ? JSON.stringify(d.extra_body, null, 2) : '',
      json_kwargs: d.json_kwargs ? JSON.stringify(d.json_kwargs, null, 2) : '',
    }
  }
  // ollama
  if (parsed.ollama) {
    const o = parsed.ollama
    ollama.value = {
      base_url: o.base_url ?? '',
      model: o.model ?? '',
      reasoning: o.reasoning ?? '',
    }
  }
  // aliyun
  if (parsed.aliyun) {
    const a = parsed.aliyun
    aliyun.value = {
      base_url: a.base_url ?? '',
      model: a.model ?? '',
      enable_thinking: a.enable_thinking ?? false,
    }
  }
  // openai
  if (parsed.openai) {
    const o = parsed.openai
    openai.value = {
      base_url: o.base_url ?? '',
      model: o.model ?? '',
      extra_body: o.extra_body ? JSON.stringify(o.extra_body, null, 2) : '',
    }
  }
  // moonshot
  if (parsed.moonshot) {
    const m = parsed.moonshot
    moonshot.value = {
      model: m.model ?? '',
      thinking: m.thinking ?? false,
    }
  }
  // embedding
  if (parsed.embedding) {
    pick(embedding.value, parsed.embedding)
  }
  // reranker
  if (parsed.reranker) {
    const r = parsed.reranker
    reranker.value = {
      model: r.model ?? '',
      top_n: r.top_n ?? 10,
    }
  }
}

function formToYaml(): string {
  const obj: Record<string, any> = {}

  // active_provider
  obj.active_provider = activeProvider.value

  function clean(v: ProviderForm): Partial<ProviderForm> {
    const r: Partial<ProviderForm> = {}
    if (v.model) r.model = v.model
    if (v.base_url) r.base_url = v.base_url
    return r
  }

  // deepseek
  {
    const d = deepseek.value
    const entry: Record<string, any> = { ...clean(d) }
    if (d.json_model) entry.json_model = d.json_model
    if (d.reasoning_effort) entry.reasoning_effort = d.reasoning_effort
    if (d.extra_body?.trim()) {
      try { entry.extra_body = JSON.parse(d.extra_body) } catch {}
    }
    if (d.json_kwargs?.trim()) {
      try { entry.json_kwargs = JSON.parse(d.json_kwargs) } catch {}
    }
    obj.deepseek = entry
  }
  // ollama
  {
    const o = ollama.value
    const entry: Record<string, any> = { ...clean(o) }
    if (o.reasoning) entry.reasoning = o.reasoning
    obj.ollama = entry
  }
  // aliyun
  {
    const a = aliyun.value
    obj.aliyun = { ...clean(a), enable_thinking: a.enable_thinking || undefined }
  }
  // openai
  {
    const o = openai.value
    const entry: Record<string, any> = { ...clean(o) }
    if (o.extra_body?.trim()) {
      try { entry.extra_body = JSON.parse(o.extra_body) } catch {}
    }
    obj.openai = entry
  }
  // moonshot
  {
    const m = moonshot.value
    obj.moonshot = { model: m.model || undefined, thinking: m.thinking || undefined }
  }
  // embedding
  { obj.embedding = clean(embedding.value) }
  // reranker
  {
    const r = reranker.value
    obj.reranker = { model: r.model || undefined, top_n: r.top_n || undefined }
  }

  try {
    return yamlDump(obj, { indent: 2, lineWidth: -1, noRefs: true })
  } catch {
    status.value = 'YAML 序列化失败'
    return ''
  }
}

// ── 生命週期 ──
onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    const raw = await props.load()
    yamlToForm(raw)
  } catch (e: any) {
    error.value = '加载失败: ' + (e?.body?.detail ?? String(e))
  } finally {
    loading.value = false
  }
})

async function handleSave() {
  saving.value = true
  status.value = ''
  try {
    const yamlStr = formToYaml()
    await props.save(yamlStr)
    status.value = '已保存 ✓'
    setTimeout(() => (status.value = ''), 3000)
  } catch (e: any) {
    status.value = '保存失败: ' + (e?.body?.detail ?? String(e))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="model-config-form">
    <!-- 顶栏 -->
    <div class="form-toolbar">
      <span class="form-title">model_config.yaml</span>
      <div class="toolbar-right">
        <span v-if="status" class="form-status">{{ status }}</span>
        <button class="save-btn" :disabled="saving || loading" @click="handleSave">
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <!-- 加载 / 错误 -->
    <div v-if="loading" class="form-loading">加载中...</div>
    <div v-else-if="error" class="form-error">{{ error }}</div>

    <!-- 表单主体 -->
    <div v-else class="form-body">
      <!-- ── 当前激活模型厂商 ── -->
      <fieldset class="provider-section provider-section--active">
        <legend>🔋 当前激活厂商</legend>
        <p class="active-hint">选择后点击「保存」，再点击顶部「保存并重建」即可热生效。</p>
        <div class="active-radios">
          <label
            v-for="opt in PROVIDER_OPTIONS"
            :key="opt.key"
            class="active-radio-card"
            :class="{ checked: activeProvider === opt.key }"
          >
            <input
              v-model="activeProvider"
              type="radio"
              :value="opt.key"
              class="sr-only"
            />
            <span class="radio-icon">{{ opt.icon }}</span>
            <span class="radio-label">{{ opt.label }}</span>
          </label>
        </div>
      </fieldset>

      <!-- DeepSeek -->
      <fieldset class="provider-section">
        <legend>🤖 DeepSeek</legend>
        <div class="form-grid">
          <div class="field">
            <label>服务地址</label>
            <input v-model="deepseek.base_url" class="ff-input" placeholder="https://api.deepseek.com" />
          </div>
          <div class="field">
            <label>默认模型</label>
            <input v-model="deepseek.model" class="ff-input" placeholder="deepseek-v4-flash" />
          </div>
          <div class="field">
            <label>JSON 模型</label>
            <input v-model="deepseek.json_model" class="ff-input" placeholder="deepseek-v4-pro" />
          </div>
          <div class="field">
            <label>推理强度</label>
            <select v-model="deepseek.reasoning_effort" class="ff-input">
              <option value="">默认</option>
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="max">max</option>
            </select>
          </div>
        </div>
        <div class="field field--json">
          <label>extra_body (JSON)</label>
          <textarea v-model="deepseek.extra_body" class="ff-textarea" rows="4" spellcheck="false" placeholder='{"thinking": {"type": "enabled"}}' />
        </div>
        <div class="field field--json">
          <label>json_kwargs (JSON)</label>
          <textarea v-model="deepseek.json_kwargs" class="ff-textarea" rows="4" spellcheck="false" placeholder='{"response_format": {"type": "json_object"}}' />
        </div>
      </fieldset>

      <!-- Ollama -->
      <fieldset class="provider-section">
        <legend>🦙 Ollama</legend>
        <div class="form-grid">
          <div class="field">
            <label>服务地址</label>
            <input v-model="ollama.base_url" class="ff-input" placeholder="http://localhost:11434" />
          </div>
          <div class="field">
            <label>模型</label>
            <input v-model="ollama.model" class="ff-input" placeholder="qwen3.5" />
          </div>
          <div class="field">
            <label>推理级别</label>
            <select v-model="ollama.reasoning" class="ff-input">
              <option value="">默认</option>
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
            </select>
          </div>
        </div>
      </fieldset>

      <!-- Aliyun -->
      <fieldset class="provider-section">
        <legend>☁️ Aliyun (DashScope)</legend>
        <div class="form-grid">
          <div class="field">
            <label>服务地址</label>
            <input v-model="aliyun.base_url" class="ff-input" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
          </div>
          <div class="field">
            <label>模型</label>
            <input v-model="aliyun.model" class="ff-input" placeholder="qwen3.6-flash-2026-04-16" />
          </div>
          <div class="field field--check">
            <label>启用 thinking</label>
            <input v-model="aliyun.enable_thinking" type="checkbox" class="ff-checkbox" />
          </div>
        </div>
      </fieldset>

      <!-- OpenAI -->
      <fieldset class="provider-section">
        <legend>🔷 OpenAI Compatible</legend>
        <div class="form-grid">
          <div class="field">
            <label>服务地址</label>
            <input v-model="openai.base_url" class="ff-input" placeholder="https://api.openai.com/v1" />
          </div>
          <div class="field">
            <label>模型</label>
            <input v-model="openai.model" class="ff-input" placeholder="gpt-4.1" />
          </div>
        </div>
        <div class="field field--json">
          <label>extra_body (JSON)</label>
          <textarea v-model="openai.extra_body" class="ff-textarea" rows="3" spellcheck="false" placeholder='{"thinking": {"type": "enabled"}}' />
        </div>
      </fieldset>

      <!-- Moonshot -->
      <fieldset class="provider-section">
        <legend>🚀 Moonshot</legend>
        <div class="form-grid">
          <div class="field">
            <label>模型</label>
            <input v-model="moonshot.model" class="ff-input" placeholder="kimi-k2.5" />
          </div>
          <div class="field field--check">
            <label>thinking</label>
            <input v-model="moonshot.thinking" type="checkbox" class="ff-checkbox" />
          </div>
        </div>
      </fieldset>

      <!-- Embedding -->
      <fieldset class="provider-section">
        <legend>🔤 嵌入模型</legend>
        <div class="form-grid">
          <div class="field">
            <label>模型</label>
            <input v-model="embedding.model" class="ff-input" placeholder="my-qwen3-embed:latest" />
          </div>
          <div class="field">
            <label>服务地址</label>
            <input v-model="embedding.base_url" class="ff-input" placeholder="http://localhost:11434" />
          </div>
        </div>
      </fieldset>

      <!-- Reranker -->
      <fieldset class="provider-section">
        <legend>📊 Reranker</legend>
        <div class="form-grid">
          <div class="field">
            <label>模型</label>
            <input v-model="reranker.model" class="ff-input" placeholder="gte-rerank-v2" />
          </div>
          <div class="field">
            <label>Top N</label>
            <input v-model.number="reranker.top_n" type="number" min="1" max="100" class="ff-input ff-input--short" />
          </div>
        </div>
      </fieldset>
    </div>
  </div>
</template>

<style scoped>
.model-config-form {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

/* ── 顶栏 ── */
.form-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.form-title {
  font-size: 13px;
  color: #64748b;
  font-family: monospace;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.form-status {
  font-size: 12px;
  color: #059669;
}

.save-btn {
  padding: 5px 16px;
  border: none;
  border-radius: 5px;
  background: #16a34a;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-loading,
.form-error {
  padding: 40px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}
.form-error {
  color: #dc2626;
}

/* ── 表单主体 ── */
.form-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.provider-section {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  margin: 0 0 16px 0;
  background: #fff;
}

.provider-section--active {
  border-color: #2563eb;
  background: #f8faff;
}

.provider-section--active legend {
  color: #2563eb;
}

.provider-section legend {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  padding: 0 8px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field label {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}

.field--json {
  margin-top: 12px;
}

.field--check {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ff-input {
  padding: 7px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 5px;
  font-size: 13px;
  font-family: inherit;
  color: #1e293b;
  background: #fff;
  transition: border-color 0.15s;
  box-sizing: border-box;
}
.ff-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.ff-input--short {
  width: 100px;
}

.ff-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #2563eb;
}

.ff-textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 5px;
  font-size: 12px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  color: #1e293b;
  background: #f8fafc;
  resize: vertical;
  box-sizing: border-box;
}
.ff-textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

/* ── 激活厂商选择 ── */
.active-hint {
  font-size: 12px;
  color: #64748b;
  margin: 0 0 12px 0;
}

.active-radios {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.active-radio-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
  user-select: none;
}
.active-radio-card:hover {
  border-color: #93c5fd;
  background: #eff6ff;
}
.active-radio-card.checked {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.radio-icon {
  font-size: 18px;
}

.radio-label {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>

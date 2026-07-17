<script setup lang="ts">
import { ref, watch, computed, toRef } from 'vue'
import type { FileEntry } from '@/api/files'
import { useMarkdownRenderer } from '../rendering/useMarkdownRenderer'
import { getFileManager } from '../useFileManager'

const props = defineProps<{
  entry: FileEntry
  content: string
  contentType: string
  fileUrl: string
  loading: boolean
}>()

const emit = defineEmits<{
  save: [content: string]
}>()

const editedContent = ref('')

// .md 文件编辑/预览切换，默认预览
const isEditing = ref(false)
const copied = ref(false)

watch(
  () => props.content,
  (val) => {
    editedContent.value = val ?? ''
  },
  { immediate: true },
)

// 切换文件时重置编辑模式
watch(
  () => props.entry.path,
  () => { isEditing.value = false },
)

function handleSave() {
  emit('save', editedContent.value)
  // .md 文件保存后自动切回预览
  if (isMarkdown.value) {
    isEditing.value = false
  }
}

async function handleCopy() {
  try {
    await navigator.clipboard.writeText(props.content)
  } catch {
    // 降级
    const ta = document.createElement('textarea')
    ta.value = props.content
    ta.style.position = 'fixed'; ta.style.opacity = '0'
    document.body.appendChild(ta); ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

// 判断文件是否可文本编辑
function isTextEditable(): boolean {
  if (props.entry.editable) return true
  const ext = props.entry.name.split('.').pop()?.toLowerCase()
  const textExts = ['txt', 'md', 'json', 'xml', 'yml', 'yaml', 'toml', 'ini', 'cfg', 'csv', 'tsv', 'log', 'html', 'css', 'js', 'ts', 'py', 'java', 'go', 'rs', 'c', 'cpp', 'h', 'sh', 'bat', 'ps1', 'env', 'gitignore', 'editorconfig', 'vue', 'jsx', 'tsx']
  return !!(ext && textExts.includes(ext))
}

// 是否为 Markdown 文件
const isMarkdown = computed(() =>
  props.entry.name.toLowerCase().endsWith('.md'),
)

// Markdown 渲染
const contentRef = toRef(props, 'content')
const { renderedHtml, outline } = useMarkdownRenderer(contentRef, isMarkdown)

// ── Mermaid 缩放 & 平移 ──
const mermaidZoom = ref(140)
const isPanMode = ref(false)
const isDragging = ref(false)
const panOffset = ref({ x: 0, y: 0 })
const dragStart = ref({ x: 0, y: 0 })
const panStart = ref({ x: 0, y: 0 })

const mermaidStyle = computed(() => ({
  '--mermaid-scale': String(mermaidZoom.value / 100),
  '--mermaid-tx': `${panOffset.value.x}px`,
  '--mermaid-ty': `${panOffset.value.y}px`,
}))

const hasMermaid = computed(() => renderedHtml.value.includes('mermaid-container'))

function zoomIn() { mermaidZoom.value = Math.min(300, mermaidZoom.value + 10) }
function zoomOut() { mermaidZoom.value = Math.max(30, mermaidZoom.value - 10) }
function onZoomInput(e: Event) { mermaidZoom.value = Number((e.target as HTMLInputElement).value) }
function resetZoom() {
  mermaidZoom.value = 140
  panOffset.value = { x: 0, y: 0 }
}
function togglePanMode() {
  isPanMode.value = !isPanMode.value
  if (!isPanMode.value) { panOffset.value = { x: 0, y: 0 }; isDragging.value = false }
}

function onMermaidMouseDown(e: MouseEvent) {
  if (!isPanMode.value) return
  const target = e.target as HTMLElement
  if (!target.closest('.mermaid-container')) return
  isDragging.value = true
  dragStart.value = { x: e.clientX, y: e.clientY }
  panStart.value = { ...panOffset.value }
  e.preventDefault()
}
function onMermaidMouseMove(e: MouseEvent) {
  if (!isDragging.value) return
  panOffset.value = {
    x: panStart.value.x + (e.clientX - dragStart.value.x),
    y: panStart.value.y + (e.clientY - dragStart.value.y),
  }
}
function onMermaidMouseUp() { isDragging.value = false }

// 切换文件时重置
watch(() => props.entry.path, () => {
  mermaidZoom.value = 140
  panOffset.value = { x: 0, y: 0 }
  isPanMode.value = false
  isDragging.value = false
})

// ── 大纲面板（由 FileBrowser 通过 previewRef 控制） ──
const showOutline = ref(false)

// 切换文件时关闭大纲
watch(() => props.entry.path, () => { showOutline.value = false })

// 内容类型判断
const isPdf = computed(() => props.contentType === 'pdf')
const isImage = computed(() => props.contentType === 'image')
const isBinary = computed(() => props.contentType === 'binary' && !isPdf.value && !isImage.value)
const isText = computed(() => props.contentType === 'text' || props.contentType === '')

// 文件下载
function handleDownload() {
  if (!props.fileUrl) return
  const a = document.createElement('a')
  a.href = props.fileUrl
  a.download = props.entry.name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// ── 内部 .md 链接跳转 + 代码块/mermaid 复制（事件委托） ──
function onMarkdownClick(e: MouseEvent) {
  // mermaid 源码复制
  const mermaidBtn = (e.target as HTMLElement).closest('.mermaid-copy-btn')
  if (mermaidBtn) {
    const source = mermaidBtn.parentElement?.querySelector('.mermaid-source')?.textContent
    if (source) {
      navigator.clipboard.writeText(source).then(() => {
        mermaidBtn.textContent = '已复制'
        mermaidBtn.classList.add('copied')
        setTimeout(() => { mermaidBtn.textContent = '源码'; mermaidBtn.classList.remove('copied') }, 2000)
      }).catch(() => {})
    }
    return
  }
  // 代码块复制按钮
  const copyBtn = (e.target as HTMLElement).closest('.code-copy-btn')
  if (copyBtn) {
    const wrapper = copyBtn.closest('.code-block-wrapper')
    const code = wrapper?.querySelector('code')?.textContent
    if (code) {
      navigator.clipboard.writeText(code).then(() => {
        copyBtn.textContent = '已复制'
        copyBtn.classList.add('copied')
        setTimeout(() => {
          copyBtn.textContent = '复制'
          copyBtn.classList.remove('copied')
        }, 2000)
      }).catch(() => {})
    }
    return
  }
  // .md 链接跳转
  const anchor = (e.target as HTMLElement).closest('a')
  if (!anchor) return
  const rawHref = anchor.getAttribute('href')
  if (!rawHref || /^(https?:)?\/\//.test(rawHref) || !rawHref.endsWith('.md')) return
  e.preventDefault()
  e.stopPropagation()
  // 移除 target 属性，避免浏览器尝试打开新标签页
  anchor.removeAttribute('target')

  // DOMPurify 会把中文 href 编码成 %XX 格式，先解码回来
  let href = rawHref
  try {
    href = decodeURIComponent(rawHref)
  } catch {
    // 不是合法的百分号编码，保持原样
  }

  console.log('[FilePreview] .md 链接点击', { rawHref, decoded: href, currentFilePath: props.entry.path })

  // 规范化 path：解析 ./ 和 ../ 前缀
  const currentDir = props.entry.path.includes('/')
    ? props.entry.path.substring(0, props.entry.path.lastIndexOf('/'))
    : ''
  const segments = currentDir ? currentDir.split('/').filter(Boolean) : []

  // 去掉开头的 ./
  let normalized = href
  while (normalized.startsWith('./')) {
    normalized = normalized.substring(2)
  }

  // 逐个处理路径段
  for (const part of normalized.split('/')) {
    if (part === '..') {
      segments.pop()
    } else if (part !== '.') {
      segments.push(part)
    }
  }
  const resolved = segments.join('/')
  console.log('[FilePreview] 解析后的路径', { href, normalized, currentDir, resolved })

  getFileManager().selectEntry({
    name: resolved.split('/').pop() ?? resolved,
    path: resolved,
    type: 'file',
    size: 0,
    modified: '',
  })
}

function toggleEdit() {
  isEditing.value = !isEditing.value
}

defineExpose({
  isEditing,
  isMarkdown,
  isTextEditable,
  isText,
  isBinary,
  isPdf,
  isImage,
  handleSave,
  handleCopy,
  handleDownload,
  copied,
  toggleEdit,
  outline,
  showOutline,
})
</script>

<template>
  <div class="file-preview">
<!-- 内容区：加载中 -->
    <div class="fp-body" v-if="loading">
      <span class="fp-loading">加载中...</span>
    </div>

    <!-- 内容区：Markdown 文件（可编辑，默认预览） -->
    <div class="fp-body fp-body--md" v-else-if="isMarkdown && isTextEditable() && isText">
      <textarea
        v-if="isEditing"
        v-model="editedContent"
        class="fp-editor"
        spellcheck="false"
        placeholder="文件内容..."
      />
      <div
        v-else
        class="fp-md-wrapper"
        :class="{ 'pan-mode': isPanMode, 'is-dragging': isDragging }"
        :style="mermaidStyle"
        @mousedown="onMermaidMouseDown"
        @mousemove="onMermaidMouseMove"
        @mouseup="onMermaidMouseUp"
        @mouseleave="onMermaidMouseUp"
      >
        <div class="fp-markdown" v-html="renderedHtml" @click.capture="onMarkdownClick" />
      </div>
    </div>

    <!-- 内容区：文本编辑 -->
    <div class="fp-body" v-else-if="isTextEditable() && isText">
      <textarea
        v-model="editedContent"
        class="fp-editor"
        spellcheck="false"
        placeholder="文件内容..."
      />
    </div>

    <!-- 内容区：Markdown 渲染（只读） -->
    <div class="fp-body fp-body--md" v-else-if="isText && isMarkdown">
      <div
        class="fp-md-wrapper"
        :class="{ 'pan-mode': isPanMode, 'is-dragging': isDragging }"
        :style="mermaidStyle"
        @mousedown="onMermaidMouseDown"
        @mousemove="onMermaidMouseMove"
        @mouseup="onMermaidMouseUp"
        @mouseleave="onMermaidMouseUp"
      >
        <div class="fp-markdown" v-html="renderedHtml" @click.capture="onMarkdownClick" />
      </div>
    </div>


    <!-- 内容区：只读文本 -->
    <div class="fp-body" v-else-if="isText">
      <pre class="fp-viewer">{{ content }}</pre>
    </div>

    <!-- 内容区：PDF 预览 -->
    <div class="fp-body fp-body--iframe" v-else-if="isPdf && fileUrl">
      <iframe
        :src="fileUrl"
        class="fp-iframe"
        title="PDF 预览"
      />
    </div>

    <!-- 内容区：图片预览 -->
    <div class="fp-body fp-body--image" v-else-if="isImage && fileUrl">
      <img
        :src="fileUrl"
        :alt="entry.name"
        class="fp-image"
      />
    </div>

    <!-- 内容区：通用二进制文件 -->
    <div class="fp-body" v-else-if="isBinary">
      <div class="fp-binary-hint">
        <svg class="fp-binary-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
          <polyline points="13 2 13 9 20 9"/>
        </svg>
        <p class="fp-binary-name">{{ entry.name }}</p>
        <p class="fp-binary-desc">二进制文件，不支持在线预览</p>
        <button
          class="fp-binary-download"
          @click="handleDownload"
          :disabled="!fileUrl"
        >
          下载文件
        </button>
      </div>
    </div>

    <!-- 内容区：未知/错误 -->
    <div class="fp-body" v-else>
      <div class="fp-binary-hint">
        <p class="fp-binary-desc">文件内容为空或不支持预览</p>
      </div>
    </div>

    <!-- Mermaid 工具栏 -->
    <div v-if="hasMermaid" class="fp-mermaid-toolbar">
      <button class="fp-mt-btn" @click="zoomOut" title="缩小">−</button>
      <input
        type="range"
        class="fp-mt-slider"
        :min="30"
        :max="300"
        :value="mermaidZoom"
        @input="onZoomInput"
        title="缩放"
      />
      <button class="fp-mt-btn" @click="zoomIn" title="放大">+</button>
      <span class="fp-mt-pct" @click="resetZoom" title="点击重置">{{ mermaidZoom }}%</span>
      <button
        class="fp-mt-btn fp-mt-pan"
        :class="{ active: isPanMode }"
        @click="togglePanMode"
        :title="isPanMode ? '退出拖拽' : '拖拽平移'"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 11V7a2 2 0 0 0-4 0v3"/>
          <path d="M14 10V5a2 2 0 0 0-4 0v5"/>
          <path d="M10 10V3a2 2 0 0 0-4 0v10"/>
          <path d="M6 13v5a3 3 0 0 0 6 0v-4"/>
          <path d="M12 14h5a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-3"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.file-preview {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  /* 用 flex: 1 替代 height: 100%，避免父级无显式高度时百分比失效 */
}



.fp-body {
  flex: 1;
  overflow: auto;
  position: relative;
}

.fp-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 13px;
  color: var(--text-m, #9b8eaa);
}

.fp-editor {
  width: 100%;
  height: 100%;
  border: none;
  padding: 20px 28px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-h, #08060d);
  background: var(--bg, #fff);
  resize: none;
  outline: none;
  tab-size: 2;
}

.fp-viewer {
  margin: 0;
  padding: 20px 28px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text, #6b6375);
  white-space: pre-wrap;
  word-break: break-all;
}

/* ── PDF 预览 ── */
.fp-body--iframe {
  background: #525659;
}

.fp-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

/* ── 图片预览 ── */
.fp-body--image {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-hover, #f5f3f7);
}

.fp-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

/* ── 二进制文件提示 ── */
.fp-binary-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 8px;
  padding: 24px;
  text-align: center;
}

.fp-binary-icon {
  color: var(--text-m, #9b8eaa);
  opacity: 0.5;
}

.fp-binary-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-h, #08060d);
  word-break: break-all;
}

.fp-binary-desc {
  font-size: 12px;
  color: var(--text-m, #9b8eaa);
}

.fp-binary-download {
  margin-top: 8px;
  padding: 6px 20px;
  border: 1px solid var(--accent, #aa3bff);
  border-radius: 6px;
  background: var(--accent, #aa3bff);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.12s;
}

.fp-binary-download:hover {
  background: var(--accent-hover, #9333ea);
}

.fp-binary-download:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Mermaid 工具栏 ── */
.fp-mermaid-toolbar {
  position: absolute;
  bottom: 8px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: var(--bg, #fff);
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 10;
  user-select: none;
}
.fp-mt-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 4px;
  background: var(--bg, #fff);
  color: var(--text, #6b6375);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.12s;
}
.fp-mt-btn:hover {
  background: var(--bg-hover, #f5f3f7);
  color: var(--text-h, #08060d);
}
.fp-mt-pan.active {
  background: var(--accent, #aa3bff);
  color: #fff;
  border-color: var(--accent, #aa3bff);
}
.fp-mt-slider {
  width: 64px;
  height: 4px;
  accent-color: var(--accent, #aa3bff);
  cursor: pointer;
}
.fp-mt-pct {
  font-size: 11px;
  color: var(--text-m, #9b8eaa);
  min-width: 36px;
  text-align: center;
  cursor: pointer;
  transition: color 0.12s;
}
.fp-mt-pct:hover { color: var(--text-h, #08060d); }

/* ── Markdown 预览包裹层 ── */
.fp-md-wrapper {
  flex: 1;
  overflow: auto;
  position: relative;
}
</style>

<!-- Markdown 预览全局样式（v-html 不继承 scoped） -->
<style>
.fp-markdown {
  line-height: 1.7;
  word-break: break-word;
  color: var(--text, #6b6375);
  padding: 20px 28px;
}
.fp-markdown p { margin: 0 0 10px; }
.fp-markdown p:last-child { margin-bottom: 0; }
.fp-markdown h1,.fp-markdown h2,.fp-markdown h3,.fp-markdown h4,.fp-markdown h5,.fp-markdown h6 {
  margin: 16px 0 8px; font-weight: 600; color: var(--text-h, #08060d); line-height: 1.35;
}
.fp-markdown h1:first-child,.fp-markdown h2:first-child,.fp-markdown h3:first-child,.fp-markdown h4:first-child { margin-top: 0; }
.fp-markdown h1 { font-size: 1.35em; padding-bottom: 6px; border-bottom: 1px solid var(--border, #e5e4e7); }
.fp-markdown h2 { font-size: 1.2em; }
.fp-markdown h3 { font-size: 1.1em; }
.fp-markdown h4 { font-size: 1.05em; }
.fp-markdown pre {
  margin: 10px 0; padding: 12px 14px; border-radius: 8px; background: var(--code-bg, #f4f3ec); overflow-x: auto; font-size: 13px; line-height: 1.5;
}
.fp-markdown pre code { background: none; padding: 0; color: var(--text-h, #08060d); font-family: var(--mono, ui-monospace, Consolas, monospace); }
.fp-markdown code {
  padding: 2px 6px; border-radius: 4px; font-size: 0.9em; font-family: var(--mono, ui-monospace, Consolas, monospace);
  background: var(--code-bg, #f4f3ec); color: var(--text-h, #08060d);
}
.fp-markdown ul,.fp-markdown ol { margin: 6px 0; padding-left: 22px; }
.fp-markdown li { margin: 3px 0; }
.fp-markdown blockquote {
  margin: 10px 0; padding: 8px 14px; border-left: 3px solid var(--accent, #aa3bff);
  background: rgba(170, 59, 255, 0.06); border-radius: 0 6px 6px 0;
}
.fp-markdown table { margin: 10px 0; border-collapse: collapse; width: 100%; font-size: 13px; }
.fp-markdown th,.fp-markdown td { padding: 8px 12px; border: 1px solid var(--border, #e5e4e7); text-align: left; }
.fp-markdown th { background: var(--code-bg, #f4f3ec); font-weight: 600; color: var(--text-h, #08060d); }
.fp-markdown hr { margin: 16px 0; border: none; border-top: 1px solid var(--border, #e5e4e7); }
.fp-markdown a { color: var(--accent, #aa3bff); text-decoration: underline; }
.fp-markdown img { max-width: 100%; border-radius: 8px; }
.fp-markdown del { opacity: 0.6; }
.fp-markdown strong { color: var(--text-h, #08060d); }
.fp-markdown input[type="checkbox"] { margin-right: 6px; accent-color: var(--accent, #aa3bff); }

/* ── Mermaid 图表 ── */
.fp-markdown .mermaid-container {
  display: flex;
  justify-content: center;
  margin: 12px 0;
  overflow: visible;
}
.fp-markdown .mermaid-container svg {
  max-width: 100%;
  height: auto;
  transform: translate(var(--mermaid-tx, 0px), var(--mermaid-ty, 0px)) scale(var(--mermaid-scale, 1.4));
  transform-origin: top center;
  transition: transform 0.08s ease-out;
}
/* 平移模式光标 */
.fp-md-wrapper.pan-mode .mermaid-container svg {
  cursor: grab;
}
.fp-md-wrapper.pan-mode.is-dragging .mermaid-container svg {
  cursor: grabbing;
}
.fp-markdown .mermaid-error {
  margin: 10px 0;
  padding: 12px 14px;
  border-radius: 8px;
  background: #fff0f0;
  border: 1px solid #fcc;
  color: #c33;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ── 代码块复制 ── */
.fp-markdown .code-block-wrapper {
  position: relative;
  margin: 10px 0;
}
.fp-markdown .code-block-wrapper pre {
  margin: 0;
}
.fp-markdown .code-copy-btn {
  position: absolute;
  top: 6px;
  right: 8px;
  padding: 3px 10px;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 4px;
  background: var(--bg, #fff);
  color: var(--text-m, #9b8eaa);
  font-size: 11px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.15s;
}
.fp-markdown .code-block-wrapper:hover .code-copy-btn {
  opacity: 1;
}
.fp-markdown .code-copy-btn:hover {
  background: var(--code-bg, #f4f3ec);
  color: var(--text-h, #08060d);
  border-color: var(--accent, #aa3bff);
}
.fp-markdown .code-copy-btn.copied {
  opacity: 1;
  color: #16a34a;
  border-color: #16a34a;
  background: rgba(22, 163, 74, 0.08);
}

/* ── Mermaid 源码复制 ── */
.fp-markdown .mermaid-copy-btn {
  position: absolute;
  top: 6px;
  right: 8px;
  padding: 3px 10px;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 4px;
  background: var(--bg, #fff);
  color: var(--text-m, #9b8eaa);
  font-size: 11px;
  cursor: pointer;
  z-index: 1;
  opacity: 0;
  transition: all 0.15s;
}
.fp-markdown .mermaid-container:hover .mermaid-copy-btn {
  opacity: 1;
}
.fp-markdown .mermaid-copy-btn:hover {
  background: var(--code-bg, #f4f3ec);
  color: var(--text-h, #08060d);
  border-color: var(--accent, #aa3bff);
}
.fp-markdown .mermaid-copy-btn.copied {
  opacity: 1;
  color: #16a34a;
  border-color: #16a34a;
  background: rgba(22, 163, 74, 0.08);
}
</style>

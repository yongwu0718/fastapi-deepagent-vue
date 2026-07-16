<script setup lang="ts">
import { ref, watch, computed, toRef, onBeforeUnmount } from 'vue'
import type { FileEntry } from '@/api/files'
import { useMarkdownRenderer } from './useMarkdownRenderer'
import { getFileManager } from './useFileManager'

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

// 组件卸载时释放 blob URL
onBeforeUnmount(() => {
  if (props.fileUrl && props.fileUrl.startsWith('blob:')) {
    URL.revokeObjectURL(props.fileUrl)
  }
})

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
const { renderedHtml } = useMarkdownRenderer(contentRef, isMarkdown)

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

// ── 内部 .md 链接跳转（点击后在文件浏览器中打开） ──
function onMarkdownClick(e: MouseEvent) {
  const anchor = (e.target as HTMLElement).closest('a')
  if (!anchor) return
  const href = anchor.getAttribute('href')
  // 只处理相对路径的 .md 链接，外部 URL 交给 target="_blank"
  if (!href || /^(https?:)?\/\//.test(href) || !href.endsWith('.md')) return
  e.preventDefault()
  // 基于当前文件目录解析相对路径
  const currentDir = props.entry.path.includes('/')
    ? props.entry.path.substring(0, props.entry.path.lastIndexOf('/'))
    : ''
  const resolved = currentDir ? `${currentDir}/${href}` : href
  getFileManager().selectEntry({
    name: href.split('/').pop() ?? href,
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
})
</script>

<template>
  <div class="file-preview">
<!-- 内容区：加载中 -->
    <div class="fp-body" v-if="loading">
      <span class="fp-loading">加载中...</span>
    </div>

    <!-- 内容区：Markdown 文件（可编辑，默认预览） -->
    <div class="fp-body" v-else-if="isMarkdown && isTextEditable() && isText">
      <textarea
        v-if="isEditing"
        v-model="editedContent"
        class="fp-editor"
        spellcheck="false"
        placeholder="文件内容..."
      />
      <div v-else class="fp-markdown" v-html="renderedHtml" @click="onMarkdownClick" />
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
    <div class="fp-body" v-else-if="isText && isMarkdown">
      <div class="fp-markdown" v-html="renderedHtml" @click="onMarkdownClick" />
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
  margin: 10px 0; padding: 12px 14px; border-radius: 8px; background: #1e1e2e; overflow-x: auto; font-size: 13px; line-height: 1.5;
}
.fp-markdown pre code { background: none; padding: 0; color: #cdd6f4; font-family: var(--mono, ui-monospace, Consolas, monospace); }
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
</style>

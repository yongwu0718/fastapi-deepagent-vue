<script setup lang="ts">
/**
 * Markdown 渲染组件
 * - 使用 marked 解析 Markdown → HTML
 * - 使用 DOMPurify 做 XSS 防护
 * - 启用 GFM（表格、删除线、任务列表等）
 * - 启用 breaks（单换行 → <br>）
 * - 支持 Mermaid 图表渲染
 */
import { ref, watch, useSlots } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import mermaid from 'mermaid'

// ── Mermaid 初始化 ──
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: {
    curve: 'step',
    rankSpacing: 100,
    nodeSpacing: 90,
    useMaxWidth: false,
  },
})

marked.setOptions({ gfm: true, breaks: true })

const slots = useSlots()

const props = defineProps<{
  /** 可选：代码块 ID 前缀，用于内容导航锚点。 */
  codeBlockIdSeed?: string
}>()

// ── 工具函数 ──
function escapeHtml(str: string): string {
  const map: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }
  return str.replace(/[&<>"']/g, (c) => map[c] || c)
}

function decodeHtmlEntities(str: string): string {
  return str
    .replace(/&gt;/g, '>')
    .replace(/&lt;/g, '<')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#039;/g, "'")
    .replace(/&#x27;/g, "'")
}

// ── Mermaid 渲染辅助 ──
let mermaidIdCounter = 0
const MERMAID_BLOCK_RE = /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/gi

function extractMermaidBlocks(html: string): { html: string; blocks: Array<{ id: string; code: string }> } {
  const blocks: Array<{ id: string; code: string }> = []
  const result = html.replace(MERMAID_BLOCK_RE, (_, code: string) => {
    const id = `mermaid-${++mermaidIdCounter}`
    blocks.push({ id, code: decodeHtmlEntities(code.trim()) })
    return `<div class="mermaid-container" data-mermaid-id="${id}"></div>`
  })
  return { html: result, blocks }
}

/** 给代码块包裹 .code-block-wrapper + 复制按钮 */
function addCodeCopyButtons(html: string): string {
  return html.replace(
    /<pre([^>]*)>([\s\S]*?)<\/pre>/g,
    (match, attrs, content) => {
      if (/class="[^"]*mermaid/.test(attrs) || /mermaid-container/.test(match)) return match
      return `<div class="code-block-wrapper"><pre${attrs}>${content}</pre><button class="code-copy-btn" title="复制代码">复制</button></div>`
    },
  )
}

// ── 复制按钮事件委托 ──
function onContentClick(e: MouseEvent) {
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
  const btn = (e.target as HTMLElement).closest('.code-copy-btn')
  if (!btn) return
  const wrapper = btn.closest('.code-block-wrapper')
  const code = wrapper?.querySelector('code')?.textContent
  if (!code) return
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = '已复制'
    btn.classList.add('copied')
    setTimeout(() => {
      btn.textContent = '复制'
      btn.classList.remove('copied')
    }, 2000)
  }).catch(() => {})
}

// ── 渲染逻辑 ──
const html = ref('')

function getSlotText(): string {
  const slot = slots.default?.()
  return slot
    ?.map((vnode) => (typeof vnode.children === 'string' ? vnode.children : ''))
    .join('') ?? ''
}

async function render() {
  const text = getSlotText()
  if (!text) { html.value = ''; return }
  try {
    const raw = marked.parse(text) as string
    const { html: placeholderHtml, blocks } = extractMermaidBlocks(raw)
    let clean = DOMPurify.sanitize(placeholderHtml)

    // 代码块锚点注入
    if (props.codeBlockIdSeed) {
      let idx = 0
      clean = clean.replace(/<pre>/g, () => `<pre id="${props.codeBlockIdSeed}-${idx++}">`)
    }

    // 异步渲染 mermaid
    if (blocks.length > 0) {
      let finalHtml = clean
      for (const block of blocks) {
        try {
          const { svg } = await mermaid.render(block.id, block.code)
          finalHtml = finalHtml.replace(
            `<div class="mermaid-container" data-mermaid-id="${block.id}"></div>`,
            `<div class="mermaid-container"><button class="mermaid-copy-btn" title="复制源码">源码</button>${svg}<pre style="display:none" class="mermaid-source">${escapeHtml(block.code)}</pre></div>`,
          )
        } catch (err) {
          console.error(`[Mermaid] 渲染失败 (${block.id})`, err)
          finalHtml = finalHtml.replace(
            `<div class="mermaid-container" data-mermaid-id="${block.id}"></div>`,
            `<pre class="mermaid-error">Mermaid 错误: ${escapeHtml((err as Error).message)}\n${escapeHtml(block.code.slice(0, 300))}</pre>`,
          )
        }
      }
      html.value = addCodeCopyButtons(finalHtml)
    } else {
      html.value = addCodeCopyButtons(clean)
    }
  } catch (err) {
    console.error('[Markdown] 渲染失败', err)
    html.value = `<pre style="color:red;">渲染错误: ${(err as Error).message}</pre>`
  }
}

// 监听 slot 内容变化（流式更新时触发）
watch(
  () => getSlotText(),
  () => { render() },
  { immediate: true },
)
</script>

<template>
  <div v-if="html" class="markdown-content" v-html="html" @click="onContentClick" />
</template>

<style>
/* ── 全局样式（非 scoped，因为 v-html 内容不继承 scoped） ── */

.markdown-content {
  line-height: 1.6;
  word-break: break-word;
}

/* 段落 */
.markdown-content p {
  margin: 0 0 8px;
}
.markdown-content p:last-child {
  margin-bottom: 0;
}

/* 标题 — 紧凑尺寸适配聊天气泡 */
.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
  margin: 12px 0 6px;
  font-weight: 600;
  color: var(--text-h, #08060d);
  line-height: 1.3;
}
.markdown-content h1:first-child,
.markdown-content h2:first-child,
.markdown-content h3:first-child,
.markdown-content h4:first-child {
  margin-top: 0;
}
.markdown-content h1 { font-size: 1.25em; }
.markdown-content h2 { font-size: 1.15em; }
.markdown-content h3 { font-size: 1.05em; }

/* 代码块 */
.markdown-content pre {
  margin: 8px 0;
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--code-bg, #f4f3ec);
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}
.markdown-content pre code {
  background: none;
  padding: 0;
  color: var(--text-h, #08060d);
  font-family: var(--mono, ui-monospace, Consolas, monospace);
}

/* 行内代码 */
.markdown-content code {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: var(--mono, ui-monospace, Consolas, monospace);
  background: var(--code-bg, #f4f3ec);
  color: var(--text-h, #08060d);
}

/* 列表 */
.markdown-content ul,
.markdown-content ol {
  margin: 4px 0;
  padding-left: 20px;
}
.markdown-content li {
  margin: 2px 0;
}

/* 引用 */
.markdown-content blockquote {
  margin: 8px 0;
  padding: 6px 14px;
  border-left: 3px solid var(--accent, #aa3bff);
  background: rgba(170, 59, 255, 0.06);
  border-radius: 0 6px 6px 0;
  color: var(--text, #6b6375);
}

/* 表格 */
.markdown-content table {
  margin: 8px 0;
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
}
.markdown-content th,
.markdown-content td {
  padding: 6px 10px;
  border: 1px solid var(--border, #e5e4e7);
  text-align: left;
}
.markdown-content th {
  background: var(--code-bg, #f4f3ec);
  font-weight: 600;
  color: var(--text-h, #08060d);
}
.markdown-content td {
  color: var(--text, #6b6375);
}

/* 分割线 */
.markdown-content hr {
  margin: 12px 0;
  border: none;
  border-top: 1px solid var(--border, #e5e4e7);
}

/* 链接 */
.markdown-content a {
  color: var(--accent, #aa3bff);
  text-decoration: underline;
}

/* 图片 */
.markdown-content img {
  max-width: 100%;
  border-radius: 8px;
}

/* 删除线 */
.markdown-content del {
  opacity: 0.6;
}

/* 强调 */
.markdown-content strong {
  color: var(--text-h, #08060d);
}

/* 任务列表 */
.markdown-content input[type="checkbox"] {
  margin-right: 6px;
  accent-color: var(--accent, #aa3bff);
}

/* ── Mermaid 图表 ── */
.markdown-content .mermaid-container {
  display: flex;
  justify-content: center;
  margin: 8px 0;
  overflow-x: auto;
}
.markdown-content .mermaid-container svg {
  max-width: 100%;
  height: auto;
}
.markdown-content .mermaid-error {
  margin: 8px 0;
  padding: 10px 14px;
  border-radius: 8px;
  background: #fff0f0;
  border: 1px solid #fcc;
  color: #c33;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ── 代码块复制 ── */
.markdown-content .code-block-wrapper {
  position: relative;
  margin: 8px 0;
}
.markdown-content .code-block-wrapper pre {
  margin: 0;
}
.markdown-content .code-copy-btn {
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
.markdown-content .code-block-wrapper:hover .code-copy-btn {
  opacity: 1;
}
.markdown-content .code-copy-btn:hover {
  background: var(--code-bg, #f4f3ec);
  color: var(--text-h, #08060d);
  border-color: var(--accent, #aa3bff);
}
.markdown-content .code-copy-btn.copied {
  opacity: 1;
  color: #16a34a;
  border-color: #16a34a;
  background: rgba(22, 163, 74, 0.08);
}

/* ── Mermaid 源码复制 ── */
.markdown-content .mermaid-container {
  position: relative;
}
.markdown-content .mermaid-copy-btn {
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
.markdown-content .mermaid-container:hover .mermaid-copy-btn {
  opacity: 1;
}
.markdown-content .mermaid-copy-btn:hover {
  background: var(--code-bg, #f4f3ec);
  color: var(--text-h, #08060d);
  border-color: var(--accent, #aa3bff);
}
.markdown-content .mermaid-copy-btn.copied {
  opacity: 1;
  color: #16a34a;
  border-color: #16a34a;
  background: rgba(22, 163, 74, 0.08);
}
</style>

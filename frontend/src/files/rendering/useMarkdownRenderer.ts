import { ref, watch, computed, type Ref } from 'vue'
import MarkdownIt from 'markdown-it'
import multimdTable from 'markdown-it-multimd-table'
import markdownItKatex from 'markdown-it-katex'
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

/** 大纲条目 */
export interface OutlineItem {
  level: number
  text: string
  id: string
}

// ── 工具函数 ──

/** 将标题文本转为 URL 安全的 slug */
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff]+/g, '-')
    .replace(/^-+|-+$/g, '')
    || 'heading'
}

/** 收集已用 slugs 并去重（追加 -1, -2...） */
function createUniqueSlug() {
  const used = new Map<string, number>()
  return (text: string): string => {
    const base = slugify(text)
    const count = used.get(base)
    if (count === undefined) {
      used.set(base, 1)
      return base
    }
    used.set(base, count + 1)
    return `${base}-${count}`
  }
}

/** 从原始 markdown 中提取标题大纲 */
function extractOutline(mdContent: string): OutlineItem[] {
  const getSlug = createUniqueSlug()
  const headingRe = /^(#{1,6})\s+(.+)$/gm
  const items: OutlineItem[] = []
  let match: RegExpExecArray | null
  while ((match = headingRe.exec(mdContent)) !== null) {
    const level = match[1].length
    const text = match[2].trim()
    const id = getSlug(text)
    items.push({ level, text, id })
  }
  return items
}

// ── markdown-it 单例 ──
const md = new MarkdownIt({
  html: true,
  breaks: true,
  linkify: true,
})
md.use(multimdTable, {
  multiline: true,
  rowspan: true,
  headerless: false,
})
md.use(markdownItKatex, { throwOnError: false, errorColor: '#cc0000', output: 'html' })

// ── 区分内/外链：外部链接加 target="_blank"，内部 .md 链接标记为文件内跳转 ──
const defaultLinkRender = md.renderer.rules.link_open ?? function (tokens, idx, options, _env, self) {
  return self.renderToken(tokens, idx, options)
}
md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  const token = tokens[idx]
  const href = token.attrGet('href') || ''
  if (/^https?:\/\//i.test(href)) {
    // 外部链接：新窗口打开
    token.attrSet('target', '_blank')
    token.attrSet('rel', 'noopener noreferrer')
  } else if (href.endsWith('.md')) {
    // 内部 .md 链接：由 FilePreview 点击事件处理，标记类名便于识别
    const existing = token.attrGet('class') || ''
    token.attrSet('class', (existing + ' md-internal-link').trim())
  }
  return defaultLinkRender(tokens, idx, options, env, self)
}

// ── 给标题注入 id 属性 ──
const defaultHeadingOpen = md.renderer.rules.heading_open ?? function (tokens, idx, options, _env, self) {
  return self.renderToken(tokens, idx, options)
}
md.renderer.rules.heading_open = function (tokens, idx, options, env, self) {
  const hToken = tokens[idx]
  // 下一个 token 是 inline（包含标题文本）
  const inlineToken = tokens[idx + 1]
  if (inlineToken && inlineToken.type === 'inline' && inlineToken.content) {
    const slugGen = (env as Record<string, unknown>)._headingSlugGen as ((t: string) => string) | undefined
    const getSlug = slugGen ?? createUniqueSlug()
    const id = getSlug(inlineToken.content)
    // 确保 env 中有 slug gen 供同一文档共享
    if (!slugGen && env) {
      ;(env as Record<string, unknown>)._headingSlugGen = getSlug
    }
    hToken.attrSet('id', id)
  }
  return defaultHeadingOpen(tokens, idx, options, env, self)
}

// ── 预处理函数 ──

const TABLE_ROW_RE = /^\|.+\|/

/** 移除表格行之间的空白行，保持表格块连续（GFM 中空行会打断表格解析） */
function preprocessTableContinuity(content: string): string {
  const lines = content.split('\n')
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (TABLE_ROW_RE.test(line)) {
      const block: string[] = []
      while (i < lines.length && (TABLE_ROW_RE.test(lines[i]) || lines[i].trim() === '')) {
        block.push(lines[i])
        i++
      }
      for (const bl of block) {
        if (bl.trim() !== '') {
          out.push(bl)
        }
      }
    } else {
      out.push(line)
      i++
    }
  }
  return out.join('\n')
}

const BOX_DRAWING_RE = /[\u2500-\u257F]/

/** 检测 Unicode 制表符行并包裹为代码块，保持等宽排版 */
function preprocessBoxDrawing(content: string): string {
  const lines = content.split('\n')
  const result: string[] = []
  let inBoxBlock = false

  for (const line of lines) {
    const isBoxLine = BOX_DRAWING_RE.test(line)
    if (isBoxLine && !inBoxBlock) {
      inBoxBlock = true
      result.push('```')
    } else if (!isBoxLine && inBoxBlock) {
      inBoxBlock = false
      result.push('```')
    }
    result.push(line)
  }
  if (inBoxBlock) result.push('```')

  return result.join('\n')
}

/** HTML 转义（用于错误展示） */
function escapeHtml(str: string): string {
  const map: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }
  return str.replace(/[&<>"']/g, (c) => map[c] || c)
}

/** HTML 实体解码（还原 markdown-it 对代码块内容的转义） */
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

/** 匹配 <pre><code class="language-mermaid">...</code></pre> */
const MERMAID_BLOCK_RE = /<pre[^>]*><code[^>]*class="[^"]*language-mermaid[^"]*"[^>]*>([\s\S]*?)<\/code><\/pre>/gi

/** 从 HTML 中提取 mermaid 代码块，替换为占位 div */
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

// ── composable ──

export function useMarkdownRenderer(content: Ref<string>, isMarkdown: Ref<boolean>) {
  const renderedHtml = ref('')

  async function renderContent() {
    if (!isMarkdown.value || !content.value) {
      renderedHtml.value = ''
      return
    }
    try {
      const noExtraBlanks = preprocessTableContinuity(content.value)
      const preprocessed = preprocessBoxDrawing(noExtraBlanks)
      const env = {}
      const rawHtml = md.render(preprocessed, env)
      const { html: placeholderHtml, blocks } = extractMermaidBlocks(rawHtml)
      const sanitized = DOMPurify.sanitize(placeholderHtml)

      if (blocks.length > 0) {
        let finalHtml = sanitized
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
              `<pre class="mermaid-error">Mermaid 渲染错误: ${escapeHtml((err as Error).message)}\n${escapeHtml(block.code.slice(0, 300))}</pre>`,
            )
          }
        }
        renderedHtml.value = addCodeCopyButtons(finalHtml)
      } else {
        renderedHtml.value = addCodeCopyButtons(sanitized)
      }
    } catch (err) {
      console.error('[MarkdownRenderer] 渲染失败', err)
      renderedHtml.value = `<pre style="color:red;padding:12px;">渲染错误: ${(err as Error).message}\n\n原始内容:\n${escapeHtml(content.value.slice(0, 500))}</pre>`
    }
  }

  watch([content, isMarkdown], () => { renderContent() }, { immediate: true })

  /** 大纲（标题层级） */
  const outline = computed<OutlineItem[]>(() => {
    if (!isMarkdown.value || !content.value) return []
    return extractOutline(content.value)
  })

  return { renderedHtml, outline }
}

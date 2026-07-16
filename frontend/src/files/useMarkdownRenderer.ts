import { computed, type Ref } from 'vue'
import MarkdownIt from 'markdown-it'
import multimdTable from 'markdown-it-multimd-table'
import markdownItKatex from 'markdown-it-katex'
import DOMPurify from 'dompurify'

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

// ── 给所有链接添加 target="_blank" 实现新标签页跳转 ──
const defaultLinkRender = md.renderer.rules.link_open ?? function (tokens, idx, options, _env, self) {
  return self.renderToken(tokens, idx, options)
}
md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  const token = tokens[idx]
  token.attrSet('target', '_blank')
  token.attrSet('rel', 'noopener noreferrer')
  return defaultLinkRender(tokens, idx, options, env, self)
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

// ── composable ──

export function useMarkdownRenderer(content: Ref<string>, isMarkdown: Ref<boolean>) {
  const renderedHtml = computed(() => {
    if (!isMarkdown.value || !content.value) {
      return ''
    }
    try {
      const noExtraBlanks = preprocessTableContinuity(content.value)
      const preprocessed = preprocessBoxDrawing(noExtraBlanks)
      const rawHtml = md.render(preprocessed)
      return DOMPurify.sanitize(rawHtml)
    } catch (err) {
      console.error('[MarkdownRenderer] 渲染失败', err)
      return `<pre style="color:red;padding:12px;">渲染错误: ${(err as Error).message}\n\n原始内容:\n${escapeHtml(content.value.slice(0, 500))}</pre>`
    }
  })

  return { renderedHtml }
}

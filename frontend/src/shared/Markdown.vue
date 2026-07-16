<script setup lang="ts">
/**
 * Markdown 渲染组件
 * - 使用 marked 解析 Markdown → HTML
 * - 使用 DOMPurify 做 XSS 防护
 * - 启用 GFM（表格、删除线、任务列表等）
 * - 启用 breaks（单换行 → <br>）
 */
import { computed, useSlots } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ gfm: true, breaks: true })

const slots = useSlots()

const props = defineProps<{
  /**
   * 可选：代码块 ID 前缀，用于内容导航锚点。
   * 传入 "code-nav-3" 后，第一个代码块 id="code-nav-3-0"，
   * 第二个 id="code-nav-3-1"，以此类推。
   */
  codeBlockIdSeed?: string
}>()

const html = computed(() => {
  const slot = slots.default?.()
  const text =
    slot
      ?.map((vnode) =>
        typeof vnode.children === 'string' ? vnode.children : '',
      )
      .join('') ?? ''
  if (!text) return ''
  const raw = marked.parse(text) as string
  const clean = DOMPurify.sanitize(raw)
  // 为代码块注入锚点 id（用于导航面板的精确定位）
  if (props.codeBlockIdSeed) {
    let idx = 0
    return clean.replace(
      /<pre>/g,
      () => `<pre id="${props.codeBlockIdSeed}-${idx++}">`,
    )
  }
  return clean
})
</script>

<template>
  <div v-if="html" class="markdown-content" v-html="html" />
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
  background: #1e1e2e;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}
.markdown-content pre code {
  background: none;
  padding: 0;
  color: #cdd6f4;
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
</style>

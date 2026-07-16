<script setup lang="ts">
import { ref } from 'vue'
import type { ToolCall } from '@/api/chat'

defineProps<{
  toolCall: ToolCall
}>()

const isExpanded = ref(false)

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

function formatArgs(args: Record<string, unknown> | undefined): string {
  if (!args || Object.keys(args).length === 0) {
    return '{}'
  }
  try {
    // SSE 解析失败时用 { raw } 包裹原始字符串
    if ('raw' in args && Object.keys(args).length === 1) {
      return String(args.raw)
    }
    // 标量值用 { value } 包裹
    if ('value' in args && Object.keys(args).length === 1) {
      return JSON.stringify(args.value, null, 2)
    }
    // 数组用 { items } 包裹
    if ('items' in args && Object.keys(args).length === 1) {
      return JSON.stringify(args.items, null, 2)
    }
    return JSON.stringify(args, null, 2)
  } catch {
    return String(args)
  }
}
</script>

<template>
  <div class="tool-call-card">
    <button class="tool-header" @click="toggleExpand">
      <span class="tool-icon">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
        </svg>
      </span>
      <span class="tool-name">{{ toolCall.name }}</span>
      <span v-if="toolCall.result" class="tool-status completed">✓ 完成</span>
      <span v-else class="tool-status pending">执行中.</span>
      <span :class="['tool-chevron', { expanded: isExpanded }]">▶</span>
    </button>

    <div v-show="isExpanded" class="tool-body">
      <!-- 参数 -->
      <div class="tool-section">
        <div class="tool-section-label">参数</div>
        <pre class="tool-code">{{ formatArgs(toolCall.args) }}</pre>
      </div>
      <!-- 结果 -->
      <div v-if="toolCall.result" class="tool-section">
        <div class="tool-section-label">结果</div>
        <pre class="tool-code tool-code--result">{{ toolCall.result }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tool-call-card {
  margin: 6px 0;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(170, 59, 255, 0.03);
  border-left: 3px solid var(--accent, #aa3bff);
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  color: var(--text, #6b6375);
  transition: background 0.15s;
}

.tool-header:hover {
  background: rgba(170, 59, 255, 0.06);
}

.tool-icon {
  color: var(--accent, #aa3bff);
  display: flex;
  align-items: center;
}

.tool-name {
  font-weight: 600;
  color: var(--text-h, #08060d);
  flex: 1;
  text-align: left;
}

.tool-status {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 9999px;
}

.tool-status.completed {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.tool-status.pending {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.tool-chevron {
  font-size: 10px;
  opacity: 0.5;
  transition: transform 0.2s;
}

.tool-chevron.expanded {
  transform: rotate(90deg);
}

.tool-body {
  border-top: 1px solid var(--border, #e5e4e7);
  padding: 8px 12px 10px;
}

.tool-section {
  margin-bottom: 8px;
}

.tool-section:last-child {
  margin-bottom: 0;
}

.tool-section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text, #6b6375);
  opacity: 0.6;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.tool-code {
  margin: 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--code-bg, #f4f3ec);
  font: 12px/1.5 var(--mono, monospace);
  color: var(--text-h, #08060d);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 250px;
  overflow-y: auto;
}

.tool-code--result {
  max-height: 200px;
}
</style>
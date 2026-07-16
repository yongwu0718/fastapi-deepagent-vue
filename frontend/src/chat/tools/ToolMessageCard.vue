<script setup lang="ts">
import { ref } from 'vue'
import type { ToolMessageEntry } from './useToolMessages'

defineProps<{
  entry: ToolMessageEntry
}>()

const isExpanded = ref(false)
</script>

<template>
  <div class="tool-msg-card" :class="{ expanded: isExpanded }">
    <button class="tool-msg-header" @click="isExpanded = !isExpanded">
      <span class="tool-msg-icon">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>
      <span class="tool-msg-name">{{ entry.toolName ?? '工具返回' }}</span>
      <span class="tool-msg-status done">✓ 完成</span>
      <span :class="['tool-msg-chevron', { expanded: isExpanded }]">▶</span>
    </button>

    <div v-show="isExpanded" class="tool-msg-body">
      <pre class="tool-msg-result">{{ entry.content }}</pre>
    </div>
  </div>
</template>

<style scoped>
.tool-msg-card {
  margin: 6px 0;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(16, 185, 129, 0.03);
  border-left: 3px solid #10b981;
}

.tool-msg-header {
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

.tool-msg-header:hover {
  background: rgba(16, 185, 129, 0.06);
}

.tool-msg-icon {
  color: #10b981;
  display: flex;
  align-items: center;
}

.tool-msg-name {
  font-weight: 600;
  color: var(--text-h, #08060d);
  flex: 1;
  text-align: left;
}

.tool-msg-status {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 9999px;
}

.tool-msg-status.done {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.tool-msg-chevron {
  font-size: 10px;
  opacity: 0.5;
  transition: transform 0.2s;
}

.tool-msg-chevron.expanded {
  transform: rotate(90deg);
}

.tool-msg-body {
  border-top: 1px solid var(--border, #e5e4e7);
  padding: 8px 12px 10px;
}

.tool-msg-result {
  margin: 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--code-bg, #f4f3ec);
  font: 12px/1.5 var(--mono, monospace);
  color: var(--text-h, #08060d);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}
</style>
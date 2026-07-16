<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  /** 推理内容 */
  reasoning: string
  /** 是否正在流式输出中 */
  isStreaming: boolean
}>()

const isExpanded = ref(false)

const charCount = computed(() => props.reasoning.length)

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}
</script>

<template>
  <div class="chat-reason">
    <button
      class="reason-header"
      :aria-expanded="isExpanded"
      aria-controls="reason-content"
      @click="toggleExpand"
    >
      <span class="reason-icon">
        <span v-if="isStreaming" class="reason-spinner" />
        <span v-else>💭</span>
      </span>
      <span class="reason-label">
        <template v-if="isStreaming">正在思考.</template>
        <template v-else>思考过程（{{ charCount }} 字符）</template>
      </span>
      <span :class="['reason-chevron', { expanded: isExpanded }]">▶</span>
    </button>

    <!-- 展开显示完整内容 -->
    <div v-show="isExpanded" id="reason-content" class="reason-content">
      <pre>{{ reasoning }}</pre>
    </div>
  </div>
</template>

<style scoped>
.chat-reason {
  margin-bottom: 14px;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(170, 59, 255, 0.03);
  border-left: 3px solid var(--accent, #aa3bff);
}

.reason-header {
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

.reason-header:hover {
  background: rgba(170, 59, 255, 0.06);
}

.reason-icon {
  flex-shrink: 0;
  font-size: 14px;
}

.reason-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid var(--accent, #aa3bff);
  border-top-color: transparent;
  border-radius: 50%;
  animation: reason-spin 0.8s linear infinite;
}

@keyframes reason-spin {
  to { transform: rotate(360deg); }
}

.reason-label {
  flex: 1;
  text-align: left;
  font-weight: 600;
}

.reason-chevron {
  flex-shrink: 0;
  font-size: 10px;
  transition: transform 0.2s;
  color: var(--text, #6b6375);
  opacity: 0.6;
}

.reason-chevron.expanded {
  transform: rotate(90deg);
}

.reason-content {
  padding: 0 12px 10px;
  border-top: 1px solid var(--border, #e5e4e7);
}

.reason-content pre {
  margin: 8px 0 0;
  font: 13px/1.6 var(--mono, ui-monospace, Consolas, monospace);
  color: var(--text, #6b6375);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}
</style>
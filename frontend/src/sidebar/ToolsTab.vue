<script setup lang="ts">
import { computed, ref } from 'vue'
import { useToolMessages, type ToolCallGroup, type ToolMessageEntry } from '@/chat/tools/useToolMessages'
import ToolCallCard from '@/chat/tools/ToolCallCard.vue'
import ToolMessageCard from '@/chat/tools/ToolMessageCard.vue'

const { toolCallGroups, toolMessages, toolCallCount, streamingToolCalls } = useToolMessages()

// ── 工具调用分组折叠状态 ──
const expandedGroups = ref<Set<number>>(new Set())

const allExpanded = computed(() => {
  const total = toolCallGroups.value.length + toolMessages.value.length
  if (total === 0) return false
  return expandedGroups.value.size === toolCallGroups.value.length
    && expandedToolMessages.value.size === toolMessages.value.length
})

function toggleGroup(index: number) {
  const next = new Set(expandedGroups.value)
  if (next.has(index)) {
    next.delete(index)
  } else {
    next.add(index)
  }
  expandedGroups.value = next
}

function expandAll() {
  expandedGroups.value = new Set(toolCallGroups.value.map((_, i) => i))
}

function collapseAll() {
  expandedGroups.value = new Set()
}

function toggleAll() {
  if (allExpanded.value) {
    collapseAll()
    expandedToolMessages.value = new Set()
  } else {
    expandAll()
    expandedToolMessages.value = new Set(toolMessages.value.map((_, i) => i))
  }
}

function toolLabel(group: ToolCallGroup) {
  const prefix = group.toolCalls.length > 1
    ? `${group.toolCalls.length} 个工具调用`
    : group.toolCalls[0].name
  if (group.messageContent) {
    return `${prefix}  ·  "${group.messageContent}"`
  }
  return prefix
}

// ── tool 消息分组折叠状态 ──
const expandedToolMessages = ref<Set<number>>(new Set())

function toggleToolMessageGroup(index: number) {
  const next = new Set(expandedToolMessages.value)
  if (next.has(index)) {
    next.delete(index)
  } else {
    next.add(index)
  }
  expandedToolMessages.value = next
}

function toolMessageLabel(entry: ToolMessageEntry) {
  const name = entry.toolName ?? '工具返回'
  const preview = entry.content.length > 40
    ? entry.content.slice(0, 40) + '…'
    : entry.content
  return `${name}  →  ${preview}`
}
</script>

<template>
  <div class="tab-content">
    <!-- 流式工具调用（实时） -->
    <div v-if="streamingToolCalls.length > 0" class="streaming-section">
      <div class="streaming-label">⏳ 流式工具调用</div>
      <div class="streaming-tools">
        <ToolCallCard
          v-for="tc in streamingToolCalls"
          :key="tc.id"
          :tool-call="tc"
        />
      </div>
    </div>

    <!-- 展开/折叠全部按钮 -->
    <div v-if="toolCallGroups.length > 0 || toolMessages.length > 0" class="toolbar-row">
      <button class="expand-all-btn" @click="toggleAll">
        {{ allExpanded ? '折叠全部' : '展开全部' }}
      </button>
    </div>

    <!-- 空状态 -->
    <div v-if="toolCallGroups.length === 0 && toolMessages.length === 0" class="tab-empty">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.3">
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
      </svg>
      <p>暂无工具调用记录</p>
    </div>

    <!-- 工具调用分组（assistant toolCalls） -->
    <div v-if="toolCallGroups.length > 0" class="tool-groups">
      <div
        v-for="(group, index) in toolCallGroups"
        :key="'tc-' + index"
        class="tool-group"
      >
        <button
          class="group-header"
          :aria-expanded="expandedGroups.has(index)"
          @click="toggleGroup(index)"
        >
          <span class="group-icon">🔧</span>
          <span class="group-label">{{ toolLabel(group) }}</span>
          <span
            :class="['group-chevron', { expanded: expandedGroups.has(index) }]"
          >▶</span>
        </button>

        <div v-show="expandedGroups.has(index)" class="group-body">
          <ToolCallCard
            v-for="tc in group.toolCalls"
            :key="tc.id"
            :tool-call="tc"
          />
        </div>
      </div>
    </div>

    <!-- tool 消息分隔线 -->
    <div
      v-if="toolCallGroups.length > 0 && toolMessages.length > 0"
      class="section-divider"
    >
      <span class="section-divider-label">工具返回</span>
    </div>

    <!-- tool 消息列表（来自 get-messages-history） -->
    <div v-if="toolMessages.length > 0" class="tool-groups">
      <div
        v-for="(entry, index) in toolMessages"
        :key="'tm-' + index"
        class="tool-group tool-group--result"
      >
        <button
          class="group-header"
          :aria-expanded="expandedToolMessages.has(index)"
          @click="toggleToolMessageGroup(index)"
        >
          <span class="group-icon">✅</span>
          <span class="group-label">{{ toolMessageLabel(entry) }}</span>
          <span
            :class="['group-chevron', { expanded: expandedToolMessages.has(index) }]"
          >▶</span>
        </button>

        <div v-show="expandedToolMessages.has(index)" class="group-body">
          <ToolMessageCard :entry="entry" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── 内容区 ── */
.tab-content {
  padding: 16px;
}

.tab-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: var(--text, #6b6375);
  opacity: 0.5;
  gap: 12px;
  font-size: 13px;
  text-align: center;
}

/* ── 工具栏行 ── */
.toolbar-row {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.expand-all-btn {
  padding: 4px 12px;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 6px;
  background: var(--bg, #fff);
  font: inherit;
  font-size: 12px;
  color: var(--text, #6b6375);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.expand-all-btn:hover {
  background: var(--code-bg, #f4f3ec);
  color: var(--text-h, #08060d);
}

/* ── 工具调用分组（ChatReason 折叠风格） ── */
.tool-groups {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-group {
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(170, 59, 255, 0.03);
  border-left: 3px solid var(--accent, #aa3bff);
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: 12.5px;
  color: var(--text, #6b6375);
  transition: background 0.15s;
  text-align: left;
}

.group-header:hover {
  background: rgba(170, 59, 255, 0.06);
}

.group-icon {
  flex-shrink: 0;
  font-size: 14px;
}

.group-label {
  flex: 1;
  font-weight: 600;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-chevron {
  flex-shrink: 0;
  font-size: 10px;
  transition: transform 0.2s;
  color: var(--text, #6b6375);
  opacity: 0.6;
}

.group-chevron.expanded {
  transform: rotate(90deg);
}

.group-body {
  border-top: 1px solid var(--border, #e5e4e7);
  padding: 8px 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ── 工具返回（tool 消息）配色 ── */
.tool-group--result {
  border-left-color: #10b981;
  background: rgba(16, 185, 129, 0.03);
}

/* ── 分区标题 ── */
.section-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
  margin: 4px 0;
}

.section-divider::before,
.section-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border, #e5e4e7);
}

.section-divider-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text, #6b6375);
  opacity: 0.5;
  white-space: nowrap;
}

/* ── 流式工具调用区域 ── */
.streaming-section {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px dashed var(--accent, #aa3bff);
  border-radius: 10px;
  background: rgba(170, 59, 255, 0.04);
}

.streaming-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent, #aa3bff);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.streaming-tools {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>

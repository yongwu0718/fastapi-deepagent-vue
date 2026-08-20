<script setup lang="ts">
import { computed, useTemplateRef, watch } from 'vue'
import { STATUS } from '../../constants'
import { minToTime, timeToMin } from '../../utils/date'
import { minText } from '../../utils/format'
import type { Task } from '../../types'

const props = defineProps<{
  task: Task
  flash?: boolean
}>()

const emit = defineEmits<{
  cycle: [id: string]
  edit: [id: string]
  review: [id: string]
  delete: [id: string]
}>()

const statusMeta = computed(() => STATUS[props.task.status])

const endTime = computed(() =>
  props.task.start_time && props.task.duration_minutes
    ? minToTime(timeToMin(props.task.start_time) + props.task.duration_minutes)
    : null,
)

const rowEl = useTemplateRef<HTMLElement>('rowEl')

// 高亮时滚动到可见区域
watch(
  () => props.flash,
  (flash) => {
    if (flash && rowEl.value) rowEl.value.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  },
)

function onDragStart(e: DragEvent) {
  e.dataTransfer?.setData('text/plain', props.task.id)
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}
</script>

<template>
  <div
    ref="rowEl"
    class="task-row"
    :class="{ done: task.status === 'done', flash: flash }"
    draggable="true"
    @dragstart="onDragStart"
  >
    <button
      class="status-btn"
      :class="{ done: task.status === 'done', 'in-progress': task.status === 'in-progress' }"
      :title="`${statusMeta.label}，点击切换`"
      @click="emit('cycle', task.id)"
    >
      {{ task.status === 'done' ? '✓' : task.status === 'in-progress' ? '◐' : '' }}
    </button>

    <div class="task-main">
      <div class="task-title-row">
        <span class="edot" :class="`e-${task.energy}`"></span>
        <span class="task-title">{{ task.title }}</span>
        <span v-if="task.block" class="task-block-tag">{{ task.block }}</span>
      </div>
      <div class="task-meta">
        <span v-if="task.start_time">{{ task.start_time }}<template v-if="endTime">–{{ endTime }}</template></span>
        <span v-if="task.duration_minutes">{{ minText(task.duration_minutes) }}</span>
        <span :class="`st-${task.status}`">{{ statusMeta.icon }} {{ statusMeta.label }}</span>
        <span v-if="task.actual_minutes != null">实际 {{ minText(task.actual_minutes) }}</span>
        <span v-if="task.reflection" class="reflect-badge" :title="task.reflection">📝 已复盘</span>
      </div>
    </div>

    <div class="task-actions">
      <button class="icon-btn" title="任务复盘" @click="emit('review', task.id)">📝</button>
      <button class="icon-btn" title="编辑" @click="emit('edit', task.id)">✏️</button>
      <button class="icon-btn del" title="删除" @click="emit('delete', task.id)">🗑</button>
    </div>
  </div>
</template>

<style scoped>
.task-row {
  display: flex;
  gap: 9px;
  align-items: flex-start;
  padding: 9px 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: #fff;
  cursor: grab;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.task-row:hover { border-color: #c7d2fe; box-shadow: 0 2px 8px rgba(99, 102, 241, 0.08); }
.task-row.flash { animation: flash 1.2s ease; }

@keyframes flash {
  0%, 60% { background: var(--accent-soft); border-color: #a5b4fc; }
  100% { background: #fff; }
}

.status-btn {
  flex: none;
  width: 24px;
  height: 24px;
  margin-top: 1px;
  border-radius: 50%;
  border: 2px solid #cbd5e1;
  background: #fff;
  font-size: 11px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.status-btn:hover { transform: scale(1.12); }
.status-btn.in-progress { border-color: var(--deep); background: #eff6ff; }
.status-btn.done { border-color: var(--ok); background: var(--ok); }

.task-main { flex: 1; min-width: 0; }
.task-title-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }

.edot { flex: none; width: 10px; height: 10px; border-radius: 3px; }
.edot.e-deep { background: var(--deep); }
.edot.e-collaboration { background: var(--collab); }
.edot.e-shallow { background: var(--shallow); }
.edot.e-learning { background: var(--learning); }

.task-title { font-weight: 600; font-size: 13px; word-break: break-all; }
.task-row.done .task-title { text-decoration: line-through; color: var(--text-3); }

.task-block-tag {
  font-size: 10px;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 1px 7px;
  border-radius: 999px;
}

.task-meta {
  font-size: 11px;
  color: var(--text-3);
  margin-top: 4px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.task-meta .st-in-progress { color: var(--deep); font-weight: 600; }
.task-meta .st-done { color: var(--ok); font-weight: 600; }
.task-meta .st-backlog { color: var(--text-3); font-weight: 600; }
.reflect-badge { cursor: help; }

.task-actions { display: flex; gap: 3px; flex: none; }
</style>

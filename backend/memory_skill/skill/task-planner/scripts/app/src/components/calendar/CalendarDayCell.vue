<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { ENERGY } from '../../constants'
import { usePlannerStore } from '../../composables/usePlannerStore'
import { useToast } from '../../composables/useToast'
import { useUiState } from '../../composables/useUiState'
import type { CalendarCell } from '../../utils/date'

const props = defineProps<{
  cell: CalendarCell
  selected: boolean
}>()

const store = usePlannerStore()
const ui = useUiState()
const toast = useToast()

const dayTasks = computed(() =>
  store.state.tasks
    .filter(t => t.date === props.cell.date && !t.is_quick)
    .slice()
    .sort((a, b) => (a.start_time || '99:99').localeCompare(b.start_time || '99:99')),
)
const visibleTasks = computed(() => dayTasks.value.slice(0, 3))
const moreCount = computed(() => Math.max(0, dayTasks.value.length - 3))
const hasReview = computed(() => !!store.state.reviews[props.cell.date])
const dragOver = shallowRef(false)

function onSelect() {
  ui.selectDate(props.cell.date)
}

function onChipClick(taskId: string) {
  ui.selectDate(props.cell.date)
  ui.flashTask(taskId)
}

function onChipDragStart(e: DragEvent, taskId: string) {
  e.dataTransfer?.setData('text/plain', taskId)
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
  dragOver.value = true
}

function onDragLeave() {
  dragOver.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  dragOver.value = false
  const id = e.dataTransfer?.getData('text/plain')
  if (!id) return
  const task = store.findTask(id)
  if (task && task.date !== props.cell.date) {
    store.moveTask(id, props.cell.date)
    toast.show(`「${task.title}」已移至 ${props.cell.date}`)
  }
}
</script>

<template>
  <div
    class="cal-cell"
    :class="{
      out: !cell.inMonth,
      today: cell.isToday,
      selected: selected,
      'drag-over': dragOver,
    }"
    @click="onSelect"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <div class="cal-head">
      <span class="cal-date">{{ cell.day }}</span>
      <span v-if="cell.isFirstOfMonth" class="cal-month-tag">{{ cell.month + 1 }}月</span>
      <span v-if="hasReview" class="cal-review" title="已复盘">📝</span>
    </div>
    <div class="cal-chips">
      <div
        v-for="t in visibleTasks"
        :key="t.id"
        class="chip"
        :class="[`e-${t.energy}`, { done: t.status === 'done' }]"
        draggable="true"
        :title="`${ENERGY[t.energy].label} · ${t.title}`"
        @click.stop="onChipClick(t.id)"
        @dragstart="onChipDragStart($event, t.id)"
      >
        <span v-if="t.start_time" class="chip-time">{{ t.start_time }}</span>
        <span class="chip-title">{{ t.title }}</span>
        <span v-if="t.status === 'done'" class="chip-check">✓</span>
      </div>
      <div v-if="moreCount" class="cal-more">+{{ moreCount }} 项</div>
    </div>
  </div>
</template>

<style scoped>
.cal-cell {
  background: #fafbfd;
  border: 1px solid #eef2f7;
  border-radius: 10px;
  min-height: 106px;
  padding: 7px 7px 6px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
}
.cal-cell:hover { border-color: #c7d2fe; background: #fff; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1); }
.cal-cell.out { opacity: 0.45; }
.cal-cell.today { border: 2px solid var(--accent); background: #fff; }
.cal-cell.selected { background: var(--accent-soft); border-color: #c7d2fe; }
.cal-cell.drag-over { border: 2px dashed var(--accent); background: var(--accent-soft); }

.cal-head { display: flex; align-items: center; gap: 4px; }
.cal-date { font-size: 13px; font-weight: 600; color: var(--text-2); }
.cal-cell.today .cal-date {
  background: var(--accent);
  color: #fff;
  border-radius: 999px;
  min-width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
}
.cal-month-tag { font-size: 10px; color: var(--text-3); }
.cal-review { margin-left: auto; font-size: 11px; }

.cal-chips { display: flex; flex-direction: column; gap: 3px; flex: 1; }
.cal-more { font-size: 11px; color: var(--text-3); padding-left: 2px; }

.chip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  line-height: 1.25;
  padding: 2px 5px;
  border-radius: 6px;
  white-space: nowrap;
  overflow: hidden;
  cursor: grab;
  border-left: 3px solid transparent;
}
.chip:active { cursor: grabbing; }
.chip-time { flex: none; font-weight: 600; opacity: 0.8; }
.chip-title { overflow: hidden; text-overflow: ellipsis; }
.chip-check { flex: none; color: var(--ok); font-weight: 700; }
.chip.done .chip-title { text-decoration: line-through; opacity: 0.65; }
.chip.e-deep { background: #eff6ff; color: #1d4ed8; border-left-color: var(--deep); }
.chip.e-collaboration { background: #fffbeb; color: #b45309; border-left-color: var(--collab); }
.chip.e-shallow { background: #f1f5f9; color: #475569; border-left-color: var(--shallow); }
.chip.e-learning { background: #f0fdf4; color: #15803d; border-left-color: var(--learning); }

@media (max-width: 1080px) {
  .cal-cell { min-height: 84px; }
}
@media (max-width: 640px) {
  .cal-cell { min-height: 68px; padding: 5px; }
  .chip { font-size: 10px; }
}
</style>

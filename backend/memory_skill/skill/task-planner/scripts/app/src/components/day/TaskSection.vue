<script setup lang="ts">
import { computed, reactive } from 'vue'
import { ENERGY } from '../../constants'
import { usePlannerStore } from '../../composables/usePlannerStore'
import { useToast } from '../../composables/useToast'
import { useUiState } from '../../composables/useUiState'
import type { EnergyType } from '../../types'
import TaskRow from './TaskRow.vue'

const store = usePlannerStore()
const ui = useUiState()
const toast = useToast()

const form = reactive({
  title: '',
  start_time: '',
  duration_minutes: 60,
  energy: 'deep' as EnergyType,
  block: '',
})

const sortedTasks = computed(() =>
  store
    .tasksOf(ui.selectedDate.value)
    .filter(t => !t.is_quick)
    .slice()
    .sort((a, b) => {
      const ap = a.status === 'backlog' ? 1 : 0
      const bp = b.status === 'backlog' ? 1 : 0
      if (ap !== bp) return ap - bp
      return (a.start_time || '99:99').localeCompare(b.start_time || '99:99')
    }),
)

const hasAnyTask = computed(() => store.state.tasks.length > 0)

function onSubmit() {
  if (!form.title.trim()) return
  store.addTask({
    title: form.title,
    date: ui.selectedDate.value,
    start_time: form.start_time || null,
    duration_minutes: Number(form.duration_minutes) || null,
    energy: form.energy,
    block: form.block || null,
  })
  form.title = ''
  form.start_time = ''
  form.duration_minutes = 60
  form.energy = 'deep'
  form.block = ''
  toast.show('任务已添加')
}

function onCycle(id: string) {
  store.cycleStatus(id)
}

function onEdit(id: string) {
  ui.openTaskEditor(id, 'edit')
}

function onReview(id: string) {
  ui.openTaskEditor(id, 'review')
}

function onDelete(id: string) {
  const t = store.findTask(id)
  if (t && confirm(`删除任务「${t.title}」？`)) {
    store.deleteTask(id)
    toast.show('已删除')
  }
}

function onLoadDemo() {
  store.loadDemo()
  ui.goToday()
  toast.show('示例数据已载入')
}
</script>

<template>
  <section class="panel-section">
    <h3 class="section-title">
      📋 时间块任务
      <span v-if="sortedTasks.length" class="section-count">{{ sortedTasks.length }} 项</span>
    </h3>

    <form class="add-form" autocomplete="off" @submit.prevent="onSubmit">
      <input v-model="form.title" class="field-input" placeholder="任务标题，如：写完方案初稿（单一动作 + 可验证产出）" required />
      <div class="form-grid">
        <input v-model="form.start_time" class="field-input" type="time" title="开始时间" />
        <input v-model.number="form.duration_minutes" class="field-input" type="number" placeholder="时长(分)" min="5" step="5" required title="预计时长（分钟）" />
        <select v-model="form.energy" class="field-select">
          <option v-for="(meta, key) in ENERGY" :key="key" :value="key">{{ meta.icon }} {{ meta.label }}</option>
        </select>
      </div>
      <input v-model="form.block" class="field-input" placeholder="所属时间块（可选），如：上午深度块" spellcheck="false" />
      <button class="btn primary" type="submit">＋ 添加任务</button>
    </form>

    <div class="task-list">
      <TaskRow
        v-for="t in sortedTasks"
        :key="t.id"
        :task="t"
        :flash="t.id === ui.flashTaskId.value"
        @cycle="onCycle"
        @edit="onEdit"
        @review="onReview"
        @delete="onDelete"
      />
      <div v-if="!sortedTasks.length" class="empty">
        <template v-if="!hasAnyTask">
          还没有任何任务<br />
          用上方表单添加第一个任务，或 <a href="#" @click.prevent="onLoadDemo">✨ 载入示例数据</a>
        </template>
        <template v-else>当天暂无任务<br />从上方表单添加，或把日历中的任务拖到这里改期</template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel-section { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); }

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-2);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.section-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-3);
  font-weight: 500;
  background: #f8fafc;
  border-radius: 999px;
  padding: 1px 8px;
}

.add-form { display: flex; flex-direction: column; gap: 7px; margin-bottom: 12px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr 1.4fr; gap: 7px; }

.task-list { display: flex; flex-direction: column; gap: 6px; }
</style>

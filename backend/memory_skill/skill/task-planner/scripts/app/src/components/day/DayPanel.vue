<script setup lang="ts">
import { computed, watch, shallowRef } from 'vue'
import { DOW_NAMES } from '../../constants'
import { usePlannerStore } from '../../composables/usePlannerStore'
import { useUiState } from '../../composables/useUiState'
import { parseDate } from '../../utils/date'
import { minText } from '../../utils/format'
import TaskSection from './TaskSection.vue'
import QuickTaskSection from './QuickTaskSection.vue'
import DailyReviewSection from './DailyReviewSection.vue'

const store = usePlannerStore()
const ui = useUiState()

const panelTitle = computed(() => {
  const d = parseDate(ui.selectedDate.value)
  return `${d.getMonth() + 1}月${d.getDate()}日 · ${DOW_NAMES[d.getDay()]}`
})

const hasReview = computed(() => !!store.state.reviews[ui.selectedDate.value])

// 当日主题：本地输入态，切换日期时从 store 重取
const themeInput = shallowRef('')
watch(
  () => ui.selectedDate.value,
  (date) => {
    themeInput.value = store.state.days[date]?.theme || ''
  },
  { immediate: true },
)

function onThemeChange() {
  store.setTheme(ui.selectedDate.value, themeInput.value)
}

const dayStats = computed(() => {
  const all = store.tasksOf(ui.selectedDate.value)
  const tasks = all.filter(t => !t.is_quick && t.status !== 'backlog')
  const done = tasks.filter(t => t.status === 'done').length
  const totalMin = tasks.reduce((s, t) => s + (t.duration_minutes || 0), 0)
  const deepMin = tasks.filter(t => t.energy === 'deep').reduce((s, t) => s + (t.duration_minutes || 0), 0)
  const over2h = tasks.filter(t => (t.duration_minutes || 0) > 120).length
  const backlog = all.filter(t => !t.is_quick && t.status === 'backlog').length
  return {
    done,
    total: tasks.length,
    totalMin,
    deepMin,
    over2h,
    backlog,
    rate: tasks.length ? Math.round((done / tasks.length) * 100) : 0,
  }
})

const validations = computed(() => [
  { ok: dayStats.value.totalMin <= 480, text: `总量 ${minText(dayStats.value.totalMin)}（建议 ≤8h）` },
  { ok: dayStats.value.deepMin <= 240, text: `深度专注 ${minText(dayStats.value.deepMin)}（建议 ≤4h）` },
  {
    ok: dayStats.value.over2h === 0,
    text: dayStats.value.over2h ? `${dayStats.value.over2h} 项超2小时，建议拆分` : '无超2小时任务',
  },
])
</script>

<template>
  <aside class="day-panel">
    <div class="panel-head">
      <div class="panel-head-main">
        <div class="panel-date">{{ panelTitle }}</div>
        <input
          v-model="themeInput"
          class="theme-input"
          placeholder="今日主题（可选），如：深度工作日"
          spellcheck="false"
          @change="onThemeChange"
        />
      </div>
      <span class="reviewed-tag" :class="{ no: !hasReview }">
        {{ hasReview ? '📝 已复盘' : '未复盘' }}
      </span>
    </div>

    <div class="day-progress">
      <div class="day-stat-text">
        <span>
          <template v-if="dayStats.total">
            {{ dayStats.done }}/{{ dayStats.total }} 完成 · 计划 {{ minText(dayStats.totalMin) }}
            <template v-if="dayStats.backlog"> · 待定 {{ dayStats.backlog }}</template>
          </template>
          <template v-else>今天还没有任务</template>
        </span>
        <span v-if="dayStats.total">{{ dayStats.rate }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${dayStats.rate}%` }"></div>
      </div>
      <div class="vchips">
        <span v-for="(v, i) in validations" :key="i" class="vchip" :class="v.ok ? 'ok' : 'warn'">
          {{ v.ok ? '✅' : '⚠️' }} {{ v.text }}
        </span>
      </div>
    </div>

    <TaskSection />
    <QuickTaskSection />
    <DailyReviewSection />
  </aside>
</template>

<style scoped>
.day-panel {
  width: 420px;
  flex: none;
  background: var(--card);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
  position: sticky;
  top: 76px;
  max-height: calc(100vh - 96px);
  overflow-y: auto;
}
.day-panel::-webkit-scrollbar { width: 8px; }
.day-panel::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 4px; }

.panel-head { display: flex; align-items: flex-start; gap: 10px; }
.panel-head-main { flex: 1; min-width: 0; }
.panel-date { font-size: 17px; font-weight: 700; }
.theme-input {
  margin-top: 6px;
  width: 100%;
  border: 1px dashed var(--border);
  border-radius: 8px;
  padding: 6px 10px;
  background: #fafbfd;
  outline: none;
}
.theme-input:focus { border-color: #c7d2fe; background: #fff; }

.reviewed-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #15803d;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  padding: 3px 9px;
  border-radius: 999px;
  font-weight: 600;
  white-space: nowrap;
}
.reviewed-tag.no { color: var(--text-3); background: #f8fafc; border-color: var(--border); }

.day-progress { margin-top: 12px; }
.day-stat-text {
  font-size: 13px;
  color: var(--text-2);
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
}
.progress-track { height: 8px; background: #f1f5f9; border-radius: 999px; overflow: hidden; }
.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #818cf8, #22c55e);
  transition: width 0.3s;
}
.vchips { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }

@media (max-width: 1080px) {
  .day-panel { width: 100%; position: static; max-height: none; }
}
</style>

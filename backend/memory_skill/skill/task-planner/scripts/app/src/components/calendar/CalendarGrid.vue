<script setup lang="ts">
import { computed } from 'vue'
import { usePlannerStore } from '../../composables/usePlannerStore'
import { useUiState } from '../../composables/useUiState'
import { monthGrid, monthPrefix } from '../../utils/date'
import CalendarDayCell from './CalendarDayCell.vue'

const store = usePlannerStore()
const ui = useUiState()

const cells = computed(() => monthGrid(ui.calYear.value, ui.calMonth.value))

const monthStats = computed(() => {
  const prefix = monthPrefix(ui.calYear.value, ui.calMonth.value)
  const monthTasks = store.state.tasks.filter(t => t.date.startsWith(prefix) && !t.is_quick)
  const done = monthTasks.filter(t => t.status === 'done').length
  const reviews = Object.keys(store.state.reviews).filter(d => d.startsWith(prefix)).length
  return {
    total: monthTasks.length,
    done,
    rate: monthTasks.length ? Math.round((done / monthTasks.length) * 100) : 0,
    reviews,
  }
})
</script>

<template>
  <section class="calendar-card">
    <div class="cal-week">
      <div>周一</div><div>周二</div><div>周三</div><div>周四</div><div>周五</div>
      <div class="wkend">周六</div><div class="wkend">周日</div>
    </div>
    <div class="cal-grid">
      <CalendarDayCell
        v-for="cell in cells"
        :key="cell.date"
        :cell="cell"
        :selected="cell.date === ui.selectedDate.value"
      />
    </div>
    <div class="cal-footer">
      <div class="cal-stat">
        <template v-if="monthStats.total">
          本月 <b>{{ monthStats.total }}</b> 项任务 · 完成 <b>{{ monthStats.done }}</b> ·
          完成率 <b>{{ monthStats.rate }}%</b> · 复盘 <b>{{ monthStats.reviews }}</b> 天
        </template>
        <template v-else>本月暂无任务，点击右侧日期开始规划</template>
      </div>
      <div class="legend">
        <span>🔵 深度</span><span>🟡 沟通</span><span>⚪ 机械</span><span>🟢 学习</span>
        <span>│ ✅ 完成</span><span>⏳ 待定</span><span>📝 已复盘</span>
        <span>│ 💡 拖拽任务到其他日期可改期</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.calendar-card {
  flex: 1;
  min-width: 0;
  background: var(--card);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
}

.cal-week {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
  margin-bottom: 8px;
}
.cal-week > div {
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-3);
  padding: 4px 0;
}
.cal-week > .wkend { color: #f87171; }

.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}

.cal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.cal-stat { font-size: 13px; color: var(--text-2); }
.cal-stat b { color: var(--text); }
.legend { display: flex; gap: 10px; flex-wrap: wrap; font-size: 11px; color: var(--text-3); }
.legend span { white-space: nowrap; }

@media (max-width: 640px) {
  .cal-grid { gap: 6px; }
}
</style>

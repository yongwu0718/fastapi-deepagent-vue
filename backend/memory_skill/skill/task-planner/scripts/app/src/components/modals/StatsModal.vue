<script setup lang="ts">
import { computed } from 'vue'
import { ENERGY } from '../../constants'
import { usePlannerStore } from '../../composables/usePlannerStore'
import { useUiState } from '../../composables/useUiState'
import { fmt, monthPrefix, todayStr } from '../../utils/date'
import type { EnergyType } from '../../types'

const store = usePlannerStore()
const ui = useUiState()

const monthPrefixCur = computed(() => monthPrefix(ui.calYear.value, ui.calMonth.value))

// ---- 本月完成率 ----
const monthDone = computed(() => {
  const mt = store.state.tasks.filter(t => t.date.startsWith(monthPrefixCur.value) && !t.is_quick)
  const done = mt.filter(t => t.status === 'done').length
  return {
    rate: mt.length ? Math.round((done / mt.length) * 100) : 0,
    total: mt.length,
    done,
  }
})

// ---- 复盘习惯（连续天数） ----
const reviewStreak = computed(() => {
  const dates = new Set(Object.keys(store.state.reviews))
  let n = 0
  const d = new Date()
  if (!dates.has(fmt(d))) d.setDate(d.getDate() - 1) // 今天还没复盘不算断
  while (dates.has(fmt(d))) {
    n++
    d.setDate(d.getDate() - 1)
  }
  return n
})

// ---- 精力分布 ----
const energyDist = computed(() => {
  const mt = store.state.tasks.filter(t => t.date.startsWith(monthPrefixCur.value) && !t.is_quick)
  const total = mt.length || 1
  return (Object.keys(ENERGY) as EnergyType[]).map(key => {
    const n = mt.filter(t => t.energy === key).length
    return {
      key,
      label: ENERGY[key].label,
      icon: ENERGY[key].icon,
      color: ENERGY[key].color,
      n,
      pct: Math.round((n / total) * 100),
    }
  })
})

// ---- 最近 7 天趋势 ----
const trend = computed(() => {
  const days: { date: string; label: string; done: number; planned: number }[] = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const date = fmt(d)
    const ts = store.state.tasks.filter(t => t.date === date && !t.is_quick && t.status !== 'backlog')
    days.push({
      date,
      label: `${d.getMonth() + 1}/${d.getDate()}`,
      planned: ts.length,
      done: ts.filter(t => t.status === 'done').length,
    })
  }
  const max = Math.max(1, ...days.map(d => d.planned))
  return { days, max }
})

const dataOverview = computed(() => {
  const quickCount = store.state.tasks.filter(t => t.is_quick).length
  return {
    taskCount: store.state.tasks.length,
    quickCount,
    dayCount: Object.keys(store.state.days).length,
  }
})

const storageNote = computed(() =>
  store.sync.online.value
    ? '数据自动同步到 scripts/data/task-planner-data.json'
    : '数据存储于浏览器 localStorage，用 node scripts/serve.js 启动后自动同步到 scripts/data',
)
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="ui.statsOpen.value" class="modal-backdrop" @mousedown.self="ui.closeStats()">
        <div class="modal">
          <div class="modal-head">
            <h3>📊 数据统计</h3>
            <button class="modal-close" title="关闭" @click="ui.closeStats()">×</button>
          </div>

          <div class="stats-grid">
            <div class="stat-card">
              <h4>本月完成率</h4>
              <div class="stat-big">{{ monthDone.rate }}<small>%</small></div>
              <div class="stat-sub">{{ monthDone.done }}/{{ monthDone.total }} 项非随手池任务已完成</div>
            </div>

            <div class="stat-card">
              <h4>复盘习惯</h4>
              <div class="stat-big">{{ reviewStreak }}<small>天连续</small></div>
              <div class="stat-sub">今日 {{ store.state.reviews[todayStr()] ? '已复盘 ✓' : '还未复盘' }}</div>
            </div>

            <div class="stat-card">
              <h4>本月精力分布</h4>
              <div v-for="d in energyDist" :key="d.key" class="dist-row">
                <span class="dist-label">{{ d.icon }} {{ d.label }}</span>
                <div class="dist-track">
                  <div class="dist-fill" :style="{ width: `${d.pct}%`, backgroundColor: d.color }"></div>
                </div>
                <span class="dist-num">{{ d.n }}</span>
              </div>
            </div>

            <div class="stat-card">
              <h4>最近 7 天</h4>
              <div class="trend-chart">
                <div v-for="d in trend.days" :key="d.date" class="trend-col" :title="`${d.date}：${d.done}/${d.planned} 完成`">
                  <div class="trend-bars">
                    <div
                      v-for="i in d.planned"
                      :key="i"
                      class="trend-dot"
                      :class="{ done: i <= d.done }"
                    ></div>
                  </div>
                  <div class="trend-label" :class="{ today: d.date === todayStr() }">{{ d.label }}</div>
                </div>
              </div>
              <div class="stat-sub">格子 = 当日计划任务数，实心 = 已完成</div>
            </div>

            <div class="stat-card stats-full">
              <h4>数据概览</h4>
              <div class="stat-sub">
                任务总数 {{ dataOverview.taskCount }} 条（含随手池 {{ dataOverview.quickCount }} 条）·
                每日主题 {{ dataOverview.dayCount }} 天 · {{ storageNote }}，可随时导出 JSON 备份
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.trend-chart { display: flex; gap: 6px; align-items: flex-end; min-height: 72px; }
.trend-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 5px; }
.trend-bars { display: flex; flex-direction: column-reverse; gap: 2px; align-items: center; }
.trend-dot { width: 12px; height: 7px; border-radius: 2px; background: #e2e8f0; }
.trend-dot.done { background: var(--ok); }
.trend-label { font-size: 10px; color: var(--text-3); white-space: nowrap; }
.trend-label.today { color: var(--accent); font-weight: 700; }
</style>

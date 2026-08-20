import { reactive, readonly, watch } from 'vue'
import type { DeepReadonly } from 'vue'
import type { EnergyType, PlannerData, Task, TaskStatus } from '../types'
import { createServerSync } from './useServerSync'
import { fmt, minToTime, timeToMin, uid } from '../utils/date'

const STORAGE_KEY = 'task-planner-data-v1'

function sanitize(raw: unknown): PlannerData | null {
  if (!raw || typeof raw !== 'object') return null
  const d = raw as Partial<PlannerData>
  if (!Array.isArray(d.tasks)) return null
  return {
    version: 1,
    tasks: d.tasks,
    reviews: (d.reviews && typeof d.reviews === 'object') ? d.reviews : {},
    days: (d.days && typeof d.days === 'object') ? d.days : {},
  }
}

function loadLocal(): PlannerData {
  try {
    return sanitize(JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'))
      ?? { version: 1, tasks: [], reviews: {}, days: {} }
  } catch {
    return { version: 1, tasks: [], reviews: {}, days: {} }
  }
}

export interface NewTaskInput {
  title: string
  date: string
  start_time?: string | null
  duration_minutes?: number | null
  energy?: EnergyType
  block?: string | null
  notes?: string | null
}

export interface ReviewInput {
  highlights: string
  problems: string
  improvements: string
  energy_rating: number | null
}

function createPlannerStore() {
  const sync = createServerSync()
  const state = reactive<PlannerData>(loadLocal())

  // ---- 持久化：localStorage 即时写 + 服务器防抖推送 ----
  let pushTimer: ReturnType<typeof setTimeout> | undefined
  let pushSeq = 0

  function persistLocal() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }

  async function pushNow() {
    const seq = ++pushSeq
    const ok = await sync.push(JSON.parse(JSON.stringify(state)))
    // 只有最后一次推送的结果才更新状态，避免乱序回写
    if (seq === pushSeq) sync.setStatus(ok ? 'synced' : 'error')
  }

  function schedulePush() {
    clearTimeout(pushTimer)
    pushTimer = setTimeout(() => {
      void pushNow()
    }, 400)
  }

  watch(state, () => {
    persistLocal()
    if (sync.status.value !== 'local') schedulePush()
  }, { deep: true })

  // ---- 初始化：以服务器（scripts/data）为准，服务器为空时迁移本地上行 ----
  void (async () => {
    const remote = await sync.pull()
    if (!remote) {
      sync.setStatus('local')
      return
    }
    if (remote.tasks.length > 0) {
      Object.assign(state, remote)
      persistLocal()
    } else if (state.tasks.length > 0) {
      schedulePush()
    }
    sync.setStatus('synced')
  })()

  // ---- 查询 ----
  function tasksOf(date: string): Task[] {
    return state.tasks.filter(t => t.date === date)
  }

  function findTask(id: string): Task | undefined {
    return state.tasks.find(t => t.id === id)
  }

  // ---- 任务操作 ----
  function addTask(input: NewTaskInput): Task {
    const start = input.start_time?.trim() || null
    const dur = input.duration_minutes ?? null
    const task: Task = {
      id: uid(),
      is_quick: false,
      title: input.title.trim(),
      date: input.date,
      start_time: start,
      end_time: start && dur ? minToTime(timeToMin(start) + dur) : null,
      duration_minutes: dur,
      energy: input.energy ?? 'deep',
      status: 'planned',
      block: input.block?.trim() || null,
      notes: input.notes?.trim() || null,
      reflection: null,
      actual_minutes: null,
      created_at: new Date().toISOString(),
    }
    state.tasks.push(task)
    return task
  }

  function addQuickTask(title: string, minutes: number, date: string): Task {
    const task: Task = {
      id: uid(),
      is_quick: true,
      title: title.trim(),
      date,
      start_time: null,
      end_time: null,
      duration_minutes: minutes,
      energy: 'shallow',
      status: 'planned',
      block: null,
      notes: null,
      reflection: null,
      actual_minutes: null,
      created_at: new Date().toISOString(),
    }
    state.tasks.push(task)
    return task
  }

  function updateTask(id: string, patch: Partial<Task>) {
    const t = findTask(id)
    if (!t) return
    Object.assign(t, patch, { updated_at: new Date().toISOString() })
    if ('start_time' in patch || 'duration_minutes' in patch) {
      t.end_time = t.start_time && t.duration_minutes
        ? minToTime(timeToMin(t.start_time) + t.duration_minutes)
        : null
    }
  }

  function deleteTask(id: string) {
    const i = state.tasks.findIndex(t => t.id === id)
    if (i >= 0) state.tasks.splice(i, 1)
  }

  const CYCLE: TaskStatus[] = ['planned', 'in-progress', 'done']

  function cycleStatus(id: string) {
    const t = findTask(id)
    if (!t) return
    const i = CYCLE.indexOf(t.status) // backlog → -1 → 归位到 planned
    t.status = CYCLE[(i + 1) % CYCLE.length]
    t.updated_at = new Date().toISOString()
  }

  function toggleQuick(id: string) {
    const t = findTask(id)
    if (!t) return
    t.status = t.status === 'done' ? 'planned' : 'done'
  }

  function moveTask(id: string, date: string) {
    const t = findTask(id)
    if (!t || t.date === date) return
    t.date = date
    t.updated_at = new Date().toISOString()
  }

  // ---- 每日复盘 ----
  function saveReview(date: string, input: ReviewInput) {
    state.reviews[date] = { ...input, saved_at: new Date().toISOString() }
  }

  function deleteReview(date: string) {
    delete state.reviews[date]
  }

  // ---- 当日主题 ----
  function setTheme(date: string, theme: string) {
    if (theme.trim()) {
      state.days[date] = { ...(state.days[date] || {}), theme: theme.trim() }
    } else if (state.days[date]) {
      delete state.days[date].theme
      if (Object.keys(state.days[date]).length === 0) delete state.days[date]
    }
  }

  // ---- 数据管理 ----
  function importData(raw: unknown): boolean {
    const d = sanitize(raw)
    if (!d) return false
    Object.assign(state, d)
    return true
  }

  function clearAll() {
    Object.assign(state, { version: 1, tasks: [], reviews: {}, days: {} })
  }

  function exportPayload(): PlannerData & { exported_at: string } {
    return { ...JSON.parse(JSON.stringify(state)), exported_at: new Date().toISOString() }
  }

  function loadDemo() {
    const t = new Date()
    const dOff = (n: number) => {
      const d = new Date(t)
      d.setDate(t.getDate() + n)
      return fmt(d)
    }
    const mk = (o: Partial<Task>): Task => ({
      id: uid(), is_quick: false, title: '', date: dOff(0), start_time: null, end_time: null,
      duration_minutes: null, energy: 'deep', status: 'planned', block: null, notes: null,
      reflection: null, actual_minutes: null, created_at: new Date().toISOString(), ...o,
    })
    state.days[dOff(0)] = { theme: '深度工作日' }
    state.tasks.push(
      mk({ title: '方案撰写（初稿）', date: dOff(0), start_time: '08:30', duration_minutes: 90, energy: 'deep', block: '上午深度块' }),
      mk({ title: '整理笔记与资料归档', date: dOff(0), start_time: '10:15', duration_minutes: 45, energy: 'shallow', block: '上午深度块' }),
      mk({ title: '回复邮件', date: dOff(0), start_time: '11:00', duration_minutes: 30, energy: 'shallow', block: '上午收尾' }),
      mk({ title: '团队周会', date: dOff(0), start_time: '14:00', duration_minutes: 30, energy: 'collaboration', block: '下午沟通块' }),
      mk({ title: '学习课程模块 3', date: dOff(0), start_time: '16:00', duration_minutes: 60, energy: 'learning', block: '傍晚学习块' }),
      mk({ title: '取快递', date: dOff(0), is_quick: true, duration_minutes: 10, energy: 'shallow' }),
      mk({ title: '充话费', date: dOff(0), is_quick: true, duration_minutes: 5, energy: 'shallow' }),
      mk({ title: '接口对齐会议', date: dOff(1), start_time: '10:00', duration_minutes: 45, energy: 'collaboration', block: '上午沟通块' }),
      mk({ title: '方案修改（二稿）', date: dOff(1), start_time: '14:00', duration_minutes: 90, energy: 'deep', block: '下午深度块' }),
    )
    state.reviews[dOff(-1)] = {
      highlights: '完成了方案调研，确定了技术选型',
      problems: '下午被临时会议打断，深度块只完成一半',
      improvements: '明天把深度块提前到上午 8:30，会议集中排在下午',
      energy_rating: 3,
      saved_at: new Date().toISOString(),
    }
  }

  return {
    state: readonly(state) as DeepReadonly<PlannerData>,
    sync,
    tasksOf,
    findTask,
    addTask,
    addQuickTask,
    updateTask,
    deleteTask,
    cycleStatus,
    toggleQuick,
    moveTask,
    saveReview,
    deleteReview,
    setTheme,
    importData,
    clearAll,
    exportPayload,
    loadDemo,
  }
}

export type PlannerStore = ReturnType<typeof createPlannerStore>

let store: PlannerStore | null = null

/** 全局数据 store 单例：状态只读暴露，修改一律走显式 actions */
export function usePlannerStore(): PlannerStore {
  if (!store) store = createPlannerStore()
  return store
}

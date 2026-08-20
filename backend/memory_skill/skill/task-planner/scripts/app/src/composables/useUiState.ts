import { shallowRef } from 'vue'
import { fmt } from '../utils/date'

export type ModalFocus = 'edit' | 'review'

export interface UiState {
  selectedDate: { readonly value: string }
  calYear: { readonly value: number }
  calMonth: { readonly value: number }
  editingTaskId: { readonly value: string | null }
  modalFocus: { readonly value: ModalFocus }
  statsOpen: { readonly value: boolean }
  flashTaskId: { readonly value: string | null }
  selectDate: (date: string) => void
  shiftMonth: (delta: number) => void
  goToday: () => void
  openStats: () => void
  closeStats: () => void
  openTaskEditor: (id: string, focus?: ModalFocus) => void
  closeTaskEditor: () => void
  flashTask: (id: string) => void
}

function createUiState(): UiState {
  const now = new Date()
  const selectedDate = shallowRef(fmt(now))
  const calYear = shallowRef(now.getFullYear())
  const calMonth = shallowRef(now.getMonth()) // 0-based
  const editingTaskId = shallowRef<string | null>(null)
  const modalFocus = shallowRef<ModalFocus>('edit')
  const statsOpen = shallowRef(false)
  const flashTaskId = shallowRef<string | null>(null)

  function shiftMonth(delta: number) {
    const d = new Date(calYear.value, calMonth.value + delta, 1)
    calYear.value = d.getFullYear()
    calMonth.value = d.getMonth()
  }

  function selectDate(date: string) {
    selectedDate.value = date
  }

  function goToday() {
    const t = new Date()
    calYear.value = t.getFullYear()
    calMonth.value = t.getMonth()
    selectedDate.value = fmt(t)
  }

  function openStats() {
    statsOpen.value = true
  }

  function closeStats() {
    statsOpen.value = false
  }

  function openTaskEditor(id: string, focus: ModalFocus = 'edit') {
    editingTaskId.value = id
    modalFocus.value = focus
  }

  function closeTaskEditor() {
    editingTaskId.value = null
  }

  /** 高亮某条任务（日历 chip 点击后联动右侧面板） */
  function flashTask(id: string) {
    flashTaskId.value = id
    setTimeout(() => {
      if (flashTaskId.value === id) flashTaskId.value = null
    }, 1300)
  }

  return {
    selectedDate,
    calYear,
    calMonth,
    editingTaskId,
    modalFocus,
    statsOpen,
    flashTaskId,
    selectDate,
    shiftMonth,
    goToday,
    openStats,
    closeStats,
    openTaskEditor,
    closeTaskEditor,
    flashTask,
  }
}

let ui: UiState | null = null

/** 全局 UI 状态单例（选中日期/月份导航/弹窗开关） */
export function useUiState(): UiState {
  if (!ui) ui = createUiState()
  return ui
}

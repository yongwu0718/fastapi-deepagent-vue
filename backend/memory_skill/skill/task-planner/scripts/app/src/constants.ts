import type { EnergyType, TaskStatus } from './types'

export const ENERGY: Record<EnergyType, { label: string; icon: string; color: string }> = {
  deep: { label: '深度专注', icon: '🔵', color: '#3b82f6' },
  collaboration: { label: '沟通协作', icon: '🟡', color: '#f59e0b' },
  shallow: { label: '机械执行', icon: '⚪', color: '#94a3b8' },
  learning: { label: '学习充电', icon: '🟢', color: '#22c55e' },
}

export const STATUS: Record<TaskStatus, { label: string; icon: string }> = {
  planned: { label: '计划中', icon: '📋' },
  'in-progress': { label: '进行中', icon: '🔄' },
  done: { label: '已完成', icon: '✅' },
  backlog: { label: '待定', icon: '⏳' },
}

export const DOW_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'] as const

/** 精力评分表情：1-5 */
export const RATING_FACES = ['', '😫', '😣', '😕', '🙂', '🤩'] as const

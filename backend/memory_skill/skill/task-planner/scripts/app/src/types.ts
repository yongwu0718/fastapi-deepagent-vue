// 与 assets/daily_plan_schema.json 的枚举保持一致
export type EnergyType = 'deep' | 'collaboration' | 'shallow' | 'learning'
export type TaskStatus = 'planned' | 'in-progress' | 'done' | 'backlog'

export interface Task {
  id: string
  is_quick: boolean
  title: string
  /** 日期，格式 YYYY-MM-DD */
  date: string
  /** 开始时间 HH:MM */
  start_time: string | null
  end_time: string | null
  duration_minutes: number | null
  energy: EnergyType
  status: TaskStatus
  /** 所属时间块，如"上午深度块" */
  block: string | null
  notes: string | null
  /** 任务复盘笔记 */
  reflection: string | null
  actual_minutes: number | null
  created_at: string
  updated_at?: string
}

export interface DailyReviewData {
  highlights: string
  problems: string
  improvements: string
  /** 精力状态评分 1-5，null 表示未评 */
  energy_rating: number | null
  saved_at: string
}

export interface DayMeta {
  theme?: string
}

export interface PlannerData {
  version: number
  tasks: Task[]
  /** key: YYYY-MM-DD */
  reviews: Record<string, DailyReviewData>
  days: Record<string, DayMeta>
}

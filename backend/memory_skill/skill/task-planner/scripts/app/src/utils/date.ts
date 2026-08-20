export const pad = (n: number): string => String(n).padStart(2, '0')

export const fmt = (d: Date): string =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

export const parseDate = (s: string): Date => {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export const todayStr = (): string => fmt(new Date())

export const uid = (): string =>
  't' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)

/** "YYYY-MM" 前缀，用于按月过滤 */
export const monthPrefix = (year: number, month: number): string =>
  `${year}-${pad(month + 1)}`

export const timeToMin = (t: string): number => {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

export const minToTime = (m: number): string => {
  m = ((m % 1440) + 1440) % 1440
  return `${pad(Math.floor(m / 60))}:${pad(m % 60)}`
}

export interface CalendarCell {
  date: string
  day: number
  /** 0-based 月份 */
  month: number
  inMonth: boolean
  isToday: boolean
  isFirstOfMonth: boolean
}

/** 生成以周一为一周开始的月历网格（含跨月补齐） */
export function monthGrid(year: number, month: number): CalendarCell[] {
  const first = new Date(year, month, 1)
  const offset = (first.getDay() + 6) % 7
  const start = new Date(year, month, 1 - offset)
  const last = new Date(year, month + 1, 0)
  const endOffset = (last.getDay() + 6) % 7
  const end = new Date(year, month + 1, 6 - endOffset)

  const today = todayStr()
  const cells: CalendarCell[] = []
  for (const d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const date = fmt(d)
    cells.push({
      date,
      day: d.getDate(),
      month: d.getMonth(),
      inMonth: d.getMonth() === month,
      isToday: date === today,
      isFirstOfMonth: d.getDate() === 1,
    })
  }
  return cells
}

/** 分钟数转可读时长：90 → "1小时30分钟" */
export function minText(m: number | null | undefined): string {
  const n = Number(m) || 0
  if (!n) return '0分钟'
  if (n % 60 === 0) return `${n / 60}小时`
  if (n < 60) return `${n}分钟`
  return `${Math.floor(n / 60)}小时${n % 60}分钟`
}

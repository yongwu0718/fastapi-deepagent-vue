/**
 * 结构化日志工具
 *
 * 特性：
 * - 5 级日志：trace / debug / info / warn / error
 * - 生产环境默认关闭 trace/debug/info（仅 warn/error 输出）
 * - 开发环境全量输出
 * - 模块前缀标签（便于 Console 过滤）
 * - 支持结构化数据（对象自动序列化）
 * - 可通过 URL 参数 ?log=trace 在生产临时开启
 *
 * 使用示例：
 *   const log = createLogger('[SSE]')
 *   log.debug('checkpoint received', { cid, pcid })
 *   log.warn('No threadId, aborting')
 *   log.error('Request failed', err)
 */

// ── 日志级别 ──
export const LOG_LEVELS = ['trace', 'debug', 'info', 'warn', 'error'] as const
export type LogLevel = (typeof LOG_LEVELS)[number]

const LEVEL_WEIGHT: Record<LogLevel, number> = {
  trace: 0,
  debug: 1,
  info: 2,
  warn: 3,
  error: 4,
}

// ── 级别判定 ──
function resolveLogLevel(): LogLevel {
  // 1) URL 参数优先：?log=trace 可在生产环境临时开启
  if (typeof window !== 'undefined') {
    try {
      const params = new URLSearchParams(window.location.search)
      const param = params.get('log')
      if (param && LOG_LEVELS.includes(param as LogLevel)) {
        return param as LogLevel
      }
    } catch { /* SSR 安全 */ }
  }

  // 2) Vite 环境变量
  return import.meta.env.DEV ? 'debug' : 'warn'
}

let currentLevel: LogLevel = resolveLogLevel()

/** 判断给定级别是否应输出 */
function shouldLog(level: LogLevel): boolean {
  return LEVEL_WEIGHT[level] >= LEVEL_WEIGHT[currentLevel]
}

// ── 格式化 ──
function fmtTime(): string {
  const d = new Date()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  const ms = String(d.getMilliseconds()).padStart(3, '0')
  return `${hh}:${mm}:${ss}.${ms}`
}

function fmtArgs(args: unknown[]): string {
  return args
    .map((a) => {
      if (a instanceof Error) {
        return a.stack ?? a.message
      }
      if (typeof a === 'object' && a !== null) {
        try {
          return JSON.stringify(a)
        } catch {
          return String(a)
        }
      }
      return String(a)
    })
    .join(' ')
}

// ── 核心工厂 ──
export function createLogger(prefix: string) {
  function log(level: LogLevel, ...args: unknown[]) {
    if (!shouldLog(level)) return

    const label = `[${fmtTime()}] ${prefix}`
    const message = fmtArgs(args)

    switch (level) {
      case 'trace':
      case 'debug':
        console.debug(label, message)
        break
      case 'info':
        console.info(label, message)
        break
      case 'warn':
        console.warn(label, message)
        break
      case 'error':
        console.error(label, message)
        break
    }
  }

  return {
    trace: (...args: unknown[]) => log('trace', ...args),
    debug: (...args: unknown[]) => log('debug', ...args),
    info: (...args: unknown[]) => log('info', ...args),
    warn: (...args: unknown[]) => log('warn', ...args),
    error: (...args: unknown[]) => log('error', ...args),

    /** 运行时获取当前级别 */
    get level(): LogLevel {
      return currentLevel
    },

    /** 运行时动态修改级别（如 DevTools 中手动调） */
    setLevel(level: LogLevel) {
      ;(currentLevel as string) = level
    },
  }
}

/**
 * 浏览器控制台暴露：
 *   window.__setLogLevel('trace')   // 临时开启全量日志
 *   window.__getLogLevel()          // 查看当前级别
 *   window.__logLevels              // 列出所有级别
 */
if (typeof window !== 'undefined') {
  ;(window as Record<string, unknown>).__setLogLevel = (level: string) => {
    if (LOG_LEVELS.includes(level as LogLevel)) {
      ;(currentLevel as string) = level
      console.info(`[Logger] 日志级别已切换为: ${level}（当前可用的级别: ${LOG_LEVELS.join(', ')}）`)
    } else {
      console.warn(`[Logger] 无效级别: ${level}。可用: ${LOG_LEVELS.join(', ')}`)
    }
  }
  ;(window as Record<string, unknown>).__getLogLevel = () => currentLevel
  ;(window as Record<string, unknown>).__logLevels = LOG_LEVELS
}

// ── 预置模块 Logger ──
export const loggerSSE       = createLogger('[SSE]')
export const loggerChat      = createLogger('[Chat]')
export const loggerRetry     = createLogger('[Retry]')
export const loggerFork      = createLogger('[Fork]')
export const loggerCheckpoint = createLogger('[Checkpoint]')
export const loggerVue       = createLogger('[Vue]')
export const loggerResume    = createLogger('[Resume]')

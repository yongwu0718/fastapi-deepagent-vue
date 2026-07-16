/** 轻量 toast 通知类型 */
export interface Toast {
  id: string
  type: 'info' | 'success' | 'error' | 'warning'
  title: string
  description?: string
  duration?: number
  removing?: boolean
}

type ToastListener = (toasts: Toast[]) => void

/** 简易 toast 状态管理（响应式） */
let toasts: Toast[] = []
const listeners = new Set<ToastListener>()

function notify() {
  const snapshot = [...toasts]
  listeners.forEach((fn) => fn(snapshot))
}

function removeToast(id: string) {
  const toast = toasts.find((t) => t.id === id)
  if (!toast) return
  // 先标记为移除中（触发退出动画）
  toast.removing = true
  notify()
  // 动画结束后真正移除
  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id)
    notify()
  }, 300)
}

export function addToast(toast: Omit<Toast, 'id' | 'removing'>) {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
  const duration = toast.duration ?? 4000
  toasts = [...toasts, { ...toast, id, removing: false }]
  notify()
  if (duration > 0) {
    setTimeout(() => removeToast(id), duration)
  }
  return id
}

export function dismissToast(id: string) {
  removeToast(id)
}

/** 快捷方法 */
export const toast = {
  success(title: string, description?: string) {
    addToast({ type: 'success', title, description })
  },
  error(title: string, description?: string) {
    addToast({ type: 'error', title, description, duration: 6000 })
  },
  info(title: string, description?: string) {
    addToast({ type: 'info', title, description })
  },
  warning(title: string, description?: string) {
    addToast({ type: 'warning', title, description, duration: 5000 })
  },
}

/** 订阅 toast 变化 */
export function subscribeToasts(fn: ToastListener) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

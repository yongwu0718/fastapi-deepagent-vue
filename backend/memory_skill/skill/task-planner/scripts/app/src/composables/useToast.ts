import { shallowRef } from 'vue'

export interface ToastApi {
  message: { readonly value: string }
  visible: { readonly value: boolean }
  show: (msg: string) => void
}

function createToast(): ToastApi {
  const message = shallowRef('')
  const visible = shallowRef(false)
  let timer: ReturnType<typeof setTimeout> | undefined

  function show(msg: string) {
    message.value = msg
    visible.value = true
    clearTimeout(timer)
    timer = setTimeout(() => {
      visible.value = false
    }, 2000)
  }

  return { message, visible, show }
}

let toast: ToastApi | null = null

/** 全局 toast 单例（小型非 SSR SPA，模块级单例足够） */
export function useToast(): ToastApi {
  if (!toast) toast = createToast()
  return toast
}

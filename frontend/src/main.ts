import { createApp } from 'vue'
import './style.css'
import 'katex/dist/katex.min.css'
import App from './App.vue'
import router from './router'
import { loggerVue } from '@/shared/useLogger'

const app = createApp(App)

// ── Vue 全局错误处理 ──
app.config.errorHandler = (err, instance, info) => {
  const componentName = (instance?.$ as Record<string, unknown> | undefined)?.type
    ? ((instance?.$ as Record<string, unknown> | undefined)?.type as { name?: string } | undefined)?.name
    : undefined
  loggerVue.error('未捕获的组件错误', {
    message: err instanceof Error ? err.message : String(err),
    stack: err instanceof Error ? err.stack : undefined,
    component: componentName ?? 'Unknown',
    info,
  })
}

// 生产环境也保留 warnHandler 用于调试
app.config.warnHandler = (msg, _instance, trace) => {
  loggerVue.warn(msg)
  if (trace) loggerVue.debug('组件调用栈', trace)
}

app.use(router).mount('#app')

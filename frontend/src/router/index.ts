import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

const LS_ACTIVE_THREAD_KEY = 'chat_active_thread_id'

/**
 * 路由配置
 * - /              → 自动重定向到上次活跃线程或新建线程
 * - /chat/:threadId → 主聊天视图
 * - /settings      → 设置管理页面
 * - /rag           → RAG 向量库管理页面
 */
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: () => {
      try {
        const lastId = localStorage.getItem(LS_ACTIVE_THREAD_KEY)
        if (lastId) return { path: `/chat/${lastId}`, replace: true }
      } catch { /* localStorage 不可用 */ }
      return { path: `/chat/${crypto.randomUUID()}`, replace: true }
    },
  },
  {
    path: '/chat/:threadId',
    name: 'chat',
    component: () => import('@/layout/ChatLayout.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/settings/SettingsView.vue'),
  },
  {
    path: '/rag',
    name: 'rag',
    component: () => import('@/rag/RagManagement.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router

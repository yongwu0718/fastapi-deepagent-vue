import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { useAuth } from '@/stores/useAuth'

const LS_ACTIVE_THREAD_KEY = 'chat_active_thread_id'

/**
 * 路由配置
 * - /login         → 登录页面
 * - /register      → 注册页面
 * - /              → 自动重定向到上次活跃线程或新建线程（需登录）
 * - /chat/:threadId → 主聊天视图（需登录）
 * - /settings      → 设置管理页面（需登录）
 * - /rag           → RAG 向量库管理页面（需登录）
 * - /scheduled-tasks → 定时任务管理页面（需登录）
 */
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
  },
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
  {
    path: '/scheduled-tasks',
    name: 'scheduled-tasks',
    component: () => import('@/views/ScheduledTasksView.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// ── 路由守卫：未登录重定向到登录页 ──
router.beforeEach((to, _from, next) => {
  const { isAuthenticated } = useAuth()

  if (to.path === '/login' || to.path === '/register') {
    // 已登录用户访问登录/注册页 → 重定向到主页
    if (isAuthenticated.value) {
      next('/')
      return
    }
    next()
    return
  }

  // 未登录用户访问任何其他页面 → 重定向到登录页
  if (!isAuthenticated.value) {
    next('/login')
    return
  }

  next()
})

export default router

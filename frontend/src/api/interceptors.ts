import { client } from '@/api/client/client.gen'
import { useAuth } from '@/stores/useAuth'

let _initialized = false

export function setupAuthInterceptors() {
  if (_initialized) return
  _initialized = true

  // ── 请求拦截器：自动附加 Authorization header ──
  client.interceptors.request.use(async (request) => {
    const { getToken } = useAuth()
    const t = getToken()
    if (t) {
      request.headers.set('Authorization', `Bearer ${t}`)
    }
    return request
  })

  // ── 响应拦截器：检测 401 自动清除登录态 ──
  client.interceptors.response.use(async (response) => {
    if (response.status === 401) {
      const { clearAuth } = useAuth()
      clearAuth()
    }
    return response
  })
}

import { ref, computed } from 'vue'

const TOKEN_KEY = 'auth_token'
const USERNAME_KEY = 'auth_username'

const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
const username = ref<string | null>(localStorage.getItem(USERNAME_KEY))

export function useAuth() {
  const isAuthenticated = computed(() => token.value !== null)

  function setAuth(accessToken: string, user: string) {
    token.value = accessToken
    username.value = user
    localStorage.setItem(TOKEN_KEY, accessToken)
    localStorage.setItem(USERNAME_KEY, user)
  }

  function clearAuth() {
    token.value = null
    username.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USERNAME_KEY)
  }

  function getToken(): string | null {
    return token.value
  }

  return {
    token,
    username,
    isAuthenticated,
    setAuth,
    clearAuth,
    getToken,
  }
}

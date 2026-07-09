import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../services/api.js'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const checked = ref(false)

  const isAuthenticated = computed(() => !!user.value)

  async function fetchMe() {
    try {
      const res = await authApi.me()
      user.value = res.data
    } catch {
      user.value = null
    } finally {
      checked.value = true
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      user.value = null
      window.location.href = '/'
    }
  }

  async function updateUsername(username) {
    const res = await authApi.updateMe({ username })
    user.value = res.data
  }

  return { user, checked, isAuthenticated, fetchMe, logout, updateUsername }
})

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!user.value)
  const role = computed(() => user.value?.role || '')
  const permissions = computed(() => user.value?.permissions || [])
  const token = computed(() => user.value?.token || '')

  function setUser(data) {
    user.value = data
    localStorage.setItem('user', JSON.stringify(data))
    axios.defaults.headers.common['Authorization'] = `Bearer ${data.token}`
  }

  function logout() {
    user.value = null
    localStorage.removeItem('user')
    delete axios.defaults.headers.common['Authorization']
  }

  function hasPermission(page) {
    return permissions.value.includes(page)
  }

  // 初始化时恢复 token
  if (user.value?.token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${user.value.token}`
  }

  return { user, isLoggedIn, role, permissions, token, setUser, logout, hasPermission }
})

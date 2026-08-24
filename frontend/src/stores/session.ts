import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, type DataRecord } from '../api'

export const useSessionStore = defineStore('session', () => {
  const summaryRefreshInterval = 30_000
  const ready = ref(false)
  const user = ref<DataRecord | null>(null)
  const currentProject = ref<DataRecord | null>(null)
  const projects = ref<DataRecord[]>([])
  const summary = ref<DataRecord>({})
  const options = ref<DataRecord>({})
  const isAdmin = ref(false)
  const isDark = ref(localStorage.getItem('ewll-theme') === 'dark')
  let summaryRefreshTimer: number | undefined

  const loggedIn = computed(() => Boolean(user.value))

  function applyTheme() {
    document.body.setAttribute('arco-theme', isDark.value ? 'dark' : 'light')
    document.documentElement.classList.toggle('dark', isDark.value)
  }

  function toggleTheme() {
    isDark.value = !isDark.value
    localStorage.setItem('ewll-theme', isDark.value ? 'dark' : 'light')
    applyTheme()
  }

  async function load() {
    const data = await api.bootstrap()
    user.value = data.user
    currentProject.value = data.current_project
    projects.value = data.projects || []
    summary.value = data.summary || {}
    options.value = data.options || {}
    isAdmin.value = Boolean(data.is_admin)
    ready.value = true
  }

  async function switchProject(projectId: number) {
    await api.switchProject(projectId)
    await load()
  }

  async function refreshSummary() {
    const data = await api.summary()
    summary.value = data.summary || {}
  }

  function startSummaryAutoRefresh() {
    if (summaryRefreshTimer !== undefined) return
    // 全局只保留一个轮询定时器，避免路由切换后重复请求。
    summaryRefreshTimer = window.setInterval(() => {
      void refreshSummary().catch(() => undefined)
    }, summaryRefreshInterval)
  }

  function stopSummaryAutoRefresh() {
    if (summaryRefreshTimer === undefined) return
    window.clearInterval(summaryRefreshTimer)
    summaryRefreshTimer = undefined
  }

  applyTheme()
  return {
    ready, user, currentProject, projects, summary, options, isAdmin, isDark, loggedIn,
    load, refreshSummary, startSummaryAutoRefresh, stopSummaryAutoRefresh, switchProject, toggleTheme,
  }
})

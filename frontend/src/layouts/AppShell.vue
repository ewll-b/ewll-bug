<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import {
  IconBug, IconCalendar, IconCheckCircle, IconDashboard, IconFolder,
  IconMenuUnfold, IconMoon, IconNotification, IconSettings,
  IconSun, IconUser,
} from '@arco-design/web-vue/es/icon'
import { api } from '../api'
import { useSessionStore } from '../stores/session'
import { normalizeBadgeCount } from '../utils/badge'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const logoUrl = `${import.meta.env.BASE_URL}static/logo.png`
const collapsed = ref(false)
const mobileOpen = ref(false)
const selectedKey = computed(() => {
  const path = route.path
  if (path.startsWith('/bugs')) return '/bugs'
  if (path.startsWith('/cases')) return '/cases'
  if (path.startsWith('/requirements')) return '/requirements'
  if (path.startsWith('/reports')) return '/reports/testing'
  if (path.startsWith('/admin')) return '/admin'
  return path
})

const menuItems = computed(() => [
  { key: '/bugs', label: 'Bug 列表', icon: IconBug, badge: 0 },
  { key: '/todos', label: '我的待办', icon: IconCheckCircle, badge: normalizeBadgeCount(session.summary.my_todo_count) },
  { key: '/notifications', label: '消息中心', icon: IconNotification, badge: normalizeBadgeCount(session.summary.notification_unread_count) },
  { key: '/cases', label: '用例库', icon: IconFolder, badge: 0 },
  { key: '/requirements', label: '需求管理', icon: IconCalendar, badge: 0 },
  { key: '/reports/testing', label: '测试报告', icon: IconDashboard, badge: 0 },
  ...(session.isAdmin ? [{ key: '/admin', label: '系统管理', icon: IconSettings, badge: 0 }] : []),
])

async function navigate(key: string) {
  mobileOpen.value = false
  await router.push(key)
}

async function switchProject(value: unknown) {
  if (typeof value !== 'number') return
  await session.switchProject(value)
  Message.success('项目已切换')
  await router.replace({ path: route.path, query: {} })
  window.location.reload()
}

async function logout() {
  await api.logout()
  await router.replace('/login')
}

onMounted(async () => {
  // 异步路由初始化期间登录页可能短暂创建壳层，此时不请求受保护数据。
  if (route.path === '/login' || route.meta.public === true) return
  if (!session.ready) await session.load()
  session.startSummaryAutoRefresh()
})

onBeforeUnmount(() => session.stopSummaryAutoRefresh())
</script>

<template>
  <a-layout class="app-layout">
    <a-layout-header class="app-header">
      <div class="header-left">
        <a-button class="mobile-menu-button" type="text" shape="circle" aria-label="打开导航" @click="mobileOpen = true">
          <IconMenuUnfold />
        </a-button>
        <img class="brand-logo" :src="logoUrl" alt="Alvin's Club" />
        <span class="brand-name">Bug Management</span>
        <a-select
          class="project-select"
          :model-value="session.currentProject?.id"
          placeholder="选择项目"
          @change="switchProject"
        >
          <a-option v-for="item in session.projects" :key="item.id" :value="item.id">{{ item.name }}</a-option>
        </a-select>
      </div>
      <div class="header-actions">
        <a-tooltip :content="session.isDark ? '切换白天模式' : '切换黑夜模式'">
          <a-button type="text" shape="circle" aria-label="切换主题" @click="session.toggleTheme">
            <IconSun v-if="session.isDark" />
            <IconMoon v-else />
          </a-button>
        </a-tooltip>
        <a-dropdown trigger="click">
          <a-button type="text">
            <IconUser />
            {{ session.user?.name || '账号' }}
          </a-button>
          <template #content>
            <a-doption @click="router.push('/profile')">个人资料</a-doption>
            <a-doption @click="logout">退出登录</a-doption>
          </template>
        </a-dropdown>
      </div>
    </a-layout-header>
    <a-layout>
      <a-layout-sider v-model:collapsed="collapsed" class="app-sider" collapsible :width="220" :collapsed-width="56">
        <a-menu :selected-keys="[selectedKey]" @menu-item-click="navigate">
          <a-menu-item v-for="item in menuItems" :key="item.key">
            <template #icon><component :is="item.icon" /></template>
            <span>{{ item.label }}</span>
            <a-badge v-if="item.badge > 0" :count="item.badge" :max-count="99" />
          </a-menu-item>
        </a-menu>
      </a-layout-sider>
      <a-layout-content class="app-content">
        <slot />
      </a-layout-content>
    </a-layout>
    <a-drawer v-model:visible="mobileOpen" :width="280" placement="left" :footer="false" title="导航">
      <a-menu :selected-keys="[selectedKey]" @menu-item-click="navigate">
        <a-menu-item v-for="item in menuItems" :key="item.key">
          <template #icon><component :is="item.icon" /></template>
          <span>{{ item.label }}</span>
          <a-badge v-if="item.badge > 0" :count="item.badge" :max-count="99" />
        </a-menu-item>
      </a-menu>
    </a-drawer>
  </a-layout>
</template>

<style scoped>
.app-layout { width: 100%; min-height: 100vh; background: var(--app-bg); }
.app-header { position: sticky; top: 0; z-index: 30; height: 56px; padding: 0 18px; display: flex; align-items: center; justify-content: space-between; background: var(--header-bg); border-bottom: 1px solid var(--panel-border); }
.header-left, .header-actions { display: flex; align-items: center; gap: 10px; min-width: 0; }
.brand-logo { width: 30px; height: 30px; object-fit: contain; }
.brand-name { font-size: 16px; font-weight: 600; white-space: nowrap; }
.project-select { width: 190px; }
.app-sider { position: sticky; top: 56px; height: calc(100vh - 56px); padding-top: 10px; background: var(--sider-bg); border-right: 1px solid var(--panel-border); }
/* 主内容始终占满除导航外的浏览器可用区域。 */
.app-content { width: 100%; min-width: 0; min-height: calc(100vh - 56px); padding: 20px; overflow: hidden; }
.mobile-menu-button { display: none; }
@media (max-width: 768px) {
  .app-sider { display: none; }
  .mobile-menu-button { display: inline-flex; }
  .brand-name { display: none; }
  .project-select { width: 132px; }
  .app-header { padding: 0 10px; }
  .app-content { padding: 12px; }
}
</style>

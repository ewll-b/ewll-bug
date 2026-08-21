<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconLock, IconUser } from '@arco-design/web-vue/es/icon'
import { api } from '../api'
import { withAppBase, withoutAppBase } from '../api/paths'

const route = useRoute()
const logoUrl = `${import.meta.env.BASE_URL}static/logo.png`
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function submit() {
  if (!form.username || !form.password) return Message.warning('请输入账号和密码。')
  loading.value = true
  try {
    await api.login(form)
    const requestedNext = typeof route.query.next === 'string' && route.query.next.startsWith('/') && !route.query.next.startsWith('//') ? route.query.next : '/bugs'
    const next = withoutAppBase(requestedNext)
    // 完整导航同时兼容 Vue 页面与报告导出等后端资源。
    window.location.assign(withAppBase(next))
  } finally { loading.value = false }
}
</script>

<template>
  <main class="login-page">
    <section class="login-panel">
      <div class="login-brand">
        <img :src="logoUrl" alt="Alvin's Club" />
        <div><h1>Bug Management</h1><p>质量协作与缺陷跟踪平台</p></div>
      </div>
      <a-form :model="form" layout="vertical" @submit-success="submit">
        <a-form-item field="username" label="账号" required><a-input v-model="form.username" size="large" placeholder="请输入登录账号" autocomplete="username"><template #prefix><IconUser /></template></a-input></a-form-item>
        <a-form-item field="password" label="密码" required><a-input-password v-model="form.password" size="large" placeholder="请输入密码" autocomplete="current-password" allow-clear><template #prefix><IconLock /></template></a-input-password></a-form-item>
        <a-button type="primary" size="large" long :loading="loading" html-type="submit">登录</a-button>
      </a-form>
    </section>
  </main>
</template>

<style scoped>
.login-page { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: var(--app-bg); }
.login-panel { width: min(420px, 100%); padding: 32px; background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 8px; box-shadow: 0 10px 32px rgb(0 0 0 / 8%); }
.login-brand { display: flex; align-items: center; gap: 14px; margin-bottom: 28px; }
.login-brand img { width: 46px; height: 46px; object-fit: contain; }
.login-brand h1 { margin: 0; font-size: 22px; letter-spacing: 0; }
.login-brand p { margin: 4px 0 0; color: var(--muted-text); }
</style>

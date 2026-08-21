<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconCheck, IconNotification } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import PageHeader from '../components/PageHeader.vue'

const router = useRouter()
const loading = ref(false)
const state = ref('')
const data = ref<DataRecord>({ items: [], unread_count: 0, total_count: 0 })
async function load() { loading.value = true; try { data.value = await api.notifications(state.value) } finally { loading.value = false } }
async function readAll() { const result = await api.readAllNotifications(); Message.success(result.message || '已全部标记为已读'); await load() }
async function open(item: DataRecord) {
  const result = await api.readNotification(Number(item.id)); const link = result.data?.link_path || item.link_path || '/notifications'
  await router.push(String(link).replace(/^\/for-test/, '')); await load()
}
onMounted(load)
</script>

<template>
  <div class="page-stack">
    <PageHeader title="消息中心" :description="`共 ${data.total_count || 0} 条，${data.unread_count || 0} 条未读`"><a-button :disabled="!data.unread_count" @click="readAll"><IconCheck />全部已读</a-button></PageHeader>
    <section class="page-panel page-stack">
      <a-tabs v-model:active-key="state" @change="load"><a-tab-pane key="" title="全部" /><a-tab-pane key="unread" title="未读" /></a-tabs>
      <a-list :loading="loading" :data="data.items" :bordered="false">
        <template #item="{ item }">
          <a-list-item action-layout="vertical" class="notification-item" @click="open(item)">
            <a-list-item-meta :title="item.title" :description="item.body"><template #avatar><a-badge :dot="!item.is_read"><a-avatar><IconNotification /></a-avatar></a-badge></template></a-list-item-meta>
            <template #actions><span>{{ item.created_at }}</span><a-tag>{{ item.category }}</a-tag></template>
          </a-list-item>
        </template>
      </a-list>
    </section>
  </div>
</template>

<style scoped>.notification-item { cursor: pointer; border-radius: 4px; }.notification-item:hover { background: var(--color-fill-1); }</style>

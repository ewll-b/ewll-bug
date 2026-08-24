<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconCheck, IconNotification } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import { useSessionStore } from '../stores/session'
import PageHeader from '../components/PageHeader.vue'
import BugDetailDrawer from '../components/BugDetailDrawer.vue'
import RequirementDetailDrawer from '../components/RequirementDetailDrawer.vue'
import CaseDocumentDrawer from '../components/CaseDocumentDrawer.vue'

const router = useRouter()
const session = useSessionStore()
const loading = ref(false)
const state = ref('')
const data = ref<DataRecord>({ items: [], unread_count: 0, total_count: 0 })
const bugId = ref<number>(); const bugVisible = ref(false)
const requirementId = ref<number>(); const requirementVisible = ref(false)
const documentId = ref<number>(); const documentVisible = ref(false)
async function load() { loading.value = true; try { data.value = await api.notifications(state.value) } finally { loading.value = false } }
async function readAll() {
  const result = await api.readAllNotifications()
  Message.success(result.message || '已全部标记为已读')
  await Promise.all([load(), session.refreshSummary()])
}
async function open(item: DataRecord) {
  const result = await api.readNotification(Number(item.id)); const link = result.data?.link_path || item.link_path || '/notifications'
  const path = String(link).replace(/^\/for-test/, '')
  // 消息列表中的实体详情也统一进入抽屉，其他功能链接保持正常跳转。
  const bugMatch = path.match(/^\/bugs\/(\d+)/)
  const requirementMatch = path.match(/^\/requirements\/(\d+)/)
  const documentMatch = path.match(/^\/cases\/(\d+)/)
  if (bugMatch) { bugId.value = Number(bugMatch[1]); bugVisible.value = true }
  else if (requirementMatch) { requirementId.value = Number(requirementMatch[1]); requirementVisible.value = true }
  else if (documentMatch) { documentId.value = Number(documentMatch[1]); documentVisible.value = true }
  else await router.push(path)
  await Promise.all([load(), session.refreshSummary()])
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
            <a-list-item-meta :title="item.title" :description="item.body">
              <template #avatar>
                <a-badge v-if="!item.is_read" dot :count="1"><a-avatar><IconNotification /></a-avatar></a-badge>
                <a-avatar v-else><IconNotification /></a-avatar>
              </template>
            </a-list-item-meta>
            <template #actions><span>{{ item.created_at }}</span><a-tag>{{ item.category }}</a-tag></template>
          </a-list-item>
        </template>
      </a-list>
    </section>
    <BugDetailDrawer v-model:visible="bugVisible" :bug-id="bugId" @changed="load" @deleted="load" />
    <RequirementDetailDrawer v-model:visible="requirementVisible" :requirement-id="requirementId" @changed="load" @deleted="load" />
    <CaseDocumentDrawer v-model:visible="documentVisible" :document-id="documentId" />
  </div>
</template>

<style scoped>.notification-item { cursor: pointer; border-radius: 4px; }.notification-item:hover { background: var(--color-fill-1); }</style>

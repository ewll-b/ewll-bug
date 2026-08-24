<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconRefresh } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import { useSessionStore } from '../stores/session'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import BugDetailDrawer from '../components/BugDetailDrawer.vue'

const session = useSessionStore()
const loading = ref(false)
const items = ref<DataRecord[]>([])
const detailVisible = ref(false)
const selectedBugId = ref<number>()
const columns = [
  { title: '编号', dataIndex: 'bug_no', slotName: 'bugNo', width: 100 },
  { title: '项目', dataIndex: 'project_name', width: 150 },
  { title: '标题', dataIndex: 'title', slotName: 'title', width: 300 },
  { title: '端', dataIndex: 'platform', width: 90 },
  { title: '严重级别', dataIndex: 'severity', width: 100 },
  { title: '状态', dataIndex: 'status', slotName: 'status', width: 150 },
  { title: '更新时间', dataIndex: 'updated_at', width: 170 },
]
async function load() {
  loading.value = true
  try {
    items.value = (await api.todos()).items || []
    if (session.ready) await session.refreshSummary()
  } finally {
    loading.value = false
  }
}
async function updateStatus(item: DataRecord, status: unknown) {
  if (typeof status !== 'string') return
  const form = new FormData(); form.set('action', 'change_status'); form.set('status', status)
  const result = await api.bugAction(Number(item.id), form); Message.success(result.message || '已更新'); await load()
}
function openDetail(id: number) { selectedBugId.value = id; detailVisible.value = true }
onMounted(async () => { if (!session.ready) await session.load(); await load() })
</script>

<template>
  <div class="page-stack">
    <PageHeader title="我的待办" description="展示当前账号在全部项目中的待处理缺陷"><a-button @click="load"><IconRefresh />刷新</a-button></PageHeader>
    <section class="page-panel">
      <a-table :columns="columns" :data="items" :loading="loading" :pagination="false" row-key="id" :scroll="{ x: 1000 }" stripe>
        <template #bugNo="{ record }"><a-link class="table-link" @click="openDetail(Number(record.id))">{{ record.bug_no }}</a-link></template>
        <template #title="{ record }"><a-link class="table-link" @click="openDetail(Number(record.id))">{{ record.title }}</a-link></template>
        <template #status="{ record }"><a-select :model-value="record.status" size="small" @change="(value) => updateStatus(record, value)"><a-option v-for="item in session.options.statuses" :key="item.value" :value="item.value"><StatusTag :status="item.value" /></a-option></a-select></template>
      </a-table>
    </section>
    <BugDetailDrawer v-model:visible="detailVisible" :bug-id="selectedBugId" @changed="load" @deleted="load" />
  </div>
</template>

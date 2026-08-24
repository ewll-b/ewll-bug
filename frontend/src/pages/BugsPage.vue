<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconPlus, IconRefresh, IconSearch } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import { useSessionStore } from '../stores/session'
import PageHeader from '../components/PageHeader.vue'
import StatusSelect from '../components/StatusSelect.vue'
import BugFormModal from '../components/BugFormModal.vue'
import BugDetailDrawer from '../components/BugDetailDrawer.vue'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const loading = ref(false)
const modalVisible = ref(false)
const bugInitialValues = ref<DataRecord | null>(null)
const detailVisible = ref(false)
const selectedBugId = ref<number>()
const data = ref<DataRecord>({ page: { items: [], total: 0, page: 1 }, summary: {}, versions: [], users: [], requirements: [], cases: [] })
const filters = reactive<DataRecord>({ keyword: '', version: [], platform: [], status: [], creator_id: [], assignee_id: [], created_from: '', created_to: '', page: 1 })
const columns = [
  { title: '编号', dataIndex: 'bug_no', slotName: 'bugNo', width: 100 },
  { title: '标题', dataIndex: 'title', slotName: 'title', width: 280 },
  { title: '版本', dataIndex: 'version', width: 110 },
  { title: '端', dataIndex: 'platform', width: 90 },
  { title: '严重级别', dataIndex: 'severity', slotName: 'severity', width: 110 },
  { title: '状态', dataIndex: 'status', slotName: 'status', width: 120 },
  { title: '当前处理人', dataIndex: 'assignee_name', width: 120 },
  { title: '创建人', dataIndex: 'creator_name', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', width: 168 },
]

function hydrateQuery() {
  for (const key of ['version', 'platform', 'status', 'creator_id', 'assignee_id']) {
    const value = route.query[key]
    filters[key] = value ? (Array.isArray(value) ? value : [value]) : []
  }
  filters.keyword = String(route.query.keyword || '')
  filters.created_from = String(route.query.created_from || '')
  filters.created_to = String(route.query.created_to || '')
  filters.page = Number(route.query.page || 1)
}

async function load() {
  loading.value = true
  try {
    data.value = await api.bugs({ ...filters })
    await openCreateBugFromCaseQuery()
  } finally { loading.value = false }
}

async function syncQueryAndLoad() {
  // 统一同步当前筛选和页码，避免翻页时被查询逻辑重置。
  const query: DataRecord = {}
  Object.entries(filters).forEach(([key, value]) => { if (Array.isArray(value) ? value.length : value) query[key] = value })
  await router.replace({ query })
  await load()
}

async function search() {
  if (Array.isArray(filters.createdRange) && filters.createdRange.length === 2) {
    filters.created_from = filters.createdRange[0]
    filters.created_to = filters.createdRange[1]
  } else {
    filters.created_from = ''
    filters.created_to = ''
  }
  filters.page = 1
  await syncQueryAndLoad()
}

async function changePage(page: number) {
  filters.page = page
  await syncQueryAndLoad()
}

function openDetail(id: number) { selectedBugId.value = id; detailVisible.value = true }

function failedPlatformForCase(caseItem: DataRecord) {
  if (caseItem.android_result === 'failed') return 'Android'
  if (caseItem.ios_result === 'failed') return 'iOS'
  if (caseItem.h5_result === 'failed') return 'H5'
  return ''
}

function buildBugInitialValuesFromCase(caseItem: DataRecord) {
  const caseNo = String(caseItem.case_no || '').trim()
  const caseTitle = String(caseItem.title || '').trim()
  return {
    title: caseNo && caseTitle ? `${caseNo} ${caseTitle}` : caseTitle || caseNo,
    version: String(caseItem.version || '').trim(),
    platform: failedPlatformForCase(caseItem),
    severity: '高',
    case_id: caseItem.id,
    environment: String(caseItem.environment_info || '').trim(),
    description: String(caseItem.steps || '').trim(),
    expected_result: String(caseItem.expected_result || '').trim(),
    actual_result: '',
  }
}

function openCreateBug(initialValues: DataRecord | null = null) {
  bugInitialValues.value = initialValues
  modalVisible.value = true
}

async function openCreateBugFromCaseQuery() {
  const caseId = Number(route.query.case_id || 0)
  if (!caseId || modalVisible.value) return
  const caseItem = data.value.cases.find((item: DataRecord) => Number(item.id) === caseId)
  if (!caseItem) {
    Message.warning('未找到要关联的用例，请确认当前项目是否正确。')
    return
  }
  openCreateBug(buildBugInitialValuesFromCase(caseItem))
  const query = { ...route.query }
  delete query.case_id
  delete query.project_id
  await router.replace({ query })
}

async function updateStatus(item: DataRecord, status: unknown) {
  if (typeof status !== 'string') return
  const form = new FormData(); form.set('action', 'change_status'); form.set('status', status)
  const result = await api.bugAction(Number(item.id), form)
  Message.success(result.message || '状态已更新')
  await load()
}

async function switchToQueryProject() {
  const projectId = Number(route.query.project_id || 0)
  if (!projectId) return
  if (Number(session.currentProject?.id || 0) !== projectId) await session.switchProject(projectId)
}

onMounted(async () => { hydrateQuery(); if (!session.ready) await session.load(); await switchToQueryProject(); await load() })
</script>

<template>
  <div class="page-stack">
    <PageHeader title="Bug 列表" description="集中查看、筛选和流转当前项目的缺陷">
      <a-button @click="load"><IconRefresh />刷新</a-button>
      <a-button type="primary" @click="openCreateBug()"><IconPlus />新建 Bug</a-button>
    </PageHeader>
    <div class="metric-row">
      <div class="metric"><div class="metric-label">全部</div><div class="metric-value">{{ data.summary.total || 0 }}</div></div>
      <div class="metric"><div class="metric-label">处理中</div><div class="metric-value">{{ data.summary.active_count || 0 }}</div></div>
      <div class="metric"><div class="metric-label">待验证</div><div class="metric-value">{{ data.summary.verification_count || 0 }}</div></div>
      <div class="metric"><div class="metric-label">已结束</div><div class="metric-value">{{ data.summary.closed_count || 0 }}</div></div>
    </div>
    <section class="page-panel page-stack">
      <div class="page-toolbar">
        <a-input v-model="filters.keyword" allow-clear placeholder="搜索编号、标题、创建人或处理人" @press-enter="search"><template #prefix><IconSearch /></template></a-input>
        <a-select v-model="filters.version" multiple allow-clear placeholder="版本" :max-tag-count="1"><a-option v-for="item in data.versions" :key="item" :value="item">{{ item }}</a-option></a-select>
        <a-select v-model="filters.platform" multiple allow-clear placeholder="端" :max-tag-count="1"><a-option v-for="item in session.options.platforms" :key="item" :value="item">{{ item }}</a-option></a-select>
        <a-select v-model="filters.status" multiple allow-clear placeholder="状态" :max-tag-count="1"><a-option v-for="item in session.options.statuses" :key="item.value" :value="item.value">{{ item.label }}</a-option></a-select>
        <a-range-picker v-model="filters.createdRange" style="width: 260px" />
        <a-button type="primary" @click="search"><IconSearch />查询</a-button>
      </div>
      <a-table :columns="columns" :data="data.page.items" :loading="loading" :pagination="false" row-key="id" :scroll="{ x: 1160 }" stripe>
        <template #bugNo="{ record }">
          <a-link class="bug-list-link" :title="record.bug_no" @click="openDetail(Number(record.id))">{{ record.bug_no }}</a-link>
        </template>
        <template #title="{ record }">
          <a-link class="bug-list-link bug-title-link" :title="record.title" @click="openDetail(Number(record.id))">{{ record.title }}</a-link>
        </template>
        <template #severity="{ record }"><a-tag :color="record.severity === '最高' ? 'red' : record.severity === '高' ? 'orangered' : 'gray'">{{ record.severity }}</a-tag></template>
        <template #status="{ record }">
          <StatusSelect :model-value="record.status" :options="session.options.statuses" size="small" @change="(value) => updateStatus(record, value)" />
        </template>
      </a-table>
      <a-pagination :current="data.page.page" :total="data.page.total" :page-size="20" show-total @change="changePage" />
    </section>
    <BugFormModal v-model:visible="modalVisible" :users="data.users" :requirements="data.requirements" :cases="data.cases" :default-version="filters.version[0] || ''" :initial-values="bugInitialValues" @saved="load" />
    <BugDetailDrawer v-model:visible="detailVisible" :bug-id="selectedBugId" @changed="load" @deleted="load" />
  </div>
</template>

<style scoped>
.bug-list-link {
  max-width: 100%;
  display: block;
  overflow: hidden;
  color: var(--color-text-1);
  font-weight: 400;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bug-list-link:hover { color: var(--color-text-1); }
.bug-title-link { width: 100%; }
</style>

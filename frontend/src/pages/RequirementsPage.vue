<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { IconPlus, IconSearch } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import RequirementFormModal from '../components/RequirementFormModal.vue'
import RequirementDetailDrawer from '../components/RequirementDetailDrawer.vue'

const loading = ref(false)
const modalVisible = ref(false)
const detailVisible = ref(false)
const selectedRequirementId = ref<number>()
const filters = reactive({ keyword: '', version: '', page: 1 })
const data = ref<DataRecord>({ page: { items: [], total: 0, page: 1 }, versions: [], summary: {} })
const columns = [
  { title: '编号', dataIndex: 'code', width: 130 },
  { title: '需求标题', dataIndex: 'title', slotName: 'title', width: 300 },
  { title: '版本', dataIndex: 'version', width: 100 },
  { title: '状态', dataIndex: 'status', slotName: 'status', width: 110 },
  { title: '优先级', dataIndex: 'priority', width: 90 },
  { title: '关联 Bug', dataIndex: 'linked_bug_count', width: 100 },
  { title: '创建人', dataIndex: 'creator_name', width: 100 },
  { title: '更新时间', dataIndex: 'updated_at', width: 170 },
]
async function load() { loading.value = true; try { data.value = await api.requirements(filters) } finally { loading.value = false } }
async function search() { filters.page = 1; await load() }
async function changePage(page: number) { filters.page = page; await load() }
function openDetail(id: number) { selectedRequirementId.value = id; detailVisible.value = true }
onMounted(load)
</script>

<template>
  <div class="page-stack">
    <PageHeader title="需求管理" description="维护需求文档、设计稿与关联缺陷"><a-button type="primary" @click="modalVisible = true"><IconPlus />新建需求</a-button></PageHeader>
    <div class="metric-row">
      <div class="metric"><div class="metric-label">需求总数</div><div class="metric-value">{{ data.summary.total || 0 }}</div></div>
      <div class="metric"><div class="metric-label">需求文档</div><div class="metric-value">{{ data.summary.requirement_doc_count || 0 }}</div></div>
      <div class="metric"><div class="metric-label">设计稿</div><div class="metric-value">{{ data.summary.design_doc_count || 0 }}</div></div>
      <div class="metric"><div class="metric-label">关联 Bug</div><div class="metric-value">{{ data.summary.linked_bug_total || 0 }}</div></div>
    </div>
    <section class="page-panel page-stack">
      <div class="page-toolbar"><a-input v-model="filters.keyword" allow-clear placeholder="搜索标题或链接" @press-enter="search"><template #prefix><IconSearch /></template></a-input><a-select v-model="filters.version" allow-clear placeholder="版本"><a-option v-for="item in data.versions" :key="item" :value="item">{{ item }}</a-option></a-select><a-button type="primary" @click="search"><IconSearch />查询</a-button></div>
      <a-table :columns="columns" :data="data.page.items" :loading="loading" :pagination="false" row-key="id" :scroll="{ x: 1050 }" stripe>
        <template #title="{ record }"><a-link class="table-link" @click="openDetail(Number(record.id))">{{ record.title }}</a-link></template>
        <template #status="{ record }"><StatusTag :status="record.status" /></template>
      </a-table>
      <a-pagination :current="data.page.page" :total="data.page.total" :page-size="10" show-total @change="changePage" />
    </section>
    <RequirementFormModal v-model:visible="modalVisible" @saved="load" />
    <RequirementDetailDrawer v-model:visible="detailVisible" :requirement-id="selectedRequirementId" @changed="load" @deleted="load" />
  </div>
</template>

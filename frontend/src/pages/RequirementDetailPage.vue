<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconArrowLeft, IconDelete, IconEdit } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import RequirementFormModal from '../components/RequirementFormModal.vue'
import ConfirmActionModal from '../components/ConfirmActionModal.vue'
import BugDetailDrawer from '../components/BugDetailDrawer.vue'

const props = withDefaults(defineProps<{ entityId?: number; embedded?: boolean }>(), {
  entityId: undefined,
  embedded: false,
})
const emit = defineEmits<{ changed: []; deleted: [] }>()
const route = useRoute()
const router = useRouter()
const id = computed(() => Number(props.entityId ?? route.params.id))
const loading = ref(false)
const editVisible = ref(false)
const deleteVisible = ref(false)
const deleting = ref(false)
const selectedBugId = ref<number>()
const bugDrawerVisible = ref(false)
const data = ref<DataRecord>({ requirement: {}, bugs: [], can_manage: false })
const columns = [{ title: '编号', dataIndex: 'bug_no', width: 100 }, { title: '标题', dataIndex: 'title', slotName: 'title' }, { title: '状态', dataIndex: 'status', slotName: 'status', width: 120 }, { title: '处理人', dataIndex: 'assignee_name', width: 120 }]

async function load() {
  if (!id.value) return
  loading.value = true
  try { data.value = await api.requirement(id.value) } finally { loading.value = false }
}
async function refreshAfterChange() { await load(); emit('changed') }
function openBug(bugId: number) { selectedBugId.value = bugId; bugDrawerVisible.value = true }
async function remove() {
  deleting.value = true
  try {
    const result = await api.deleteRequirement(id.value)
    Message.success(result.message || '需求已删除')
    if (props.embedded) emit('deleted')
    else await router.replace('/requirements')
  } finally { deleting.value = false }
}

watch(id, load, { immediate: true })
</script>

<template>
  <a-spin :loading="loading" class="page-stack">
    <PageHeader v-if="!embedded" :title="`${data.requirement.code || ''} ${data.requirement.title || '需求详情'}`" :description="`${data.requirement.project_name || ''} · ${data.requirement.version || ''}`">
      <a-button @click="router.back()"><IconArrowLeft />返回</a-button><a-button v-if="data.can_manage" @click="editVisible = true"><IconEdit />编辑</a-button><a-button v-if="data.can_manage" status="danger" @click="deleteVisible = true"><IconDelete />删除</a-button>
    </PageHeader>
    <div v-else class="drawer-detail-header">
      <div><h2>{{ data.requirement.code || '需求' }} {{ data.requirement.title || '需求详情' }}</h2><p>{{ data.requirement.project_name || '' }} · {{ data.requirement.version || '-' }}</p></div>
      <a-space><a-button v-if="data.can_manage" @click="editVisible = true"><IconEdit />编辑</a-button><a-button v-if="data.can_manage" status="danger" @click="deleteVisible = true"><IconDelete />删除</a-button></a-space>
    </div>
    <section class="page-panel page-stack">
      <a-descriptions :column="{ xs: 1, md: 2 }" bordered>
        <a-descriptions-item label="状态"><StatusTag :status="data.requirement.status" /></a-descriptions-item><a-descriptions-item label="优先级">{{ data.requirement.priority || '-' }}</a-descriptions-item>
        <a-descriptions-item label="需求文档"><a-link v-if="data.requirement.requirement_doc_link" :href="data.requirement.requirement_doc_link" target="_blank">打开文档</a-link><span v-else>-</span></a-descriptions-item>
        <a-descriptions-item label="设计稿"><a-link v-if="data.requirement.design_doc_link" :href="data.requirement.design_doc_link" target="_blank">打开设计稿</a-link><span v-else>-</span></a-descriptions-item>
        <a-descriptions-item label="需求描述" :span="2"><div class="content-text">{{ data.requirement.description || '-' }}</div></a-descriptions-item>
        <a-descriptions-item label="验收标准" :span="2"><div class="content-text">{{ data.requirement.acceptance_criteria || '-' }}</div></a-descriptions-item>
      </a-descriptions>
      <a-divider orientation="left">关联 Bug</a-divider>
      <a-table :columns="columns" :data="data.bugs" :pagination="false" row-key="id"><template #title="{ record }"><a-link class="table-link" @click="openBug(Number(record.id))">{{ record.title }}</a-link></template><template #status="{ record }"><StatusTag :status="record.status" /></template></a-table>
    </section>
    <RequirementFormModal v-model:visible="editVisible" :requirement="data.requirement" @saved="refreshAfterChange" />
    <ConfirmActionModal v-model:visible="deleteVisible" title="删除需求" content="仅未关联 Bug 的需求允许删除。" danger :loading="deleting" @confirm="remove" />
    <BugDetailDrawer v-model:visible="bugDrawerVisible" :bug-id="selectedBugId" @changed="refreshAfterChange" @deleted="refreshAfterChange" />
  </a-spin>
</template>

<style scoped>
.drawer-detail-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.drawer-detail-header h2 { margin: 0; font-size: 18px; }
.drawer-detail-header p { margin: 5px 0 0; color: var(--muted-text); }
@media (max-width: 640px) { .drawer-detail-header { flex-direction: column; } }
</style>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconArrowLeft, IconBug, IconCheckCircle, IconDelete } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import PageHeader from '../components/PageHeader.vue'
import ConfirmActionModal from '../components/ConfirmActionModal.vue'

const props = withDefaults(defineProps<{ entityId?: number; embedded?: boolean }>(), {
  entityId: undefined,
  embedded: false,
})
const emit = defineEmits<{ changed: []; deleted: [] }>()
const route = useRoute(); const router = useRouter()
// 在线用例详情同时服务独立路由和列表抽屉。
const routeDocumentId = computed(() => Number(props.entityId ?? route.params.id))
const activeDocumentId = ref(0)
const id = computed(() => activeDocumentId.value || routeDocumentId.value)
const loading = ref(false); const savingKey = ref(''); const data = ref<DataRecord>({ document: {}, cases: [], columns: [], meta: {} })
const deleteVisible = ref(false); const deleting = ref(false); const deletingCase = ref<DataRecord | null>(null)
const platformOptions = [
  { value: '', label: '未测', color: 'gray' },
  { value: 'pass', label: '通过', color: 'green' },
  { value: 'failed', label: '失败', color: 'red' },
  { value: 'block', label: '受阻', color: 'orange' },
  { value: 'skip', label: '跳过', color: 'arcoblue' },
]
const columns = computed(() => [
  { title: '测试编号', dataIndex: 'case_no', slotName: 'case_no', width: 150, fixed: 'left' },
  { title: '优先级', dataIndex: 'priority_level', slotName: 'priority_level', width: 100 },
  { title: '模块', dataIndex: 'module_name', slotName: 'module_name', width: 150 },
  { title: '测试步骤', dataIndex: 'steps', slotName: 'steps', width: 280 },
  { title: '预期结果', dataIndex: 'expected_result', slotName: 'expected_result', width: 240 },
  { title: 'iOS', dataIndex: 'ios_result', slotName: 'ios_result', width: 130 },
  { title: 'Android', dataIndex: 'android_result', slotName: 'android_result', width: 130 },
  { title: 'H5', dataIndex: 'h5_result', slotName: 'h5_result', width: 130 },
  { title: '执行人', dataIndex: 'executor', slotName: 'executor', width: 130 },
  { title: '备注', dataIndex: 'remark', slotName: 'remark', width: 220 },
  ...(data.value.columns || []).map((item: DataRecord) => ({ title: item.column_name, dataIndex: `dynamic_${item.id}`, slotName: `dynamic_${item.id}`, width: 180 })),
  { title: '状态', dataIndex: 'execute_status', slotName: 'execute_status', width: 100, fixed: 'right' },
  { title: '操作', dataIndex: 'actions', slotName: 'actions', width: 180, fixed: 'right' },
])
async function load() { loading.value = true; try { data.value = await api.caseDocument(id.value) } finally { loading.value = false } }
async function save(record: DataRecord, field: string, value: unknown) {
  const key = `${record.id}:${field}`; savingKey.value = key
  try { const form = new FormData(); form.set('case_id', String(record.id)); form.set('field', field); form.set('value', String(value ?? '')); const result = await api.autosaveCase(id.value, form); record.execute_status = result.data?.execute_status || record.execute_status } finally { savingKey.value = '' }
}
function dynamicValue(record: DataRecord, columnId: number) { return record.dynamic_values?.[columnId] ?? record.dynamic_values?.[String(columnId)] ?? '' }
function caseStatusOption(value: unknown) {
  const text = String(value ?? '')
  return platformOptions.find((item) => item.value === text || item.label === text) || platformOptions[0]
}
function optionValue(data: DataRecord | undefined) { return String(data?.value ?? '') }
function caseStatusClass(value: unknown) {
  return `case-result-pill is-${caseStatusOption(value).value || 'untested'}`
}
function createBug(record: DataRecord) {
  router.push({ path: '/bugs', query: { case_id: String(record.id), project_id: String(data.value.document.project_id || '') } })
}
function confirmDelete(record: DataRecord) { deletingCase.value = record; deleteVisible.value = true }
async function removeCase() {
  if (!deletingCase.value) return
  deleting.value = true
  try {
    const caseId = Number(deletingCase.value.id)
    const result = await api.deleteCaseItem(id.value, caseId)
    Message.success(result.message || '用例已删除')
    const nextDocumentId = Number(result.data?.next_document_id || 0)
    if (caseId === id.value && nextDocumentId) {
      activeDocumentId.value = nextDocumentId
      if (!props.embedded) await router.replace(`/cases/${nextDocumentId}`)
    } else if (caseId === id.value && !nextDocumentId) {
      if (props.embedded) emit('deleted')
      else await router.replace('/cases')
      return
    }
    deleteVisible.value = false
    deletingCase.value = null
    await load()
    emit('changed')
  } finally { deleting.value = false }
}
watch(routeDocumentId, (value) => { activeDocumentId.value = value }, { immediate: true })
watch(id, load, { immediate: true })
</script>

<template>
  <div class="page-stack">
    <PageHeader v-if="!embedded" :title="data.document.doc_name || '在线用例文档'" :description="`${data.document.version || '-'} · ${data.document.folder_name || '-'}`"><a-button @click="router.push('/cases')"><IconArrowLeft />返回用例库</a-button></PageHeader>
    <div v-else class="drawer-detail-header"><div><h2>{{ data.document.doc_name || '在线用例文档' }}</h2><p>{{ data.document.version || '-' }} · {{ data.document.folder_name || '-' }}</p></div></div>
    <section class="page-panel page-stack">
      <a-alert type="success"><IconCheckCircle />单元格失焦后自动保存</a-alert>
      <a-table :columns="columns" :data="data.cases" :loading="loading" :pagination="false" row-key="id" :scroll="{ x: 1960, y: 620 }" bordered>
        <template v-for="field in ['case_no', 'priority_level', 'module_name', 'steps', 'expected_result', 'executor', 'remark']" #[field]="{ record }" :key="field">
          <a-textarea v-if="['steps', 'expected_result', 'remark'].includes(field)" v-model="record[field]" :auto-size="{ minRows: 1, maxRows: 5 }" :loading="savingKey === `${record.id}:${field}`" @blur="save(record, field, record[field])" />
          <a-input v-else v-model="record[field]" :loading="savingKey === `${record.id}:${field}`" @blur="save(record, field, record[field])" />
        </template>
        <template v-for="field in ['ios_result', 'android_result', 'h5_result']" #[field]="{ record }" :key="field">
          <a-select class="case-result-select" v-model="record[field]" @change="(value) => save(record, field, value)">
            <template #label="{ data }">
              <span :class="caseStatusClass(optionValue(data))">{{ caseStatusOption(optionValue(data)).label }}</span>
            </template>
            <a-option v-for="item in platformOptions" :key="item.value" :value="item.value" :label="item.label">
              <span :class="caseStatusClass(item.value)">{{ item.label }}</span>
            </a-option>
          </a-select>
        </template>
        <template v-for="item in data.columns" #[`dynamic_${item.id}`]="{ record }" :key="item.id">
          <a-input :model-value="dynamicValue(record, item.id)" @update:model-value="(value) => record.dynamic_values[item.id] = value" @blur="save(record, `dynamic_${item.id}`, dynamicValue(record, item.id))" />
        </template>
        <template #execute_status="{ record }">
          <span :class="caseStatusClass(record.execute_status)">{{ caseStatusOption(record.execute_status).label }}</span>
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-button type="text" size="small" @click="createBug(record)"><IconBug />创建 Bug</a-button>
            <a-button v-if="data.can_manage" type="text" status="danger" size="small" @click="confirmDelete(record)"><IconDelete />删除</a-button>
          </a-space>
        </template>
      </a-table>
    </section>
    <ConfirmActionModal v-model:visible="deleteVisible" title="删除用例" content="删除后会解除已关联 Bug 与该用例的关系，此操作不可恢复。" danger :loading="deleting" @confirm="removeCase" />
  </div>
</template>

<style scoped>
.drawer-detail-header h2 { margin: 0; font-size: 18px; }
.drawer-detail-header p { margin: 5px 0 0; color: var(--muted-text); }
:deep(.case-result-select) { width: 100%; padding-right: 8px !important; padding-left: 8px !important; }
:deep(.case-result-select .arco-select-view-value) { flex: 1 1 auto !important; display: flex; align-items: center; min-width: 42px !important; overflow: visible !important; }
:deep(.case-result-select .arco-select-view-suffix) { flex: 0 0 auto; margin-left: 4px; padding-left: 4px !important; }
.case-result-pill { display: inline-flex; align-items: center; justify-content: center; min-width: 42px; height: 22px; padding: 0 7px; border: 1px solid transparent; border-radius: 4px; font-size: 12px; font-weight: 600; line-height: 20px; white-space: nowrap; }
.case-result-pill.is-untested { border-color: #e5e6eb; background: #f2f3f5; color: #4e5969; }
.case-result-pill.is-pass { border-color: #aff0c4; background: #e8f7ef; color: #00a870; }
.case-result-pill.is-failed { border-color: #fdcdc5; background: #ffece8; color: #f53f3f; }
.case-result-pill.is-block { border-color: #ffe4ba; background: #fff7e8; color: #ff7d00; }
.case-result-pill.is-skip { border-color: #bedaff; background: #e8f3ff; color: #168cff; }
</style>

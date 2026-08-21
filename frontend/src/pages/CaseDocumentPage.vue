<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconArrowLeft, IconCheckCircle } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import PageHeader from '../components/PageHeader.vue'

const route = useRoute(); const router = useRouter(); const id = computed(() => Number(route.params.id))
const loading = ref(false); const savingKey = ref(''); const data = ref<DataRecord>({ document: {}, cases: [], columns: [], meta: {} })
const platformOptions = [{ value: '', label: '未测' }, { value: 'pass', label: '通过' }, { value: 'failed', label: '失败' }, { value: 'block', label: '受阻' }, { value: 'skip', label: '跳过' }]
const columns = computed(() => [
  { title: '测试编号', dataIndex: 'case_no', slotName: 'case_no', width: 150, fixed: 'left' },
  { title: '优先级', dataIndex: 'priority_level', slotName: 'priority_level', width: 100 },
  { title: '模块', dataIndex: 'module_name', slotName: 'module_name', width: 150 },
  { title: '测试步骤', dataIndex: 'steps', slotName: 'steps', width: 280 },
  { title: '预期结果', dataIndex: 'expected_result', slotName: 'expected_result', width: 240 },
  { title: 'iOS', dataIndex: 'ios_result', slotName: 'ios_result', width: 110 },
  { title: 'Android', dataIndex: 'android_result', slotName: 'android_result', width: 110 },
  { title: 'H5', dataIndex: 'h5_result', slotName: 'h5_result', width: 110 },
  { title: '执行人', dataIndex: 'executor', slotName: 'executor', width: 130 },
  { title: '备注', dataIndex: 'remark', slotName: 'remark', width: 220 },
  ...(data.value.columns || []).map((item: DataRecord) => ({ title: item.column_name, dataIndex: `dynamic_${item.id}`, slotName: `dynamic_${item.id}`, width: 180 })),
  { title: '状态', dataIndex: 'execute_status', width: 100, fixed: 'right' },
])
async function load() { loading.value = true; try { data.value = await api.caseDocument(id.value) } finally { loading.value = false } }
async function save(record: DataRecord, field: string, value: unknown) {
  const key = `${record.id}:${field}`; savingKey.value = key
  try { const form = new FormData(); form.set('case_id', String(record.id)); form.set('field', field); form.set('value', String(value ?? '')); const result = await api.autosaveCase(id.value, form); record.execute_status = result.data?.execute_status || record.execute_status } finally { savingKey.value = '' }
}
function dynamicValue(record: DataRecord, columnId: number) { return record.dynamic_values?.[columnId] ?? record.dynamic_values?.[String(columnId)] ?? '' }
onMounted(load)
</script>

<template>
  <div class="page-stack">
    <PageHeader :title="data.document.doc_name || '在线用例文档'" :description="`${data.document.version || '-'} · ${data.document.folder_name || '-'}`"><a-button @click="router.push('/cases')"><IconArrowLeft />返回用例库</a-button></PageHeader>
    <section class="page-panel page-stack">
      <a-alert type="success"><IconCheckCircle />单元格失焦后自动保存</a-alert>
      <a-table :columns="columns" :data="data.cases" :loading="loading" :pagination="false" row-key="id" :scroll="{ x: 1900, y: 620 }" bordered>
        <template v-for="field in ['case_no', 'priority_level', 'module_name', 'steps', 'expected_result', 'executor', 'remark']" #[field]="{ record }" :key="field">
          <a-textarea v-if="['steps', 'expected_result', 'remark'].includes(field)" v-model="record[field]" :auto-size="{ minRows: 1, maxRows: 5 }" :loading="savingKey === `${record.id}:${field}`" @blur="save(record, field, record[field])" />
          <a-input v-else v-model="record[field]" :loading="savingKey === `${record.id}:${field}`" @blur="save(record, field, record[field])" />
        </template>
        <template v-for="field in ['ios_result', 'android_result', 'h5_result']" #[field]="{ record }" :key="field">
          <a-select v-model="record[field]" @change="(value) => save(record, field, value)"><a-option v-for="item in platformOptions" :key="item.value" :value="item.value">{{ item.label }}</a-option></a-select>
        </template>
        <template v-for="item in data.columns" #[`dynamic_${item.id}`]="{ record }" :key="item.id">
          <a-input :model-value="dynamicValue(record, item.id)" @update:model-value="(value) => record.dynamic_values[item.id] = value" @blur="save(record, `dynamic_${item.id}`, dynamicValue(record, item.id))" />
        </template>
      </a-table>
    </section>
  </div>
</template>

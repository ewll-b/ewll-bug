<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Message, type FileItem } from '@arco-design/web-vue'
import { api, type DataRecord } from '../api'
import { useSessionStore } from '../stores/session'
import DragPasteUpload from './DragPasteUpload.vue'

const props = withDefaults(defineProps<{
  visible: boolean
  bug?: DataRecord | null
  users: DataRecord[]
  requirements: DataRecord[]
  cases: DataRecord[]
  defaultVersion?: string
}>(), { bug: null, defaultVersion: '' })
const emit = defineEmits<{ 'update:visible': [value: boolean]; saved: [] }>()
const session = useSessionStore()
const saving = ref(false)
const files = ref<FileItem[]>([])
const form = reactive<DataRecord>({})

function reset() {
  Object.assign(form, {
    title: props.bug?.title || '',
    version: props.bug?.version || props.defaultVersion || '',
    platform: props.bug?.platform || '',
    severity: props.bug?.severity || '高',
    assignee_id: props.bug?.assignee_id || undefined,
    requirement_id: props.bug?.requirement_id || undefined,
    case_id: props.bug?.case_id || undefined,
    environment: props.bug?.environment || '',
    description: props.bug?.description || '',
    expected_result: props.bug?.expected_result || '',
    actual_result: props.bug?.actual_result || '',
  })
  files.value = []
}

watch(() => props.visible, (visible) => { if (visible) reset() })

async function submit() {
  if (!form.title || !form.version || !form.platform || !form.assignee_id || !form.description) {
    Message.warning('请完整填写标题、版本、端、处理人和问题描述。')
    return
  }
  saving.value = true
  try {
    const data = new FormData()
    Object.entries(form).forEach(([key, value]) => {
      if (value !== undefined && value !== null) data.append(key, String(value))
    })
    data.set('module', String(form.platform || 'WEB'))
    data.set('priority', String(form.severity || '高'))
    files.value.forEach((item) => { if (item.file) data.append('attachments', item.file) })
    const result = props.bug ? await api.editBug(Number(props.bug.id), data) : await api.createBug(data)
    Message.success(result.message || '保存成功')
    emit('update:visible', false)
    emit('saved')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <a-modal
    :visible="props.visible"
    :title="props.bug ? '编辑 Bug' : '新建 Bug'"
    :width="760"
    :modal-style="{ maxWidth: 'calc(100vw - 24px)' }"
    :body-style="{ maxHeight: 'calc(100vh - 164px)', overflowY: 'auto' }"
    :ok-loading="saving"
    unmount-on-close
    @ok="submit"
    @cancel="emit('update:visible', false)"
  >
    <a-form :model="form" layout="vertical">
      <a-grid :cols="2" :col-gap="16" :row-gap="4" :collapsed="false">
        <a-grid-item :span="2"><a-form-item label="标题" required><a-input v-model="form.title" placeholder="请输入 Bug 标题" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="版本" required><a-input v-model="form.version" placeholder="例如 2.8.0" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="端" required><a-select v-model="form.platform" placeholder="请选择"><a-option v-for="item in session.options.platforms" :key="item" :value="item">{{ item }}</a-option></a-select></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="严重级别"><a-select v-model="form.severity"><a-option v-for="item in session.options.severities" :key="item" :value="item">{{ item }}</a-option></a-select></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="处理人" required><a-select v-model="form.assignee_id" allow-search><a-option v-for="item in users" :key="item.id" :value="item.id">{{ item.name }} · {{ item.role }}</a-option></a-select></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="关联需求"><a-select v-model="form.requirement_id" allow-clear allow-search><a-option v-for="item in requirements" :key="item.id" :value="item.id">{{ item.code }} / {{ item.title }}</a-option></a-select></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="关联用例"><a-select v-model="form.case_id" allow-clear allow-search><a-option v-for="item in cases" :key="item.id" :value="item.id">{{ item.case_no }} / {{ item.title }}</a-option></a-select></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="环境"><a-input v-model="form.environment" placeholder="设备、版本、网络等环境信息" /></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="问题描述" required><a-textarea v-model="form.description" :auto-size="{ minRows: 4, maxRows: 10 }" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="期望结果"><a-textarea v-model="form.expected_result" :auto-size="{ minRows: 3, maxRows: 6 }" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="实际结果"><a-textarea v-model="form.actual_result" :auto-size="{ minRows: 3, maxRows: 6 }" /></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="附件"><DragPasteUpload v-model="files" /></a-form-item></a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>
</template>

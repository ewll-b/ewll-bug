<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { api, type DataRecord } from '../api'
import { useSessionStore } from '../stores/session'

const props = withDefaults(defineProps<{ visible: boolean; requirement?: DataRecord | null }>(), { requirement: null })
const emit = defineEmits<{ 'update:visible': [value: boolean]; saved: [] }>()
const session = useSessionStore()
const saving = ref(false)
const form = reactive<DataRecord>({})

watch(() => props.visible, (visible) => {
  if (!visible) return
  Object.assign(form, {
    code: props.requirement?.code || '', title: props.requirement?.title || '', version: props.requirement?.version || '',
    status: props.requirement?.status || 'pending', priority: props.requirement?.priority || '中',
    description: props.requirement?.description || '', acceptance_criteria: props.requirement?.acceptance_criteria || '',
    requirement_doc_link: props.requirement?.requirement_doc_link || '', design_doc_link: props.requirement?.design_doc_link || '',
  })
})

async function submit() {
  if (!form.title || !form.version) return Message.warning('请填写需求标题和版本。')
  saving.value = true
  try {
    const data = new FormData()
    Object.entries(form).forEach(([key, value]) => data.append(key, String(value ?? '')))
    const result = props.requirement ? await api.editRequirement(Number(props.requirement.id), data) : await api.createRequirement(data)
    Message.success(result.message || '保存成功')
    emit('update:visible', false)
    emit('saved')
  } finally { saving.value = false }
}
</script>

<template>
  <a-modal :visible="visible" :title="requirement ? '编辑需求' : '新建需求'" :width="680" :modal-style="{ maxWidth: 'calc(100vw - 24px)' }" :body-style="{ maxHeight: 'calc(100vh - 164px)', overflowY: 'auto' }" :ok-loading="saving" @ok="submit" @cancel="emit('update:visible', false)">
    <a-form :model="form" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item><a-form-item label="需求编号"><a-input v-model="form.code" placeholder="留空自动生成" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="版本" required><a-input v-model="form.version" /></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="需求标题" required><a-input v-model="form.title" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="状态"><a-select v-model="form.status"><a-option v-for="item in session.options.requirement_statuses" :key="item.value" :value="item.value">{{ item.label }}</a-option></a-select></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="优先级"><a-select v-model="form.priority"><a-option v-for="item in session.options.priorities" :key="item" :value="item">{{ item }}</a-option></a-select></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="需求描述"><a-textarea v-model="form.description" :auto-size="{ minRows: 3, maxRows: 8 }" /></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="验收标准"><a-textarea v-model="form.acceptance_criteria" :auto-size="{ minRows: 3, maxRows: 8 }" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="需求文档"><a-input v-model="form.requirement_doc_link" placeholder="https://" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="设计稿"><a-input v-model="form.design_doc_link" placeholder="https://" /></a-form-item></a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { api, type DataRecord } from '../api'

const props = withDefaults(defineProps<{ visible: boolean; project?: DataRecord | null }>(), { project: null })
const emit = defineEmits<{ 'update:visible': [value: boolean]; saved: [] }>()
const saving = ref(false)
const form = reactive<DataRecord>({})
watch(() => props.visible, (visible) => {
  if (visible) Object.assign(form, { name: props.project?.name || '', description: props.project?.description || '', bug_notify_enabled: Boolean(props.project?.bug_notify_enabled), bug_notify_webhook: '', bug_notify_base_url: props.project?.bug_notify_base_url || '' })
})
async function submit() {
  if (!form.name) return Message.warning('请输入项目名称。')
  saving.value = true
  try {
    const data = new FormData()
    data.set('entity', 'project'); data.set('action', props.project ? 'update' : 'create')
    if (props.project) { data.set('project_id', String(props.project.id)); data.set('preserve_notify_rules', '1') }
    Object.entries(form).forEach(([key, value]) => {
      // 已配置的敏感字段留空时不提交，由服务端保留原值。
      if (props.project && key === 'bug_notify_webhook' && !value) return
      data.set(key, typeof value === 'boolean' ? (value ? '1' : '0') : String(value ?? ''))
    })
    const result = await api.adminAction(data)
    Message.success(result.message || '保存成功')
    emit('update:visible', false); emit('saved')
  } finally { saving.value = false }
}
</script>

<template>
  <a-modal :visible="visible" :title="project ? '编辑项目' : '新建项目'" :modal-style="{ maxWidth: 'calc(100vw - 24px)' }" :body-style="{ maxHeight: 'calc(100vh - 164px)', overflowY: 'auto' }" :ok-loading="saving" @ok="submit" @cancel="emit('update:visible', false)">
    <a-form :model="form" layout="vertical">
      <a-form-item label="项目名称" required><a-input v-model="form.name" /></a-form-item>
      <a-form-item label="项目描述"><a-textarea v-model="form.description" :auto-size="{ minRows: 3, maxRows: 6 }" /></a-form-item>
      <a-form-item label="新建 Bug 群通知"><a-switch v-model="form.bug_notify_enabled" /></a-form-item>
      <a-alert v-if="project?.bug_notify_webhook_configured" type="success">Webhook 已安全配置，留空将保留原值。</a-alert>
      <a-form-item label="Webhook"><a-input-password v-model="form.bug_notify_webhook" placeholder="未修改可留空" autocomplete="new-password" /></a-form-item>
      <a-form-item label="访问地址"><a-input v-model="form.bug_notify_base_url" placeholder="https://" /></a-form-item>
    </a-form>
  </a-modal>
</template>

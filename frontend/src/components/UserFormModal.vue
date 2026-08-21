<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { api, type DataRecord } from '../api'
import { useSessionStore } from '../stores/session'

const props = withDefaults(defineProps<{ visible: boolean; user?: DataRecord | null }>(), { user: null })
const emit = defineEmits<{ 'update:visible': [value: boolean]; saved: [] }>()
const session = useSessionStore()
const saving = ref(false)
const form = reactive<DataRecord>({})
watch(() => props.visible, (visible) => {
  if (visible) Object.assign(form, { name: props.user?.name || '', account_type: props.user?.account_type || 'member', role_code: props.user?.role_code || 'tester', username: props.user?.username || '', email: props.user?.email || '', password: '' })
})
async function submit() {
  if (!form.name || !form.username || !form.email || (!props.user && !form.password)) return Message.warning('请完整填写账号信息。')
  saving.value = true
  try {
    const data = new FormData()
    data.set('entity', 'user'); data.set('action', props.user ? 'update' : 'create')
    if (props.user) data.set('user_id', String(props.user.id))
    Object.entries(form).forEach(([key, value]) => data.set(key, String(value ?? '')))
    const result = await api.adminAction(data)
    Message.success(result.message || '保存成功')
    emit('update:visible', false); emit('saved')
  } finally { saving.value = false }
}
</script>

<template>
  <a-modal :visible="visible" :title="user ? '编辑账号' : '新建账号'" :modal-style="{ maxWidth: 'calc(100vw - 24px)' }" :body-style="{ maxHeight: 'calc(100vh - 164px)', overflowY: 'auto' }" :ok-loading="saving" @ok="submit" @cancel="emit('update:visible', false)">
    <a-form :model="form" layout="vertical">
      <a-form-item label="姓名" required><a-input v-model="form.name" /></a-form-item>
      <a-form-item label="账号类型"><a-radio-group v-model="form.account_type" type="button"><a-radio value="member">普通成员</a-radio><a-radio value="admin">管理员</a-radio></a-radio-group></a-form-item>
      <a-form-item label="角色"><a-select v-model="form.role_code"><a-option v-for="item in session.options.roles" :key="item.value" :value="item.value">{{ item.label }}</a-option><a-option value="admin">管理员</a-option></a-select></a-form-item>
      <a-form-item label="登录账号" required><a-input v-model="form.username" autocomplete="username" /></a-form-item>
      <a-form-item label="邮箱" required><a-input v-model="form.email" autocomplete="email" /></a-form-item>
      <a-form-item :label="user ? '新密码' : '密码'" :required="!user"><a-input-password v-model="form.password" :placeholder="user ? '不修改可留空' : '请输入密码'" autocomplete="new-password" /></a-form-item>
    </a-form>
  </a-modal>
</template>

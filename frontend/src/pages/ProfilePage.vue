<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconSave, IconUser } from '@arco-design/web-vue/es/icon'
import { api } from '../api'
import PageHeader from '../components/PageHeader.vue'

const loading = ref(false); const saving = ref(false); const form = reactive({ name: '', username: '', email: '', role: '', role_code: '', password: '' })
async function load() { loading.value = true; try { Object.assign(form, (await api.profile()).user, { password: '' }) } finally { loading.value = false } }
async function save() { if (!form.name) return Message.warning('姓名不能为空。'); saving.value = true; try { const data = new FormData(); data.set('name', form.name); data.set('email', form.email); data.set('password', form.password); const result = await api.updateProfile(data); Message.success(result.message || '保存成功'); await load() } finally { saving.value = false } }
onMounted(load)
</script>

<template>
  <div class="page-stack"><PageHeader title="个人资料" description="维护姓名、邮箱和登录密码" /><section class="page-panel profile-panel"><a-spin :loading="loading"><a-form :model="form" layout="vertical"><a-form-item label="姓名" required><a-input v-model="form.name"><template #prefix><IconUser /></template></a-input></a-form-item><a-form-item label="登录账号"><a-input v-model="form.username" disabled /></a-form-item><a-form-item label="邮箱"><a-input v-model="form.email" /></a-form-item><a-form-item label="角色"><a-input :model-value="`${form.role} / ${form.role_code}`" disabled /></a-form-item><a-form-item label="新密码"><a-input-password v-model="form.password" placeholder="不修改可留空" /></a-form-item><a-button type="primary" :loading="saving" @click="save"><IconSave />保存资料</a-button></a-form></a-spin></section></div>
</template>

<style scoped>.profile-panel { width: min(640px, 100%); }</style>

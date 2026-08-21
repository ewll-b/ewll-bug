<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { api } from '../api'

const props = defineProps<{ visible: boolean; folders: string[] }>()
const emit = defineEmits<{ 'update:visible': [value: boolean]; saved: [] }>()
const saving = ref(false)
const form = reactive({ action: 'create_document', folder_name: '', doc_name: '' })
watch(() => props.visible, (visible) => { if (visible) { form.folder_name = props.folders[0] || ''; form.doc_name = '' } })
async function submit() {
  if (form.action === 'create_folder' && !form.folder_name) return Message.warning('请输入文件夹名称。')
  if (form.action === 'create_document' && !form.doc_name) return Message.warning('请输入在线文档名称。')
  saving.value = true
  try {
    const data = new FormData(); data.set('action', form.action); data.set('folder_name', form.folder_name); data.set('doc_name', form.doc_name)
    const result = await api.manageCases(data); Message.success(result.message || '操作成功'); emit('update:visible', false); emit('saved')
  } finally { saving.value = false }
}
</script>

<template>
  <a-modal :visible="visible" title="新建用例资源" :ok-loading="saving" @ok="submit" @cancel="emit('update:visible', false)">
    <a-form :model="form" layout="vertical">
      <a-form-item label="创建类型"><a-radio-group v-model="form.action" type="button"><a-radio value="create_document">在线文档</a-radio><a-radio value="create_folder">文件夹</a-radio></a-radio-group></a-form-item>
      <a-form-item label="文件夹" required><a-input v-if="form.action === 'create_folder'" v-model="form.folder_name" placeholder="输入新文件夹名称" /><a-select v-else v-model="form.folder_name" allow-create placeholder="选择或输入文件夹"><a-option v-for="item in folders" :key="item" :value="item">{{ item }}</a-option></a-select></a-form-item>
      <a-form-item v-if="form.action === 'create_document'" label="在线文档名称" required><a-input v-model="form.doc_name" /></a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconArrowLeft, IconDelete, IconEdit } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import RequirementFormModal from '../components/RequirementFormModal.vue'
import ConfirmActionModal from '../components/ConfirmActionModal.vue'

const route = useRoute(); const router = useRouter(); const id = computed(() => Number(route.params.id))
const loading = ref(false); const editVisible = ref(false); const deleteVisible = ref(false); const deleting = ref(false)
const data = ref<DataRecord>({ requirement: {}, bugs: [], can_manage: false })
const columns = [{ title: '编号', dataIndex: 'bug_no', width: 100 }, { title: '标题', dataIndex: 'title', slotName: 'title' }, { title: '状态', dataIndex: 'status', slotName: 'status', width: 120 }, { title: '处理人', dataIndex: 'assignee_name', width: 120 }]
async function load() { loading.value = true; try { data.value = await api.requirement(id.value) } finally { loading.value = false } }
async function remove() { deleting.value = true; try { const result = await api.deleteRequirement(id.value); Message.success(result.message || '需求已删除'); await router.replace('/requirements') } finally { deleting.value = false } }
onMounted(load)
</script>

<template>
  <a-spin :loading="loading" class="page-stack">
    <PageHeader :title="`${data.requirement.code || ''} ${data.requirement.title || '需求详情'}`" :description="`${data.requirement.project_name || ''} · ${data.requirement.version || ''}`">
      <a-button @click="router.back()"><IconArrowLeft />返回</a-button><a-button v-if="data.can_manage" @click="editVisible = true"><IconEdit />编辑</a-button><a-button v-if="data.can_manage" status="danger" @click="deleteVisible = true"><IconDelete />删除</a-button>
    </PageHeader>
    <section class="page-panel page-stack">
      <a-descriptions :column="2" bordered>
        <a-descriptions-item label="状态"><StatusTag :status="data.requirement.status" /></a-descriptions-item><a-descriptions-item label="优先级">{{ data.requirement.priority || '-' }}</a-descriptions-item>
        <a-descriptions-item label="需求文档"><a-link v-if="data.requirement.requirement_doc_link" :href="data.requirement.requirement_doc_link" target="_blank">打开文档</a-link><span v-else>-</span></a-descriptions-item>
        <a-descriptions-item label="设计稿"><a-link v-if="data.requirement.design_doc_link" :href="data.requirement.design_doc_link" target="_blank">打开设计稿</a-link><span v-else>-</span></a-descriptions-item>
        <a-descriptions-item label="需求描述" :span="2"><div class="content-text">{{ data.requirement.description || '-' }}</div></a-descriptions-item>
        <a-descriptions-item label="验收标准" :span="2"><div class="content-text">{{ data.requirement.acceptance_criteria || '-' }}</div></a-descriptions-item>
      </a-descriptions>
      <a-divider orientation="left">关联 Bug</a-divider>
      <a-table :columns="columns" :data="data.bugs" :pagination="false" row-key="id"><template #title="{ record }"><router-link class="table-link" :to="`/bugs/${record.id}`">{{ record.title }}</router-link></template><template #status="{ record }"><StatusTag :status="record.status" /></template></a-table>
    </section>
    <RequirementFormModal v-model:visible="editVisible" :requirement="data.requirement" @saved="load" />
    <ConfirmActionModal v-model:visible="deleteVisible" title="删除需求" content="仅未关联 Bug 的需求允许删除。" danger :loading="deleting" @confirm="remove" />
  </a-spin>
</template>

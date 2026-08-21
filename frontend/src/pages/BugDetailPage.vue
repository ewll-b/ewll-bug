<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconArrowLeft, IconDelete, IconEdit, IconSend } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import { useSessionStore } from '../stores/session'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import AttachmentGallery from '../components/AttachmentGallery.vue'
import BugFormModal from '../components/BugFormModal.vue'
import ConfirmActionModal from '../components/ConfirmActionModal.vue'

const props = withDefaults(defineProps<{ entityId?: number; embedded?: boolean }>(), {
  entityId: undefined,
  embedded: false,
})
const emit = defineEmits<{ changed: []; deleted: [] }>()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const loading = ref(false)
const data = ref<DataRecord>({ bug: {}, history: [], comments: [], attachments: [], users: [], requirements: [], cases: [], permissions: {} })
const editVisible = ref(false)
const deleteVisible = ref(false)
const deleting = ref(false)
const comment = ref('')
const commentSaving = ref(false)
// 详情页和详情抽屉共用同一业务内容，避免两套逻辑产生差异。
const id = computed(() => Number(props.entityId ?? route.params.id))

async function load() {
  if (!id.value) return
  loading.value = true
  try { data.value = await api.bug(id.value) } finally { loading.value = false }
}
async function refreshAfterChange() { await load(); emit('changed') }
async function changeStatus(status: unknown) {
  if (typeof status !== 'string') return
  const form = new FormData(); form.set('action', 'change_status'); form.set('status', status)
  const result = await api.bugAction(id.value, form); Message.success(result.message || '状态已更新'); await refreshAfterChange()
}
async function addComment() {
  if (!comment.value.trim()) return Message.warning('请输入评论内容。')
  commentSaving.value = true
  try {
    const form = new FormData(); form.set('content', comment.value.trim())
    const result = await api.addComment(id.value, form)
    Message.success(result.message || '评论已发布')
    comment.value = ''
    await refreshAfterChange()
  } finally { commentSaving.value = false }
}
async function removeBug() {
  deleting.value = true
  try {
    const result = await api.deleteBug(id.value)
    Message.success(result.message || 'Bug 已删除')
    if (props.embedded) emit('deleted')
    else await router.replace('/bugs')
  } finally { deleting.value = false }
}

watch(id, async () => {
  if (!session.ready) await session.load()
  await load()
}, { immediate: true })
</script>

<template>
  <a-spin :loading="loading" class="page-stack">
    <PageHeader v-if="!embedded" :title="`${data.bug.bug_no || ''} ${data.bug.title || '缺陷详情'}`" :description="`${data.bug.project_name || ''} · 创建于 ${data.bug.created_at || '-'}`">
      <a-button @click="router.back()"><IconArrowLeft />返回</a-button>
      <a-button v-if="data.permissions.can_manage" @click="editVisible = true"><IconEdit />编辑</a-button>
      <a-button v-if="data.permissions.can_manage" status="danger" @click="deleteVisible = true"><IconDelete />删除</a-button>
    </PageHeader>
    <div v-else class="drawer-detail-header">
      <div>
        <h2>{{ data.bug.bug_no || 'Bug' }} {{ data.bug.title || '缺陷详情' }}</h2>
        <p>{{ data.bug.project_name || '' }} · 创建于 {{ data.bug.created_at || '-' }}</p>
      </div>
      <a-space>
        <a-button v-if="data.permissions.can_manage" @click="editVisible = true"><IconEdit />编辑</a-button>
        <a-button v-if="data.permissions.can_manage" status="danger" @click="deleteVisible = true"><IconDelete />删除</a-button>
      </a-space>
    </div>

    <section class="page-panel page-stack">
      <h3 class="section-title">详情</h3>
      <a-descriptions :column="{ xs: 1, md: 2 }" bordered size="large">
        <a-descriptions-item label="状态"><a-select :model-value="data.bug.status" style="width: 160px" @change="changeStatus"><a-option v-for="item in session.options.statuses" :key="item.value" :value="item.value"><StatusTag :status="item.value" /></a-option></a-select></a-descriptions-item>
        <a-descriptions-item label="严重级别"><a-tag color="orangered">{{ data.bug.severity || '-' }}</a-tag></a-descriptions-item>
        <a-descriptions-item label="版本">{{ data.bug.version || '-' }}</a-descriptions-item>
        <a-descriptions-item label="端">{{ data.bug.platform || '-' }}</a-descriptions-item>
        <a-descriptions-item label="当前处理人">{{ data.bug.assignee_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="创建人">{{ data.bug.creator_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="环境" :span="2"><div class="content-text">{{ data.bug.environment || '-' }}</div></a-descriptions-item>
        <a-descriptions-item label="问题描述" :span="2"><div class="content-text">{{ data.bug.description || '-' }}</div></a-descriptions-item>
        <a-descriptions-item label="期望结果" :span="2"><div class="content-text">{{ data.bug.expected_result || '-' }}</div></a-descriptions-item>
        <a-descriptions-item label="实际结果" :span="2"><div class="content-text">{{ data.bug.actual_result || '-' }}</div></a-descriptions-item>
        <a-descriptions-item label="处理说明" :span="2"><div class="content-text">{{ data.bug.resolution_note || '-' }}</div></a-descriptions-item>
      </a-descriptions>
    </section>

    <section class="page-panel page-stack">
      <h3 class="section-title">处理记录</h3>
      <a-timeline v-if="data.history.length">
        <a-timeline-item v-for="item in data.history" :key="item.id" :label="item.created_at"><strong>{{ item.action }}</strong><div class="content-text muted">{{ item.detail }}</div><small>{{ item.operator_name }}</small></a-timeline-item>
      </a-timeline>
      <a-empty v-else description="暂无处理记录" />
    </section>

    <section class="page-panel page-stack">
      <h3 class="section-title">附件（{{ data.attachments.length }}）</h3>
      <AttachmentGallery :items="data.attachments" />
    </section>

    <section class="page-panel page-stack">
      <h3 class="section-title">评论</h3>
      <a-comment v-for="item in data.comments" :key="item.id" :author="item.author_name" :datetime="item.created_at" :content="item.content" />
      <a-empty v-if="!data.comments.length" description="暂无评论" />
      <a-textarea v-model="comment" :auto-size="{ minRows: 3, maxRows: 6 }" placeholder="补充评论，支持 @ 成员文本" />
      <div class="comment-actions"><a-button type="primary" :loading="commentSaving" @click="addComment"><IconSend />发布评论</a-button></div>
    </section>

    <BugFormModal v-model:visible="editVisible" :bug="data.bug" :users="data.users" :requirements="data.requirements" :cases="data.cases" @saved="refreshAfterChange" />
    <ConfirmActionModal v-model:visible="deleteVisible" title="删除 Bug" content="删除后将同时清理评论、附件和流转历史，此操作不可恢复。" danger :loading="deleting" @confirm="removeBug" />
  </a-spin>
</template>

<style scoped>
.section-title { margin: 0; font-size: 16px; }
.drawer-detail-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.drawer-detail-header h2 { margin: 0; font-size: 18px; }
.drawer-detail-header p { margin: 5px 0 0; color: var(--muted-text); }
.comment-actions { display: flex; justify-content: flex-end; }
@media (max-width: 640px) { .drawer-detail-header { flex-direction: column; }.comment-actions .arco-btn { width: 100%; } }
</style>

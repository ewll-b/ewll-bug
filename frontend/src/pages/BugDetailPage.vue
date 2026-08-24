<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconArrowLeft, IconDelete, IconEdit, IconSend } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import { useSessionStore } from '../stores/session'
import PageHeader from '../components/PageHeader.vue'
import StatusSelect from '../components/StatusSelect.vue'
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
const data = ref<DataRecord>({ bug: {}, history: [], comments: [], mention_users: [], attachments: [], users: [], requirements: [], cases: [], permissions: {} })
const editVisible = ref(false)
const deleteVisible = ref(false)
const deleting = ref(false)
const comment = ref('')
const commentSaving = ref(false)
const commentEditorRef = ref<HTMLElement | null>(null)
const mentionRange = ref<{ start: number; end: number; query: string } | null>(null)
const mentionActive = ref(false)
const selectedMentionIndex = ref(0)
let mentionHideTimer: number | undefined
// 详情页和详情抽屉共用同一业务内容，避免两套逻辑产生差异。
const id = computed(() => Number(props.entityId ?? route.params.id))
const inlineImageFields = new Set(['title', 'version', 'environment', 'description', 'expected_result', 'actual_result'])
const attachmentsByField = computed(() => {
  const groups: Record<string, DataRecord[]> = {}
  inlineImageFields.forEach((field) => { groups[field] = [] })
  data.value.attachments.forEach((item: DataRecord) => {
    const sourceField = String(item.source_field || 'attachments')
    if (item.is_image && inlineImageFields.has(sourceField)) groups[sourceField].push(item)
  })
  return groups
})
const generalAttachments = computed(() => data.value.attachments.filter((item: DataRecord) => !item.is_image || !inlineImageFields.has(String(item.source_field || 'attachments'))))
const filteredMentionUsers = computed(() => {
  const query = mentionRange.value?.query.trim().toLowerCase() || ''
  return (data.value.mention_users || []).filter((user: DataRecord) => {
    const searchText = [user.name, user.username, user.role, user.email].filter(Boolean).join(' ').toLowerCase()
    return !query || searchText.includes(query)
  }).slice(0, 12)
})
const showMentionPicker = computed(() => mentionActive.value && filteredMentionUsers.value.length > 0)
function fieldAttachments(field: string) { return attachmentsByField.value[field] || [] }
function mentionName(user: DataRecord) { return String(user.name || user.username || '').trim() }
function mentionMeta(user: DataRecord) { return [user.role, user.username ? `@${user.username}` : ''].filter(Boolean).join(' · ') }
function commentTextarea() { return commentEditorRef.value?.querySelector('textarea') as HTMLTextAreaElement | null }
function activeMentionRange() {
  const textarea = commentTextarea()
  if (!textarea || typeof textarea.selectionStart !== 'number') return null
  const cursor = textarea.selectionStart
  const prefix = textarea.value.slice(0, cursor)
  const atIndex = prefix.lastIndexOf('@')
  if (atIndex < 0) return null
  const query = prefix.slice(atIndex + 1)
  if (query.includes('@') || /\s/.test(query)) return null
  return { start: atIndex, end: cursor, query }
}
function hideMentionPicker() {
  mentionActive.value = false
  mentionRange.value = null
  selectedMentionIndex.value = 0
}
function syncMentionPicker() {
  if (mentionHideTimer) window.clearTimeout(mentionHideTimer)
  const range = activeMentionRange()
  mentionRange.value = range
  mentionActive.value = Boolean(range)
  selectedMentionIndex.value = 0
}
function scheduleMentionHide() {
  mentionHideTimer = window.setTimeout(hideMentionPicker, 160)
}
async function insertMention(user?: DataRecord) {
  if (!user) return
  const name = mentionName(user)
  if (!name) return
  const textarea = commentTextarea()
  const value = textarea?.value ?? comment.value
  const range = mentionRange.value || activeMentionRange()
  const start = range?.start ?? textarea?.selectionStart ?? value.length
  const end = range?.end ?? textarea?.selectionEnd ?? start
  const prefix = value.slice(0, start)
  const suffix = value.slice(end)
  const spacer = prefix && !/\s$/.test(prefix) ? ' ' : ''
  const mentionText = `@${name} `
  comment.value = `${prefix}${spacer}${mentionText}${suffix}`
  hideMentionPicker()
  await nextTick()
  const cursor = `${prefix}${spacer}${mentionText}`.length
  const nextTextarea = commentTextarea()
  nextTextarea?.focus()
  nextTextarea?.setSelectionRange(cursor, cursor)
}
function handleCommentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    hideMentionPicker()
    return
  }
  if (!showMentionPicker.value) return
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    const step = event.key === 'ArrowDown' ? 1 : -1
    selectedMentionIndex.value = (selectedMentionIndex.value + step + filteredMentionUsers.value.length) % filteredMentionUsers.value.length
  } else if (event.key === 'Enter' || event.key === 'Tab') {
    event.preventDefault()
    insertMention(filteredMentionUsers.value[selectedMentionIndex.value])
  }
}
function handleCommentKeyup(event: KeyboardEvent) {
  if (['ArrowDown', 'ArrowUp', 'Enter', 'Tab', 'Escape'].includes(event.key)) return
  syncMentionPicker()
}

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
        <a-descriptions-item label="状态"><StatusSelect :model-value="data.bug.status" :options="session.options.statuses" style="width: 160px" @change="changeStatus" /></a-descriptions-item>
        <a-descriptions-item label="严重级别"><a-tag color="orangered">{{ data.bug.severity || '-' }}</a-tag></a-descriptions-item>
        <a-descriptions-item label="标题" :span="2">
          <div class="field-content-block">
            <div class="content-text">{{ data.bug.title || '-' }}</div>
            <AttachmentGallery v-if="fieldAttachments('title').length" :items="fieldAttachments('title')" />
          </div>
        </a-descriptions-item>
        <a-descriptions-item label="版本">
          <div class="field-content-block">
            <div class="content-text">{{ data.bug.version || '-' }}</div>
            <AttachmentGallery v-if="fieldAttachments('version').length" :items="fieldAttachments('version')" />
          </div>
        </a-descriptions-item>
        <a-descriptions-item label="端">{{ data.bug.platform || '-' }}</a-descriptions-item>
        <a-descriptions-item label="当前处理人">{{ data.bug.assignee_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="创建人">{{ data.bug.creator_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="环境" :span="2">
          <div class="field-content-block">
            <div class="content-text">{{ data.bug.environment || '-' }}</div>
            <AttachmentGallery v-if="fieldAttachments('environment').length" :items="fieldAttachments('environment')" />
          </div>
        </a-descriptions-item>
        <a-descriptions-item label="问题描述" :span="2">
          <div class="field-content-block">
            <div class="content-text">{{ data.bug.description || '-' }}</div>
            <AttachmentGallery v-if="fieldAttachments('description').length" :items="fieldAttachments('description')" />
          </div>
        </a-descriptions-item>
        <a-descriptions-item label="期望结果" :span="2">
          <div class="field-content-block">
            <div class="content-text">{{ data.bug.expected_result || '-' }}</div>
            <AttachmentGallery v-if="fieldAttachments('expected_result').length" :items="fieldAttachments('expected_result')" />
          </div>
        </a-descriptions-item>
        <a-descriptions-item label="实际结果" :span="2">
          <div class="field-content-block">
            <div class="content-text">{{ data.bug.actual_result || '-' }}</div>
            <AttachmentGallery v-if="fieldAttachments('actual_result').length" :items="fieldAttachments('actual_result')" />
          </div>
        </a-descriptions-item>
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
      <h3 class="section-title">附件（{{ generalAttachments.length }}）</h3>
      <AttachmentGallery :items="generalAttachments" />
    </section>

    <section class="page-panel page-stack">
      <h3 class="section-title">评论</h3>
      <a-comment v-for="item in data.comments" :key="item.id" :author="item.author_name" :datetime="item.created_at" :content="item.content" />
      <a-empty v-if="!data.comments.length" description="暂无评论" />
      <div ref="commentEditorRef" class="comment-mention-editor">
        <a-textarea
          v-model="comment"
          :auto-size="{ minRows: 3, maxRows: 6 }"
          placeholder="补充评论，输入 @ 选择成员"
          @input="syncMentionPicker"
          @click="syncMentionPicker"
          @focus="syncMentionPicker"
          @blur="scheduleMentionHide"
          @keydown="handleCommentKeydown"
          @keyup="handleCommentKeyup"
        />
        <div v-if="showMentionPicker" class="comment-mention-picker">
          <div class="comment-mention-head">
            <span class="comment-mention-symbol">@</span>
            <div>
              <strong>系统成员</strong>
              <span>选择后插入评论并通知对方</span>
            </div>
          </div>
          <div class="comment-mention-list">
            <button
              v-for="(user, index) in filteredMentionUsers"
              :key="user.id"
              type="button"
              class="comment-mention-option"
              :class="{ 'is-active': index === selectedMentionIndex }"
              @mousedown.prevent="insertMention(user)"
            >
              <span class="comment-mention-avatar">{{ mentionName(user).slice(0, 1).toUpperCase() }}</span>
              <span class="comment-mention-person">
                <strong>{{ mentionName(user) }}</strong>
                <span>{{ mentionMeta(user) || '成员' }}</span>
              </span>
            </button>
          </div>
        </div>
      </div>
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
.field-content-block { display: grid; gap: 10px; }
.comment-mention-editor { position: relative; }
.comment-mention-picker { position: absolute; left: 0; bottom: calc(100% + 8px); z-index: 30; width: min(360px, 100%); max-height: 300px; overflow: auto; padding: 10px; border: 1px solid var(--color-border-2); border-radius: 8px; background: var(--color-bg-popup); box-shadow: 0 18px 42px rgba(15, 23, 42, 0.16); }
.comment-mention-head { display: flex; align-items: center; gap: 10px; padding: 8px 8px 10px; border-bottom: 1px solid var(--color-border-1); }
.comment-mention-symbol { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 999px; background: rgb(var(--primary-6)); color: #fff; font-size: 14px; font-weight: 800; }
.comment-mention-head div { display: grid; gap: 2px; min-width: 0; }
.comment-mention-head strong { color: var(--color-text-1); font-size: 13px; }
.comment-mention-head span:not(.comment-mention-symbol) { color: var(--color-text-3); font-size: 12px; }
.comment-mention-list { display: grid; gap: 4px; padding-top: 8px; }
.comment-mention-option { display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 10px; align-items: center; width: 100%; min-height: 42px; padding: 6px 8px; border: 0; border-radius: 8px; background: transparent; color: var(--color-text-1); text-align: left; cursor: pointer; }
.comment-mention-option:hover, .comment-mention-option.is-active { background: var(--color-fill-2); }
.comment-mention-avatar { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 999px; background: var(--color-success-light-1); color: rgb(var(--green-7)); font-size: 12px; font-weight: 800; }
.comment-mention-person { display: grid; gap: 2px; min-width: 0; }
.comment-mention-person strong, .comment-mention-person span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.comment-mention-person strong { font-size: 13px; font-weight: 700; }
.comment-mention-person span { color: var(--color-text-3); font-size: 12px; }
.comment-actions { display: flex; justify-content: flex-end; }
@media (max-width: 640px) { .drawer-detail-header { flex-direction: column; }.comment-actions .arco-btn { width: 100%; } }
</style>

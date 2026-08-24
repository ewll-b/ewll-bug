<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconDelete, IconEdit, IconPlus, IconSave, IconSend } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import PageHeader from '../components/PageHeader.vue'
import ProjectFormModal from '../components/ProjectFormModal.vue'
import UserFormModal from '../components/UserFormModal.vue'
import ConfirmActionModal from '../components/ConfirmActionModal.vue'

const route = useRoute(); const router = useRouter(); const loading = ref(false); const saving = ref(false); const sending = ref(false)
const activeKey = ref(String(route.params.section || 'overview'))
const data = ref<DataRecord>({ cards: [], projects: [], users: [], project_usage: {}, user_usage: {}, report_notify: {} })
const projectVisible = ref(false); const userVisible = ref(false); const selectedProject = ref<DataRecord | null>(null); const selectedUser = ref<DataRecord | null>(null)
const deleteVisible = ref(false); const deleteType = ref<'project' | 'user'>('project'); const deleteItem = ref<DataRecord | null>(null)
const notifyForm = reactive<DataRecord>({})
const notifySecrets = reactive<DataRecord>({ webhook_url: '', secret: '', lark_app_secret: '' })
const projectColumns = [{ title: '项目名称', dataIndex: 'name' }, { title: '描述', dataIndex: 'description' }, { title: '通知', dataIndex: 'bug_notify_enabled', slotName: 'notify', width: 100 }, { title: '引用数据', slotName: 'usage', width: 100 }, { title: '操作', slotName: 'actions', width: 150 }]
const userColumns = [{ title: '姓名', dataIndex: 'name' }, { title: '账号', dataIndex: 'username' }, { title: '角色', dataIndex: 'role' }, { title: '类型', dataIndex: 'account_type', slotName: 'accountType', width: 100 }, { title: '邮箱', dataIndex: 'email' }, { title: '操作', slotName: 'actions', width: 150 }]

// 数字使用统计组件，文本状态使用标签，避免组件类型转换产生无效日期。
function isNumericCard(item: DataRecord) { return typeof item.count === 'number' }

async function load() {
  loading.value = true
  try {
    data.value = await api.admin()
    Object.assign(notifyForm, data.value.report_notify)
    Object.assign(notifySecrets, { webhook_url: '', secret: '', lark_app_secret: '' })
  } finally { loading.value = false }
}
function changeTab(key: string | number) { activeKey.value = String(key); router.replace(`/admin/${key}`) }
function openProject(item: DataRecord | null = null) { selectedProject.value = item; projectVisible.value = true }
function openUser(item: DataRecord | null = null) { selectedUser.value = item; userVisible.value = true }
function confirmDelete(type: 'project' | 'user', item: DataRecord) { deleteType.value = type; deleteItem.value = item; deleteVisible.value = true }
async function remove() {
  if (!deleteItem.value) return
  const form = new FormData(); form.set('entity', deleteType.value); form.set('action', 'delete'); form.set(`${deleteType.value}_id`, String(deleteItem.value.id))
  const result = await api.adminAction(form); Message.success(result.message || '已删除'); deleteVisible.value = false; await load()
}
function buildNotifyForm() {
  const form = new FormData(); form.set('entity', 'report_notify'); form.set('action', 'update')
  for (const key of ['send_time', 'project_id', 'version', 'base_url', 'manual_note', 'tracking_progress', 'message_format', 'lark_app_id']) form.set(key, String(notifyForm[key] ?? ''))
  for (const key of ['webhook_url', 'secret', 'lark_app_secret']) {
    const value = String(notifySecrets[key] ?? '').trim()
    if (value) form.set(key, value)
  }
  form.set('enabled', notifyForm.enabled ? '1' : '0')
  return form
}
async function saveNotify() {
  saving.value = true
  try {
    const result = await api.adminAction(buildNotifyForm()); Message.success(result.message || '设置已保存'); await load()
  } finally { saving.value = false }
}
async function sendReportNow() {
  sending.value = true
  try {
    await api.adminAction(buildNotifyForm())
    const form = new FormData(); form.set('entity', 'report_notify'); form.set('action', 'send_test')
    const result = await api.adminAction(form); Message.success(result.message || '报告已发送'); await load()
  } finally { sending.value = false }
}
watch(() => route.params.section, (section) => { activeKey.value = String(section || 'overview') })
onMounted(load)
</script>

<template>
  <div class="page-stack">
    <PageHeader title="系统管理" description="维护项目、账号和测试报告通知" />
    <section class="page-panel">
      <a-tabs :active-key="activeKey" @change="changeTab">
        <a-tab-pane key="overview" title="概览">
          <div class="admin-overview"><a-card v-for="item in data.cards" :key="item.title" :title="item.title" :bordered="true"><p class="muted">{{ item.desc }}</p><a-statistic v-if="isNumericCard(item)" :title="item.count_label" :value="item.count" /><div v-else class="admin-card-status"><span class="muted">{{ item.count_label }}</span><a-tag :color="item.count === '已开启' ? 'green' : 'gray'">{{ item.count }}</a-tag></div></a-card></div>
        </a-tab-pane>
        <a-tab-pane key="projects" title="项目管理">
          <div class="page-stack"><div class="page-toolbar"><a-button type="primary" @click="openProject()"><IconPlus />新建项目</a-button></div><a-table :columns="projectColumns" :data="data.projects" :loading="loading" :pagination="false" row-key="id"><template #notify="{ record }"><a-tag :color="record.bug_notify_enabled ? 'green' : 'gray'">{{ record.bug_notify_enabled ? '已开启' : '未开启' }}</a-tag></template><template #usage="{ record }">{{ data.project_usage[String(record.id)] || 0 }}</template><template #actions="{ record }"><a-space><a-tooltip content="编辑项目"><a-button type="text" size="small" aria-label="编辑项目" @click="openProject(record)"><IconEdit /></a-button></a-tooltip><a-tooltip content="删除项目"><a-button type="text" status="danger" size="small" aria-label="删除项目" @click="confirmDelete('project', record)"><IconDelete /></a-button></a-tooltip></a-space></template></a-table></div>
        </a-tab-pane>
        <a-tab-pane key="users" title="账号管理">
          <div class="page-stack"><div class="page-toolbar"><a-button type="primary" @click="openUser()"><IconPlus />新建账号</a-button></div><a-table :columns="userColumns" :data="data.users" :loading="loading" :pagination="false" row-key="id"><template #accountType="{ record }"><a-tag :color="record.account_type === 'admin' ? 'arcoblue' : 'gray'">{{ record.account_type === 'admin' ? '管理员' : '普通成员' }}</a-tag></template><template #actions="{ record }"><a-space><a-tooltip content="编辑账号"><a-button type="text" size="small" aria-label="编辑账号" @click="openUser(record)"><IconEdit /></a-button></a-tooltip><a-tooltip content="删除账号"><a-button type="text" status="danger" size="small" aria-label="删除账号" @click="confirmDelete('user', record)"><IconDelete /></a-button></a-tooltip></a-space></template></a-table></div>
        </a-tab-pane>
        <a-tab-pane key="notifications" title="报告通知">
          <a-form class="notify-form" :model="notifyForm" layout="vertical">
            <a-alert :type="notifyForm.webhook_configured ? 'success' : 'warning'">群机器人 Webhook：{{ notifyForm.webhook_configured ? '已安全配置，留空保留原值' : '未配置，请在下方填写' }}</a-alert>
            <a-form-item label="启用通知"><a-switch v-model="notifyForm.enabled" /></a-form-item>
            <a-form-item label="群机器人 Webhook">
              <a-input-password v-model="notifySecrets.webhook_url" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/...，留空保留原值" allow-clear />
            </a-form-item>
            <a-form-item label="机器人密钥（可选）">
              <a-input-password v-model="notifySecrets.secret" placeholder="如果群机器人开启加签，这里填写 Secret；留空保留原值" allow-clear />
            </a-form-item>
            <a-form-item label="发送时间"><a-time-picker v-model="notifyForm.send_time" format="HH:mm" value-format="HH:mm" /></a-form-item>
            <a-form-item label="项目"><a-select v-model="notifyForm.project_id" allow-clear><a-option v-for="item in data.projects" :key="item.id" :value="String(item.id)">{{ item.name }}</a-option></a-select></a-form-item>
            <a-form-item label="版本"><a-input v-model="notifyForm.version" /></a-form-item>
            <a-form-item label="平台访问地址"><a-input v-model="notifyForm.base_url" placeholder="https://" /></a-form-item>
            <a-form-item label="报告里的风险备注（可以艾特相关人）"><a-textarea v-model="notifyForm.manual_note" placeholder="例如：1. @张三 支付链路还需补一次回归" :auto-size="{ minRows: 3, maxRows: 6 }" /></a-form-item>
            <a-form-item label="埋点进度"><a-textarea v-model="notifyForm.tracking_progress" placeholder="例如：60%" :auto-size="{ minRows: 3, maxRows: 6 }" /></a-form-item>
            <a-form-item label="消息格式"><a-radio-group v-model="notifyForm.message_format" type="button"><a-radio value="card">卡片</a-radio><a-radio value="image">图片</a-radio></a-radio-group></a-form-item>
            <a-form-item label="飞书 App ID"><a-input v-model="notifyForm.lark_app_id" placeholder="选择图片消息时填写" allow-clear /></a-form-item>
            <a-form-item label="飞书 App Secret"><a-input-password v-model="notifySecrets.lark_app_secret" placeholder="选择图片消息时填写；留空保留原值" allow-clear /></a-form-item>
            <div class="notify-actions">
              <a-button type="primary" :loading="saving" :disabled="sending" @click="saveNotify"><IconSave />保存设置</a-button>
              <a-button status="success" :loading="sending" :disabled="saving" @click="sendReportNow"><IconSend />立即发送报告</a-button>
            </div>
            <div class="notify-run-status">
              <span>上次发送时间：{{ notifyForm.last_sent_at || '暂无' }}</span>
              <span>上次结果：{{ notifyForm.last_result || '暂无' }}</span>
            </div>
          </a-form>
        </a-tab-pane>
      </a-tabs>
    </section>
    <ProjectFormModal v-model:visible="projectVisible" :project="selectedProject" @saved="load" />
    <UserFormModal v-model:visible="userVisible" :user="selectedUser" @saved="load" />
    <ConfirmActionModal v-model:visible="deleteVisible" :title="`删除${deleteType === 'project' ? '项目' : '账号'}`" :content="`确认删除“${deleteItem?.name || ''}”吗？有关联数据时系统会阻止不安全操作。`" danger @confirm="remove" />
  </div>
</template>

<style scoped>.admin-overview { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }.admin-card-status { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; }.notify-form { max-width: 680px; }.notify-form .arco-alert { margin-bottom: 16px; }.notify-actions { display: flex; flex-wrap: wrap; gap: 12px; }.notify-run-status { margin-top: 16px; padding: 12px; border: 1px solid var(--color-border-2); border-radius: 6px; background: var(--color-fill-1); color: var(--color-text-2); display: grid; gap: 6px; }@media (max-width: 800px) { .admin-overview { grid-template-columns: 1fr; } }</style>

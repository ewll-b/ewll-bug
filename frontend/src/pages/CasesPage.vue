<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Message, type FileItem } from '@arco-design/web-vue'
import { IconFolderAdd, IconUpload } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import PageHeader from '../components/PageHeader.vue'
import CaseManageModal from '../components/CaseManageModal.vue'
import CaseDocumentDrawer from '../components/CaseDocumentDrawer.vue'

const loading = ref(false); const manageVisible = ref(false); const version = ref(''); const uploadFolder = ref(''); const files = ref<FileItem[]>([])
const documentVisible = ref(false); const selectedDocumentId = ref<number>()
const data = ref<DataRecord>({ documents: [], tree: [], versions: [], distribution: [] })
const folders = computed<string[]>(() => data.value.tree.map((item: DataRecord) => String(item.name)))
const openFolderKeys = computed(() => folders.value.map((item) => `folder:${item}`))
async function load() { loading.value = true; try { data.value = await api.cases(version.value); if (!uploadFolder.value) uploadFolder.value = folders.value[0] || '' } finally { loading.value = false } }
function selectDocument(key: string) { if (key.startsWith('doc:')) { selectedDocumentId.value = Number(key.slice(4)); documentVisible.value = true } }
async function upload() {
  const file = files.value[0]?.file
  if (!uploadFolder.value || !file) return Message.warning('请选择目标文件夹和 Excel 文件。')
  const form = new FormData(); form.set('folder_name', uploadFolder.value); form.set('version_filter', version.value); form.set('excel_file', file)
  const result = await api.uploadCases(form); Message.success(result.message || '导入完成'); files.value = []; await load()
}
onMounted(load)
</script>

<template>
  <div class="page-stack">
    <PageHeader title="用例库" description="管理文件夹、在线文档与 Excel 用例"><a-button type="primary" @click="manageVisible = true"><IconFolderAdd />新建</a-button></PageHeader>
    <div class="case-layout">
      <section class="page-panel case-tree-panel">
        <a-select v-model="version" allow-clear placeholder="全部版本" long @change="load"><a-option v-for="item in data.versions" :key="item" :value="item">{{ item }}</a-option></a-select>
        <a-divider />
        <a-menu :open-keys="openFolderKeys" @menu-item-click="selectDocument">
          <a-sub-menu v-for="folder in data.tree" :key="`folder:${folder.name}`">
            <template #title>{{ folder.name }}</template>
            <a-menu-item v-for="document in folder.documents" :key="`doc:${document.id}`">{{ document.doc_name }}</a-menu-item>
          </a-sub-menu>
        </a-menu>
      </section>
      <section class="page-panel page-stack">
        <a-alert>选择左侧在线文档进入标准表格编辑；Excel 导入会同步到所选文件夹。</a-alert>
        <div class="distribution-row"><div v-for="item in data.distribution" :key="item.status" class="distribution-item"><span>{{ item.status }}</span><strong>{{ item.count }}</strong><small>{{ item.percent }}</small></div></div>
        <a-divider orientation="left">导入 Excel</a-divider>
        <a-form :model="{ uploadFolder, files }" layout="vertical">
          <a-form-item label="目标文件夹"><a-select v-model="uploadFolder"><a-option v-for="item in folders" :key="item" :value="item">{{ item }}</a-option></a-select></a-form-item>
          <a-form-item label="Excel 文件"><a-upload v-model:file-list="files" accept=".xlsx,.xls" :auto-upload="false" :limit="1" draggable /></a-form-item>
          <a-button type="primary" :disabled="!files.length" @click="upload"><IconUpload />开始导入</a-button>
        </a-form>
      </section>
    </div>
    <CaseManageModal v-model:visible="manageVisible" :folders="folders" @saved="load" />
    <CaseDocumentDrawer v-model:visible="documentVisible" :document-id="selectedDocumentId" />
  </div>
</template>

<style scoped>
.case-layout { display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: 16px; }
.case-tree-panel { min-height: 520px; }
.distribution-row { display: grid; grid-template-columns: repeat(5, minmax(90px, 1fr)); gap: 8px; }
.distribution-item { padding: 12px; display: grid; gap: 3px; border: 1px solid var(--panel-border); border-radius: 4px; }.distribution-item strong { font-size: 20px; }.distribution-item small { color: var(--muted-text); }
@media (max-width: 800px) { .case-layout { grid-template-columns: 1fr; }.case-tree-panel { min-height: 0; }.distribution-row { grid-template-columns: repeat(2, 1fr); } }
</style>

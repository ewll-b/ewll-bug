<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { IconDownload, IconRefresh } from '@arco-design/web-vue/es/icon'
import { api, type DataRecord } from '../api'
import { withAppBase } from '../api/paths'
import { useSessionStore } from '../stores/session'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import BugDetailDrawer from '../components/BugDetailDrawer.vue'

const session = useSessionStore(); const loading = ref(false); const version = ref(''); const page = ref(1); const data = ref<DataRecord>({ summary: {}, distribution: [], bugs: [], versions: [], bug_page: { total: 0, page: 1 } }); const chartEl = ref<HTMLElement | null>(null)
const detailVisible = ref(false); const selectedBugId = ref<number>()
const columns = [
  { title: '编号', dataIndex: 'bug_no' },
  { title: '标题', dataIndex: 'title', slotName: 'title' },
  { title: '端', dataIndex: 'platform' },
  { title: '状态', dataIndex: 'status', slotName: 'status' },
  { title: '处理人', dataIndex: 'assignee_name' },
]
echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])
let chart: echarts.ECharts | null = null
async function renderChart() {
  await nextTick(); if (!chartEl.value) return
  chart?.dispose(); chart = echarts.init(chartEl.value, session.isDark ? 'dark' : undefined)
  chart.setOption({ backgroundColor: 'transparent', tooltip: { trigger: 'axis' }, grid: { left: 44, right: 20, top: 24, bottom: 36 }, xAxis: { type: 'category', data: data.value.distribution.map((item: DataRecord) => item.status) }, yAxis: { type: 'value', minInterval: 1 }, series: [{ type: 'bar', barMaxWidth: 48, data: data.value.distribution.map((item: DataRecord) => ({ value: item.count, itemStyle: { color: item.color } })) }] })
}
async function load() { loading.value = true; try { data.value = await api.report({ version: version.value, page: page.value }); page.value = Number(data.value.bug_page?.page || page.value); await renderChart() } finally { loading.value = false } }
// 切换版本后从第一页重新加载，避免沿用超出范围的旧页码。
async function changeVersion() { page.value = 1; await load() }
async function changePage(nextPage: number) { page.value = nextPage; await load() }
function download() { window.open(`${withAppBase('/reports/testing/export')}?version=${encodeURIComponent(version.value)}`, '_blank') }
function openDetail(id: number) { selectedBugId.value = id; detailVisible.value = true }
function resize() { chart?.resize() }
watch(() => session.isDark, renderChart)
onMounted(async () => { window.addEventListener('resize', resize); await load() }); onBeforeUnmount(() => { window.removeEventListener('resize', resize); chart?.dispose() })
</script>

<template>
  <div class="page-stack">
    <PageHeader title="测试报告" description="查看当前项目的用例执行与缺陷分布"><a-button @click="load"><IconRefresh />刷新</a-button><a-button type="primary" @click="download"><IconDownload />导出报告</a-button></PageHeader>
    <div class="page-toolbar"><a-select v-model="version" allow-clear placeholder="全部版本" @change="changeVersion"><a-option v-for="item in data.versions" :key="item" :value="item">{{ item }}</a-option></a-select></div>
    <div class="metric-row"><div class="metric"><div class="metric-label">测试用例</div><div class="metric-value">{{ data.case_total || 0 }}</div></div><div class="metric"><div class="metric-label">Bug 总数</div><div class="metric-value">{{ data.summary.total || 0 }}</div></div><div class="metric"><div class="metric-label">处理中</div><div class="metric-value">{{ data.summary.active_count || 0 }}</div></div><div class="metric"><div class="metric-label">待验证</div><div class="metric-value">{{ data.summary.verification_count || 0 }}</div></div></div>
    <section class="page-panel"><div ref="chartEl" class="chart-box" /></section>
    <section class="page-panel page-stack"><a-table :columns="columns" :data="data.bugs" :loading="loading" row-key="id" :pagination="false"><template #title="{ record }"><a-link class="table-link" @click="openDetail(Number(record.id))">{{ record.title }}</a-link></template><template #status="{ record }"><StatusTag :status="record.status" /></template></a-table><a-pagination :current="data.bug_page.page" :total="data.bug_page.total" :page-size="20" show-total @change="changePage" /></section>
    <BugDetailDrawer v-model:visible="detailVisible" :bug-id="selectedBugId" @changed="load" @deleted="load" />
  </div>
</template>

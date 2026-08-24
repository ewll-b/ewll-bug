<script setup lang="ts">
const props = defineProps<{ status?: string }>()
const labels: Record<string, string> = {
  open: '已打开', in_progress: '处理中', pending_verification: '待验证',
  closed: '已关闭', duplicate: '重复', on_hold: '搁置',
  pending: '待开始', doing: '进行中', completed: '已完成',
}

// 使用实底高对比色，让每种状态在明暗主题下都能快速识别。
const colors: Record<string, string> = {
  open: '#c92a2a', in_progress: '#1769c2', pending_verification: '#c2410c',
  closed: '#15803d', duplicate: '#7e22ce', on_hold: '#b4236a',
  pending: '#b45309', doing: '#1769c2', completed: '#15803d',
}
</script>

<template><a-tag class="status-tag" :color="colors[props.status || ''] || '#475569'">{{ labels[props.status || ''] || props.status || '-' }}</a-tag></template>

<style scoped>
.arco-tag.status-tag { color: #fff; font-weight: 600; }
</style>

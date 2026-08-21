<script setup lang="ts">
const props = defineProps<{ status?: string }>()
const labels: Record<string, string> = {
  open: '已打开', in_progress: '处理中', pending_verification: '待验证',
  closed: '已关闭', duplicate: '重复', on_hold: '搁置',
  pending: '待开始', doing: '进行中', completed: '已完成',
}
const colors: Record<string, string> = {
  open: 'red', in_progress: 'arcoblue', pending_verification: 'orange',
  closed: 'green', duplicate: 'gray', on_hold: 'gray',
  pending: 'orange', doing: 'arcoblue', completed: 'green',
}
</script>

<template><a-tag :color="colors[props.status || ''] || 'gray'">{{ labels[props.status || ''] || props.status || '-' }}</a-tag></template>

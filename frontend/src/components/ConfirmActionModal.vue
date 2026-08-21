<script setup lang="ts">
const props = withDefaults(defineProps<{ visible: boolean; title?: string; content: string; danger?: boolean; loading?: boolean }>(), {
  title: '确认操作', danger: false, loading: false,
})
const emit = defineEmits<{ 'update:visible': [value: boolean]; confirm: [] }>()
</script>

<template>
  <a-modal
    :visible="props.visible"
    :title="props.title"
    :ok-loading="props.loading"
    :ok-button-props="{ status: props.danger ? 'danger' : 'normal' }"
    @ok="emit('confirm')"
    @cancel="emit('update:visible', false)"
  >
    <a-alert :type="props.danger ? 'warning' : 'info'">{{ props.content }}</a-alert>
  </a-modal>
</template>

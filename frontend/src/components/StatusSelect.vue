<script setup lang="ts">
import StatusTag from './StatusTag.vue'
import type { DataRecord } from '../api'

withDefaults(defineProps<{
  modelValue?: string
  options: DataRecord[]
  size?: 'mini' | 'small' | 'medium' | 'large'
}>(), { modelValue: '', size: 'medium' })
const emit = defineEmits<{
  'update:modelValue': [value: string]
  change: [value: string]
}>()

function optionValue(data: DataRecord | undefined) {
  return String(data?.value || '')
}

function handleChange(value: unknown) {
  if (typeof value !== 'string') return
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<template>
  <a-select class="status-select" :model-value="modelValue" :size="size" @change="handleChange">
    <template #label="{ data }">
      <StatusTag :status="optionValue(data)" />
    </template>
    <a-option v-for="item in options" :key="item.value" :value="item.value" :label="item.label">
      <StatusTag :status="item.value" />
    </a-option>
  </a-select>
</template>

<style scoped>
.status-select :deep(.arco-select-view-value) { display: flex; align-items: center; }
.status-select :deep(.arco-tag) { margin-right: 0; }
</style>

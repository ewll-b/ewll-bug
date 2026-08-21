<script setup lang="ts">
import RequirementDetailPage from '../pages/RequirementDetailPage.vue'

defineProps<{ visible: boolean; requirementId?: number }>()
const emit = defineEmits<{ 'update:visible': [value: boolean]; changed: []; deleted: [] }>()

function close() { emit('update:visible', false) }
function handleDeleted() { close(); emit('deleted') }
</script>

<template>
  <a-drawer
    :visible="visible"
    width="min(920px, calc(100vw - 16px))"
    title="需求详情"
    :footer="false"
    unmount-on-close
    @update:visible="emit('update:visible', $event)"
  >
    <RequirementDetailPage v-if="requirementId" :entity-id="requirementId" embedded @changed="emit('changed')" @deleted="handleDeleted" />
  </a-drawer>
</template>

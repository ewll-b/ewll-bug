<script setup lang="ts">
import BugDetailPage from '../pages/BugDetailPage.vue'

defineProps<{ visible: boolean; bugId?: number }>()
const emit = defineEmits<{ 'update:visible': [value: boolean]; changed: []; deleted: [] }>()

function close() { emit('update:visible', false) }
function handleDeleted() { close(); emit('deleted') }
</script>

<template>
  <a-drawer
    :visible="visible"
    width="min(1080px, calc(100vw - 16px))"
    title="Bug 详情"
    :footer="false"
    unmount-on-close
    @update:visible="emit('update:visible', $event)"
  >
    <BugDetailPage v-if="bugId" :entity-id="bugId" embedded @changed="emit('changed')" @deleted="handleDeleted" />
  </a-drawer>
</template>

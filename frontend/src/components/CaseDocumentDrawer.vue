<script setup lang="ts">
import CaseDocumentPage from '../pages/CaseDocumentPage.vue'

defineProps<{ visible: boolean; documentId?: number }>()
const emit = defineEmits<{ 'update:visible': [value: boolean] }>()
</script>

<template>
  <a-drawer
    :visible="visible"
    width="min(1240px, calc(100vw - 16px))"
    title="在线用例详情"
    :footer="false"
    unmount-on-close
    @update:visible="emit('update:visible', $event)"
  >
    <CaseDocumentPage v-if="documentId" :entity-id="documentId" embedded />
  </a-drawer>
</template>

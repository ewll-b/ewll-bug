<script setup lang="ts">
import { ref } from 'vue'
import { IconFile } from '@arco-design/web-vue/es/icon'
import type { DataRecord } from '../api'

defineProps<{ items: DataRecord[] }>()
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewImages = ref<string[]>([])

function openPreview(items: DataRecord[], item: DataRecord) {
  previewImages.value = items.filter((entry) => entry.is_image).map((entry) => entry.url)
  previewIndex.value = Math.max(0, previewImages.value.indexOf(item.url))
  previewVisible.value = true
}
</script>

<template>
  <div v-if="items.length" class="attachment-grid">
    <template v-for="item in items" :key="item.id">
      <a-image
        v-if="item.is_image"
        :src="item.url"
        :title="item.filename"
        width="100%"
        height="112"
        fit="cover"
        :preview="false"
        class="attachment-image"
        @click="openPreview(items, item)"
      />
      <a-link v-else :href="item.url" target="_blank" class="file-link"><IconFile />{{ item.filename }}</a-link>
    </template>
    <a-image-preview-group
      v-model:visible="previewVisible"
      v-model:current="previewIndex"
      :src-list="previewImages"
      infinite
    />
  </div>
  <a-empty v-else description="暂无附件" />
</template>

<style scoped>
.attachment-image { cursor: zoom-in; border-radius: 4px; overflow: hidden; border: 1px solid var(--panel-border); }
.file-link { min-height: 44px; padding: 10px; display: flex; align-items: center; gap: 8px; border: 1px solid var(--panel-border); border-radius: 4px; overflow-wrap: anywhere; }
</style>

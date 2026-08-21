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
      <button
        v-if="item.is_image"
        type="button"
        class="attachment-image-button"
        :aria-label="`查看大图：${item.filename}`"
        @click="openPreview(items, item)"
      >
        <!-- 原生按钮统一承接单击，避免图片组件内部事件造成双击体验。 -->
        <a-image
          :src="item.url"
          :title="item.filename"
          width="100%"
          height="112"
          fit="cover"
          :preview="false"
          class="attachment-image"
        />
        <span>{{ item.filename }}</span>
      </button>
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
.attachment-image-button { min-width: 0; padding: 0; display: grid; gap: 7px; color: inherit; text-align: left; background: transparent; border: 0; cursor: zoom-in; }
.attachment-image { border-radius: 4px; overflow: hidden; border: 1px solid var(--panel-border); }
.attachment-image-button span { overflow: hidden; color: var(--muted-text); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.attachment-image-button:focus-visible { outline: 2px solid rgb(var(--primary-3)); outline-offset: 2px; }
.file-link { min-height: 44px; padding: 10px; display: flex; align-items: center; gap: 8px; border: 1px solid var(--panel-border); border-radius: 4px; overflow-wrap: anywhere; }
</style>

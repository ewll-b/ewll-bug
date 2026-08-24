<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'
import { IconClose } from '@arco-design/web-vue/es/icon'
import type { DataRecord } from '../api'

const props = withDefaults(defineProps<{
  modelValue: string
  images: DataRecord[]
  minRows?: number
  placeholder?: string
  fieldLabel?: string
}>(), {
  minRows: 3,
  placeholder: '',
  fieldLabel: '正文',
})
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:images': [value: DataRecord[]]
}>()
const editorStyle = computed(() => ({
  '--image-paste-min-height': `${Math.max(1, props.minRows) * 24 + 18}px`,
}))

function revokeImageUrl(item: DataRecord) {
  const url = String(item.url || '')
  if (url.startsWith('blob:')) URL.revokeObjectURL(url)
}

function updateText(event: Event) {
  emit('update:modelValue', (event.target as HTMLTextAreaElement).value)
}

function clipboardImageFiles(event: ClipboardEvent) {
  const files = Array.from(event.clipboardData?.files || []).filter((file) => file.type.startsWith('image/'))
  if (files.length) return files
  return Array.from(event.clipboardData?.items || [])
    .filter((item) => item.kind === 'file' && item.type.startsWith('image/'))
    .map((item) => item.getAsFile())
    .filter((file): file is File => Boolean(file))
}

function normalizedPastedImage(file: File, timestamp: string, index: number): DataRecord {
  const extension = file.type.split('/')[1]?.replace('jpeg', 'jpg') || 'png'
  const normalizedFile = new File([file], `${props.fieldLabel}-image-${timestamp}-${index + 1}.${extension}`, { type: file.type })
  return {
    uid: `inline-${timestamp}-${index}`,
    name: normalizedFile.name,
    file: normalizedFile,
    url: URL.createObjectURL(normalizedFile),
  }
}

function insertTextAtCursor(textarea: HTMLTextAreaElement, text: string) {
  if (!text) return props.modelValue
  const start = textarea.selectionStart ?? props.modelValue.length
  const end = textarea.selectionEnd ?? props.modelValue.length
  const nextValue = `${props.modelValue.slice(0, start)}${text}${props.modelValue.slice(end)}`
  requestAnimationFrame(() => {
    const cursor = start + text.length
    textarea.setSelectionRange(cursor, cursor)
  })
  return nextValue
}

function handlePaste(event: ClipboardEvent) {
  const pastedImages = clipboardImageFiles(event)
  if (!pastedImages.length) return
  event.preventDefault()
  const timestamp = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14)
  const text = event.clipboardData?.getData('text/plain') || ''
  const nextText = insertTextAtCursor(event.currentTarget as HTMLTextAreaElement, text)
  emit('update:modelValue', nextText)
  emit('update:images', [
    ...props.images,
    ...pastedImages.map((file, index) => normalizedPastedImage(file, timestamp, index)),
  ])
}

function removeImage(uid: string) {
  const target = props.images.find((item) => item.uid === uid)
  if (target) revokeImageUrl(target)
  emit('update:images', props.images.filter((item) => item.uid !== uid))
}

watch(() => props.images, (nextImages, previousImages) => {
  for (const item of previousImages || []) {
    if (!nextImages.some((nextItem) => nextItem.uid === item.uid)) revokeImageUrl(item)
  }
})

onBeforeUnmount(() => {
  props.images.forEach(revokeImageUrl)
})
</script>

<template>
  <div class="image-paste-textarea" :style="editorStyle">
    <textarea
      class="image-paste-control"
      :value="modelValue"
      :rows="minRows"
      :placeholder="placeholder"
      @input="updateText"
      @paste="handlePaste"
    />
    <div v-if="images.length" class="image-paste-list">
      <div v-for="item in images" :key="item.uid" class="image-paste-item">
        <img :src="item.url" :alt="item.name" class="image-paste-thumb">
        <span class="image-paste-name">{{ item.name }}</span>
        <a-button type="text" size="mini" shape="circle" :aria-label="`移除图片：${item.name}`" @click="removeImage(String(item.uid))">
          <IconClose />
        </a-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.image-paste-textarea { display: grid; gap: 8px; }
.image-paste-textarea {
  width: 100%;
  padding: 1px;
  background: var(--color-fill-2);
  border: 1px solid transparent;
  border-radius: 4px;
  transition: color .1s cubic-bezier(0, 0, 1, 1), border-color .1s cubic-bezier(0, 0, 1, 1), background-color .1s cubic-bezier(0, 0, 1, 1);
}
.image-paste-textarea:hover { background: var(--color-fill-3); }
.image-paste-textarea:focus-within {
  background: var(--color-bg-2);
  border-color: rgb(var(--primary-6));
}
.image-paste-control {
  width: 100%;
  min-height: var(--image-paste-min-height);
  padding: 7px 12px;
  color: var(--color-text-1);
  font: inherit;
  line-height: 1.5715;
  background: transparent;
  border: 0;
  border-radius: 4px;
  outline: none;
  resize: vertical;
}
.image-paste-control::placeholder { color: var(--color-text-3); }
.image-paste-list { padding: 0 7px 7px; display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.image-paste-item {
  min-width: 0;
  padding: 6px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 24px;
  align-items: center;
  gap: 8px;
  background: var(--color-fill-1);
  border: 1px solid var(--panel-border);
  border-radius: 4px;
}
.image-paste-thumb { width: 42px; height: 42px; object-fit: cover; border-radius: 4px; border: 1px solid var(--panel-border); }
.image-paste-name { min-width: 0; overflow: hidden; color: var(--muted-text); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
</style>

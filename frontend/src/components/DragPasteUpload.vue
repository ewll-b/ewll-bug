<script setup lang="ts">
import { ref } from 'vue'
import type { FileItem } from '@arco-design/web-vue'

const props = withDefaults(defineProps<{
  modelValue: FileItem[]
  accept?: string
  multiple?: boolean
  limit?: number
}>(), { accept: '', multiple: true, limit: 0 })
const emit = defineEmits<{ 'update:modelValue': [value: FileItem[]] }>()
const uploadArea = ref<HTMLElement>()

function updateFiles(value: FileItem[]) { emit('update:modelValue', value) }

function handlePaste(event: ClipboardEvent) {
  const clipboardFiles = Array.from(event.clipboardData?.files || []).filter((file) => file.type.startsWith('image/'))
  if (!clipboardFiles.length) return
  event.preventDefault()
  // 浏览器粘贴截图通常没有可辨识名称，这里生成稳定的图片文件名。
  const timestamp = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14)
  const pastedItems = clipboardFiles.map((file, index) => {
    const extension = file.type.split('/')[1]?.replace('jpeg', 'jpg') || 'png'
    const normalizedFile = new File([file], `screenshot-${timestamp}-${index + 1}.${extension}`, { type: file.type })
    return { uid: `paste-${timestamp}-${index}`, name: normalizedFile.name, file: normalizedFile } as FileItem
  })
  const nextFiles = [...props.modelValue, ...pastedItems]
  updateFiles(props.limit > 0 ? nextFiles.slice(0, props.limit) : nextFiles)
}

function focusPasteArea() { uploadArea.value?.focus() }
</script>

<template>
  <a-tooltip content="支持拖拽文件或粘贴剪贴板截图">
    <div
      ref="uploadArea"
      class="drag-paste-upload"
      tabindex="0"
      role="group"
      aria-label="附件上传"
      @click.capture="focusPasteArea"
      @paste="handlePaste"
    >
      <a-upload
        :file-list="modelValue"
        :accept="accept"
        :multiple="multiple"
        :limit="limit || undefined"
        draggable
        :auto-upload="false"
        @update:file-list="updateFiles"
      />
    </div>
  </a-tooltip>
</template>

<style scoped>
.drag-paste-upload { width: 100%; border-radius: 4px; outline: none; }
.drag-paste-upload:focus-visible { box-shadow: 0 0 0 2px rgb(var(--primary-3)); }
</style>

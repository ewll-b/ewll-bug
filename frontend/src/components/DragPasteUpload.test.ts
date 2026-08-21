import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import DragPasteUpload from './DragPasteUpload.vue'

const UploadStub = defineComponent({ props: ['fileList'], template: '<div data-upload>{{ fileList.length }}</div>' })

describe('DragPasteUpload', () => {
  it('粘贴截图后加入附件列表', async () => {
    const wrapper = mount(DragPasteUpload, {
      props: { modelValue: [] },
      global: { stubs: { 'a-upload': UploadStub, 'a-tooltip': { template: '<div><slot /></div>' } } },
    })
    const screenshot = new File(['image'], 'image.png', { type: 'image/png' })

    await wrapper.find('.drag-paste-upload').trigger('paste', { clipboardData: { files: [screenshot] } })

    const files = wrapper.emitted('update:modelValue')?.[0]?.[0] as Array<{ file: File }>
    expect(files).toHaveLength(1)
    expect(files[0].file.name).toMatch(/^screenshot-\d{14}-1\.png$/)
  })
})

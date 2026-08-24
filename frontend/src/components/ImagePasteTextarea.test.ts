import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import ImagePasteTextarea from './ImagePasteTextarea.vue'

const ButtonStub = defineComponent({ template: '<button type="button"><slot /></button>' })

describe('ImagePasteTextarea', () => {
  it('粘贴截图后生成预览图片文件', async () => {
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test-image')
    const wrapper = mount(ImagePasteTextarea, {
      props: { modelValue: '', images: [], fieldLabel: 'expected-result' },
      global: { stubs: { 'a-button': ButtonStub, IconClose: true } },
    })
    const screenshot = new File(['image'], 'image.png', { type: 'image/png' })

    await wrapper.find('textarea').trigger('paste', { clipboardData: { files: [screenshot], getData: () => '' } })

    const images = wrapper.emitted('update:images')?.[0]?.[0] as Array<{ file: File; name: string; url: string }>
    expect(images).toHaveLength(1)
    expect(images[0].file.name).toMatch(/^expected-result-image-\d{14}-1\.png$/)
    expect(images[0].url).toBe('blob:test-image')
    createObjectURL.mockRestore()
  })

  it('粘贴图文内容时同步保留文字和图片', async () => {
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test-image')
    const wrapper = mount(ImagePasteTextarea, {
      props: { modelValue: '', images: [], fieldLabel: 'description' },
      global: { stubs: { 'a-button': ButtonStub, IconClose: true } },
    })
    const screenshot = new File(['image'], 'image.png', { type: 'image/png' })

    await wrapper.find('textarea').trigger('paste', { clipboardData: { files: [screenshot], getData: () => '文字说明' } })

    expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toBe('文字说明')
    const images = wrapper.emitted('update:images')?.[0]?.[0] as Array<{ file: File }>
    expect(images).toHaveLength(1)
    createObjectURL.mockRestore()
  })
})

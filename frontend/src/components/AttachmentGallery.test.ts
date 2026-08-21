import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AttachmentGallery from './AttachmentGallery.vue'

const ImageStub = defineComponent({ template: '<span data-image>图片</span>' })
const PreviewStub = defineComponent({ props: ['visible', 'current', 'srcList'], template: '<div data-preview>{{ visible }}|{{ current }}|{{ srcList?.join(\',\') }}</div>' })

describe('AttachmentGallery', () => {
  it('点击图片后打开组件库预览并定位当前图片', async () => {
    const wrapper = mount(AttachmentGallery, {
      props: { items: [
        { id: 1, filename: 'a.png', url: '/a.png', is_image: true },
        { id: 2, filename: 'readme.txt', url: '/readme.txt', is_image: false },
        { id: 3, filename: 'b.png', url: '/b.png', is_image: true },
      ] },
      global: { stubs: { 'a-image': ImageStub, 'a-image-preview-group': PreviewStub, 'a-link': true, 'a-empty': true, IconFile: true } },
    })

    await wrapper.findAll('.attachment-image-button')[1].trigger('click')
    expect(wrapper.find('[data-preview]').text()).toBe('true|1|/a.png,/b.png')
  })
})

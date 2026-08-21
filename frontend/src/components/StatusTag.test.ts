import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import StatusTag from './StatusTag.vue'

const TagStub = defineComponent({ template: '<span><slot /></span>' })

describe('StatusTag', () => {
  it('展示标准中文状态文本', () => {
    const wrapper = mount(StatusTag, {
      props: { status: 'pending_verification' },
      global: { stubs: { 'a-tag': TagStub } },
    })

    expect(wrapper.text()).toBe('待验证')
  })
})

import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import StatusTag from './StatusTag.vue'

const TagStub = defineComponent({
  props: { color: String },
  template: '<span :data-color="color"><slot /></span>',
})

describe('StatusTag', () => {
  it('展示标准中文状态文本', () => {
    const wrapper = mount(StatusTag, {
      props: { status: 'pending_verification' },
      global: { stubs: { 'a-tag': TagStub } },
    })

    expect(wrapper.text()).toBe('待验证')
    expect(wrapper.attributes('data-color')).toBe('#c2410c')
  })

  it('为不同 Bug 状态分配不同的鲜艳颜色', () => {
    const statuses = ['open', 'in_progress', 'pending_verification', 'closed', 'duplicate', 'on_hold']
    const colors = statuses.map((status) => mount(StatusTag, {
      props: { status },
      global: { stubs: { 'a-tag': TagStub } },
    }).attributes('data-color'))

    expect(new Set(colors).size).toBe(statuses.length)
  })
})

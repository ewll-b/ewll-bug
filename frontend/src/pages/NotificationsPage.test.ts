import { createPinia } from 'pinia'
import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const apiMock = vi.hoisted(() => ({
  notifications: vi.fn(),
  readAllNotifications: vi.fn(),
  readNotification: vi.fn(),
  summary: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

import NotificationsPage from './NotificationsPage.vue'

const ListStub = defineComponent({
  props: ['data'],
  template: '<div><template v-for="item in data" :key="item.id"><slot name="item" :item="item" /></template></div>',
})
const ListItemMetaStub = defineComponent({
  props: ['title', 'description'],
  template: '<div><slot name="avatar" /><span>{{ title }}</span><span>{{ description }}</span></div>',
})
const BadgeStub = defineComponent({
  props: ['count', 'dot'],
  template: '<span data-badge><slot />{{ count }}</span>',
})

describe('NotificationsPage', () => {
  it('仅为未读消息头像展示红点且不出现 NaN', async () => {
    apiMock.notifications.mockResolvedValue({
      items: [
        { id: 1, title: '未读消息', body: '内容一', is_read: 0 },
        { id: 2, title: '已读消息', body: '内容二', is_read: 1 },
      ],
      unread_count: 1,
      total_count: 2,
    })

    const wrapper = mount(NotificationsPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          'a-list': ListStub,
          'a-list-item': defineComponent({ template: '<div><slot /><slot name="actions" /></div>' }),
          'a-list-item-meta': ListItemMetaStub,
          'a-badge': BadgeStub,
          'a-avatar': defineComponent({ template: '<span data-avatar><slot /></span>' }),
          'a-tabs': defineComponent({ template: '<div><slot /></div>' }),
          'a-tab-pane': true,
          'a-button': true,
          'a-tag': true,
          PageHeader: true,
          BugDetailDrawer: true,
          RequirementDetailDrawer: true,
          CaseDocumentDrawer: true,
          IconCheck: true,
          IconNotification: true,
        },
      },
    })
    await flushPromises()

    expect(wrapper.findAll('[data-avatar]')).toHaveLength(2)
    expect(wrapper.findAll('[data-badge]')).toHaveLength(1)
    expect(wrapper.find('[data-badge]').text()).toBe('1')
    expect(wrapper.text()).not.toContain('NaN')
  })
})

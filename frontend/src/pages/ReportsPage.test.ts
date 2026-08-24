import { defineComponent } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiMock = vi.hoisted(() => ({ report: vi.fn() }))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../stores/session', () => ({ useSessionStore: () => ({ isDark: false }) }))
vi.mock('echarts/core', () => ({
  use: vi.fn(),
  init: vi.fn(() => ({ setOption: vi.fn(), dispose: vi.fn(), resize: vi.fn() })),
}))

import ReportsPage from './ReportsPage.vue'

const PaginationStub = defineComponent({
  emits: ['change'],
  template: '<button data-page-two @click="$emit(\'change\', 2)">第 2 页</button>',
})
const TableStub = defineComponent({
  props: ['data'],
  template: '<div><div v-for="record in data" :key="record.id"><slot name="title" :record="record" /></div></div>',
})

describe('ReportsPage pagination', () => {
  beforeEach(() => {
    apiMock.report.mockReset().mockImplementation(({ page }) => Promise.resolve({
      summary: {}, distribution: [], bugs: [{ id: page, title: `报告第 ${page} 页` }], versions: [], case_total: 0,
      bug_page: { items: [], total: 45, page, pages: 3 },
    }))
  })

  it('点击页码后按目标页重新加载报告', async () => {
    const wrapper = shallowMount(ReportsPage, { global: { stubs: { 'a-pagination': PaginationStub, 'a-table': TableStub } } })
    await flushPromises()

    await wrapper.get('[data-page-two]').trigger('click')
    await flushPromises()

    expect(apiMock.report).toHaveBeenLastCalledWith({ version: '', page: 2 })
    expect(wrapper.text()).toContain('报告第 2 页')
  })
})

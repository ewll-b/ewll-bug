import { defineComponent } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiMock = vi.hoisted(() => ({ bugs: vi.fn() }))
const routerReplace = vi.hoisted(() => vi.fn())

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ replace: routerReplace }),
}))
vi.mock('../stores/session', () => ({
  useSessionStore: () => ({ ready: true, options: { platforms: [], statuses: [] }, currentProject: { id: 1 }, switchProject: vi.fn() }),
}))

import BugsPage from './BugsPage.vue'

const PaginationStub = defineComponent({
  emits: ['change'],
  template: '<button data-page-two @click="$emit(\'change\', 2)">第 2 页</button>',
})

describe('BugsPage pagination', () => {
  beforeEach(() => {
    apiMock.bugs.mockReset().mockResolvedValue({ page: { items: [], total: 45, page: 1 }, summary: {}, versions: [], users: [], requirements: [], cases: [] })
    routerReplace.mockReset().mockResolvedValue(undefined)
  })

  it('翻页时保留目标页码并同步到查询参数', async () => {
    const wrapper = shallowMount(BugsPage, { global: { stubs: { 'a-pagination': PaginationStub } } })
    await flushPromises()

    await wrapper.get('[data-page-two]').trigger('click')
    await flushPromises()

    expect(apiMock.bugs).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 }))
    expect(routerReplace).toHaveBeenLastCalledWith({ query: expect.objectContaining({ page: 2 }) })
  })
})

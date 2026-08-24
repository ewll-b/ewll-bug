import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const apiMock = vi.hoisted(() => ({
  bootstrap: vi.fn(),
  summary: vi.fn(),
  switchProject: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

import { useSessionStore } from './session'

describe('session summary refresh', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => vi.useRealTimers())

  it('每 30 秒刷新一次菜单角标并可停止', async () => {
    apiMock.summary.mockResolvedValue({ summary: { my_todo_count: 4, notification_unread_count: 2 } })
    const session = useSessionStore()

    session.startSummaryAutoRefresh()
    session.startSummaryAutoRefresh()
    await vi.advanceTimersByTimeAsync(30_000)

    expect(apiMock.summary).toHaveBeenCalledTimes(1)
    expect(session.summary).toEqual({ my_todo_count: 4, notification_unread_count: 2 })

    session.stopSummaryAutoRefresh()
    await vi.advanceTimersByTimeAsync(30_000)
    expect(apiMock.summary).toHaveBeenCalledTimes(1)
  })
})

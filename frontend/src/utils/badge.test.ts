import { describe, expect, it } from 'vitest'
import { normalizeBadgeCount } from './badge'

describe('normalizeBadgeCount', () => {
  it('将异常值和非正数统一归零', () => {
    expect(normalizeBadgeCount(undefined)).toBe(0)
    expect(normalizeBadgeCount('invalid')).toBe(0)
    expect(normalizeBadgeCount(-2)).toBe(0)
    expect(normalizeBadgeCount(0)).toBe(0)
  })

  it('将有效数量转换为非负整数', () => {
    expect(normalizeBadgeCount('5')).toBe(5)
    expect(normalizeBadgeCount(3.9)).toBe(3)
  })
})

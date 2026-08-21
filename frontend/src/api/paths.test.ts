import { describe, expect, it } from 'vitest'
import { withAppBase, withoutAppBase } from './paths'

describe('子路径工具', () => {
  it('为资源和后端入口补充应用前缀', () => {
    expect(withAppBase('/reports/testing/export', '/for-test')).toBe('/for-test/reports/testing/export')
    expect(withAppBase('login', '')).toBe('/login')
  })

  it('登录回跳时移除 Router 已管理的前缀', () => {
    expect(withoutAppBase('/for-test/bugs', '/for-test')).toBe('/bugs')
    expect(withoutAppBase('/for-test', '/for-test')).toBe('/')
    expect(withoutAppBase('/other/bugs', '/for-test')).toBe('/other/bugs')
  })
})

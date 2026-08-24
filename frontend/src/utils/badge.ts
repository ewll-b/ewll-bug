export function normalizeBadgeCount(value: unknown): number {
  const count = Number(value)
  // 角标只接受非负整数，防止组件把空值或异常值显示为 NaN。
  return Number.isFinite(count) && count > 0 ? Math.floor(count) : 0
}

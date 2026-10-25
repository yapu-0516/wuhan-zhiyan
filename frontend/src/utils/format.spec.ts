import { describe, expect, it } from 'vitest'
import { fixed, isToday, metricLabel, metricValue, parseTime, percent, relativeTime, thousands } from '@/utils/format'

describe('通用指标格式化', () => {
  it('parseTime 支持空格与 ISO 时间', () => {
    expect(parseTime('2026-03-18 10:30:00')?.getHours()).toBe(10)
    expect(parseTime('2026-03-18T10:30:00')?.getHours()).toBe(10)
    expect(parseTime(undefined)).toBeNull()
  })

  it('relativeTime 处理未来时间', () => {
    const now = new Date('2026-03-18T12:00:00').getTime()
    expect(relativeTime('2026-03-18 13:00:00', now)).toBe('03-18 13:00')
    expect(relativeTime('2026-03-18 11:30:00', now)).toBe('30 分钟前')
  })

  it('isToday 比较本地日期', () => {
    expect(isToday('2026-03-18 08:00:00', new Date('2026-03-18T12:00:00'))).toBe(true)
    expect(isToday('2026-03-17 23:59:59', new Date('2026-03-18T12:00:00'))).toBe(false)
  })

  it('fixed / percent / thousands 对非法值输出占位符', () => {
    expect(fixed(1.234, 2)).toBe('1.23')
    expect(fixed(null)).toBe('--')
    expect(percent(0.875)).toBe('88%')
    expect(percent(undefined)).toBe('--')
    expect(thousands(1234567)).toBe('1,234,567')
    expect(thousands(null)).toBe('--')
  })

  it('未知指标保留原值并可格式化数值', () => {
    expect(metricLabel('unknown_metric')).toBe('unknown_metric')
    expect(metricValue('unknown_metric', 1.234)).toBe('1.23')
  })
})

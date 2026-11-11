import { describe, expect, it } from 'vitest'
import { ORDER_STATUS_META, ORDER_TRANSITIONS, TASK_STATUS_META, TASK_TRANSITIONS } from './workflow'

describe('workflow state metadata', () => {
  it('only exposes declared order transitions', () => {
    for (const targets of Object.values(ORDER_TRANSITIONS)) {
      for (const target of targets) expect(ORDER_STATUS_META[target]).toBeDefined()
    }
    expect(ORDER_TRANSITIONS.pending).toContain('accepted')
    expect(ORDER_TRANSITIONS.completed).toEqual(['verified', 'rejected'])
    expect(ORDER_TRANSITIONS.verified).toEqual([])
  })

  it('keeps task status labels and transitions complete', () => {
    for (const targets of Object.values(TASK_TRANSITIONS)) {
      for (const target of targets) expect(TASK_STATUS_META[target]).toBeDefined()
    }
    expect(TASK_TRANSITIONS.draft).toEqual(['scheduled', 'running'])
    expect(TASK_TRANSITIONS.running).toEqual(['completed', 'failed'])
  })
})

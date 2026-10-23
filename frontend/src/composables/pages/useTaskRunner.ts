// AI 任务跟踪器：WebSocket task.updated 优先，1s 轮询兜底，直至任务结束。
// 组件卸载时自动取消订阅并清理定时器。
import { computed, onBeforeUnmount, ref } from 'vue'
import { getTask } from '@/api/task'
import { useRealtime } from '@/composables/useRealtime'
import { isTerminal } from './aiMeta'
import { parseTs } from './format'
import type { AnalysisTask } from '@/types/api'

const POLL_MS = 1000
const MAX_TRACK_MS = 3 * 60 * 1000

export interface TaskRunnerOptions {
  /** 任务进入终态（done / failed）时回调 */
  onTerminal?: (t: AnalysisTask) => void
  /** 收到任意任务的 WebSocket 更新（用于刷新历史列表） */
  onAnyUpdate?: (t: AnalysisTask) => void
}

export function useTaskRunner(opts: TaskRunnerOptions = {}) {
  const current = ref<AnalysisTask | null>(null)
  const elapsedMs = ref(0)
  const stalled = ref(false)
  let startedAt = 0
  let pollTimer: number | undefined
  let tickTimer: number | undefined
  let pollFailures = 0

  const active = computed(() => !!current.value && !isTerminal(current.value))

  function stopTimers() {
    window.clearInterval(pollTimer)
    window.clearInterval(tickTimer)
    pollTimer = undefined
    tickTimer = undefined
  }

  function finalizeElapsed(t: AnalysisTask) {
    const a = parseTs(t.createdAt)
    const b = parseTs(t.finished_at)
    if (a && b && b.getTime() >= a.getTime()) elapsedMs.value = b.getTime() - a.getTime()
    else if (startedAt) elapsedMs.value = Date.now() - startedAt
  }

  /** 合并更新：终态不被旧的进行中消息覆盖，进度不回退 */
  function apply(t: AnalysisTask) {
    const cur = current.value
    if (!cur || cur.id !== t.id) return
    if (isTerminal(cur) && !isTerminal(t)) return
    if (!isTerminal(t) && (t.progress ?? 0) < (cur.progress ?? 0)) return
    current.value = { ...cur, ...t }
    if (isTerminal(t)) {
      stopTimers()
      finalizeElapsed(t)
      opts.onTerminal?.(current.value)
    }
  }

  async function poll() {
    const cur = current.value
    if (!cur || isTerminal(cur)) return stopTimers()
    if (Date.now() - startedAt > MAX_TRACK_MS) {
      stalled.value = true
      return stopTimers()
    }
    try {
      apply(await getTask(cur.id))
      pollFailures = 0
    } catch {
      if (++pollFailures >= 15) {
        stalled.value = true
        stopTimers()
      }
    }
  }

  /** 开始跟踪（或仅展示）一个任务 */
  function track(task: AnalysisTask) {
    stopTimers()
    stalled.value = false
    pollFailures = 0
    current.value = task
    startedAt = Date.now()
    if (isTerminal(task)) {
      elapsedMs.value = 0
      finalizeElapsed(task)
      return
    }
    elapsedMs.value = 0
    tickTimer = window.setInterval(() => (elapsedMs.value = Date.now() - startedAt), 100)
    pollTimer = window.setInterval(() => void poll(), POLL_MS)
  }

  function clear() {
    stopTimers()
    current.value = null
    elapsedMs.value = 0
    stalled.value = false
  }

  const unsub = useRealtime().on('task.updated', (t) => {
    opts.onAnyUpdate?.(t)
    apply(t)
  })

  onBeforeUnmount(() => {
    unsub()
    stopTimers()
  })

  return { current, active, elapsedMs, stalled, track, clear }
}

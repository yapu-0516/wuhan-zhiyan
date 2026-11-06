import { ref } from 'vue'

/** 全屏演示共享状态：平静基线时，总览和全局状态栏都不展示历史异常。 */
const calmBaseline = ref(true)
const demoEventIds = ref<string[]>([])

export function useDemoBaseline() {
  return {
    calm: calmBaseline,
    demoEventIds,
    enterCalmBaseline: () => (calmBaseline.value = true),
    revealAnomalies: () => (calmBaseline.value = false),
    setDemoEventIds: (ids: string[]) => (demoEventIds.value = ids)
  }
}

// 视口宽度（响应式）：表格在窄屏下按优先级收起次要列，避免出现横向滚动
import { onBeforeUnmount, onMounted, ref } from 'vue'

export function useViewportWidth() {
  const width = ref(typeof window === 'undefined' ? 1920 : window.innerWidth)
  const update = () => (width.value = window.innerWidth)
  onMounted(() => window.addEventListener('resize', update, { passive: true }))
  onBeforeUnmount(() => window.removeEventListener('resize', update))
  return width
}

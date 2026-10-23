<script setup lang="ts">
// 数字滚动：值变化时以缓动从旧值过渡到新值（requestAnimationFrame，卸载时取消）
import { onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ value: number; decimals?: number; duration?: number }>(), {
  decimals: 0,
  duration: 900
})

const display = ref(Number.isFinite(props.value) ? props.value : 0)
let raf = 0

watch(
  () => props.value,
  (to) => {
    cancelAnimationFrame(raf)
    if (!Number.isFinite(to)) return
    const from = display.value
    const start = performance.now()
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / props.duration)
      const e = 1 - Math.pow(1 - t, 3)
      display.value = from + (to - from) * e
      if (t < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
  }
)

onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <span class="ce-num">{{ display.toFixed(decimals) }}</span>
</template>

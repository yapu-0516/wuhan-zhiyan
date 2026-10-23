<script setup lang="ts">
// 数字平滑过渡（requestAnimationFrame 缓动），用于 KPI 与实时吞吐展示
import { onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    value: number
    digits?: number
    duration?: number
  }>(),
  { digits: 0, duration: 600 }
)

const shown = ref(props.value)
let raf = 0

function tween(from: number, to: number) {
  cancelAnimationFrame(raf)
  if (!Number.isFinite(from) || !Number.isFinite(to) || props.duration <= 0 || from === to) {
    shown.value = to
    return
  }
  const t0 = performance.now()
  const step = (now: number) => {
    const k = Math.min(1, (now - t0) / props.duration)
    const eased = 1 - Math.pow(1 - k, 3)
    shown.value = from + (to - from) * eased
    if (k < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
}

watch(
  () => props.value,
  (to) => tween(shown.value, to)
)

onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <span class="anum">{{
    Number.isFinite(shown) ? shown.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—'
  }}</span>
</template>

<style scoped>
.anum {
  font-variant-numeric: tabular-nums;
}
</style>

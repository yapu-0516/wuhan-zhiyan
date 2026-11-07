<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    value: number
    digits?: number
    duration?: number
  }>(),
  { digits: 0, duration: 700 }
)

const shown = ref(Number.isFinite(props.value) ? props.value : 0)
let frame = 0

watch(
  () => props.value,
  (target) => {
    cancelAnimationFrame(frame)
    if (!Number.isFinite(target) || props.duration <= 0 || target === shown.value) {
      shown.value = Number.isFinite(target) ? target : 0
      return
    }
    const from = shown.value
    const startedAt = performance.now()
    const step = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / props.duration)
      shown.value = from + (target - from) * (1 - Math.pow(1 - progress, 3))
      if (progress < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
  }
)

onBeforeUnmount(() => cancelAnimationFrame(frame))
</script>

<template>
  <span class="ce-num">{{ shown.toFixed(digits) }}</span>
</template>

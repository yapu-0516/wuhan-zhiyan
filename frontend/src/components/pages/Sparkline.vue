<script setup lang="ts">
// 轻量 SVG 迷你折线（实时吞吐等）。不足 2 个点时画虚线占位，不伪造历史。
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    values: number[]
    color?: string
    height?: number
    /** 固定 y 轴下限/上限；缺省按数据自适应 */
    min?: number
    max?: number
  }>(),
  { color: '#4fc3f7', height: 36 }
)

const W = 100

const geometry = computed(() => {
  const v = props.values.filter((x) => Number.isFinite(x))
  if (v.length < 2) return null
  let lo = props.min ?? Math.min(...v)
  let hi = props.max ?? Math.max(...v)
  if (hi - lo < 1e-9) {
    lo -= 1
    hi += 1
  }
  const pad = (hi - lo) * 0.12
  lo -= pad
  hi += pad
  const pts = v.map((y, i) => {
    const x = (i / (v.length - 1)) * W
    const yy = props.height - ((y - lo) / (hi - lo)) * props.height
    return [x, yy] as const
  })
  const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(2)},${y.toFixed(2)}`).join(' ')
  const area = `${line} L${W},${props.height} L0,${props.height} Z`
  const last = pts[pts.length - 1]
  return { line, area, last }
})

const gid = `spk-${Math.random().toString(36).slice(2, 8)}`
</script>

<template>
  <svg class="spark" :viewBox="`0 0 ${W} ${height}`" preserveAspectRatio="none" :style="{ height: `${height}px` }">
    <defs>
      <linearGradient :id="gid" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity="0.35" />
        <stop offset="100%" :stop-color="color" stop-opacity="0" />
      </linearGradient>
    </defs>
    <template v-if="geometry">
      <path :d="geometry.area" :fill="`url(#${gid})`" />
      <path :d="geometry.line" fill="none" :stroke="color" stroke-width="1.6" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
    </template>
    <line v-else x1="0" :y1="height / 2" :x2="W" :y2="height / 2" :stroke="color" stroke-opacity="0.4" stroke-width="1" stroke-dasharray="3 4" vector-effect="non-scaling-stroke" />
  </svg>
</template>

<style scoped>
.spark {
  display: block;
  width: 100%;
  overflow: visible;
}
</style>

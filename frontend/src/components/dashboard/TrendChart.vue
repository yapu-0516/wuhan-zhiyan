<script setup lang="ts">
// 近 24 小时事件总量趋势：单序列折线，类型构成由上方分布区承担。
import { computed } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import type { TrendPoint } from '@/types/api'

const props = defineProps<{ trend: TrendPoint[] }>()

const option = computed(() => {
  const list = Array.isArray(props.trend) ? props.trend : []
  return {
    grid: { left: 30, right: 8, top: 14, bottom: 22 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: '#56616a' } }
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: list.map((p) => p.time),
      axisLine: { lineStyle: { color: '#353c42' } },
      axisTick: { show: false },
      axisLabel: { color: '#858e95', fontSize: 11, interval: 3 }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitNumber: 3,
      axisLabel: { color: '#858e95', fontSize: 11 },
      splitLine: { lineStyle: { color: '#252a2f' } }
    },
    series: [
      {
        name: '事件总量',
        type: 'line',
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 2, color: '#6dc7e7' },
        itemStyle: { color: '#6dc7e7' },
        data: list.map((p) => (Number(p.fire) || 0) + (Number(p.traffic) || 0) + (Number(p.building) || 0) + (Number(p.flood) || 0))
      }
    ]
  }
})
</script>

<template>
  <div class="trend">
    <EChart v-if="trend?.length" :option="option" />
    <div v-else class="trend__empty">暂无趋势数据</div>
  </div>
</template>

<style scoped>
.trend {
  flex: 1;
  min-height: 130px;
  display: flex;
}
.trend > * {
  flex: 1;
}
.trend__empty {
  display: grid;
  place-items: center;
  font-size: 12px;
  color: var(--ce-text-faint);
}
</style>

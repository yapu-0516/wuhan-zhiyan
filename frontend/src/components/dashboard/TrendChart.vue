<script setup lang="ts">
// 近 24 小时事件趋势：按类型堆叠面积图
import { computed } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import type { TrendPoint } from '@/types/api'
import { EVENT_TYPES, EVENT_TYPE_META } from '@/types/event'
import { rgba } from '@/utils/color'

const props = defineProps<{ trend: TrendPoint[] }>()

const option = computed(() => {
  const list = Array.isArray(props.trend) ? props.trend : []
  return {
    grid: { left: 28, right: 8, top: 30, bottom: 20 },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 10,
      itemHeight: 6,
      itemGap: 12,
      icon: 'roundRect',
      textStyle: { color: '#8aa3c4', fontSize: 11 },
      // 窄面板内保持单行：图例只显示类型前两字（火灾 / 交通 / 建筑 / 内涝）
      formatter: (name: string) => name.slice(0, 2),
      data: EVENT_TYPES.map((t) => EVENT_TYPE_META[t].label)
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: 'rgba(79,195,247,0.5)' } }
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: list.map((p) => p.time),
      axisLine: { lineStyle: { color: 'rgba(79,195,247,0.25)' } },
      axisTick: { show: false },
      axisLabel: { color: '#6f87a8', fontSize: 10, interval: 3 }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitNumber: 3,
      axisLabel: { color: '#6f87a8', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(79,195,247,0.07)' } }
    },
    series: EVENT_TYPES.map((t) => {
      const c = EVENT_TYPE_META[t].color
      return {
        name: EVENT_TYPE_META[t].label,
        type: 'line',
        stack: 'total',
        smooth: 0.35,
        symbol: 'none',
        lineStyle: { width: 1.6, color: c },
        itemStyle: { color: c },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: rgba(c, 0.42) },
              { offset: 1, color: rgba(c, 0.03) }
            ]
          }
        },
        emphasis: { focus: 'series' },
        data: list.map((p) => Number(p[t]) || 0)
      }
    })
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

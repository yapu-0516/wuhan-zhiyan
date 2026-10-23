<script setup lang="ts">
// 数据入库状态分布：横向条形图
import { computed } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import { DATA_STATUSES, dataStatusMeta } from '@/composables/pages/dataMeta'

const props = defineProps<{ counts: Record<string, number> }>()

const statuses = computed(() => {
  const known = [...DATA_STATUSES] as string[]
  const extra = Object.keys(props.counts).filter((k) => !known.includes(k))
  return [...known, ...extra]
})

const option = computed(() => ({
  grid: { left: 8, right: 44, top: 6, bottom: 6, containLabel: true },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  xAxis: { type: 'value', show: false, minInterval: 1 },
  yAxis: {
    type: 'category',
    inverse: true,
    data: statuses.value,
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#b9cdec', fontSize: 13 }
  },
  series: [
    {
      type: 'bar',
      barWidth: 14,
      showBackground: true,
      backgroundStyle: { color: 'rgba(120, 160, 210, 0.1)', borderRadius: 7 },
      label: { show: true, position: 'right', color: '#d6e4ff', fontSize: 13, fontWeight: 600 },
      data: statuses.value.map((s) => ({
        value: props.counts[s] ?? 0,
        itemStyle: {
          borderRadius: 7,
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: `${dataStatusMeta(s).color}55` },
              { offset: 1, color: dataStatusMeta(s).color }
            ]
          }
        }
      }))
    }
  ]
}))
</script>

<template>
  <EChart :option="option" style="height: 210px" />
</template>

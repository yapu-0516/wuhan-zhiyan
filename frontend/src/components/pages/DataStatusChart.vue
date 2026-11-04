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
    axisLabel: { color: '#b1b4b7', fontSize: 13 }
  },
  series: [
    {
      type: 'bar',
      barWidth: 14,
      showBackground: true,
      backgroundStyle: { color: '#2a2c2f', borderRadius: 4 },
      label: { show: true, position: 'right', color: '#dddfe1', fontSize: 13, fontWeight: 600 },
      data: statuses.value.map((s) => ({
        value: props.counts[s] ?? 0,
        itemStyle: {
          borderRadius: 4,
          color: dataStatusMeta(s).color
        }
      }))
    }
  ]
}))
</script>

<template>
  <EChart :option="option" style="height: 100%; min-height: 300px" />
</template>

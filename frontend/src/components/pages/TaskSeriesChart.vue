<script setup lang="ts">
// 时序类分析结果图：result.series 中 v 为主曲线，其余数值列作为副轴曲线；指标中的阈值绘制为 markLine
import { computed } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import { describeMetric, isThresholdKey, seriesLabel } from '@/composables/pages/metrics'
import { typeMeta } from '@/composables/pages/aiMeta'
import type { TaskResult } from '@/types/api'

type Series = NonNullable<TaskResult['series']>

const props = defineProps<{
  series: Series
  type: string
  metrics: Record<string, number | string>
  height?: number
}>()

const MAIN_NAME: Record<string, string> = {
  traffic: '车速 (km/h)',
  flood: '水位 (cm)',
  building: '位移 (mm)',
  fire: '监测值'
}
const EXTRA_COLORS = ['#ffb86b', '#9b8fff', '#5eead4', '#ff7eb6']

const extraKeys = computed(() => {
  const keys = new Set<string>()
  for (const row of props.series) {
    for (const [k, v] of Object.entries(row)) {
      if (k !== 't' && k !== 'v' && typeof v === 'number') keys.add(k)
    }
  }
  return [...keys]
})

const thresholds = computed(() =>
  Object.entries(props.metrics)
    .filter(([k, v]) => isThresholdKey(k) && typeof v === 'number')
    .map(([k, v]) => ({ label: describeMetric(k, v).label, value: v as number }))
)

const option = computed(() => {
  const main = typeMeta(props.type)?.color ?? '#4fc3f7'
  const dense = props.series.length > 60
  const hasExtra = extraKeys.value.length > 0
  const axisText = { color: '#8aa3c4', fontSize: 11 }
  const mainName = MAIN_NAME[props.type] ?? '监测值'
  return {
    color: [main, ...EXTRA_COLORS],
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        lineStyle: { color: 'rgba(79,195,247,0.4)' },
        crossStyle: { color: 'rgba(79,195,247,0.4)' }
      }
    },
    legend: hasExtra
      ? { top: 0, right: 8, textStyle: { color: '#b9cdec' }, itemWidth: 14, itemHeight: 3 }
      : { show: false },
    grid: { left: 8, right: hasExtra ? 8 : 20, top: hasExtra ? 34 : 26, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.series.map((p) => p.t),
      axisLine: { lineStyle: { color: 'rgba(120,160,210,0.35)' } },
      axisTick: { show: false },
      axisLabel: { ...axisText, hideOverlap: true }
    },
    yAxis: [
      {
        type: 'value',
        name: mainName,
        nameTextStyle: { color: '#8aa3c4', align: 'left' },
        scale: true,
        axisLabel: axisText,
        splitLine: { lineStyle: { color: 'rgba(120,160,210,0.12)', type: 'dashed' } }
      },
      ...(hasExtra
        ? [{ type: 'value', scale: true, axisLabel: axisText, splitLine: { show: false }, axisLine: { show: false } }]
        : [])
    ],
    series: [
      {
        name: mainName,
        type: 'line',
        smooth: 0.2,
        showSymbol: !dense,
        symbolSize: 6,
        lineStyle: { width: 2.4, color: main, shadowBlur: 10, shadowColor: main },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: `${main}55` },
              { offset: 1, color: `${main}00` }
            ]
          }
        },
        data: props.series.map((p) => p.v),
        markLine: thresholds.value.length
          ? {
              symbol: 'none',
              silent: true,
              lineStyle: { color: '#ff6b6b', type: 'dashed', width: 1.4 },
              label: { color: '#ffb0b0', position: 'insideEndTop', fontSize: 11 },
              data: thresholds.value.map((t) => ({
                yAxis: t.value,
                name: t.label,
                label: { formatter: `${t.label} ${t.value}` }
              }))
            }
          : undefined
      },
      ...extraKeys.value.map((k, i) => ({
        name: seriesLabel(k),
        type: 'line',
        yAxisIndex: 1,
        smooth: 0.2,
        showSymbol: false,
        lineStyle: { width: 1.8, color: EXTRA_COLORS[i % EXTRA_COLORS.length], type: 'solid' },
        data: props.series.map((p) => (typeof p[k] === 'number' ? (p[k] as number) : null))
      }))
    ]
  }
})
</script>

<template>
  <EChart :option="option" :style="{ height: `${height ?? 260}px` }" />
</template>

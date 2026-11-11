<script setup lang="ts">
// 通用 ECharts 容器：按需引入 + 自适应尺寸 + 深色主题
// 用法：<EChart :option="option" style="height: 200px" />
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, GaugeChart, RadarChart, GraphChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DatasetComponent,
  MarkLineComponent,
  MarkAreaComponent,
  VisualMapComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsCoreOption } from 'echarts/core'

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  GaugeChart,
  RadarChart,
  GraphChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DatasetComponent,
  MarkLineComponent,
  MarkAreaComponent,
  VisualMapComponent,
  CanvasRenderer
])

const props = defineProps<{ option: EChartsCoreOption }>()
const el = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)
let ro: ResizeObserver | null = null

/** 深色大屏默认样式，页面 option 可覆盖 */
const BASE: EChartsCoreOption = {
  backgroundColor: 'transparent',
  textStyle: { color: '#8aa3c4', fontFamily: 'inherit' },
  tooltip: {
    backgroundColor: 'rgba(10, 18, 38, 0.92)',
    borderColor: 'rgba(79, 195, 247, 0.35)',
    textStyle: { color: '#d6e4ff', fontSize: 12 }
  }
}

onMounted(() => {
  chart.value = echarts.init(el.value as HTMLDivElement, undefined, { renderer: 'canvas' })
  chart.value.setOption({ ...BASE, ...props.option })
  ro = new ResizeObserver(() => chart.value?.resize())
  ro.observe(el.value as HTMLDivElement)
})

watch(
  () => props.option,
  (opt) => chart.value?.setOption({ ...BASE, ...opt }, { notMerge: false, lazyUpdate: true }),
  { deep: true }
)

onBeforeUnmount(() => {
  ro?.disconnect()
  chart.value?.dispose()
})

defineExpose({ getChart: () => chart.value })
</script>

<template>
  <div ref="el" class="echart"></div>
</template>

<style scoped>
.echart {
  width: 100%;
  height: 100%;
  min-height: 60px;
}
</style>

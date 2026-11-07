<script setup lang="ts">
// 城市安全指数仪表 + 实时路网 TPI
import { computed } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import AnimatedNumber from '../common/AnimatedNumber.vue'
import type { TrafficLevel } from '@/types/building'
import { TRAFFIC_LEVEL_META } from '@/types/building'

const props = defineProps<{ score: number; tpi: number; level: TrafficLevel; monitored?: number }>()

const LEVELS: TrafficLevel[] = ['smooth', 'basic', 'light', 'moderate', 'heavy']

const grade = computed(() => {
  const s = props.score
  if (s >= 90) return { label: '优', color: '#2ed47a' }
  if (s >= 80) return { label: '良', color: '#4fc3f7' }
  if (s >= 70) return { label: '中', color: '#f0c050' }
  return { label: '差', color: '#ff6b6b' }
})

const levelMeta = computed(() => TRAFFIC_LEVEL_META[props.level] ?? TRAFFIC_LEVEL_META.smooth)
const marker = computed(() => `${Math.max(0, Math.min(10, props.tpi || 0)) * 10}%`)

const option = computed(() => {
  const c = grade.value.color
  const score = Math.round(Math.max(0, Math.min(100, props.score || 0)))
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 225,
        endAngle: -45,
        radius: '98%',
        center: ['50%', '54%'],
        min: 0,
        max: 100,
        splitNumber: 10,
        silent: true,
        axisLine: { lineStyle: { width: 1, color: [[1, '#343a3f']] } },
        axisTick: { distance: -7, length: 3, splitNumber: 4, lineStyle: { color: '#4b535a', width: 1 } },
        splitLine: { distance: -9, length: 7, lineStyle: { color: '#626b73', width: 1 } },
        axisLabel: { show: false },
        pointer: { show: false },
        detail: { show: false },
        title: { show: false },
        data: [{ value: 0 }]
      },
      {
        type: 'gauge',
        startAngle: 225,
        endAngle: -45,
        radius: '80%',
        center: ['50%', '54%'],
        min: 0,
        max: 100,
        progress: {
          show: true,
          width: 9,
          roundCap: true,
          itemStyle: { color: c }
        },
        axisLine: { roundCap: true, lineStyle: { width: 7, color: [[1, '#2a3035']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        title: { show: true, offsetCenter: [0, '46%'], color: '#a2a9af', fontSize: 12 },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '2%'],
          fontSize: 30,
          fontWeight: 600,
          fontFamily: 'DIN Alternate, Bahnschrift, Roboto Condensed, Arial',
          color: '#f5f7f8',
          formatter: '{value}'
        },
        data: [{ value: score, name: `安全等级 · ${grade.value.label}` }]
      }
    ]
  }
})
</script>

<template>
  <div class="safety">
    <div class="safety__gauge">
      <EChart :option="option" />
    </div>
    <div class="safety__tpi">
      <div class="tpi-label">实时路网 TPI</div>
      <div class="tpi-value" :style="{ color: levelMeta.color }">
        <AnimatedNumber :value="tpi || 0" :digits="1" />
        <span class="ce-tag" :style="{ color: levelMeta.color }">{{ levelMeta.label }}</span>
      </div>
      <div class="tpi-scale">
        <i
          v-for="l in LEVELS"
          :key="l"
          :style="{ background: TRAFFIC_LEVEL_META[l].color, color: TRAFFIC_LEVEL_META[l].color }"
          :class="{ on: l === level }"
        />
        <b class="tpi-marker" :style="{ left: marker }" />
      </div>
      <div class="tpi-ticks ce-num">
        <span>0</span><span>2</span><span>4</span><span>6</span><span>8</span><span>10</span>
      </div>
      <div v-if="monitored !== undefined" class="tpi-foot">
        沉降监测建筑 <b class="ce-num">{{ monitored }}</b> 栋
      </div>
    </div>
  </div>
</template>

<style scoped>
.safety {
  flex: 1;
  min-height: 150px;
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: 8px;
  align-items: center;
}
.safety__gauge {
  height: 100%;
  min-height: 150px;
}
.safety__tpi {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: 10px;
  border-left: 1px solid var(--ce-divider);
}
.tpi-label {
  font-size: 13px;
  color: var(--ce-text-dim);
  letter-spacing: 0;
}
.tpi-value {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 28px;
  font-weight: 600;
  line-height: 1.1;
}
.tpi-value .ce-tag {
  font-weight: 400;
}
.tpi-scale {
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 2px;
  margin-top: 4px;
}
.tpi-scale i {
  height: 6px;
  border-radius: 1px;
  opacity: 0.35;
}
.tpi-scale i.on {
  opacity: 1;
}
.tpi-marker {
  position: absolute;
  top: -5px;
  width: 0;
  height: 0;
  margin-left: -5px;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid #fff;
  transition: left 0.8s var(--ce-ease);
}
.tpi-ticks {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ce-text-faint);
}
.tpi-foot {
  margin-top: 4px;
  font-size: 13px;
  color: var(--ce-text-dim);
}
.tpi-foot b {
  font-size: 15px;
  color: var(--ce-text-strong);
}
</style>

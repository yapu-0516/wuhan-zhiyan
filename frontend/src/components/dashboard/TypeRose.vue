<script setup lang="ts">
// 事件类型分布：南丁格尔玫瑰图 + 直接标注的图例（图标 + 名称 + 数量 + 占比）
import { computed } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import type { EventType } from '@/types/event'
import { EVENT_TYPES, EVENT_TYPE_META } from '@/types/event'

const props = defineProps<{ byType: Record<EventType, number> }>()

const total = computed(() => EVENT_TYPES.reduce((s, t) => s + (props.byType?.[t] ?? 0), 0))
const rows = computed(() =>
  EVENT_TYPES.map((t) => {
    const n = props.byType?.[t] ?? 0
    return { t, n, pct: total.value ? Math.round((n / total.value) * 100) : 0, ...EVENT_TYPE_META[t] }
  })
)

const option = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}：{c} 件（{d}%）' },
  series: [
    {
      type: 'pie',
      roseType: 'radius',
      radius: ['26%', '88%'],
      center: ['50%', '50%'],
      itemStyle: { borderRadius: 3, borderColor: 'rgba(7,17,36,0.9)', borderWidth: 2 },
      label: { show: false },
      labelLine: { show: false },
      emphasis: { scale: true, scaleSize: 4 },
      data: rows.value.map((r) => ({
        name: r.label,
        value: r.n,
        itemStyle: { color: r.color, shadowColor: r.color, shadowBlur: 8 }
      }))
    },
    {
      type: 'pie',
      radius: ['18%', '20%'],
      center: ['50%', '50%'],
      silent: true,
      label: { show: false },
      data: [{ value: 1, itemStyle: { color: 'rgba(79,195,247,0.35)' } }]
    }
  ]
}))
</script>

<template>
  <div class="rose">
    <div class="rose__chart">
      <EChart :option="option" />
      <div class="rose__center">
        <b class="ce-num">{{ total }}</b>
        <span>事件总数</span>
      </div>
    </div>
    <ul class="rose__legend">
      <li v-for="r in rows" :key="r.t">
        <i class="dot" :style="{ background: r.color, boxShadow: `0 0 6px ${r.color}` }" />
        <span class="icon">{{ r.icon }}</span>
        <span class="name">{{ r.label }}</span>
        <b class="ce-num">{{ r.n }}</b>
        <em class="ce-num">{{ r.pct }}%</em>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.rose {
  flex: 1;
  min-height: 140px;
  display: grid;
  grid-template-columns: 1fr 1.05fr;
  align-items: center;
  gap: 6px;
}
.rose__chart {
  position: relative;
  height: 100%;
  min-height: 140px;
}
.rose__center {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
}
.rose__center b {
  font-size: 18px;
  line-height: 1;
  color: var(--ce-text-strong);
}
.rose__center span {
  font-size: 9px;
  color: var(--ce-text-faint);
  transform: scale(0.9);
}
.rose__legend {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.rose__legend li {
  display: grid;
  grid-template-columns: 8px 18px 1fr auto 38px;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 2px;
  font-size: 12.5px;
  background: rgba(79, 195, 247, 0.04);
  cursor: default;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}
.icon {
  font-size: 13px;
}
.name {
  color: var(--ce-text);
  white-space: nowrap;
}
.rose__legend b {
  font-size: 15px;
  color: var(--ce-text-strong);
}
.rose__legend em {
  font-style: normal;
  font-size: 12px;
  text-align: right;
  color: var(--ce-text-dim);
}
</style>

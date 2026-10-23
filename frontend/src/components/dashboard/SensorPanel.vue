<script setup lang="ts">
// 感知设备在线率：总在线率环 + 各类数据源在线情况（GET /api/sources，WS sensor.tick 实时刷新）
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getSources } from '@/api/system'
import { useRealtime } from '@/composables/useRealtime'
import type { DataSource } from '@/types/api'
import AnimatedNumber from './AnimatedNumber.vue'

const props = defineProps<{ online: number; total: number }>()

const sources = ref<DataSource[]>([])
let off: (() => void) | null = null

onMounted(async () => {
  off = useRealtime().on('sensor.tick', (d) => {
    const list = Array.isArray(d?.sources) ? d.sources : []
    if (!list.length || !sources.value.length) return
    sources.value = sources.value.map((s) => {
      const u = list.find((x) => x.id === s.id)
      return u ? { ...s, throughput: u.throughput, devices_online: u.devices_online } : s
    })
  })
  try {
    const list = await getSources()
    sources.value = Array.isArray(list) ? list : []
  } catch {
    sources.value = []
  }
})
onBeforeUnmount(() => off?.())

// 总数：优先总览 city_index，缺失时用数据源汇总
const totals = computed(() => {
  if (props.total > 0) return { online: props.online, total: props.total }
  const online = sources.value.reduce((s, x) => s + (x.devices_online || 0), 0)
  const total = sources.value.reduce((s, x) => s + (x.devices_total || 0), 0)
  return { online, total }
})
const rate = computed(() => (totals.value.total ? (totals.value.online / totals.value.total) * 100 : 0))
const rows = computed(() =>
  sources.value
    .filter((s) => s.devices_total > 0)
    .slice(0, 4)
    .map((s) => ({ ...s, pct: Math.round((s.devices_online / s.devices_total) * 100) }))
)
</script>

<template>
  <div class="sensor">
    <div class="sensor__ring" :style="{ '--p': rate.toFixed(1) }">
      <div class="sensor__ring-inner">
        <b><AnimatedNumber :value="rate" :decimals="1" /><small>%</small></b>
        <span class="ce-num">{{ totals.online }}/{{ totals.total }}</span>
      </div>
    </div>
    <ul v-if="rows.length" class="sensor__list">
      <li v-for="s in rows" :key="s.id">
        <span class="sensor__icon">{{ s.icon }}</span>
        <span class="sensor__name" :title="s.name">{{ s.name }}</span>
        <span class="sensor__bar"><i :style="{ width: s.pct + '%' }" /></span>
        <span class="sensor__v ce-num">{{ s.devices_online }}<em>/{{ s.devices_total }}</em></span>
      </li>
    </ul>
    <div v-else class="sensor__hint">
      <p>覆盖无人机、卫星遥感、视频监控与物联感知四类数据源。</p>
    </div>
  </div>
</template>

<style scoped>
.sensor {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 104px 1fr;
  align-items: center;
  gap: 12px;
}
.sensor__ring {
  --p: 0;
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background:
    conic-gradient(from 210deg, #1f78d1 0%, #36e4ff calc(var(--p) * 1%), rgba(79, 195, 247, 0.1) calc(var(--p) * 1%) 100%);
  box-shadow: 0 0 18px rgba(54, 228, 255, 0.25);
  display: grid;
  place-items: center;
}
.sensor__ring::after {
  content: '';
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  border: 1px dashed rgba(79, 195, 247, 0.3);
  animation: sensor-rot 24s linear infinite;
}
@keyframes sensor-rot {
  to {
    transform: rotate(360deg);
  }
}
.sensor__ring-inner {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: radial-gradient(circle, #0b1a36 0%, #071124 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.sensor__ring-inner b {
  font-size: 20px;
  line-height: 1.1;
  color: var(--ce-text-strong);
}
.sensor__ring-inner small {
  font-size: 11px;
  color: var(--ce-text-dim);
}
.sensor__ring-inner span {
  font-size: 10px;
  color: var(--ce-text-faint);
}
.sensor__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}
.sensor__list li {
  display: grid;
  grid-template-columns: 18px 64px 1fr 54px;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.sensor__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ce-text);
}
.sensor__bar {
  height: 5px;
  border-radius: 3px;
  background: rgba(79, 195, 247, 0.08);
  overflow: hidden;
}
.sensor__bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #1f78d1, #4dd984);
  transition: width 0.8s var(--ce-ease);
}
.sensor__v {
  text-align: right;
  color: var(--ce-text-strong);
}
.sensor__v em {
  font-style: normal;
  color: var(--ce-text-faint);
}
.sensor__hint p {
  margin: 0;
  font-size: 12px;
  color: var(--ce-text-dim);
  line-height: 1.6;
}
</style>

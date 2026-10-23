<script setup lang="ts">
// 监测数据源卡片：状态 / 设备在线率 / 实时吞吐 + 迷你折线 / 覆盖范围 / 最近活跃
import { computed } from 'vue'
import AnimatedNumber from './AnimatedNumber.vue'
import Sparkline from './Sparkline.vue'
import { relativeTime } from '@/composables/pages/format'
import type { DataSource } from '@/types/api'

const props = defineProps<{
  source: DataSource
  /** 最近若干次吞吐（真实推送累积，不足时不画曲线） */
  history: number[]
  now: number
}>()

const STATUS: Record<DataSource['status'], { color: string; pulse?: boolean }> = {
  在线: { color: '#4dd984' },
  采集中: { color: '#4fc3f7', pulse: true },
  离线: { color: '#ff6b6b' },
  待接入: { color: '#7f8ea6' }
}
const st = computed(() => STATUS[props.source.status] ?? { color: '#8aa3c4' })
const ratio = computed(() => (props.source.devices_total ? props.source.devices_online / props.source.devices_total : 0))
const ratioColor = computed(() => (props.source.devices_total === 0 ? '#7f8ea6' : ratio.value >= 0.9 ? '#4dd984' : ratio.value >= 0.6 ? '#f0c050' : '#ff6b6b'))
const idle = computed(() => props.source.status === '待接入' || props.source.status === '离线')
</script>

<template>
  <article class="sc cp-panel cp-panel--glow" :class="{ 'is-idle': idle }" :style="{ '--c': st.color }">
    <header class="sc__head">
      <span class="sc__icon">{{ source.icon }}</span>
      <div class="sc__title">
        <b>{{ source.name }}</b>
        <span class="cp-ellipsis" :title="source.desc">{{ source.desc }}</span>
      </div>
      <span class="cp-pill cp-pill--sm" :style="{ '--c': st.color }">
        <i class="cp-dot" :class="{ 'cp-dot--pulse': st.pulse }"></i>{{ source.status }}
      </span>
    </header>

    <div class="sc__dev">
      <div class="sc__devtxt">
        <span class="cp-label">设备在线</span>
        <b>{{ source.devices_online }}<small> / {{ source.devices_total }}</small></b>
      </div>
      <span class="cp-bar" :style="{ '--c': ratioColor }"><i :style="{ width: `${ratio * 100}%` }"></i></span>
    </div>

    <div class="sc__tp">
      <div class="sc__tpnum">
        <span class="cp-label">实时吞吐</span>
        <b><AnimatedNumber :value="source.throughput" :duration="500" /><small>{{ source.unit }}</small></b>
      </div>
      <div class="sc__spark">
        <Sparkline :values="history" :color="st.color" :height="38" />
        <span v-if="history.length < 2" class="sc__hint">等待实时数据…</span>
      </div>
    </div>

    <footer class="sc__foot">
      <span class="cp-ellipsis" :title="source.coverage">📍 {{ source.coverage || '—' }}</span>
      <span>{{ relativeTime(source.last_active, now) }}</span>
    </footer>
  </article>
</template>

<style scoped>
.sc {
  --c: #4fc3f7;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 18px 12px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.sc.is-idle {
  opacity: 0.82;
}
.sc__head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.sc__icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  font-size: 22px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--c) 14%, rgba(9, 16, 34, 0.8));
  border: 1px solid color-mix(in srgb, var(--c) 42%, transparent);
  box-shadow: 0 0 16px color-mix(in srgb, var(--c) 22%, transparent);
}
.sc__title {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.sc__title b {
  font-size: 15px;
  color: #f0f6ff;
}
.sc__title span {
  font-size: 12px;
  color: #7f98b8;
}
.sc__dev {
  display: flex;
  align-items: center;
  gap: 14px;
}
.sc__devtxt {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 78px;
}
.sc__devtxt b {
  font-size: 18px;
  color: #e6f2ff;
  font-variant-numeric: tabular-nums;
}
.sc__devtxt small {
  font-size: 12px;
  font-weight: 400;
  color: #6f89aa;
}
.sc__dev .cp-bar {
  flex: 1;
  height: 6px;
}
.sc__tp {
  display: grid;
  grid-template-columns: minmax(100px, auto) 1fr;
  align-items: end;
  gap: 14px;
}
.sc__tpnum {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sc__tpnum b {
  display: flex;
  align-items: baseline;
  gap: 5px;
  font-size: 26px;
  line-height: 1.15;
  font-weight: 600;
  color: color-mix(in srgb, var(--c) 40%, #fff);
  font-variant-numeric: tabular-nums;
  text-shadow: 0 0 16px color-mix(in srgb, var(--c) 35%, transparent);
}
.sc__tpnum small {
  font-size: 11.5px;
  font-weight: 400;
  color: #7f98b8;
  text-shadow: none;
}
.sc__spark {
  position: relative;
  min-width: 0;
}
.sc__hint {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 11px;
  color: #5d748f;
}
.sc__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 10px;
  font-size: 12px;
  color: #6f89aa;
  border-top: 1px dashed rgba(64, 120, 180, 0.2);
}
.sc__foot span:last-child {
  flex: none;
}
</style>

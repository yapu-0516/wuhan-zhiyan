<script setup lang="ts">
// 底部城市状态栏：事件统计（含内涝）、待处置数、实时通道状态、数据模式、最近更新时间
import { computed } from 'vue'
import { useCityEvents } from '@/composables/useCityEvents'
import { useRealtime } from '@/composables/useRealtime'
import { apiState } from '@/api/http'
import { EVENT_TYPES, EVENT_TYPE_META } from '@/types/event'
import { isToday, shortTime } from '@/utils/format'

const { stats, events, revision } = useCityEvents()
const { connected, lastMessageAt } = useRealtime()

const MODE_LABEL = { live: '实时数据', offline: '离线快照', mock: '演示数据' } as const

const pad = (n: number) => String(n).padStart(2, '0') // taste-skill-ignore numbering: clock/date formatting

// 最近更新：WS 最近一条消息时间；离线时取最新事件时间
const lastUpdate = computed(() => {
  void revision.value
  if (lastMessageAt.value) {
    const d = new Date(lastMessageAt.value)
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  }
  const latest = events.value.reduce((m, e) => (e.updated_at > m ? e.updated_at : m), '')
  if (!latest) return '--:--:--'
  // 快照可能来自历史日期，非当天时补上 MM-dd，避免误读为今天
  return isToday(latest) ? latest.slice(11, 19) : shortTime(latest)
})
</script>

<template>
  <footer class="status-panel">
    <div class="sp-total">
      <span class="sp-label">监测事件</span>
      <span class="sp-value ce-num">{{ stats.total }}</span>
    </div>
    <div class="sp-active">
      <span class="sp-label">待处置</span>
      <span class="sp-value sp-value--warn ce-num">{{ stats.active }}</span>
    </div>
    <span class="sp-divider" />
    <div class="sp-types">
      <span v-for="t in EVENT_TYPES" :key="t" class="sp-type">
        <i class="sp-type-dot" :style="{ background: EVENT_TYPE_META[t].color }" />
        <span class="sp-name">{{ EVENT_TYPE_META[t].label }}</span>
        <span class="sp-count ce-num" :style="{ color: EVENT_TYPE_META[t].color }">{{ stats.byType[t] ?? 0 }}</span>
      </span>
    </div>
    <span class="sp-spacer" />
    <div class="sp-sys">
      <span class="sp-chip" :class="connected ? 'ok' : 'off'">
        <i class="ce-dot" :class="{ 'ce-dot--pulse': connected }" />WS {{ connected ? '已连接' : '未连接' }}
      </span>
      <span class="sp-chip" :class="apiState.mode === 'live' ? 'ok' : 'warn'">数据：{{ MODE_LABEL[apiState.mode] }}</span>
      <span class="sp-chip">最近更新 <b class="ce-num">{{ lastUpdate }}</b></span>
    </div>
  </footer>
</template>

<style scoped>
.status-panel {
  position: relative;
  z-index: 10;
  height: var(--status-h);
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 18px;
  background: var(--ce-bg);
  border-top: 1px solid var(--ce-divider);
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
}
.sp-total,
.sp-active {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.sp-label {
  color: var(--ce-text-dim);
}
.sp-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--ce-text-strong);
}
.sp-value--warn {
  color: var(--ce-warning);
}
.sp-divider {
  width: 1px;
  height: 18px;
  background: var(--ce-divider);
}
.sp-types {
  display: flex;
  align-items: center;
  gap: 18px;
}
.sp-type {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--ce-text-dim);
}
.sp-type-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.sp-count {
  font-size: 13px;
  font-weight: 600;
}
.sp-spacer {
  flex: 1;
}
.sp-sys {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sp-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 22px;
  padding: 0 7px;
  border: 1px solid var(--ce-divider);
  border-radius: 4px;
  font-size: 12px;
  color: var(--ce-text-dim);
}
.sp-chip b {
  color: var(--ce-text);
  font-weight: 400;
}
.sp-chip.ok {
  color: #2ed47a;
  color: var(--ce-success);
}
.sp-chip.off {
  color: var(--ce-text-faint);
}
.sp-chip.warn {
  color: var(--ce-warning);
  color: var(--ce-warning);
}
@media (max-width: 1200px) {
  .sp-name {
    display: none;
  }
}
</style>

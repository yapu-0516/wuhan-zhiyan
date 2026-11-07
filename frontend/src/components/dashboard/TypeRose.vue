<script setup lang="ts">
// 事件类型分布：横向条形列表，便于在大屏内快速比较数量。
import { computed } from 'vue'
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
</script>

<template>
  <div class="types">
    <div class="types__total">
      <span>事件总数</span>
      <b class="ce-num">{{ total }}</b>
      <span>件</span>
    </div>
    <ul class="types__list">
      <li v-for="r in rows" :key="r.t">
        <i class="dot" :style="{ background: r.color }" />
        <span class="name">{{ r.label }}</span>
        <span class="bar"><i :style="{ width: `${r.pct}%`, background: r.color }" /></span>
        <b class="ce-num">{{ r.n }}</b>
        <em class="ce-num">{{ r.pct }}%</em>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.types {
  flex: 1;
  min-height: 140px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.types__total {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 13px;
  color: var(--ce-text-dim);
}
.types__total b {
  margin-left: auto;
  font-size: 24px;
  color: var(--ce-text-strong);
}
.types__list {
  flex: 1;
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 4px;
}
.types__list li {
  display: grid;
  grid-template-columns: 7px 52px 1fr 26px 32px;
  align-items: center;
  gap: 8px;
  min-height: 22px;
  font-size: 13px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.name {
  color: var(--ce-text-dim);
  white-space: nowrap;
}
.bar {
  height: 3px;
  overflow: hidden;
  background: #2a3035;
}
.bar i {
  display: block;
  height: 100%;
  transition: width 0.5s var(--ce-ease);
}
.types__list b {
  font-size: 13px;
  text-align: right;
  color: var(--ce-text-strong);
}
.types__list em {
  font-style: normal;
  font-size: 12px;
  text-align: right;
  color: var(--ce-text-faint);
}
</style>

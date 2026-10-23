<script setup lang="ts">
// 场景图例：路况等级 / 事件类型（可点击筛选）/ 事件等级 / 建筑高度与沉降风险
import { ref } from 'vue'
import type { EventType } from '@/types/event'
import { EVENT_TYPES, EVENT_TYPE_META, SEVERITY_META } from '@/types/event'
import type { Severity } from '@/types/event'
import type { TrafficLevel } from '@/types/building'
import { RISK_LEVEL_META, TRAFFIC_LEVEL_META } from '@/types/building'
import { BUILDING_LEGEND_GRADIENT } from '@/components/scene/buildingLayer'
import type { EventTypeFilter } from '@/components/scene/types'

defineProps<{ eventTypes: EventTypeFilter; showResolved: boolean }>()
const emit = defineEmits<{ (e: 'toggle-type', t: EventType): void; (e: 'toggle-resolved'): void }>()

const open = ref(true)
const LEVELS: TrafficLevel[] = ['smooth', 'basic', 'light', 'moderate', 'heavy']
const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low']
</script>

<template>
  <div class="legend" :class="{ collapsed: !open }">
    <button class="legend__head" @click="open = !open">
      <span>图例</span>
      <i class="legend__caret" />
    </button>
    <div v-show="open" class="legend__body">
      <div class="lg-sec">
        <div class="lg-title">实时路况</div>
        <div class="lg-row">
          <span v-for="l in LEVELS" :key="l" class="lg-traffic">
            <i :style="{ background: TRAFFIC_LEVEL_META[l].color, boxShadow: `0 0 6px ${TRAFFIC_LEVEL_META[l].color}` }" />{{ TRAFFIC_LEVEL_META[l].label }}
          </span>
        </div>
      </div>
      <div class="lg-sec">
        <div class="lg-title">事件类型 <small>点击筛选</small></div>
        <div class="lg-row">
          <button
            v-for="t in EVENT_TYPES"
            :key="t"
            class="lg-type"
            :class="{ off: eventTypes[t] === false }"
            :style="{ '--c': EVENT_TYPE_META[t].color }"
            @click="emit('toggle-type', t)"
          >
            <span>{{ EVENT_TYPE_META[t].icon }}</span>{{ EVENT_TYPE_META[t].label }}
          </button>
        </div>
        <label class="lg-check">
          <input type="checkbox" :checked="showResolved" @change="emit('toggle-resolved')" />
          显示已办结事件
        </label>
      </div>
      <div class="lg-sec">
        <div class="lg-title">事件等级（定位针外环）</div>
        <div class="lg-row">
          <span v-for="s in SEVERITIES" :key="s" class="lg-sev">
            <i :style="{ borderColor: SEVERITY_META[s].color }" />{{ SEVERITY_META[s].label }}
          </span>
        </div>
      </div>
      <div class="lg-sec">
        <div class="lg-title">建筑高度 / 沉降风险</div>
        <div class="lg-height">
          <span class="ce-num">0m</span>
          <i :style="{ background: BUILDING_LEGEND_GRADIENT }" />
          <span class="ce-num">150m+</span>
        </div>
        <div class="lg-row">
          <span class="lg-traffic"><i :style="{ background: RISK_LEVEL_META.watch.color }" />沉降关注</span>
          <span class="lg-traffic"><i :style="{ background: RISK_LEVEL_META.warning.color }" />沉降预警</span>
          <span class="lg-traffic"><i class="pulse" />关联活动事件</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.legend {
  width: 268px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 4px;
  background: linear-gradient(180deg, rgba(12, 28, 58, 0.86), rgba(6, 15, 34, 0.84));
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  font-size: 12px;
}
.legend.collapsed {
  width: auto;
}
.legend__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  height: 30px;
  padding: 0 10px;
  border: none;
  background: transparent;
  color: var(--ce-text-strong);
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 2px;
  cursor: pointer;
}
.legend__caret {
  width: 7px;
  height: 7px;
  border-right: 1.5px solid var(--ce-accent);
  border-bottom: 1.5px solid var(--ce-accent);
  transform: rotate(45deg) translateY(-2px);
  transition: transform 0.2s ease;
}
.collapsed .legend__caret {
  transform: rotate(-135deg) translateY(-2px);
}
.legend__body {
  padding: 0 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.lg-title {
  margin-bottom: 5px;
  font-size: 11px;
  color: var(--ce-text-faint);
  letter-spacing: 1px;
}
.lg-title small {
  margin-left: 4px;
  font-size: 10px;
  color: var(--ce-text-faint);
  opacity: 0.8;
}
.lg-row {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 10px;
}
.lg-traffic,
.lg-sev {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--ce-text-dim);
}
.lg-traffic i {
  width: 14px;
  height: 4px;
  border-radius: 2px;
}
.lg-traffic i.pulse {
  background: #ff3b30;
  animation: lg-pulse 1.1s ease-in-out infinite alternate;
}
@keyframes lg-pulse {
  from {
    opacity: 0.4;
  }
  to {
    opacity: 1;
    box-shadow: 0 0 8px #ff3b30;
  }
}
.lg-sev i {
  width: 10px;
  height: 10px;
  border: 2px solid;
  border-radius: 50%;
}
.lg-type {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 22px;
  padding: 0 7px;
  border: 1px solid color-mix(in srgb, var(--c) 55%, transparent);
  border-radius: 11px;
  background: color-mix(in srgb, var(--c) 14%, transparent);
  color: var(--ce-text);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.lg-type.off {
  opacity: 0.4;
  filter: grayscale(0.8);
  border-style: dashed;
}
.lg-check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  color: var(--ce-text-dim);
  cursor: pointer;
}
.lg-check input {
  accent-color: #4fc3f7;
}
.lg-height {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 10px;
  color: var(--ce-text-faint);
}
.lg-height i {
  flex: 1;
  height: 6px;
  border-radius: 3px;
}
</style>

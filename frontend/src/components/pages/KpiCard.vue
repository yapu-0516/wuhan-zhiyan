<script setup lang="ts">
// 指标卡：左侧色条 + 大数字 + 说明；可点击（用作筛选器）
import AnimatedNumber from './AnimatedNumber.vue'

withDefaults(
  defineProps<{
    label: string
    value: number | string
    unit?: string
    hint?: string
    color?: string
    icon?: string
    active?: boolean
    clickable?: boolean
    digits?: number
  }>(),
  { color: '#4fc3f7', digits: 0 }
)

const emit = defineEmits<{ (e: 'click'): void }>()
</script>

<template>
  <component
    :is="clickable ? 'button' : 'div'"
    class="kpi cp-panel"
    :class="{ 'is-active': active, 'is-clickable': clickable }"
    :style="{ '--c': color }"
    :type="clickable ? 'button' : undefined"
    @click="clickable && emit('click')"
  >
    <span class="kpi__bar"></span>
    <span class="kpi__main">
      <span class="kpi__label">{{ label }}</span>
      <span class="kpi__row">
        <span class="kpi__value">
          <AnimatedNumber v-if="typeof value === 'number'" :value="value" :digits="digits" />
          <template v-else>{{ value }}</template>
        </span>
        <span v-if="unit" class="kpi__unit">{{ unit }}</span>
      </span>
      <span v-if="hint" class="kpi__hint">{{ hint }}</span>
    </span>
  </component>
</template>

<style scoped>
.kpi {
  --c: #4fc3f7;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 16px 14px 20px;
  text-align: left;
  font: inherit;
  color: inherit;
  overflow: hidden;
  min-width: 0;
  transition:
    border-color 0.2s,
    background-color 0.2s;
}
.kpi__bar {
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 2px;
  border-radius: 0;
  background: var(--c);
}
.kpi__main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}
.kpi__label {
  font-size: 13px;
  letter-spacing: 0;
  color: var(--ce-text-dim, #8aa3c4);
}
.kpi__row {
  display: flex;
  align-items: baseline;
  gap: 5px;
}
.kpi__value {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.15;
  color: var(--ce-text-strong);
  font-variant-numeric: tabular-nums;
}
.kpi__unit {
  font-size: 12px;
  color: var(--ce-text-dim, #8aa3c4);
}
.kpi__hint {
  font-size: 12px;
  color: var(--ce-text-faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kpi.is-clickable {
  cursor: pointer;
}
.kpi.is-clickable:hover {
  border-color: color-mix(in srgb, var(--c) 42%, var(--ce-panel-border));
}
.kpi.is-clickable:focus-visible {
  outline: 2px solid var(--c);
  outline-offset: 2px;
}
.kpi.is-active {
  border-color: color-mix(in srgb, var(--c) 48%, var(--ce-panel-border));
  background: #1e2023;
}
</style>

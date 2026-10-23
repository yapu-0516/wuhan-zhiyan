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
    <span v-if="icon" class="kpi__icon">{{ icon }}</span>
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
    box-shadow 0.2s,
    transform 0.2s,
    background 0.2s;
}
.kpi__bar {
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--c);
  box-shadow: 0 0 10px var(--c);
}
.kpi__icon {
  font-size: 24px;
  line-height: 1;
  filter: drop-shadow(0 0 8px color-mix(in srgb, var(--c) 60%, transparent));
}
.kpi__main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}
.kpi__label {
  font-size: 12px;
  letter-spacing: 1.2px;
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
  color: color-mix(in srgb, var(--c) 35%, #fff);
  font-variant-numeric: tabular-nums;
  text-shadow: 0 0 18px color-mix(in srgb, var(--c) 40%, transparent);
}
.kpi__unit {
  font-size: 12px;
  color: var(--ce-text-dim, #8aa3c4);
}
.kpi__hint {
  font-size: 11.5px;
  color: #6f89aa;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kpi.is-clickable {
  cursor: pointer;
}
.kpi.is-clickable:hover {
  border-color: color-mix(in srgb, var(--c) 60%, transparent);
  box-shadow:
    0 8px 28px rgba(0, 0, 0, 0.3),
    0 0 18px color-mix(in srgb, var(--c) 22%, transparent);
  transform: translateY(-1px);
}
.kpi.is-clickable:focus-visible {
  outline: 2px solid var(--c);
  outline-offset: 2px;
}
.kpi.is-active {
  border-color: color-mix(in srgb, var(--c) 70%, transparent);
  background: linear-gradient(135deg, color-mix(in srgb, var(--c) 14%, rgba(16, 26, 48, 0.72)), rgba(16, 26, 48, 0.72) 70%);
  box-shadow:
    0 8px 28px rgba(0, 0, 0, 0.3),
    0 0 22px color-mix(in srgb, var(--c) 25%, transparent);
}
</style>

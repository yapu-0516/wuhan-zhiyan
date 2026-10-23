<script setup lang="ts">
// 分析类型选择卡：图标 / 中文名 / 算法名称与方法（来自 system/info.algorithms）/ 支持的输入
import { computed } from 'vue'
import { Check } from '@element-plus/icons-vue'
import type { AlgorithmInfo } from '@/types/api'
import type { EventType } from '@/types/event'
import { ANALYSIS_TYPES } from '@/composables/pages/aiMeta'

const props = defineProps<{
  selected: EventType
  algorithms: AlgorithmInfo[]
  loading?: boolean
}>()
const emit = defineEmits<{ (e: 'select', t: EventType): void }>()

const EN: Record<EventType, string> = {
  fire: 'FIRE DETECTION',
  traffic: 'TRAFFIC CONGESTION',
  building: 'STRUCTURAL ANOMALY',
  flood: 'WATERLOGGING MONITOR'
}

const algoOf = computed(() => {
  const m = new Map<string, AlgorithmInfo>()
  for (const a of props.algorithms) m.set(a.type, a)
  return m
})
</script>

<template>
  <div class="tcs">
    <button
      v-for="t in ANALYSIS_TYPES"
      :key="t.key"
      type="button"
      class="tc"
      :class="{ 'is-on': selected === t.key }"
      :style="{ '--c': t.color }"
      @click="emit('select', t.key)"
    >
      <span class="tc__check"><el-icon v-if="selected === t.key"><Check /></el-icon></span>
      <div class="tc__top">
        <span class="tc__icon">{{ t.icon }}</span>
        <div class="tc__title">
          <b>{{ t.label }}</b>
          <span>{{ EN[t.key] }}</span>
        </div>
      </div>
      <p class="tc__blurb">{{ t.blurb }}</p>

      <div class="tc__algo">
        <template v-if="algoOf.get(t.key)">
          <div class="tc__algoname">
            <span class="cp-label">算法</span>
            <b class="cp-mono">{{ algoOf.get(t.key)!.name }}</b>
            <i>v{{ algoOf.get(t.key)!.version }}</i>
          </div>
          <el-tooltip :content="algoOf.get(t.key)!.method" placement="right" popper-class="cp-popper">
            <p class="tc__method">{{ algoOf.get(t.key)!.method }}</p>
          </el-tooltip>
        </template>
        <el-skeleton v-else-if="loading" animated :rows="1" />
        <p v-else class="tc__method tc__method--na">算法信息由后端提供（当前不可用）</p>
      </div>

      <div class="tc__inputs">
        <span v-for="i in t.inputs" :key="i" class="tc__chip">{{ i }}</span>
      </div>
    </button>
  </div>
</template>

<style scoped>
.tcs {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.tc {
  --c: #4fc3f7;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px 14px;
  text-align: left;
  font: inherit;
  color: var(--ce-text, #d6e4ff);
  border-radius: 10px;
  cursor: pointer;
  background: var(--ce-panel, rgba(16, 26, 48, 0.72));
  border: 1px solid var(--ce-panel-border, rgba(64, 120, 180, 0.28));
  transition:
    border-color 0.2s,
    box-shadow 0.2s,
    transform 0.2s,
    background 0.2s;
  overflow: hidden;
}
.tc::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  background: var(--c);
  opacity: 0.35;
  transition: opacity 0.2s, box-shadow 0.2s;
}
.tc:hover {
  border-color: color-mix(in srgb, var(--c) 55%, transparent);
  transform: translateY(-1px);
}
.tc.is-on {
  border-color: var(--c);
  background: linear-gradient(135deg, color-mix(in srgb, var(--c) 15%, rgba(16, 26, 48, 0.8)), rgba(16, 26, 48, 0.78) 65%);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--c) 40%, transparent),
    0 8px 28px rgba(0, 0, 0, 0.3),
    0 0 24px color-mix(in srgb, var(--c) 24%, transparent);
}
.tc.is-on::before {
  opacity: 1;
  box-shadow: 0 0 12px var(--c);
}
.tc:focus-visible {
  outline: 2px solid var(--c);
  outline-offset: 2px;
}
.tc__check {
  position: absolute;
  top: 12px;
  right: 12px;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid rgba(138, 163, 196, 0.35);
  color: #06101f;
  font-size: 13px;
}
.tc.is-on .tc__check {
  background: var(--c);
  border-color: var(--c);
  box-shadow: 0 0 10px var(--c);
}
.tc__top {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-right: 26px;
}
.tc__icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  font-size: 22px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--c) 15%, rgba(9, 16, 34, 0.8));
  border: 1px solid color-mix(in srgb, var(--c) 45%, transparent);
}
.tc__title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.tc__title b {
  font-size: 15px;
  font-weight: 600;
  color: #f0f6ff;
}
.tc__title span {
  font-size: 10px;
  letter-spacing: 1.6px;
  color: var(--c);
  opacity: 0.85;
}
.tc__blurb {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #9db4d2;
}
.tc__algo {
  padding: 8px 10px;
  border-radius: 7px;
  background: rgba(7, 12, 28, 0.55);
  border: 1px dashed rgba(64, 120, 180, 0.3);
}
.tc__algoname {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.tc__algoname b {
  font-size: 13px;
  color: var(--c);
}
.tc__algoname i {
  font-style: normal;
  font-size: 11px;
  color: #6f89aa;
}
.tc__method {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #8aa3c4;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tc__method--na {
  color: #5d748f;
}
.tc__inputs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tc__chip {
  padding: 0 8px;
  line-height: 20px;
  font-size: 11.5px;
  border-radius: 4px;
  color: #a9cdf0;
  background: rgba(79, 195, 247, 0.08);
  border: 1px solid rgba(64, 120, 180, 0.3);
}
</style>

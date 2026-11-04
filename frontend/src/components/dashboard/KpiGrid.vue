<script setup lang="ts">
// 核心指标：今日事件 / 待处置 / 处置率 / 平均响应
import AnimatedNumber from './AnimatedNumber.vue'

defineProps<{ today: number; total: number; active: number; resolveRate: number; avgResponse: number; critical: number }>()
</script>

<template>
  <div class="kpis">
    <div class="ce-kpi kpi">
      <span class="ce-kpi__label">今日事件</span>
      <span class="ce-kpi__value"><AnimatedNumber :value="today" /><small>件</small></span>
      <span class="kpi__sub">累计 <b class="ce-num">{{ total }}</b></span>
    </div>
    <div class="ce-kpi kpi kpi--warn">
      <span class="ce-kpi__label">待处置</span>
      <span class="ce-kpi__value"><AnimatedNumber :value="active" /><small>件</small></span>
      <span class="kpi__sub">Ⅰ/Ⅱ级 <b class="ce-num">{{ critical }}</b></span>
    </div>
    <div class="ce-kpi kpi">
      <span class="ce-kpi__label">处置率</span>
      <span class="ce-kpi__value"><AnimatedNumber :value="resolveRate * 100" :decimals="1" /><small>%</small></span>
      <span class="kpi__bar"><i :style="{ width: Math.min(100, resolveRate * 100) + '%' }" /></span>
    </div>
    <div class="ce-kpi kpi">
      <span class="ce-kpi__label">平均响应</span>
      <span class="ce-kpi__value"><AnimatedNumber :value="avgResponse" :decimals="1" /><small>分钟</small></span>
      <span class="kpi__sub">创建 → 首次处置</span>
    </div>
  </div>
</template>

<style scoped>
.kpis {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  margin: -12px -14px;
}
.kpi {
  min-width: 0;
  padding: 12px 14px;
  border-right: 1px solid var(--ce-divider);
  border-bottom: 1px solid var(--ce-divider);
}
.kpi:nth-child(2n) {
  border-right: 0;
}
.kpi:nth-child(n + 3) {
  border-bottom: 0;
}
.kpi--warn .ce-kpi__value {
  color: var(--ce-warning);
}
.kpi__sub {
  font-size: 13px;
  color: var(--ce-text-dim);
}
.kpi__sub b {
  color: var(--ce-text-dim);
  font-size: 13px;
}
.kpi__bar {
  display: block;
  height: 4px;
  margin-top: 4px;
  border-radius: 2px;
  background: #2a3035;
  overflow: hidden;
}
.kpi__bar i {
  display: block;
  height: 100%;
  border-radius: 2px;
  background: var(--ce-accent);
  transition: width 0.8s var(--ce-ease);
}
</style>

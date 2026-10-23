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
  gap: 8px;
}
.kpi {
  min-width: 0;
}
.kpi--warn .ce-kpi__value {
  color: #ffb37a;
  text-shadow: 0 0 12px rgba(255, 159, 67, 0.45);
}
.kpi__sub {
  font-size: 11px;
  color: var(--ce-text-faint);
}
.kpi__sub b {
  color: var(--ce-text-dim);
  font-size: 12px;
}
.kpi__bar {
  display: block;
  height: 4px;
  margin-top: 4px;
  border-radius: 2px;
  background: rgba(79, 195, 247, 0.12);
  overflow: hidden;
}
.kpi__bar i {
  display: block;
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, #1f78d1, #4dd984);
  transition: width 0.8s var(--ce-ease);
}
</style>

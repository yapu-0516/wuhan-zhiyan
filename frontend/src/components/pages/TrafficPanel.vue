<script setup lang="ts">
// 实时路况：城市 TPI 仪表盘 + 拥堵等级分布 + 最拥堵道路 Top10（随 traffic.updated 实时刷新）
import { computed } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import AnimatedNumber from './AnimatedNumber.vue'
import { TRAFFIC_LEVEL_META } from '@/types/building'
import type { Road } from '@/types/building'
import { HIGHWAY_LABEL, TRAFFIC_LEVELS, cityTpiOf, groupRoads, levelOfTpi } from '@/composables/pages/traffic'

const props = defineProps<{
  roads: Road[]
  /** 服务端推送的全路网 TPI（缺省时按路段长度加权计算） */
  cityTpi: number | null
  loading?: boolean
  live: boolean
}>()

const groups = computed(() => groupRoads(props.roads))
const tpi = computed(() => props.cityTpi ?? cityTpiOf(props.roads))
const level = computed(() => levelOfTpi(tpi.value))
const meta = computed(() => TRAFFIC_LEVEL_META[level.value])

const top10 = computed(() => [...groups.value].sort((a, b) => b.tpi - a.tpi || a.speed - b.speed).slice(0, 10))

const levelCounts = computed(() => {
  const c: Record<string, number> = { smooth: 0, basic: 0, light: 0, moderate: 0, heavy: 0 }
  for (const g of groups.value) c[g.level]++
  return TRAFFIC_LEVELS.map((l) => ({ level: l, count: c[l], ...TRAFFIC_LEVEL_META[l] }))
})
const totalRoads = computed(() => groups.value.length)

const gauge = computed(() => ({
  series: [
    {
      type: 'gauge',
      min: 0,
      max: 10,
      startAngle: 205,
      endAngle: -25,
      splitNumber: 5,
      radius: '96%',
      center: ['50%', '60%'],
      axisLine: {
        lineStyle: {
          width: 15,
          color: TRAFFIC_LEVELS.map((l, i) => [(i + 1) / 5, TRAFFIC_LEVEL_META[l].color])
        }
      },
      progress: { show: false },
      pointer: { length: '62%', width: 5, itemStyle: { color: meta.value.color, shadowBlur: 10, shadowColor: meta.value.color } },
      anchor: { show: true, size: 12, itemStyle: { color: '#0d1630', borderColor: meta.value.color, borderWidth: 3 } },
      axisTick: { show: false },
      splitLine: { length: 15, distance: -15, lineStyle: { color: '#0b1430', width: 3 } },
      axisLabel: { color: '#8aa3c4', fontSize: 11, distance: -34 },
      title: { show: false },
      detail: {
        valueAnimation: true,
        offsetCenter: [0, '56%'],
        fontSize: 34,
        fontWeight: 600,
        color: meta.value.color,
        formatter: (v: number) => v.toFixed(1)
      },
      data: [{ value: Number(tpi.value.toFixed(2)) }]
    }
  ]
}))

const hw = (h: string) => HIGHWAY_LABEL[h] ?? h
</script>

<template>
  <section class="tp cp-panel">
    <div class="cp-panel__header">
      <h3 class="cp-panel__title">实时路况</h3>
      <span class="cp-panel__sub">
        <i class="cp-dot" :class="{ 'cp-dot--pulse': live }" :style="{ '--c': live ? '#4dd984' : '#8aa3c4' }"></i>
        {{ live ? '约 10 秒刷新' : '静态数据' }}
      </span>
    </div>

    <div class="cp-panel__body tp__body">
      <el-skeleton v-if="loading && !roads.length" animated :rows="8" />
      <el-empty v-else-if="!roads.length" :image-size="72" description="暂无路网数据" />
      <template v-else>
        <div class="tp__left">
          <div class="gauge">
            <EChart :option="gauge" style="height: 220px" />
            <div class="gauge__level" :style="{ '--c': meta.color }">
              <span class="cp-pill" :style="{ '--c': meta.color }">{{ meta.label }}</span>
            </div>
          </div>
          <div class="gauge__cap"><span class="cp-label">全路网交通运行指数 TPI</span></div>

          <div class="lv">
            <div class="lv__bar">
              <span
                v-for="l in levelCounts"
                :key="l.level"
                class="lv__seg"
                :style="{ '--c': l.color, flex: `${l.count} 1 0%` }"
                :title="`${l.label}：${l.count} 条`"
              >
                <b v-if="l.count && l.count / totalRoads > 0.09">{{ l.count }}</b>
              </span>
            </div>
            <ul class="lv__legend">
              <li v-for="l in levelCounts" :key="l.level" :style="{ '--c': l.color }">
                <i></i>{{ l.label }}<b>{{ l.count }}</b>
              </li>
            </ul>
            <p class="lv__sum">共监测 <b>{{ totalRoads }}</b> 条主干道（{{ roads.length }} 个路段）</p>
          </div>
        </div>

        <div class="tp__right">
          <div class="rk__head">
            <span class="cp-label">最拥堵道路 TOP {{ top10.length }}</span>
            <span class="rk__cols"><i>车速</i><i>TPI</i><i>等级</i></span>
          </div>
          <TransitionGroup name="rank" tag="ol" class="rk">
            <li v-for="(g, i) in top10" :key="g.key" class="rk__row" :style="{ '--c': TRAFFIC_LEVEL_META[g.level].color }">
              <span class="rk__no" :class="{ 'is-top': i < 3 }">{{ i + 1 }}</span>
              <div class="rk__name">
                <b class="cp-ellipsis" :title="g.name">{{ g.name }}</b>
                <small>{{ hw(g.highway) }}<template v-if="g.segments > 1"> · {{ g.segments }} 段</template> · 限速 {{ g.speed_limit }}</small>
              </div>
              <span class="rk__speed"><AnimatedNumber :value="g.speed" :digits="0" :duration="500" /><small>km/h</small></span>
              <span class="rk__tpi">
                <b><AnimatedNumber :value="g.tpi" :digits="1" :duration="500" /></b>
                <span class="cp-bar"><i :style="{ width: `${Math.min(100, g.tpi * 10)}%` }"></i></span>
              </span>
              <span class="cp-pill cp-pill--sm rk__lv" :style="{ '--c': TRAFFIC_LEVEL_META[g.level].color }">{{ TRAFFIC_LEVEL_META[g.level].label }}</span>
            </li>
          </TransitionGroup>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.tp__body {
  display: grid;
  grid-template-columns: minmax(250px, 300px) minmax(0, 1fr);
  gap: 22px;
}
@media (max-width: 1100px) {
  .tp__body {
    grid-template-columns: 1fr;
  }
}
.tp__left {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.gauge {
  position: relative;
}
.gauge__level {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 6px;
  display: flex;
  justify-content: center;
}
.gauge__cap {
  text-align: center;
  margin: 2px 0 16px;
}
.lv__bar {
  display: flex;
  gap: 2px;
  height: 22px;
  border-radius: 6px;
  overflow: hidden;
  background: rgba(120, 160, 210, 0.12);
}
.lv__seg {
  --c: #4dd984;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  min-width: 0;
  background: linear-gradient(180deg, color-mix(in srgb, var(--c) 90%, #fff), var(--c));
  transition: flex-grow 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}
.lv__seg b {
  font-size: 11px;
  color: #06101f;
}
.lv__legend {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin: 10px 0 0;
  padding: 0;
  font-size: 12px;
  color: #9db4d2;
}
.lv__legend li {
  display: flex;
  align-items: center;
  gap: 5px;
}
.lv__legend i {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--c);
}
.lv__legend b {
  color: #fff;
  font-variant-numeric: tabular-nums;
}
.lv__sum {
  margin: 10px 0 0;
  font-size: 12px;
  color: #6f89aa;
}
.lv__sum b {
  color: #cfe0fa;
}
.tp__right {
  min-width: 0;
}
.rk__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  padding: 0 4px;
}
.rk__cols {
  display: grid;
  grid-template-columns: 84px 108px 78px;
  gap: 10px;
  font-size: 11px;
  font-style: normal;
  letter-spacing: 1.2px;
  color: #5d748f;
}
.rk__cols i {
  font-style: normal;
}
.rk {
  position: relative;
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.rk__row {
  --c: #f0c050;
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) 84px 108px 78px;
  align-items: center;
  gap: 10px;
  padding: 7px 4px;
  border-radius: 7px;
  border: 1px solid transparent;
  transition: background 0.2s, border-color 0.2s;
}
.rk__row:hover {
  background: color-mix(in srgb, var(--c) 8%, transparent);
  border-color: color-mix(in srgb, var(--c) 28%, transparent);
}
.rk__no {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  font-size: 12px;
  border-radius: 6px;
  color: #8aa3c4;
  background: rgba(120, 160, 210, 0.12);
  font-variant-numeric: tabular-nums;
}
.rk__no.is-top {
  color: #06101f;
  font-weight: 700;
  background: var(--c);
  box-shadow: 0 0 10px color-mix(in srgb, var(--c) 55%, transparent);
}
.rk__name {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.rk__name b {
  font-size: 13.5px;
  font-weight: 500;
  color: #e6f0ff;
}
.rk__name small {
  font-size: 11px;
  color: #6f89aa;
}
.rk__speed {
  font-size: 15px;
  font-weight: 600;
  color: #dbe8ff;
  font-variant-numeric: tabular-nums;
}
.rk__speed small {
  margin-left: 3px;
  font-size: 10.5px;
  font-weight: 400;
  color: #6f89aa;
}
.rk__tpi {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rk__tpi b {
  font-size: 14px;
  line-height: 1;
  color: var(--c);
  font-variant-numeric: tabular-nums;
}
.rk__lv {
  justify-self: start;
}
.rank-move {
  transition: transform 0.55s cubic-bezier(0.22, 1, 0.36, 1);
}
.rank-enter-active,
.rank-leave-active {
  transition: opacity 0.3s;
}
.rank-enter-from,
.rank-leave-to {
  opacity: 0;
}
.rank-leave-active {
  position: absolute;
  left: 0;
  right: 0;
}
@media (prefers-reduced-motion: reduce) {
  .rank-move,
  .lv__seg {
    transition: none;
  }
}
</style>

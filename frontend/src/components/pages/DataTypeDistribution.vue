<script setup lang="ts">
// 数据类型分布：环形图 + 可点击图例（点击即按类型筛选）
import { computed } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import { dataTypeMeta } from '@/composables/pages/dataMeta'
import AnimatedNumber from './AnimatedNumber.vue'

const props = defineProps<{
  items: { type: string; count: number }[]
  /** 当前筛选的类型（空表示全部） */
  selected: string
}>()
const emit = defineEmits<{ (e: 'select', type: string): void }>()

const total = computed(() => props.items.reduce((s, i) => s + i.count, 0))

const option = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: (p: { name: string; value: number; percent: number }) =>
      `${dataTypeMeta(p.name).icon} ${p.name}<br/><b>${p.value}</b> 项 · ${p.percent}%`
  },
  series: [
    {
      type: 'pie',
      radius: ['60%', '84%'],
      center: ['50%', '50%'],
      padAngle: 2,
      minAngle: 6,
      avoidLabelOverlap: true,
      label: { show: false },
      labelLine: { show: false },
      itemStyle: { borderRadius: 6, borderColor: 'rgba(12, 20, 40, 0.95)', borderWidth: 2 },
      emphasis: { scale: true, scaleSize: 5, itemStyle: { shadowBlur: 18, shadowColor: 'rgba(79, 195, 247, 0.5)' } },
      data: props.items.map((i) => ({
        name: i.type,
        value: i.count,
        itemStyle: {
          color: dataTypeMeta(i.type).color,
          opacity: !props.selected || props.selected === i.type ? 1 : 0.28
        }
      }))
    }
  ]
}))
</script>

<template>
  <div class="dist">
    <div class="dist__chart">
      <EChart :option="option" style="height: 210px" />
      <div class="dist__center">
        <b><AnimatedNumber :value="total" /></b>
        <span>数据资产</span>
      </div>
    </div>
    <ul class="dist__legend">
      <li
        v-for="i in items"
        :key="i.type"
        :class="{ 'is-on': selected === i.type, 'is-dim': selected && selected !== i.type }"
        :style="{ '--c': dataTypeMeta(i.type).color }"
        @click="emit('select', selected === i.type ? '' : i.type)"
      >
        <span class="dist__ic">{{ dataTypeMeta(i.type).icon }}</span>
        <span class="dist__name">{{ i.type }}</span>
        <span class="dist__bar"><i :style="{ width: total ? `${(i.count / total) * 100}%` : '0%' }"></i></span>
        <b class="dist__n">{{ i.count }}</b>
        <span class="dist__p">{{ total ? Math.round((i.count / total) * 100) : 0 }}%</span>
      </li>
      <li v-if="!items.length" class="dist__empty">暂无分类数据</li>
    </ul>
  </div>
</template>

<style scoped>
.dist {
  display: grid;
  grid-template-columns: minmax(170px, 230px) 1fr;
  align-items: center;
  gap: 20px;
}
.dist__chart {
  position: relative;
}
.dist__center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  pointer-events: none;
}
.dist__center b {
  font-size: 30px;
  font-weight: 600;
  color: #eaf5ff;
  text-shadow: 0 0 18px rgba(79, 195, 247, 0.5);
}
.dist__center span {
  font-size: 12px;
  letter-spacing: 2px;
  color: var(--ce-text-dim, #8aa3c4);
}
.dist__legend {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.dist__legend li {
  --c: #4fc3f7;
  display: grid;
  grid-template-columns: 24px 82px 1fr 30px 38px;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 7px;
  border: 1px solid transparent;
  font-size: 13px;
  color: #c9dbf5;
  cursor: pointer;
  transition: all 0.16s;
}
.dist__legend li:hover {
  background: color-mix(in srgb, var(--c) 9%, transparent);
}
.dist__legend li.is-on {
  border-color: color-mix(in srgb, var(--c) 55%, transparent);
  background: color-mix(in srgb, var(--c) 13%, transparent);
}
.dist__legend li.is-dim {
  opacity: 0.55;
}
.dist__ic {
  font-size: 16px;
  text-align: center;
}
.dist__bar {
  height: 5px;
  border-radius: 3px;
  background: rgba(120, 160, 210, 0.15);
  overflow: hidden;
}
.dist__bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: var(--c);
  box-shadow: 0 0 8px var(--c);
  transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}
.dist__n {
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: #fff;
}
.dist__p {
  text-align: right;
  font-size: 12px;
  color: #6f89aa;
  font-variant-numeric: tabular-nums;
}
.dist__empty {
  color: #5d748f;
  cursor: default !important;
}
@media (max-width: 1500px) {
  .dist {
    grid-template-columns: 1fr;
  }
}
</style>

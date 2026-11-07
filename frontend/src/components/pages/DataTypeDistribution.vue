<script setup lang="ts">
// 数据类型分布：环形图 + 可点击图例（点击即按类型筛选）
import { computed } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import { dataTypeMeta } from '@/composables/pages/dataMeta'
import AnimatedNumber from '../common/AnimatedNumber.vue'

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
      `${p.name}<br/><b>${p.value}</b> 项 · ${p.percent}%`
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
      itemStyle: { borderRadius: 4, borderColor: '#17181a', borderWidth: 2 },
      emphasis: { scale: true, scaleSize: 3 },
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
        <span class="dist__dot" />
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
}
.dist__center span {
  font-size: 12px;
  letter-spacing: 0;
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
  grid-template-columns: 12px 82px 1fr 30px 38px;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  border: 1px solid transparent;
  font-size: 13px;
  color: var(--ce-text);
  cursor: pointer;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease;
}
.dist__legend li:hover {
  background: #1d1f22;
}
.dist__legend li.is-on {
  border-color: var(--c);
  background: #1d1f22;
}
.dist__legend li.is-dim {
  opacity: 0.55;
}
.dist__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c);
}
.dist__bar {
  height: 5px;
  border-radius: 3px;
  background: #2a2c2f;
  overflow: hidden;
}
.dist__bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: var(--c);
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
  color: var(--ce-text-faint);
  font-variant-numeric: tabular-nums;
}
.dist__empty {
  color: var(--ce-text-faint);
  cursor: default !important;
}
@media (max-width: 1500px) {
  .dist {
    grid-template-columns: 1fr;
  }
}
</style>

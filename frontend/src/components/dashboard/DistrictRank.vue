<script setup lang="ts">
// 区域事件排行：横向条形（前 6）
import { computed } from 'vue'

const props = defineProps<{ items: { name: string; count: number }[] }>()

const rows = computed(() => {
  const list = [...(props.items ?? [])].filter((x) => x && x.name).sort((a, b) => b.count - a.count).slice(0, 6)
  const max = Math.max(1, ...list.map((x) => x.count))
  return list.map((x, i) => ({ ...x, rank: i + 1, pct: (x.count / max) * 100 }))
})
</script>

<template>
  <ol v-if="rows.length" class="rank">
    <li v-for="r in rows" :key="r.name" :class="'r' + r.rank">
      <span class="rank__no ce-num">{{ String(r.rank).padStart(2, '0') }}</span>
      <span class="rank__name" :title="r.name">{{ r.name }}</span>
      <span class="rank__bar"><i :style="{ width: r.pct + '%' }" /></span>
      <b class="rank__v ce-num">{{ r.count }}</b>
    </li>
  </ol>
  <div v-else class="rank__empty">暂无区域统计</div>
</template>

<style scoped>
.rank {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  gap: 6px;
  flex: 1;
}
.rank li {
  display: grid;
  grid-template-columns: 24px 64px 1fr 32px;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
}
.rank__no {
  display: grid;
  place-items: center;
  height: 18px;
  border-radius: 2px;
  font-size: 11px;
  color: var(--ce-text-dim);
  background: rgba(79, 195, 247, 0.08);
}
.r1 .rank__no {
  color: #08111f;
  background: linear-gradient(135deg, #ffd36b, #ff9f43);
}
.r2 .rank__no {
  color: #08111f;
  background: linear-gradient(135deg, #8fe7ff, #4fc3f7);
}
.r3 .rank__no {
  color: #08111f;
  background: linear-gradient(135deg, #b9a8ff, #8b7cff);
}
.rank__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ce-text);
}
.rank__bar {
  height: 6px;
  border-radius: 3px;
  background: rgba(79, 195, 247, 0.08);
  overflow: hidden;
}
.rank__bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, rgba(31, 120, 209, 0.6), #36e4ff);
  box-shadow: 0 0 8px rgba(54, 228, 255, 0.5);
  transition: width 0.8s var(--ce-ease);
}
.r1 .rank__bar i {
  background: linear-gradient(90deg, rgba(255, 159, 67, 0.5), #ffd36b);
  box-shadow: 0 0 8px rgba(255, 191, 90, 0.5);
}
.rank__v {
  text-align: right;
  font-size: 15px;
  color: var(--ce-text-strong);
}
.rank__empty {
  flex: 1;
  display: grid;
  place-items: center;
  font-size: 12px;
  color: var(--ce-text-faint);
}
</style>

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
      <span class="rank__no ce-num">{{ r.rank }}</span>
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
  gap: 8px;
  flex: 1;
}
.rank li {
  display: grid;
  grid-template-columns: 18px 64px 1fr 32px;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.rank__no {
  font-size: 12px;
  color: var(--ce-text-faint);
}
.r1 .rank__no {
  color: var(--ce-text-strong);
}
.rank__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ce-text);
}
.rank__bar {
  height: 3px;
  background: #2a3035;
  overflow: hidden;
}
.rank__bar i {
  display: block;
  height: 100%;
  background: #6d777f;
  transition: width 0.8s var(--ce-ease);
}
.r1 .rank__bar i {
  background: var(--ce-accent);
}
.rank__v {
  text-align: right;
  font-size: 14px;
  color: var(--ce-text-strong);
}
.rank__empty {
  flex: 1;
  display: grid;
  place-items: center;
  font-size: 13px;
  color: var(--ce-text-faint);
}
</style>

<script setup lang="ts">
// 底部城市状态栏：从事件状态动态统计，不写死
// 数据源：useCityEvents（阶段3 为空，阶段6 填充 mock 后自动生效）
import { useCityEvents } from '@/composables/useCityEvents'
import { EVENT_TYPE_META, type EventType } from '@/types/event'

const { stats } = useCityEvents()
const types: EventType[] = ['fire', 'traffic', 'building']
</script>

<template>
  <footer class="status-panel">
    <div class="stat-total">
      <span class="stat-label">当前监测事件</span>
      <span class="stat-value">{{ stats.total }}</span>
    </div>
    <div class="stat-divider"></div>
    <div class="stat-list">
      <div v-for="t in types" :key="t" class="stat-item">
        <span class="stat-emoji">{{ EVENT_TYPE_META[t].icon }}</span>
        <span class="stat-name">{{ EVENT_TYPE_META[t].label }}</span>
        <span class="stat-count" :style="{ color: EVENT_TYPE_META[t].color }">
          {{ stats.byType[t] ?? 0 }}
        </span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.status-panel {
  height: 44px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 22px;
  background: rgba(10, 18, 38, 0.85);
  border-top: 1px solid var(--ce-panel-border);
  backdrop-filter: blur(8px);
  font-size: 13px;
}
.stat-total {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stat-label {
  color: var(--ce-text-dim);
}
.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--ce-accent);
}
.stat-divider {
  width: 1px;
  height: 20px;
  background: var(--ce-panel-border);
}
.stat-list {
  display: flex;
  align-items: center;
  gap: 22px;
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ce-text-dim);
}
.stat-emoji {
  font-size: 15px;
}
.stat-count {
  font-weight: 600;
  font-size: 14px;
}
</style>

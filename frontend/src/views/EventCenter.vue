<script setup lang="ts">
// 事件中心 —— 阶段9
// 用 Element Plus 表格汇总所有城市事件，点击行跳转回三维城市并 flyTo 定位该事件。
// 数据来自 useCityEvents（阶段6 注入 mock），阶段11 后改由 API 层获取。
import { useRouter } from 'vue-router'
import { useCityEvents } from '@/composables/useCityEvents'
import { EVENT_TYPE_META, EVENT_STATUS_LABEL } from '@/types/event'
import type { CityEvent } from '@/types/event'

const router = useRouter()
const { events } = useCityEvents()

// 点击行 → 携带 eventId 跳转回 Dashboard，CesiumViewer 监听 query 后 flyTo
function locateEvent(row: CityEvent) {
  router.push({ path: '/dashboard', query: { eventId: row.id } })
}
</script>

<template>
  <div class="page">
    <h2 class="page-title">事件中心</h2>
    <p class="page-hint">
      所有城市事件汇总。点击任一行，将跳转回三维城市并将相机定位到该事件位置。
    </p>
    <el-table
      :data="events"
      stripe
      highlight-current-row
      class="event-table"
      @row-click="locateEvent"
    >
      <el-table-column prop="id" label="编号" width="100" />
      <el-table-column label="类型" width="160">
        <template #default="{ row }">
          <span class="type-cell">
            <span class="type-emoji">{{ EVENT_TYPE_META[row.event_type as CityEvent['event_type']].icon }}</span>
            <span :style="{ color: EVENT_TYPE_META[row.event_type as CityEvent['event_type']].color }">
              {{ EVENT_TYPE_META[row.event_type as CityEvent['event_type']].label }}
            </span>
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="timestamp" label="时间" width="200" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">{{ EVENT_STATUS_LABEL[row.status as CityEvent['status']] }}</template>
      </el-table-column>
      <el-table-column label="置信度" width="120">
        <template #default="{ row }">{{ Math.round(row.confidence * 100) }}%</template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default>
          <span class="locate-link">定位 →</span>
        </template>
      </el-table-column>
    </el-table>
    <p class="mock-tip">⚠️ 当前为 mock 数据，不代表真实 AI 检测结果。</p>
  </div>
</template>

<style scoped>
.page {
  padding: 24px 32px;
  color: var(--ce-text);
  height: 100%;
  overflow: auto;
}
.page-title {
  margin: 0 0 10px;
  font-size: 22px;
  letter-spacing: 2px;
}
.page-hint {
  margin: 0 0 18px;
  color: var(--ce-text-dim);
  font-size: 13px;
}
.event-table {
  width: 100%;
  background: transparent;
}
.event-table :deep(.el-table__row) {
  cursor: pointer;
}
.type-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}
.type-emoji {
  font-size: 16px;
}
.locate-link {
  color: var(--ce-accent);
  font-size: 13px;
}
.mock-tip {
  margin-top: 16px;
  font-size: 12px;
  color: #5d748f;
}
</style>

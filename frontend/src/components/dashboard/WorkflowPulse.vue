<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getAssessments, getMonitoringTasks, getReviews, getWorkOrders } from '@/api/workflow'
import { getDataList, getDataStats } from '@/api/data'
import type { Assessment, MonitoringTask, ReviewRecord, WorkOrder } from '@/types/workflow'
import type { DataItem, DataStats } from '@/types/api'

const tasks = ref<MonitoringTask[]>([])
const assessments = ref<Assessment[]>([])
const orders = ref<WorkOrder[]>([])
const reviews = ref<ReviewRecord[]>([])
const dataStats = ref<DataStats | null>(null)
const dataItems = ref<DataItem[]>([])
const loading = ref(true)
let timer = 0

const activeTasks = computed(
  () => tasks.value.filter((item) => ['scheduled', 'running'].includes(item.status)).length
)
const activeOrders = computed(
  () => orders.value.filter((item) => !['verified', 'cancelled'].includes(item.status)).length
)
const overdueOrders = computed(() => {
  const now = Date.now()
  return orders.value.filter(
    (item) =>
      item.due_at &&
      !['verified', 'cancelled'].includes(item.status) &&
      new Date(item.due_at.replace(' ', 'T')).getTime() < now
  ).length
})

const items = computed(() => [
  {
    to: '/workflow/tasks',
    label: '运行任务',
    value: activeTasks.value,
    hint: `${tasks.value.length} 项任务`
  },
  {
    to: '/workflow/assessment',
    label: '研判记录',
    value: assessments.value.length,
    hint: '证据与结论'
  },
  {
    to: '/workflow/orders',
    label: '活跃工单',
    value: activeOrders.value,
    hint: overdueOrders.value ? `${overdueOrders.value} 张超时` : '执行与复核'
  },
  {
    to: '/workflow/reviews',
    label: '复盘记录',
    value: reviews.value.length,
    hint: '经验与改进'
  }
])

async function load() {
  const results = await Promise.allSettled([
    getMonitoringTasks(),
    getAssessments(),
    getWorkOrders(),
    getReviews(),
    getDataStats(),
    getDataList()
  ])
  if (results[0].status === 'fulfilled') tasks.value = results[0].value
  if (results[1].status === 'fulfilled') assessments.value = results[1].value
  if (results[2].status === 'fulfilled') orders.value = results[2].value
  if (results[3].status === 'fulfilled') reviews.value = results[3].value
  if (results[4].status === 'fulfilled') dataStats.value = results[4].value
  if (results[5].status === 'fulfilled') dataItems.value = results[5].value
  loading.value = false
}

onMounted(() => {
  void load()
  timer = window.setInterval(() => void load(), 30_000)
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div v-loading="loading" class="workflow-pulse" aria-label="业务运行摘要">
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="workflow-pulse__item"
      :class="{ 'is-alert': item.label === '活跃工单' && overdueOrders > 0 }"
    >
      <span>{{ item.label }}</span>
      <b class="ce-num">{{ item.value }}</b>
      <small>{{ item.hint }}</small>
    </RouterLink>
    <div class="workflow-pulse__coverage">
      <span>数据覆盖</span>
      <b>{{ dataStats?.analyzable ?? dataItems.filter((item) => item.analysis_status === 'ready').length }}</b>
      <small>可分析资源</small>
      <time>{{ dataItems[0]?.time || '暂无更新时间' }}</time>
    </div>
  </div>
</template>

<style scoped>
.workflow-pulse {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 112px;
}
.workflow-pulse__item {
  position: relative;
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  padding: 9px 12px;
  color: var(--ce-text-dim);
  text-decoration: none;
}
.workflow-pulse__item:nth-child(even) {
  border-left: 1px solid var(--ce-divider);
}
.workflow-pulse__item:nth-child(n + 3) {
  border-top: 1px solid var(--ce-divider);
}
.workflow-pulse__item:hover,
.workflow-pulse__item:focus-visible {
  color: var(--ce-text-strong);
  background: var(--ce-active);
  outline: none;
}
.workflow-pulse__item:hover::after,
.workflow-pulse__item:focus-visible::after {
  position: absolute;
  inset: auto 10px 0;
  height: 1px;
  background: var(--ce-accent);
  content: '';
}
.workflow-pulse__item span {
  overflow: hidden;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workflow-pulse__item b {
  color: var(--ce-text-strong);
  font-size: 22px;
  line-height: 1.15;
}
.workflow-pulse__item small {
  overflow: hidden;
  color: var(--ce-text-faint);
  font-size: 10.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workflow-pulse__item.is-alert b,
.workflow-pulse__item.is-alert small {
  color: var(--ce-warning);
}
.workflow-pulse__coverage {
  display: flex;
  grid-column: 1 / -1;
  align-items: baseline;
  gap: 6px;
  padding: 7px 12px 8px;
  border-top: 1px solid var(--ce-divider);
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.workflow-pulse__coverage b {
  color: var(--ce-accent);
  font: 600 13px var(--ce-font-num);
}
.workflow-pulse__coverage time {
  margin-left: auto;
  color: var(--ce-text-dim);
  font: 10px var(--ce-font-num);
}
</style>

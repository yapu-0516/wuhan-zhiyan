<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { getAssessments, getMonitoringRuns, getMonitoringTasks, getReviews, getWorkOrders } from '@/api/workflow'
import { useCityEvents } from '@/composables/useCityEvents'
import { useRealtime } from '@/composables/useRealtime'
import PageShell from '@/components/pages/PageShell.vue'
import DataErrorNotice from '@/components/pages/DataErrorNotice.vue'
import TaskQueue from '@/components/workflow/TaskQueue.vue'
import AssessmentQueue from '@/components/workflow/AssessmentQueue.vue'
import OrderBoard from '@/components/workflow/OrderBoard.vue'
import ReviewBoard from '@/components/workflow/ReviewBoard.vue'
import type { Assessment, MonitoringRun, MonitoringTask, ReviewRecord, WorkOrder } from '@/types/workflow'

export type WorkflowSection = 'tasks' | 'assessment' | 'orders' | 'reviews'
const props = defineProps<{ section: WorkflowSection }>()

const router = useRouter()
const eventStore = useCityEvents()
const { events, loaded: eventsLoaded } = eventStore
const realtime = useRealtime()
const tasks = ref<MonitoringTask[]>([])
const runs = ref<MonitoringRun[]>([])
const assessments = ref<Assessment[]>([])
const orders = ref<WorkOrder[]>([])
const reviews = ref<ReviewRecord[]>([])
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')

const sections = [
  { key: 'tasks' as const, to: '/workflow/tasks', label: '监测任务', hint: '配置监测目标、区域、数据源与责任人' },
  { key: 'assessment' as const, to: '/workflow/assessment', label: '风险研判', hint: '核查线索、证据与影响，形成可追溯结论' },
  { key: 'orders' as const, to: '/workflow/orders', label: '协同处置', hint: '跟踪核查、处置与复核工单' },
  { key: 'reviews' as const, to: '/workflow/reviews', label: '复盘评估', hint: '沉淀过程评价、发现与改进建议' }
]
const current = computed(() => sections.find((item) => item.key === props.section) ?? sections[0])
const activeOrders = computed(() => orders.value.filter((item) => !['verified', 'cancelled'].includes(item.status)).length)
const trace = computed(() => [
  { key: 'tasks', label: '监测任务', value: tasks.value.length, to: '/workflow/tasks' },
  { key: 'runs', label: '运行记录', value: runs.value.length, to: '/workflow/tasks' },
  { key: 'events', label: '风险事件', value: events.value.length, to: '/event-center' },
  { key: 'assessment', label: '研判记录', value: assessments.value.length, to: '/workflow/assessment' },
  { key: 'orders', label: '活跃工单', value: activeOrders.value, to: '/workflow/orders' },
  { key: 'reviews', label: '复盘记录', value: reviews.value.length, to: '/workflow/reviews' }
])

async function load(silent = false) {
  if (!silent) loading.value = true
  error.value = ''
  const results = await Promise.allSettled([
    getMonitoringTasks(),
    getMonitoringRuns(),
    getAssessments(),
    getWorkOrders(),
    getReviews(),
    eventsLoaded.value ? Promise.resolve() : eventStore.loadFromApi()
  ])
  const failed = results.find((item) => item.status === 'rejected')
  if (results[0].status === 'fulfilled') tasks.value = results[0].value
  if (results[1].status === 'fulfilled') runs.value = results[1].value
  if (results[2].status === 'fulfilled') assessments.value = results[2].value
  if (results[3].status === 'fulfilled') orders.value = results[3].value
  if (results[4].status === 'fulfilled') reviews.value = results[4].value
  if (failed?.status === 'rejected') error.value = (failed.reason as Error)?.message || '业务数据加载失败'
  loading.value = false
}

async function refresh() {
  refreshing.value = true
  await load(true)
  refreshing.value = false
}

function locate(eventId: string) {
  void router.push({ path: '/dashboard', query: { eventId } })
}

onMounted(() => {
  realtime.start()
  void load()
})
</script>

<template>
  <PageShell title="业务闭环" :hint="current.hint" banner-detail="离线状态可浏览记录，新增和状态变更需要后端服务。">
    <template #actions>
      <el-button :icon="Refresh" :loading="refreshing" @click="refresh">刷新</el-button>
    </template>

    <DataErrorNotice v-if="error" :message="error" :busy="refreshing" @retry="refresh" />

    <nav class="workflow-nav" aria-label="业务闭环工作区">
      <RouterLink
        v-for="item in sections"
        :key="item.key"
        :to="item.to"
        :class="{ active: section === item.key }"
      >
        <span>{{ item.label }}</span>
        <small>{{ item.hint }}</small>
      </RouterLink>
    </nav>

    <section class="trace" aria-label="业务记录链">
      <template v-for="(item, index) in trace" :key="item.key">
        <RouterLink :to="item.to" class="trace-node" :class="{ active: item.key === section }">
          <span>{{ item.label }}</span>
          <b class="ce-num">{{ item.value }}</b>
        </RouterLink>
        <i v-if="index < trace.length - 1" aria-hidden="true" />
      </template>
    </section>

    <div v-loading="loading" class="workspace">
      <TaskQueue
        v-if="section === 'tasks'"
        :tasks="tasks"
        :runs="runs"
        @refresh="refresh"
      />
      <AssessmentQueue
        v-else-if="section === 'assessment'"
        :events="events"
        :assessments="assessments"
        :runs="runs"
        @refresh="refresh"
        @locate="locate"
      />
      <OrderBoard
        v-else-if="section === 'orders'"
        :events="events"
        :assessments="assessments"
        :orders="orders"
        @refresh="refresh"
      />
      <ReviewBoard
        v-else
        :reviews="reviews"
        :events="events"
        :tasks="tasks"
        @refresh="refresh"
      />
    </div>
  </PageShell>
</template>

<style scoped>
.workflow-nav {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  overflow: hidden;
  border: 1px solid var(--ce-panel-border);
  background: var(--ce-divider);
}
.workflow-nav a {
  min-width: 0;
  padding: 12px 14px;
  color: var(--ce-text-dim);
  text-decoration: none;
  background: var(--ce-panel-solid);
}
.workflow-nav a:hover,
.workflow-nav a.active {
  color: var(--ce-text-strong);
  background: #1d2226;
}
.workflow-nav a.active {
  box-shadow: inset 0 -2px var(--ce-accent);
}
.workflow-nav span,
.workflow-nav small {
  display: block;
}
.workflow-nav span {
  font-size: 14px;
  font-weight: 600;
}
.workflow-nav small {
  margin-top: 3px;
  overflow: hidden;
  color: var(--ce-text-faint);
  font-size: 11.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trace {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border: 1px solid var(--ce-panel-border);
  background: var(--ce-panel-solid);
}
.trace > i {
  flex: 1;
  height: 1px;
  background: var(--ce-divider);
}
.trace > i::after {
  display: block;
  width: 5px;
  height: 5px;
  margin-top: -2px;
  margin-left: auto;
  border-top: 1px solid var(--ce-text-faint);
  border-right: 1px solid var(--ce-text-faint);
  content: '';
  transform: rotate(45deg);
}
.trace-node {
  flex: none;
  min-width: 92px;
  padding: 4px 8px;
  color: var(--ce-text-dim);
  text-align: center;
  text-decoration: none;
}
.trace-node span,
.trace-node b {
  display: block;
}
.trace-node span {
  font-size: 11px;
}
.trace-node b {
  margin-top: 2px;
  color: var(--ce-text-strong);
  font-size: 20px;
}
.trace-node:hover,
.trace-node.active {
  color: var(--ce-text-strong);
}
.trace-node.active b {
  color: var(--ce-accent);
}
.workspace {
  min-height: 520px;
}
@media (max-width: 900px) {
  .workflow-nav {
    grid-template-columns: 1fr 1fr;
  }
  .trace {
    overflow-x: auto;
  }
  .trace > i {
    min-width: 18px;
  }
}
@media (max-width: 560px) {
  .workflow-nav small {
    display: none;
  }
  .trace {
    padding-inline: 8px;
  }
  .trace-node {
    min-width: 72px;
  }
}
</style>

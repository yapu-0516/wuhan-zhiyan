<script setup lang="ts">
// 事件中心 —— 城市事件的运营中枢
// KPI 筛选 + 多维过滤 + 排序分页表格 + 详情/处置抽屉 + 人工上报。
// 数据取自 useCityEvents 共享 store（WebSocket 实时增量），路由 ?id=E0001 可直接打开详情抽屉。
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, Search, RefreshLeft } from '@element-plus/icons-vue'
import { useCityEvents } from '@/composables/useCityEvents'
import { todayPrefix } from '@/composables/pages/format'
import PageShell from '@/components/pages/PageShell.vue'
import KpiCard from '@/components/pages/KpiCard.vue'
import EventTable, { type SortState } from '@/components/pages/EventTable.vue'
import EventDrawer from '@/components/pages/EventDrawer.vue'
import EventCreateDialog from '@/components/pages/EventCreateDialog.vue'
import DataErrorNotice from '@/components/pages/DataErrorNotice.vue'
import type { CityEvent, EventStatus, EventType, Severity } from '@/types/event'
import {
  EVENT_STATUS_COLOR,
  EVENT_STATUS_LABEL,
  EVENT_TYPES,
  EVENT_TYPE_META,
  SEVERITY_META
} from '@/types/event'

const route = useRoute()
const router = useRouter()
const store = useCityEvents()
const { events, stats, error: loadError } = store

// ---------- 筛选状态（与 URL query 双向同步，刷新/分享/后退不丢失） ----------
type StatusFilter = 'all' | EventStatus
const STATUS_VALUES: StatusFilter[] = ['all', 'pending', 'monitoring', 'processing', 'resolved']
const FILTER_KEYS = ['type', 'status', 'sev', 'kw', 'active', 'today'] as const
const SEVERITY_VALUES = Object.keys(SEVERITY_META) as Severity[]

function queryText(v: unknown): string {
  if (typeof v === 'string') return v
  if (Array.isArray(v) && typeof v[0] === 'string') return v[0]
  return ''
}

function initialType(): EventType | '' {
  const t = queryText(route.query.type)
  return EVENT_TYPES.includes(t as EventType) ? (t as EventType) : ''
}

const typeFilter = ref<EventType | ''>(initialType())
const statusFilter = ref<StatusFilter>(
  STATUS_VALUES.includes(queryText(route.query.status) as StatusFilter)
    ? (queryText(route.query.status) as StatusFilter)
    : 'all'
)
const severityFilter = ref<Severity | ''>(
  SEVERITY_VALUES.includes(queryText(route.query.sev) as Severity) ? (queryText(route.query.sev) as Severity) : ''
)
const keyword = ref(queryText(route.query.kw))
const activeOnly = ref(queryText(route.query.active) === '1')
const todayOnly = ref(queryText(route.query.today) === '1')
const sort = reactive<SortState>({ prop: 'timestamp', order: 'descending' })
const page = ref(1)
const pageSize = ref(20)
const refreshing = ref(false)
const createVisible = ref(false)

/** 当前筛选 → URL query（空值不写入） */
function filterQuery(): Record<string, string> {
  const q: Record<string, string> = {}
  if (typeFilter.value) q.type = typeFilter.value
  if (statusFilter.value !== 'all') q.status = statusFilter.value
  if (severityFilter.value) q.sev = severityFilter.value
  if (keyword.value.trim()) q.kw = keyword.value.trim()
  if (activeOnly.value) q.active = '1'
  if (todayOnly.value) q.today = '1'
  return q
}

let queryTimer: number | undefined
let applyingQuery = false

function syncQuery() {
  if (applyingQuery) return
  const query: Record<string, string | string[]> = { ...route.query } as Record<string, string | string[]>
  FILTER_KEYS.forEach((k) => delete query[k])
  Object.assign(query, filterQuery())
  void router.replace({ query })
}

/** URL query → 筛选状态（浏览器前进/后退、外部链接） */
function applyQuery() {
  const nextType = initialType()
  const status = queryText(route.query.status)
  const nextStatus = STATUS_VALUES.includes(status as StatusFilter) ? (status as StatusFilter) : 'all'
  const sev = queryText(route.query.sev)
  const nextSev = SEVERITY_VALUES.includes(sev as Severity) ? (sev as Severity) : ''
  const nextKw = queryText(route.query.kw)
  const nextActive = queryText(route.query.active) === '1'
  const nextToday = queryText(route.query.today) === '1'
  if (
    nextType === typeFilter.value &&
    nextStatus === statusFilter.value &&
    nextSev === severityFilter.value &&
    nextKw === keyword.value &&
    nextActive === activeOnly.value &&
    nextToday === todayOnly.value
  ) {
    return
  }
  applyingQuery = true
  typeFilter.value = nextType
  statusFilter.value = nextStatus
  severityFilter.value = nextSev
  keyword.value = nextKw
  activeOnly.value = nextActive
  todayOnly.value = nextToday
  applyingQuery = false
}

watch(
  () => route.query,
  () => applyQuery(),
  { deep: true }
)

// 筛选变化后写入 URL（关键词输入做 300ms 防抖，避免频繁替换历史记录）
watch([typeFilter, statusFilter, severityFilter, keyword, activeOnly, todayOnly], () => {
  window.clearTimeout(queryTimer)
  queryTimer = window.setTimeout(syncQuery, 300)
})

onBeforeUnmount(() => window.clearTimeout(queryTimer))

const todayCount = computed(() => {
  const prefix = todayPrefix()
  return events.value.filter((e) => e.timestamp.startsWith(prefix)).length
})

const filtered = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  const prefix = todayPrefix()
  return events.value.filter((e) => {
    if (typeFilter.value && e.event_type !== typeFilter.value) return false
    if (statusFilter.value !== 'all' && e.status !== statusFilter.value) return false
    if (severityFilter.value && e.severity !== severityFilter.value) return false
    if (activeOnly.value && e.status === 'resolved') return false
    if (todayOnly.value && !e.timestamp.startsWith(prefix)) return false
    if (q) {
      const hay = `${e.id} ${e.name} ${e.address} ${e.district} ${e.grid} ${e.assignee ?? ''}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })
})

const sorted = computed(() => {
  const dir = sort.order === 'ascending' ? 1 : -1
  const key = (e: CityEvent): number =>
    sort.prop === 'severity' ? SEVERITY_META[e.severity].rank : sort.prop === 'confidence' ? e.confidence : 0
  return [...filtered.value].sort((a, b) => {
    let d = 0
    if (sort.prop === 'timestamp') d = a.timestamp.localeCompare(b.timestamp)
    else d = key(a) - key(b)
    if (d === 0) d = a.timestamp.localeCompare(b.timestamp) || a.id.localeCompare(b.id)
    return d * dir
  })
})

const pageRows = computed(() => sorted.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
const hasFilter = computed(
  () =>
    !!typeFilter.value ||
    statusFilter.value !== 'all' ||
    !!severityFilter.value ||
    !!keyword.value.trim() ||
    activeOnly.value ||
    todayOnly.value
)

watch([typeFilter, statusFilter, severityFilter, keyword, activeOnly, todayOnly, pageSize], () => {
  page.value = 1
})
// 数据量缩小导致当前页越界时回退
watch(
  () => sorted.value.length,
  (n) => {
    const maxPage = Math.max(1, Math.ceil(n / pageSize.value))
    if (page.value > maxPage) page.value = maxPage
  }
)
// "仅看活跃"与"已办结"互斥
watch(activeOnly, (on) => {
  if (on && statusFilter.value === 'resolved') statusFilter.value = 'all'
})
watch(statusFilter, (s) => {
  if (s === 'resolved') activeOnly.value = false
})

function resetFilters() {
  typeFilter.value = ''
  statusFilter.value = 'all'
  severityFilter.value = ''
  keyword.value = ''
  activeOnly.value = false
  todayOnly.value = false
}

// ---------- KPI ----------
const kpis = computed(() => [
  { key: 'all', label: '全部事件', value: stats.value.total, color: '#4fc3f7', icon: '📋', hint: `活跃 ${stats.value.active} · 已办结 ${stats.value.byStatus.resolved}` },
  { key: 'pending', label: EVENT_STATUS_LABEL.pending, value: stats.value.byStatus.pending, color: EVENT_STATUS_COLOR.pending, icon: '🔔', hint: '等待人工核查确认' },
  { key: 'monitoring', label: EVENT_STATUS_LABEL.monitoring, value: stats.value.byStatus.monitoring, color: EVENT_STATUS_COLOR.monitoring, icon: '👁️', hint: '持续观察中' },
  { key: 'processing', label: EVENT_STATUS_LABEL.processing, value: stats.value.byStatus.processing, color: EVENT_STATUS_COLOR.processing, icon: '🚨', hint: '已派单处置' },
  { key: 'resolved', label: EVENT_STATUS_LABEL.resolved, value: stats.value.byStatus.resolved, color: EVENT_STATUS_COLOR.resolved, icon: '✅', hint: '已闭环办结' },
  { key: 'today', label: '今日新增', value: todayCount.value, color: '#9b8fff', icon: '🆕', hint: todayPrefix() }
])

function kpiActive(key: string): boolean {
  if (key === 'today') return todayOnly.value
  if (key === 'all') return statusFilter.value === 'all' && !todayOnly.value
  return statusFilter.value === key
}

function onKpi(key: string) {
  if (key === 'today') {
    todayOnly.value = !todayOnly.value
    return
  }
  todayOnly.value = false
  statusFilter.value = key === 'all' || statusFilter.value === key ? 'all' : (key as EventStatus)
}

const statusOptions = computed(() => [
  { label: '全部', value: 'all', count: stats.value.total },
  ...(['pending', 'monitoring', 'processing', 'resolved'] as EventStatus[]).map((s) => ({
    label: EVENT_STATUS_LABEL[s],
    value: s,
    count: stats.value.byStatus[s]
  }))
])

const severityOptions = (Object.keys(SEVERITY_META) as Severity[])
  .sort((a, b) => SEVERITY_META[b].rank - SEVERITY_META[a].rank)
  .map((k) => ({ value: k, label: SEVERITY_META[k].label, color: SEVERITY_META[k].color }))

// ---------- 实时高亮 ----------
const flash = reactive<Record<string, 'new' | 'updated'>>({})
const seen = new Map<string, string>()
const timers = new Set<number>()

function mark(id: string, kind: 'new' | 'updated') {
  flash[id] = kind
  const t = window.setTimeout(() => {
    delete flash[id]
    timers.delete(t)
  }, 4200)
  timers.add(t)
}

function diffFlash(initial = false) {
  for (const e of events.value) {
    const prev = seen.get(e.id)
    if (!initial) {
      if (prev === undefined) mark(e.id, 'new')
      else if (prev !== e.updated_at) mark(e.id, 'updated')
    }
    seen.set(e.id, e.updated_at)
  }
}

watch(
  () => [events.value.length, store.revision.value],
  () => diffFlash(),
  { flush: 'post' }
)

onMounted(() => diffFlash(true))
onBeforeUnmount(() => timers.forEach((t) => window.clearTimeout(t)))

// ---------- 排序 / 抽屉 / 定位 ----------
function onSort(s: SortState) {
  sort.prop = s.prop
  sort.order = s.order
  page.value = 1
}

const drawerId = computed(() => (typeof route.query.id === 'string' ? route.query.id : ''))
const drawerOpen = computed(() => !!drawerId.value)

function openDetail(row: CityEvent) {
  void router.replace({ query: { ...route.query, id: row.id } })
}
function onDrawerVisible(v: boolean) {
  if (v) return
  const q = { ...route.query }
  delete q.id
  void router.replace({ query: q })
}
function locate(row: CityEvent) {
  void router.push({ path: '/dashboard', query: { eventId: row.id } })
}

async function refresh() {
  refreshing.value = true
  try {
    await store.loadFromApi()
    if (loadError.value) {
      ElMessage.error(`事件刷新失败：${loadError.value}`)
    } else {
      diffFlash(true)
      ElMessage.success('事件列表已刷新')
    }
  } finally {
    refreshing.value = false
  }
}

function onCreated(ev: CityEvent) {
  seen.set(ev.id, ev.updated_at)
  mark(ev.id, 'new')
  // 新上报的事件固定回到"最新优先"视图，确保能看到
  sort.prop = 'timestamp'
  sort.order = 'descending'
  page.value = 1
}
</script>

<template>
  <PageShell title="事件中心" hint="汇聚火灾、交通拥堵、建筑异常、内涝积水四类城市事件，支持核查、派单、办结全流程闭环处置" banner-detail="处置操作仅在本地生效。">
    <template #actions>
      <el-button :icon="Refresh" :loading="refreshing" @click="refresh">刷新</el-button>
      <el-button type="primary" :icon="Plus" @click="createVisible = true">上报事件</el-button>
    </template>

    <!-- 加载失败提示（与“暂无数据”区分） -->
    <DataErrorNotice v-if="loadError" :message="loadError" :busy="refreshing" @retry="refresh" />

    <!-- KPI -->
    <section class="kpis">
      <KpiCard
        v-for="k in kpis"
        :key="k.key"
        :label="k.label"
        :value="k.value"
        :color="k.color"
        :icon="k.icon"
        :hint="k.hint"
        :active="kpiActive(k.key)"
        clickable
        @click="onKpi(k.key)"
      />
    </section>

    <!-- 过滤工具栏 -->
    <section class="cp-panel toolbar">
      <el-select v-model="typeFilter" clearable placeholder="全部类型" class="toolbar__type" popper-class="cp-popper">
        <template #prefix>{{ typeFilter ? EVENT_TYPE_META[typeFilter].icon : '🗂️' }}</template>
        <el-option v-for="t in EVENT_TYPES" :key="t" :value="t" :label="EVENT_TYPE_META[t].label">
          <span class="opt">
            <span>{{ EVENT_TYPE_META[t].icon }}</span>
            <span :style="{ color: EVENT_TYPE_META[t].color }">{{ EVENT_TYPE_META[t].label }}</span>
            <em>{{ stats.byType[t] }}</em>
          </span>
        </el-option>
      </el-select>

      <el-segmented v-model="statusFilter" :options="statusOptions" class="toolbar__status">
        <template #default="{ item }">
          <span class="seg">{{ item.label }}<em>{{ item.count }}</em></span>
        </template>
      </el-segmented>

      <el-select v-model="severityFilter" clearable placeholder="全部等级" class="toolbar__sev" popper-class="cp-popper">
        <el-option v-for="s in severityOptions" :key="s.value" :value="s.value" :label="s.label">
          <span class="opt"><i class="cp-dot" :style="{ '--c': s.color }"></i>{{ s.label }}</span>
        </el-option>
      </el-select>

      <el-input v-model="keyword" clearable placeholder="搜索编号 / 名称 / 地址 / 网格 / 处置单位" :prefix-icon="Search" class="toolbar__kw" />

      <el-switch v-model="activeOnly" inline-prompt active-text="活跃" inactive-text="全部" />
      <span class="toolbar__swlabel">仅看活跃</span>

      <el-button v-if="hasFilter" link type="primary" :icon="RefreshLeft" @click="resetFilters">重置筛选</el-button>
      <span class="toolbar__count">命中 <b>{{ filtered.length }}</b> / {{ stats.total }}</span>
    </section>

    <!-- 事件表格 -->
    <section class="cp-panel table-panel">
      <EventTable
        v-model:page="page"
        v-model:page-size="pageSize"
        :rows="pageRows"
        :total="sorted.length"
        :sort="sort"
        :flash="flash"
        :has-filter="hasFilter"
        @sort="onSort"
        @open="openDetail"
        @locate="locate"
        @reset="resetFilters"
        @create="createVisible = true"
      />
    </section>

    <EventDrawer :model-value="drawerOpen" :event-id="drawerId" @update:model-value="onDrawerVisible" />
    <EventCreateDialog v-model="createVisible" @created="onCreated" />
  </PageShell>
</template>

<style scoped>
.kpis {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 1379px) {
  .kpis {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px 14px;
  padding: 12px 16px;
}
.toolbar__type {
  width: 160px;
}
.toolbar__sev {
  width: 150px;
}
.toolbar__kw {
  flex: 1 1 260px;
  min-width: 220px;
  max-width: 460px;
}
.toolbar__swlabel {
  margin-left: -6px;
  font-size: 12.5px;
  color: var(--ce-text-dim, #8aa3c4);
}
.toolbar__count {
  margin-left: auto;
  font-size: 12.5px;
  color: var(--ce-text-dim, #8aa3c4);
}
.toolbar__count b {
  padding: 0 2px;
  color: var(--ce-accent, #4fc3f7);
  font-weight: 600;
}
.opt {
  display: flex;
  align-items: center;
  gap: 8px;
}
.opt em {
  margin-left: auto;
  font-style: normal;
  font-size: 12px;
  color: #6f89aa;
}
.seg {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.seg em {
  font-style: normal;
  font-size: 11px;
  opacity: 0.65;
}
.table-panel {
  flex: 1 0 480px;
  display: flex;
  flex-direction: column;
  min-height: 480px;
  overflow: hidden;
}
</style>

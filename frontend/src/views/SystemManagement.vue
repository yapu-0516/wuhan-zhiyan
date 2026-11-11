<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Bell, Connection, DataAnalysis, Document, Grid, Monitor, Refresh, View } from '@element-plus/icons-vue'
import { API_BASE } from '@/config/api'
import { apiState } from '@/api/http'
import PageShell from '@/components/pages/PageShell.vue'
import KpiCard from '@/components/pages/KpiCard.vue'
import EChart from '@/components/charts/EChart.vue'
import type { EChartsCoreOption } from 'echarts/core'
import {
  getAuditLogs,
  getNotifications,
  getResponsibilityGrids,
  getSlaSummary,
  getServiceStatus,
  getReviewStats,
  getTraceabilityGraph,
  patchRuntimeConfig,
  markAllNotificationsRead,
  markNotificationRead,
  patchResponsibilityGrid
} from '@/api/support'
import { useOperator } from '@/composables/useOperator'
import { getSpatialFeature, patchSpatialFeature } from '@/api/geo'
import type {
  AuditLogRecord,
  NotificationRecord,
  ResponsibilityGrid,
  ReviewStats,
  ServiceStatus,
  SlaSummary,
  TraceabilityGraph
} from '@/types/support'
import { NOTIFICATION_META, OPERATOR_ROLE_META } from '@/types/support'
import type { OperatorAccount } from '@/types/support'
import { ORDER_STATUS_META } from '@/types/workflow'

type Section = 'identity' | 'notifications' | 'audit' | 'sla' | 'lineage' | 'status'

const { accounts, current, currentId, load: loadOperator, setCurrent } = useOperator()
const section = ref<Section>('identity')
const grids = ref<ResponsibilityGrid[]>([])
const notifications = ref<NotificationRecord[]>([])
const audit = ref<AuditLogRecord[]>([])
const sla = ref<SlaSummary | null>(null)
const serviceStatus = ref<ServiceStatus | null>(null)
const reviewStats = ref<ReviewStats | null>(null)
const lineage = ref<TraceabilityGraph | null>(null)
const lineageType = ref('')
const lineageId = ref('')
const lineageBusy = ref(false)
const auditDetailVisible = ref(false)
const auditDetail = ref<AuditLogRecord | null>(null)
const configForm = reactive({ task_pacing_sec: 0.6, workflow_interval_sec: 15, max_upload_mb: 20 })
const configBusy = ref(false)
const gridEditVisible = ref(false)
const editingGridId = ref('')
const gridForm = reactive({ organization: '', owner: '', contact: '', risk_types: '' })
const spatialType = ref<'building' | 'road'>('building')
const spatialId = ref('')
const spatialProperties = ref('{}')
const spatialGeometry = ref('{}')
const spatialBusy = ref(false)
const loading = ref(true)
const error = ref('')

const sections = [
  { key: 'identity' as const, label: '身份与网格', hint: '角色、组织与责任边界', icon: Grid },
  { key: 'notifications' as const, label: '站内提醒', hint: '待办、反馈与复核提醒', icon: Bell },
  { key: 'audit' as const, label: '操作审计', hint: '统一记录写操作与身份', icon: Document },
  { key: 'sla' as const, label: 'SLA 报表', hint: '响应、执行与复核时限', icon: DataAnalysis },
  { key: 'lineage' as const, label: '业务链路', hint: '数据到复盘的关系图', icon: Connection },
  { key: 'status' as const, label: '服务状态', hint: '数据库、调度与算法版本', icon: Monitor }
]

const unreadCount = computed(() => notifications.value.filter((item) => !item.is_read).length)
const overdueCount = computed(() => sla.value?.overdue_orders ?? 0)
const currentRole = computed(() =>
  current.value ? OPERATOR_ROLE_META[current.value.role] : { label: '未选择身份', color: '#8aa3c4' }
)
const lineageTypes = [
  { value: '', label: '全部对象' },
  { value: 'data_asset', label: '数据资源' },
  { value: 'monitoring_task', label: '监测任务' },
  { value: 'event', label: '风险事件' },
  { value: 'assessment', label: '风险研判' },
  { value: 'scenario_session', label: '情景会话' },
  { value: 'scenario_run', label: '推演结果' },
  { value: 'work_order', label: '处置工单' },
  { value: 'review', label: '复盘记录' }
]

const slaTrendOption = computed<EChartsCoreOption>(() => {
  const trend = sla.value?.trend ?? []
  return {
    grid: { left: 38, right: 18, top: 26, bottom: 28 },
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 12,
      itemHeight: 6,
      textStyle: { color: '#8aa3c4', fontSize: 11 }
    },
    xAxis: {
      type: 'category',
      data: trend.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: 'rgba(138,163,196,.25)' } },
      axisLabel: { color: '#71869f', fontSize: 10 }
    },
    yAxis: [
      {
        type: 'value',
        name: '工单',
        nameTextStyle: { color: '#71869f', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(138,163,196,.10)' } },
        axisLabel: { color: '#71869f', fontSize: 10 }
      },
      {
        type: 'value',
        name: '分钟',
        nameTextStyle: { color: '#71869f', fontSize: 10 },
        splitLine: { show: false },
        axisLabel: { color: '#71869f', fontSize: 10 }
      }
    ],
    series: [
      {
        name: '新增工单',
        type: 'bar',
        barMaxWidth: 18,
        data: trend.map((item) => item.total),
        itemStyle: { color: '#67c6df', borderRadius: [2, 2, 0, 0] }
      },
      {
        name: '超时',
        type: 'bar',
        barMaxWidth: 18,
        data: trend.map((item) => item.overdue),
        itemStyle: { color: '#e4777b', borderRadius: [2, 2, 0, 0] }
      },
      {
        name: '平均响应',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 5,
        data: trend.map((item) => item.avg_response_min),
        lineStyle: { color: '#72c39a', width: 2 },
        itemStyle: { color: '#72c39a' }
      }
    ]
  }
})

const lineageOption = computed<EChartsCoreOption>(() => {
  const nodes = lineage.value?.nodes ?? []
  const links = lineage.value?.edges ?? []
  const categories = [...new Set(nodes.map((item) => item.display_name))]
  return {
    tooltip: {
      formatter: (params: { dataType?: string; data?: Record<string, unknown> }) => {
        const data = params.data ?? {}
        if (params.dataType === 'edge') return String(data.relation ?? '业务关联')
        return [
          `<b>${String(data.label ?? '')}</b>`,
          `${String(data.display_name ?? '')} · ${String(data.entity_id ?? '')}`,
          String(data.summary ?? '')
        ].filter(Boolean).join('<br/>')
      }
    },
    legend: {
      bottom: 0,
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: '#8aa3c4', fontSize: 10 }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        top: 10,
        bottom: 28,
        categories: categories.map((name) => ({ name })),
        data: nodes.map((item) => ({
          id: item.id,
          name: item.label,
          category: categories.indexOf(item.display_name),
          symbolSize: item.entity_type === 'event' ? 19 : item.entity_type === 'work_order' ? 16 : 13,
          itemStyle: { color: item.color },
          label: { show: nodes.length <= 90, color: '#d7e3ef', fontSize: 9 },
          labelText: item.label,
          entity_id: item.entity_id,
          display_name: item.display_name,
          summary: item.summary
        })),
        links: links.map((item) => ({
          source: item.source,
          target: item.target,
          relation: item.relation
        })),
        force: { repulsion: 155, edgeLength: [48, 105], gravity: 0.08 },
        lineStyle: { color: 'source', opacity: 0.28, width: 1, curveness: 0.08 },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { opacity: 0.85, width: 2 },
          label: { show: true }
        }
      }
    ]
  }
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    await loadOperator(true)
    const [gridRows, noticeRows, auditRows, slaRow, lineageRow, statusRow, reviewStatsRow] = await Promise.all([
      getResponsibilityGrids(),
      getNotifications(),
      getAuditLogs(100),
      getSlaSummary(),
      getTraceabilityGraph(),
      getServiceStatus(),
      getReviewStats()
    ])
    grids.value = gridRows
    notifications.value = noticeRows
    audit.value = auditRows
    sla.value = slaRow
    lineage.value = lineageRow
    serviceStatus.value = statusRow
    reviewStats.value = reviewStatsRow
    configForm.task_pacing_sec = statusRow.task_pacing_sec
    configForm.workflow_interval_sec = statusRow.workflow_interval_sec
    configForm.max_upload_mb = statusRow.max_upload_mb
  } catch (e) {
    error.value = (e as Error).message || '系统管理数据加载失败'
  } finally {
    loading.value = false
  }
}

async function selectOperator(account: OperatorAccount) {
  if (account.status !== 'active') {
    ElMessage.warning('该身份已停用')
    return
  }
  setCurrent(account.id)
  ElMessage.success(`当前身份已切换为 ${account.name} · ${OPERATOR_ROLE_META[account.role].label}`)
}

function onOperatorChange(value: string) {
  const account = accounts.value.find((item) => item.id === value)
  if (account) void selectOperator(account)
}

async function readOne(item: NotificationRecord) {
  if (item.is_read) return
  const updated = await markNotificationRead(item.id)
  notifications.value = notifications.value.map((row) => (row.id === updated.id ? updated : row))
}

async function readAll() {
  const result = await markAllNotificationsRead()
  notifications.value = notifications.value.map((row) => ({ ...row, is_read: true }))
  ElMessage.success(`已将 ${result.updated} 条提醒标记为已读`)
}

function roleLabel(role: string): string {
  return OPERATOR_ROLE_META[role as keyof typeof OPERATOR_ROLE_META]?.label ?? role
}

function levelMeta(level: string) {
  return NOTIFICATION_META[level as keyof typeof NOTIFICATION_META] ?? NOTIFICATION_META.info
}

function orderStatus(status: string): string {
  return ORDER_STATUS_META[status as keyof typeof ORDER_STATUS_META]?.label ?? status
}

function deadline(row: { sla?: { overdue: boolean; remaining_min: number | null } }): string {
  if (!row.sla || (row.sla.remaining_min === null && !row.sla.overdue)) return '未设置时限'
  return row.sla.overdue ? `已超时 ${Math.abs(row.sla.remaining_min ?? 0)} 分钟` : `剩余 ${row.sla.remaining_min ?? 0} 分钟`
}

function openGridEdit(row: ResponsibilityGrid) {
  editingGridId.value = row.id
  gridForm.organization = row.organization
  gridForm.owner = row.owner
  gridForm.contact = row.contact
  gridForm.risk_types = row.risk_types.join(', ')
  gridEditVisible.value = true
}

async function saveGrid() {
  if (!editingGridId.value) return
  try {
    const updated = await patchResponsibilityGrid(editingGridId.value, {
      organization: gridForm.organization.trim(),
      owner: gridForm.owner.trim(),
      contact: gridForm.contact.trim(),
      risk_types: gridForm.risk_types.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean)
    })
    grids.value = grids.value.map((item) => (item.id === updated.id ? updated : item))
    gridEditVisible.value = false
    ElMessage.success(`${updated.name} 已更新`)
  } catch (error) {
    ElMessage.error((error as Error).message || '责任网格更新失败')
  }
}

async function loadSpatialFeature() {
  if (!spatialId.value.trim() || spatialBusy.value) return
  spatialBusy.value = true
  try {
    const feature = await getSpatialFeature(spatialType.value, spatialId.value.trim())
    spatialProperties.value = JSON.stringify(feature.properties, null, 2)
    spatialGeometry.value = JSON.stringify(feature.geometry, null, 2)
    ElMessage.success('空间对象已加载')
  } catch (error) {
    ElMessage.error((error as Error).message || '空间对象加载失败')
  } finally {
    spatialBusy.value = false
  }
}

async function saveSpatialFeature() {
  if (!spatialId.value.trim() || spatialBusy.value) return
  let properties: Record<string, unknown>
  let geometry: Record<string, unknown>
  try {
    properties = JSON.parse(spatialProperties.value) as Record<string, unknown>
    geometry = JSON.parse(spatialGeometry.value) as Record<string, unknown>
  } catch {
    ElMessage.warning('属性和几何必须是合法 JSON')
    return
  }
  spatialBusy.value = true
  try {
    await patchSpatialFeature(spatialType.value, spatialId.value.trim(), {
      properties,
      geometry
    })
    ElMessage.success('空间对象已保存并重新加载地图索引')
  } catch (error) {
    ElMessage.error((error as Error).message || '空间对象保存失败')
  } finally {
    spatialBusy.value = false
  }
}

async function saveRuntimeConfig() {
  configBusy.value = true
  try {
    serviceStatus.value = await patchRuntimeConfig({ ...configForm })
    ElMessage.success('本地运行配置已更新')
  } catch (error) {
    ElMessage.error((error as Error).message || '运行配置更新失败')
  } finally {
    configBusy.value = false
  }
}

function exportCsv(kind: 'audit' | 'sla-summary') {
  if (apiState.mode !== 'live') {
    ElMessage.warning('离线快照模式不支持导出，请启动后端服务')
    return
  }
  window.open(`${API_BASE}/support/${kind}/export`, '_blank', 'noopener')
}

function openAuditDetail(row: AuditLogRecord) {
  auditDetail.value = row
  auditDetailVisible.value = true
}

function formatPayload(value: Record<string, unknown>): string {
  return Object.keys(value ?? {}).length ? JSON.stringify(value, null, 2) : '—'
}

async function loadLineage() {
  if (lineageBusy.value) return
  lineageBusy.value = true
  try {
    lineage.value = await getTraceabilityGraph(lineageType.value, lineageId.value.trim(), 240)
    ElMessage.success(`已加载 ${lineage.value.stats.nodes} 个业务对象`)
  } catch (error) {
    ElMessage.error((error as Error).message || '业务链路加载失败')
  } finally {
    lineageBusy.value = false
  }
}

function exportLineage() {
  if (apiState.mode !== 'live') {
    ElMessage.warning('离线快照模式不支持导出，请启动后端服务')
    return
  }
  window.open(`${API_BASE}/traceability/export`, '_blank', 'noopener')
}

onMounted(() => void load())
</script>

<template>
  <PageShell title="系统管理" hint="角色、责任网格、站内提醒、操作审计和工单 SLA 的统一入口">
    <template #actions>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </template>

    <div v-if="error" class="support-error">{{ error }}</div>

    <div class="support-layout">
      <nav class="support-nav" aria-label="系统管理分区">
        <button
          v-for="item in sections"
          :key="item.key"
          type="button"
          :class="{ active: section === item.key }"
          @click="section = item.key"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>
            <b>{{ item.label }}</b>
            <small>{{ item.hint }}</small>
          </span>
          <em v-if="item.key === 'notifications' && unreadCount">{{ unreadCount }}</em>
          <em v-else-if="item.key === 'sla' && overdueCount">{{ overdueCount }}</em>
        </button>
      </nav>

      <section v-loading="loading" class="support-panel">
        <template v-if="section === 'identity'">
          <header class="panel-heading">
            <div>
              <span class="panel-kicker">当前操作身份</span>
              <h2>{{ current?.name || '未选择身份' }}</h2>
              <p>
                {{ current?.organization || '请选择演示身份' }} · {{ currentRole.label }}
              </p>
            </div>
            <el-select
              :model-value="currentId"
              class="identity-select"
              aria-label="切换当前操作身份"
              @update:model-value="onOperatorChange"
            >
              <el-option
                v-for="account in accounts"
                :key="account.id"
                :value="account.id"
                :disabled="account.status !== 'active'"
                :label="`${account.name} · ${roleLabel(account.role)}`"
              />
            </el-select>
          </header>

          <div class="account-grid">
            <button
              v-for="account in accounts"
              :key="account.id"
              type="button"
              class="account-card"
              :class="{ selected: account.id === currentId, disabled: account.status !== 'active' }"
              @click="selectOperator(account)"
            >
              <span class="account-avatar">{{ account.name.slice(0, 1) }}</span>
              <span class="account-info">
                <b>{{ account.name }}</b>
                <small>{{ account.organization }}</small>
                <em :style="{ color: OPERATOR_ROLE_META[account.role].color }">{{ roleLabel(account.role) }}</em>
              </span>
              <i v-if="account.id === currentId">当前</i>
            </button>
          </div>

          <section class="subpanel">
            <header class="subpanel-heading">
              <div>
                <h3>责任网格</h3>
                <p>地图上的事件、任务和工单按属地责任关系组织。</p>
              </div>
              <span>{{ grids.length }} 个网格</span>
            </header>
            <el-table :data="grids" row-key="id" class="support-table">
              <el-table-column label="网格" min-width="210">
                <template #default="{ row }">
                  <div class="grid-name">
                    <b>{{ (row as ResponsibilityGrid).name }}</b>
                    <small>{{ (row as ResponsibilityGrid).id }}</small>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="district" label="行政区" width="100" />
              <el-table-column prop="organization" label="责任单位" min-width="200" show-overflow-tooltip />
              <el-table-column prop="owner" label="责任人" width="100" />
              <el-table-column prop="contact" label="联系方式" width="120" />
              <el-table-column label="风险类型" min-width="170">
                <template #default="{ row }">
                  <span class="type-chips">
                    <i v-for="type in (row as ResponsibilityGrid).risk_types" :key="type">{{ type }}</i>
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="72" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openGridEdit(row as ResponsibilityGrid)">编辑</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
          <section class="subpanel spatial-maintenance">
            <header class="subpanel-heading">
              <div>
                <h3>空间对象维护</h3>
                <p>按对象编号修改建筑或道路属性与 GeoJSON 几何，保存后重新加载地图索引。</p>
              </div>
            </header>
            <div class="spatial-maintenance__tools">
              <el-select v-model="spatialType">
                <el-option value="building" label="建筑" />
                <el-option value="road" label="道路" />
              </el-select>
              <el-input v-model="spatialId" placeholder="对象编号，例如 B0001 / R001" />
              <el-button :loading="spatialBusy" @click="loadSpatialFeature">读取</el-button>
              <el-button type="primary" :loading="spatialBusy" @click="saveSpatialFeature">保存并发布</el-button>
            </div>
            <div class="spatial-maintenance__editors">
              <label>
                <span>属性 JSON</span>
                <el-input v-model="spatialProperties" type="textarea" :rows="7" />
              </label>
              <label>
                <span>几何 GeoJSON</span>
                <el-input v-model="spatialGeometry" type="textarea" :rows="7" />
              </label>
            </div>
          </section>
        </template>

        <template v-else-if="section === 'notifications'">
          <header class="subpanel-heading">
            <div>
              <h3>站内提醒</h3>
              <p>演示环境中的工单、研判和现场反馈统一进入此列表。</p>
            </div>
            <div class="heading-actions">
              <span>{{ unreadCount }} 条未读</span>
              <el-button size="small" :disabled="!unreadCount" @click="readAll">全部已读</el-button>
            </div>
          </header>
          <div v-if="!notifications.length" class="empty-state">暂时没有提醒</div>
          <button
            v-for="item in notifications"
            :key="item.id"
            type="button"
            class="notice-row"
            :class="{ unread: !item.is_read }"
            @click="readOne(item)"
          >
            <i class="notice-level" :style="{ '--c': levelMeta(item.level).color }" />
            <span class="notice-main">
              <b>{{ item.title }}</b>
              <small>{{ item.body }}</small>
            </span>
            <span class="notice-meta">
              <em>{{ levelMeta(item.level).label }}</em>
              <time>{{ item.created_at }}</time>
            </span>
          </button>
        </template>

        <template v-else-if="section === 'audit'">
          <header class="subpanel-heading">
            <div>
              <h3>跨模块操作审计</h3>
              <p>记录写请求、操作身份、关联对象与响应状态；读取操作不写入审计。</p>
            </div>
            <div class="heading-actions">
              <span>{{ audit.length }} 条</span>
              <el-button size="small" @click="exportCsv('audit')">导出 CSV</el-button>
            </div>
          </header>
          <el-table :data="audit" row-key="id" class="support-table">
            <el-table-column prop="created_at" label="时间" width="166" />
            <el-table-column prop="operator_name" label="操作人" width="120" />
            <el-table-column prop="role" label="角色" width="100">
              <template #default="{ row }">{{ roleLabel((row as AuditLogRecord).role) }}</template>
            </el-table-column>
            <el-table-column prop="action" label="动作" width="145" />
            <el-table-column label="对象" min-width="150">
              <template #default="{ row }">
                <span>{{ (row as AuditLogRecord).entity_type || '—' }}</span>
                <small class="entity-id">{{ (row as AuditLogRecord).entity_id }}</small>
              </template>
            </el-table-column>
            <el-table-column prop="status_code" label="状态" width="80" />
            <el-table-column prop="path" label="请求路径" min-width="220" show-overflow-tooltip />
            <el-table-column label="修改前后值" width="108" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" :icon="View" @click="openAuditDetail(row as AuditLogRecord)">
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <template v-else-if="section === 'sla'">
          <header class="subpanel-heading">
            <div>
              <h3>工单 SLA 报表</h3>
              <p>以状态流转时间计算响应、执行、复核和超时，不改变事件办结状态。</p>
            </div>
            <div class="heading-actions">
              <span>{{ sla?.total_orders ?? 0 }} 张工单</span>
              <el-button size="small" @click="exportCsv('sla-summary')">导出 CSV</el-button>
            </div>
          </header>
          <div class="sla-kpis">
            <KpiCard label="活跃工单" :value="sla?.active_orders ?? 0" unit="张" color="#67c6df" hint="尚未复核或取消" />
            <KpiCard label="超时工单" :value="sla?.overdue_orders ?? 0" unit="张" color="#e4777b" hint="需优先协调" />
            <KpiCard label="平均响应" :value="sla?.avg_response_min ?? '—'" unit="分钟" color="#72c39a" hint="创建到接单" />
            <KpiCard label="平均执行" :value="sla?.avg_execution_min ?? '—'" unit="分钟" color="#f0c050" hint="接单到完成" />
          </div>
          <section v-if="sla?.trend.length" class="trend-panel">
            <header class="subpanel-heading">
              <div>
                <h3>近 14 个业务日趋势</h3>
                <p>按工单创建日聚合新增量、当前超时量和平均接单响应。</p>
              </div>
              <span>{{ sla.trend.at(-1)?.date }}</span>
            </header>
            <EChart :option="slaTrendOption" style="height: 230px" />
          </section>
          <div class="sla-breakdowns">
            <section>
              <h4>按责任单位</h4>
              <div v-for="item in sla?.by_unit ?? []" :key="item.name">
                <span>{{ item.name }}</span>
                <b>{{ item.count }}</b>
                <em v-if="item.overdue">超时 {{ item.overdue }}</em>
              </div>
            </section>
            <section>
              <h4>按优先级</h4>
              <div v-for="item in sla?.by_priority ?? []" :key="item.name">
                <span>{{ item.name }}</span>
                <b>{{ item.count }}</b>
                <em v-if="item.overdue">超时 {{ item.overdue }}</em>
              </div>
            </section>
            <section>
              <h4>按场景</h4>
              <div v-for="item in sla?.by_scenario ?? []" :key="item.name">
                <span>{{ item.name }}</span>
                <b>{{ item.count }}</b>
                <em v-if="item.overdue">超时 {{ item.overdue }}</em>
              </div>
            </section>
          </div>
          <el-table :data="sla?.orders ?? []" row-key="id" class="support-table">
            <el-table-column label="工单" min-width="230">
              <template #default="{ row }">
                <div class="grid-name">
                  <b>{{ row.title }}</b>
                  <small>{{ row.id }} · {{ row.event_id }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="unit" label="责任单位" min-width="190" show-overflow-tooltip />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">{{ orderStatus(row.status) }}</template>
            </el-table-column>
            <el-table-column label="时限" width="135">
              <template #default="{ row }">
                <span :class="{ 'is-overdue': row.sla?.overdue }">{{ deadline(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="响应 / 执行 / 复核" min-width="170">
              <template #default="{ row }">
                <span class="metric-triplet">
                  {{ row.sla?.response_min ?? '—' }} / {{ row.sla?.execution_min ?? '—' }} / {{ row.sla?.review_min ?? '—' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <template v-else-if="section === 'lineage'">
          <header class="subpanel-heading">
            <div>
              <h3>统一业务关系图</h3>
              <p>从数据资源、监测任务和算法作业，经事件研判、情景推演和协同处置，追踪到复盘评估。</p>
            </div>
            <div class="heading-actions">
              <span>{{ lineage?.stats.nodes ?? 0 }} 个对象 · {{ lineage?.stats.edges ?? 0 }} 条关系</span>
              <el-button size="small" :loading="lineageBusy" @click="loadLineage">重新布局</el-button>
              <el-button size="small" @click="exportLineage">导出完整链路</el-button>
            </div>
          </header>
          <div class="lineage-tools">
            <el-select v-model="lineageType" aria-label="链路对象类型">
              <el-option v-for="item in lineageTypes" :key="item.value" :value="item.value" :label="item.label" />
            </el-select>
            <el-input
              v-model="lineageId"
              clearable
              :disabled="!lineageType"
              placeholder="输入对象编号，留空显示完整关系图"
              @keydown.enter="loadLineage"
            />
            <el-button type="primary" :loading="lineageBusy" @click="loadLineage">定位链路</el-button>
          </div>
          <div class="lineage-summary">
            <span><i />节点大小表示对象层级，连线表示业务来源或去向</span>
            <b v-if="lineage?.stats.truncated">当前展示最近 {{ lineage.stats.nodes }} / {{ lineage.stats.available_nodes }} 个对象</b>
            <b v-else>当前展示全部可追溯对象</b>
          </div>
          <div v-loading="lineageBusy" class="lineage-chart">
            <EChart v-if="lineage?.nodes.length" :option="lineageOption" style="height: 560px" />
            <el-empty v-else description="没有匹配的业务链路" />
          </div>
          <details v-if="lineage?.edges.length" class="lineage-ledger">
            <summary>关系清单 · {{ lineage.stats.edges }} 条</summary>
            <div v-for="edge in lineage.edges.slice(0, 120)" :key="edge.id">
              <span>{{ edge.source }}</span>
              <b>{{ edge.relation }}</b>
              <span>{{ edge.target }}</span>
            </div>
          </details>
        </template>

        <template v-else>
          <header class="subpanel-heading">
            <div>
              <h3>系统配置与服务状态</h3>
              <p>只展示当前服务可观测状态、本地调度配置和已注册算法版本。</p>
            </div>
            <span>数据库 {{ serviceStatus?.database || '—' }}</span>
          </header>
          <div class="sla-kpis">
            <KpiCard label="模拟器" :value="serviceStatus?.simulator_enabled ? '开启' : '关闭'" color="#67c6df" hint="本地事件模拟" />
            <KpiCard label="调度检查" :value="serviceStatus?.workflow_interval_sec ?? '—'" unit="秒" color="#72c39a" hint="周期任务扫描间隔" />
            <KpiCard label="超时工单" :value="serviceStatus?.overdue_orders ?? 0" unit="张" color="#e4777b" hint="当前需升级" />
            <KpiCard label="未读提醒" :value="serviceStatus?.unread_notifications ?? 0" unit="条" color="#f0c050" hint="站内通知" />
          </div>
          <div class="status-counts">
            <div>
              <b>{{ Object.values(serviceStatus?.task_counts ?? {}).reduce((sum, value) => sum + value, 0) }}</b>
              <span>AI 分析任务</span>
              <small v-for="(value, key) in serviceStatus?.task_counts ?? {}" :key="key">{{ key }} {{ value }}</small>
            </div>
            <div>
              <b>{{ Object.values(serviceStatus?.run_counts ?? {}).reduce((sum, value) => sum + value, 0) }}</b>
              <span>业务运行</span>
              <small v-for="(value, key) in serviceStatus?.run_counts ?? {}" :key="key">{{ key }} {{ value }}</small>
            </div>
            <div>
              <b>{{ Object.values(serviceStatus?.data_counts ?? {}).reduce((sum, value) => sum + value, 0) }}</b>
              <span>数据资源</span>
              <small v-for="(value, key) in serviceStatus?.data_counts ?? {}" :key="key">{{ key }} {{ value }}</small>
            </div>
          </div>
          <section class="subpanel">
            <header class="subpanel-heading">
              <div>
                <h3>复盘分类统计</h3>
                <p>真实事件、监测任务与演练复盘分开计数。</p>
              </div>
              <span>已确认 {{ reviewStats?.confirmed ?? 0 }} · 草稿 {{ reviewStats?.draft ?? 0 }}</span>
            </header>
            <div class="review-type-stats">
              <div v-for="item in reviewStats?.by_entity_type ?? []" :key="item.name">
                <b>{{ item.count }}</b>
                <span>{{ item.name }}</span>
                <small>确认 {{ item.confirmed }} / 草稿 {{ item.draft }}</small>
              </div>
            </div>
          </section>
          <section class="subpanel runtime-config">
            <header class="subpanel-heading">
              <div>
                <h3>本地运行配置</h3>
                <p>修改后立即影响新分析任务、上传限制和周期任务扫描；不写入外部配置中心。</p>
              </div>
            </header>
            <div class="runtime-config-grid">
              <label>
                <span>算法阶段节奏（秒）</span>
                <el-input-number v-model="configForm.task_pacing_sec" :min="0" :max="10" :step="0.1" />
              </label>
              <label>
                <span>周期任务扫描（秒）</span>
                <el-input-number v-model="configForm.workflow_interval_sec" :min="5" :max="3600" :step="5" />
              </label>
              <label>
                <span>单文件上传上限（MB）</span>
                <el-input-number v-model="configForm.max_upload_mb" :min="1" :max="500" />
              </label>
              <el-button type="primary" :loading="configBusy" @click="saveRuntimeConfig">保存本地配置</el-button>
            </div>
          </section>
          <section class="subpanel">
            <header class="subpanel-heading">
              <div>
                <h3>算法版本</h3>
                <p>来源：本地算法注册表。</p>
              </div>
              <span>{{ serviceStatus?.algorithms.length ?? 0 }} 个</span>
            </header>
            <el-table :data="serviceStatus?.algorithms ?? []" row-key="type" class="support-table">
              <el-table-column prop="type" label="场景" width="100" />
              <el-table-column prop="name" label="算法" min-width="160" />
              <el-table-column prop="version" label="版本" width="100" />
              <el-table-column prop="method" label="方法" min-width="260" show-overflow-tooltip />
            </el-table>
          </section>
        </template>
      </section>
    </div>

    <el-dialog v-model="gridEditVisible" title="维护责任网格" width="min(560px, 94vw)" append-to-body>
      <el-form label-position="top">
        <el-form-item label="责任单位">
          <el-input v-model="gridForm.organization" maxlength="96" />
        </el-form-item>
        <div class="grid-edit-row">
          <el-form-item label="责任人">
            <el-input v-model="gridForm.owner" maxlength="64" />
          </el-form-item>
          <el-form-item label="联系方式">
            <el-input v-model="gridForm.contact" maxlength="64" />
          </el-form-item>
        </div>
        <el-form-item label="风险类型">
          <el-input v-model="gridForm.risk_types" placeholder="fire, traffic, building, flood" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="gridEditVisible = false">取消</el-button>
        <el-button type="primary" @click="saveGrid">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="auditDetailVisible"
      title="操作审计修改前后值"
      class="audit-detail-dialog"
      width="min(820px, 95vw)"
      append-to-body
    >
      <template v-if="auditDetail">
        <div class="audit-detail-head">
          <b>{{ auditDetail.action }}</b>
          <span>{{ auditDetail.operator_name }} · {{ roleLabel(auditDetail.role) }}</span>
          <time>{{ auditDetail.created_at }}</time>
        </div>
        <p class="audit-detail-path">{{ auditDetail.method }} {{ auditDetail.path }}</p>
        <div class="audit-detail-grid">
          <label>
            <span>修改前</span>
            <pre>{{ formatPayload(auditDetail.before_data) }}</pre>
          </label>
          <label>
            <span>修改后</span>
            <pre>{{ formatPayload(auditDetail.after_data) }}</pre>
          </label>
        </div>
      </template>
    </el-dialog>
  </PageShell>
</template>

<style scoped>
:global(.audit-detail-dialog) {
  border: 1px solid var(--ce-panel-border);
  background: #10161d;
  box-shadow: 0 24px 72px rgba(0, 0, 0, 0.58);
}
:global(.audit-detail-dialog .el-dialog__title) {
  color: var(--ce-text-strong);
}
:global(.audit-detail-dialog .el-dialog__header),
:global(.audit-detail-dialog .el-dialog__body) {
  background: #10161d;
}
.support-layout {
  display: grid;
  grid-template-columns: 230px minmax(0, 1fr);
  gap: 14px;
  min-height: 650px;
}
.support-nav {
  align-self: start;
  border: 1px solid var(--ce-panel-border);
  background: var(--ce-panel-solid);
}
.support-nav button {
  position: relative;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 58px;
  padding: 8px 12px;
  border: 0;
  border-bottom: 1px solid var(--ce-divider);
  background: transparent;
  color: var(--ce-text-dim);
  text-align: left;
  cursor: pointer;
}
.support-nav button:last-child {
  border-bottom: 0;
}
.support-nav button:hover,
.support-nav button.active {
  color: var(--ce-text-strong);
  background: var(--ce-active);
}
.support-nav button.active::before {
  position: absolute;
  inset: 0 auto 0 0;
  width: 2px;
  background: var(--ce-accent);
  content: '';
}
.support-nav .el-icon {
  color: var(--ce-accent);
}
.support-nav b,
.support-nav small {
  display: block;
}
.support-nav b {
  font-size: 13px;
}
.support-nav small {
  margin-top: 3px;
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.support-nav em {
  min-width: 20px;
  padding: 2px 5px;
  border-radius: 9px;
  color: var(--ce-danger);
  background: rgba(228, 119, 123, 0.13);
  font-size: 10.5px;
  font-style: normal;
  text-align: center;
}
.support-panel {
  min-width: 0;
  min-height: 650px;
  padding: 18px;
  border: 1px solid var(--ce-panel-border);
  background: var(--ce-panel-solid);
}
.support-error {
  padding: 10px 12px;
  border-left: 2px solid var(--ce-danger);
  color: var(--ce-danger);
  background: rgba(228, 119, 123, 0.08);
}
.panel-heading,
.subpanel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.panel-kicker {
  color: var(--ce-accent);
  font-size: 11px;
}
.panel-heading h2 {
  margin: 5px 0 4px;
  color: var(--ce-text-strong);
  font-size: 24px;
  font-weight: 600;
}
.panel-heading p,
.subpanel-heading p {
  margin: 0;
  color: var(--ce-text-dim);
  font-size: 12px;
  line-height: 1.6;
}
.identity-select {
  width: 220px;
}
.account-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 20px 0;
}
.account-card {
  position: relative;
  display: flex;
  min-width: 0;
  gap: 10px;
  padding: 11px;
  border: 1px solid var(--ce-divider);
  background: transparent;
  color: var(--ce-text);
  text-align: left;
  cursor: pointer;
}
.account-card:hover,
.account-card.selected {
  border-color: var(--ce-accent);
  background: var(--ce-active);
}
.account-card.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.account-avatar {
  display: grid;
  flex: none;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 50%;
  color: var(--ce-accent);
  font-size: 14px;
}
.account-info {
  display: flex;
  min-width: 0;
  flex-direction: column;
}
.account-info b,
.account-info small,
.account-info em {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.account-info b {
  color: var(--ce-text-strong);
  font-size: 13px;
}
.account-info small {
  margin-top: 2px;
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.account-info em {
  margin-top: 4px;
  font-size: 10.5px;
  font-style: normal;
}
.account-card > i {
  position: absolute;
  top: 6px;
  right: 7px;
  color: var(--ce-accent);
  font-size: 10px;
  font-style: normal;
}
.subpanel {
  padding-top: 16px;
  border-top: 1px solid var(--ce-divider);
}
.subpanel-heading {
  align-items: center;
  margin-bottom: 12px;
}
.subpanel-heading h3 {
  margin: 0 0 3px;
  color: var(--ce-text-strong);
  font-size: 14px;
}
.subpanel-heading > span,
.heading-actions > span {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.heading-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.grid-name b,
.grid-name small,
.entity-id {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.grid-name b {
  color: var(--ce-text-strong);
  font-size: 12.5px;
}
.grid-name small,
.entity-id {
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.type-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}
.type-chips i {
  padding: 2px 5px;
  border: 1px solid var(--ce-divider);
  color: var(--ce-text-dim);
  font-size: 10px;
  font-style: normal;
}
.notice-row {
  display: grid;
  grid-template-columns: 5px minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  width: 100%;
  padding: 12px 0;
  border: 0;
  border-bottom: 1px solid var(--ce-divider);
  background: transparent;
  color: var(--ce-text);
  text-align: left;
  cursor: pointer;
}
.notice-row:hover {
  background: var(--ce-active);
}
.notice-level {
  align-self: stretch;
  border-radius: 3px;
  background: var(--c);
  opacity: 0.75;
}
.notice-main,
.notice-main b,
.notice-main small {
  display: block;
  min-width: 0;
}
.notice-main b {
  color: var(--ce-text-faint);
  font-size: 13px;
  font-weight: 500;
}
.notice-row.unread .notice-main b {
  color: var(--ce-text-strong);
  font-weight: 600;
}
.notice-main small {
  margin-top: 4px;
  overflow: hidden;
  color: var(--ce-text-dim);
  font-size: 12px;
  line-height: 1.55;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.notice-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.notice-meta em {
  color: var(--ce-text-dim);
  font-size: 10.5px;
  font-style: normal;
}
.notice-meta time {
  color: var(--ce-text-faint);
  font: 10.5px var(--ce-font-num);
}
.empty-state {
  padding: 48px 0;
  color: var(--ce-text-faint);
  font-size: 13px;
  text-align: center;
}
.sla-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.status-counts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 16px;
}
.status-counts > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 11px;
  border: 1px solid var(--ce-divider);
}
.status-counts b {
  color: var(--ce-text-strong);
  font: 600 22px var(--ce-font-num);
}
.status-counts span {
  color: var(--ce-text-dim);
  font-size: 12px;
}
.status-counts small {
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.review-type-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.review-type-stats > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px;
  border: 1px solid var(--ce-divider);
}
.review-type-stats b {
  color: var(--ce-text-strong);
  font: 600 20px var(--ce-font-num);
}
.review-type-stats span {
  color: var(--ce-text-dim);
  font-size: 12px;
}
.review-type-stats small {
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.runtime-config-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
  align-items: end;
  gap: 10px;
}
.runtime-config-grid label {
  display: grid;
  gap: 5px;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.runtime-config-grid :deep(.el-input-number) {
  width: 100%;
}
.sla-breakdowns {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 16px;
}
.sla-breakdowns section {
  padding: 10px;
  border: 1px solid var(--ce-divider);
}
.sla-breakdowns h4 {
  margin: 0 0 7px;
  color: var(--ce-text-strong);
  font-size: 12px;
}
.sla-breakdowns section > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 6px;
  padding: 4px 0;
  border-top: 1px solid var(--ce-divider);
  color: var(--ce-text-dim);
  font-size: 11px;
}
.sla-breakdowns span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sla-breakdowns b {
  color: var(--ce-text-strong);
  font-family: var(--ce-font-num);
}
.sla-breakdowns em {
  color: var(--ce-danger);
  font-style: normal;
}
.trend-panel {
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid var(--ce-divider);
  background: rgba(9, 20, 31, 0.42);
}
.trend-panel .subpanel-heading {
  margin-bottom: 2px;
}
.trend-panel h3 {
  margin: 0 0 3px;
  color: var(--ce-text-strong);
  font-size: 13px;
}
.lineage-tools {
  display: grid;
  grid-template-columns: 180px minmax(180px, 1fr) auto;
  gap: 8px;
  margin: 16px 0 8px;
}
.lineage-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 6px;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.lineage-summary span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.lineage-summary i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ce-accent);
  box-shadow: 0 0 10px var(--ce-accent);
}
.lineage-summary b {
  color: var(--ce-text-dim);
  font-weight: 500;
}
.lineage-chart {
  min-height: 560px;
  border: 1px solid var(--ce-divider);
  background:
    radial-gradient(circle at 50% 42%, rgba(62, 139, 173, 0.09), transparent 48%),
    rgba(7, 16, 25, 0.44);
}
.lineage-ledger {
  margin-top: 10px;
  border: 1px solid var(--ce-divider);
}
.lineage-ledger summary {
  padding: 9px 11px;
  color: var(--ce-text-dim);
  font-size: 11.5px;
  cursor: pointer;
}
.lineage-ledger > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 10px;
  padding: 6px 10px;
  border-top: 1px solid var(--ce-divider);
  color: var(--ce-text-faint);
  font: 10.5px var(--ce-font-num);
}
.lineage-ledger span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lineage-ledger b {
  color: var(--ce-accent);
  font-family: var(--ce-font);
  font-weight: 500;
}
.audit-detail-head {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ce-text-dim);
  font-size: 12px;
}
.audit-detail-head b {
  color: var(--ce-text-strong);
}
.audit-detail-head time {
  margin-left: auto;
  color: var(--ce-text-faint);
  font: 11px var(--ce-font-num);
}
.audit-detail-path {
  margin: 8px 0 12px;
  color: var(--ce-text-faint);
  font: 11px var(--ce-font-num);
}
.audit-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.audit-detail-grid label {
  display: grid;
  gap: 5px;
  color: var(--ce-text-dim);
  font-size: 11px;
}
.audit-detail-grid pre {
  min-height: 230px;
  max-height: 420px;
  margin: 0;
  padding: 10px;
  overflow: auto;
  border: 1px solid var(--ce-divider);
  color: #bfd2df;
  background: #0b1118;
  font: 11px/1.55 var(--ce-font-num);
  white-space: pre-wrap;
}
.grid-edit-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 12px;
}
.spatial-maintenance__tools {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr) auto auto;
  gap: 8px;
}
.spatial-maintenance__editors {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 10px;
}
.spatial-maintenance__editors label {
  display: grid;
  gap: 5px;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.metric-triplet {
  color: var(--ce-text-dim);
  font: 11.5px var(--ce-font-num);
}
.is-overdue {
  color: var(--ce-danger);
  font-weight: 600;
}
@media (max-width: 1100px) {
  .support-layout {
    grid-template-columns: 1fr;
  }
  .support-nav {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .support-nav button {
    border-right: 1px solid var(--ce-divider);
    border-bottom: 0;
  }
  .support-nav button:last-child {
    border-right: 0;
  }
  .account-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 700px) {
  .support-panel {
    min-height: 0;
    padding: 12px;
  }
  .support-nav {
    grid-template-columns: 1fr 1fr;
  }
  .support-nav button:nth-child(n + 3) {
    border-top: 1px solid var(--ce-divider);
  }
  .panel-heading,
  .subpanel-heading {
    flex-direction: column;
  }
  .identity-select {
    width: 100%;
  }
  .account-grid,
  .sla-kpis {
    grid-template-columns: 1fr 1fr;
  }
  .status-counts {
    grid-template-columns: 1fr;
  }
  .review-type-stats {
    grid-template-columns: 1fr;
  }
  .runtime-config-grid {
    grid-template-columns: 1fr;
  }
  .sla-breakdowns {
    grid-template-columns: 1fr;
  }
  .lineage-tools,
  .lineage-summary,
  .audit-detail-grid {
    grid-template-columns: 1fr;
  }
  .lineage-summary {
    display: grid;
  }
  .lineage-ledger > div {
    grid-template-columns: 1fr;
  }
  .grid-edit-row {
    grid-template-columns: 1fr;
  }
  .spatial-maintenance__tools,
  .spatial-maintenance__editors {
    grid-template-columns: 1fr;
  }
}
</style>

<script setup lang="ts">
// 城市总览（城市运行指挥中心大屏）
// 全屏三维数字孪生场景 + 左右 HUD 数据面板 + 顶部场景工具条 + 左下图例 + 一键演示字幕。
// 组件名 Dashboard 与 App.vue 中 <KeepAlive include="Dashboard"> 对应：切页时不销毁 Cesium Viewer。
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import CesiumViewer from '@/components/CesiumViewer.vue'
import HudPanel from '@/components/dashboard/HudPanel.vue'
import SafetyPanel from '@/components/dashboard/SafetyPanel.vue'
import KpiGrid from '@/components/dashboard/KpiGrid.vue'
import TypeRose from '@/components/dashboard/TypeRose.vue'
import TrendChart from '@/components/dashboard/TrendChart.vue'
import LiveFeed from '@/components/dashboard/LiveFeed.vue'
import DistrictRank from '@/components/dashboard/DistrictRank.vue'
import SensorPanel from '@/components/dashboard/SensorPanel.vue'
import SceneToolbar from '@/components/dashboard/SceneToolbar.vue'
import SceneLegend from '@/components/dashboard/SceneLegend.vue'
import TaskParsePanel from '@/components/pages/TaskParsePanel.vue'
import AssistantChatPanel from '@/components/pages/AssistantChatPanel.vue'
import CrowdSimulationPanel from '@/components/pages/CrowdSimulationPanel.vue'
import ScenarioWorkspace from '@/components/pages/ScenarioWorkspace.vue'
import DataErrorNotice from '@/components/pages/DataErrorNotice.vue'
import { useOverview } from '@/composables/useOverview'
import { useCityEvents } from '@/composables/useCityEvents'
import { useDemoBaseline } from '@/composables/useDemoBaseline'
import type { DemoTourHooks } from '@/composables/useDemoTour'
import { DEFAULT_BASEMAP, type BasemapKey } from '@/config/cesium'
import {
  DEFAULT_LAYERS,
  type EventTypeFilter,
  type LayerKey,
  type LayerVisibility,
  type TourFocus
} from '@/components/scene/types'
import { EVENT_TYPE_META, type CityEvent, type EventType } from '@/types/event'
import { hhmm, shortTime } from '@/utils/format'
import { apiState } from '@/api/http'
import { resetDemo, triggerScenario } from '@/api/system'

defineOptions({ name: 'Dashboard' })

const viewerRef = ref<InstanceType<typeof CesiumViewer> | null>(null)
const assistantRef = ref<InstanceType<typeof AssistantChatPanel> | null>(null)
const scenarioRef = ref<InstanceType<typeof ScenarioWorkspace> | null>(null)
const rootRef = ref<HTMLDivElement | null>(null)
const router = useRouter()

// 自然语言任务解析：工具条入口 + 弹窗（付费 API，仅在点击「解析」时触发）
const parseOpen = ref(false)
const assistantOpen = ref(false)
const crowdOpen = ref(false)
const scenarioOpen = ref(false)
const scenarioMapReview = ref(false)
const { calm: calmBaseline, demoEventIds, enterCalmBaseline, revealAnomalies, setDemoEventIds } = useDemoBaseline()
const assistantDemoQuestion = ref('')
let assistantSettled: (() => void) | null = null
let assistantTimer = 0
let resettingDemo = false
const crowdLayer = computed(() => viewerRef.value?.getCrowd() ?? null)
function openScenario() {
  scenarioMapReview.value = false
  scenarioOpen.value = true
}
function viewScenarioMap() {
  scenarioOpen.value = false
  scenarioMapReview.value = true
}
function reopenScenario() {
  scenarioMapReview.value = false
  scenarioOpen.value = true
}
function gotoScene(t: EventType) {
  parseOpen.value = false
  void router.push({ path: `/ai-analysis/${t}` })
}

// ---------------- 场景状态（工具条 / 图例 → CesiumViewer）
const layers = reactive<LayerVisibility>({ ...DEFAULT_LAYERS, effects: false, pois: false })
const sceneLayers = computed<LayerVisibility>(() => ({
  ...layers,
  events: calmBaseline.value || scenarioOpen.value || scenarioMapReview.value ? false : layers.events,
  pois: scenarioOpen.value || scenarioMapReview.value ? false : layers.pois
}))
const basemap = ref<BasemapKey>(DEFAULT_BASEMAP)
const autoTrack = ref(false)
const eventTypes = reactive<EventTypeFilter>({ fire: true, traffic: true, building: true, flood: true })
const showResolved = ref(false)
const focus = ref<TourFocus | null>(null)
const selectedEventId = ref<string | null>(null)
const monitored = ref<number | undefined>(undefined)

const touring = computed(() => viewerRef.value?.tourState?.running ?? false)

function onFineDistrictChange(active: boolean) {
  layers.buildingsFine = active
  viewerRef.value?.setBuildingRiskOnly(active)
}

async function toggleLayer(key: LayerKey) {
  layers[key] = !layers[key]
  if (layers[key] && key === 'buildingsFine') {
    ElMessage.info('正在加载城区精细建筑模型…')
    const ok = await viewerRef.value?.loadFineBuildingLayer()
    if (ok && layers.buildingsFine) {
      viewerRef.value?.setBuildingRiskOnly(true)
      layers.buildings = true
    } else if (!ok) {
      layers.buildingsFine = false
    }
  } else if (!layers[key] && key === 'buildingsFine') {
    viewerRef.value?.setBuildingRiskOnly(false)
    layers.buildings = true
  }
}
function toggleType(t: EventType) {
  eventTypes[t] = !eventTypes[t]
}
function goHome() {
  viewerRef.value?.closePanels()
  void viewerRef.value?.flyHome()
}
async function toggleTour() {
  const v = viewerRef.value
  if (!v) return
  if (v.tourState.running) v.stopTour()
  else {
    if (resettingDemo) return
    resettingDemo = true
    enterCalmBaseline()
    setDemoEventIds([])
    scenarioOpen.value = false
    scenarioMapReview.value = false
    assistantOpen.value = false
    v.closePanels()
    v.getCrowd()?.startAmbient(420, 120)
    leftOpen.value = true
    rightOpen.value = true
    try {
      if (apiState.mode === 'live') {
        await resetDemo()
        await loadEvents()
      }
      await v.startTour()
    } catch (e) {
      console.warn('[demo] 恢复演示数据失败，继续使用当前数据', e)
      ElMessage.warning('演示数据恢复失败，将继续使用当前数据')
      await v.startTour()
    } finally {
      resettingDemo = false
    }
  }
}
function locateEvent(id: string) {
  void viewerRef.value?.flyToEvent(id, { open: true })
}
function onSceneReady() {
  monitored.value = viewerRef.value?.sceneStats().monitored
}
function onSelection(p: { kind: 'event' | 'building' | null; id: string | null }) {
  selectedEventId.value = p.kind === 'event' ? p.id : null
}

// ---------------- 数据
const { data: overview, remote, resume, pause, lastRefresh } = useOverview()
const { events, error: eventsError, loadFromApi: loadEvents } = useCityEvents()
const eventsLoading = ref(false)

async function retryEvents() {
  eventsLoading.value = true
  try {
    await loadEvents()
    monitored.value = viewerRef.value?.sceneStats().monitored
  } finally {
    eventsLoading.value = false
  }
}

const criticalActive = computed(
  () =>
    events.value.filter((e) => e.status !== 'resolved' && (e.severity === 'critical' || e.severity === 'high')).length
)
const updatedText = computed(() => {
  void lastRefresh.value
  return hhmm(overview.value.updated_at)
})
// 离线时趋势来自快照，需标注数据截止时间，避免被误读为“近 24 小时”
const trendSub = computed(() => {
  if (apiState.mode === 'live' || !remote.value?.trend?.length) return 'TREND'
  return `截至 ${shortTime(remote.value.updated_at)}`
})

const demoEvents = computed(() => {
  if (!demoEventIds.value.length) return []
  const ids = new Set(demoEventIds.value)
  return events.value.filter((event) => ids.has(event.id))
})

const calmOverview = computed(() => {
  const current = overview.value
  return {
    ...current,
    today: 0,
    total: 0,
    active: 0,
    resolve_rate: 0,
    avg_response_min: 0,
    by_type: { fire: 0, traffic: 0, building: 0, flood: 0 },
    by_district: [],
    city_index: {
      ...current.city_index,
      safety_score: 96,
      traffic_tpi: 1.8,
      traffic_level: 'smooth' as const
    },
    trend: current.trend.map((point) => ({ ...point, fire: 0, traffic: 0, building: 0, flood: 0 }))
  }
})
const displayOverview = computed(() => {
  if (calmBaseline.value) return calmOverview.value
  if (!demoEventIds.value.length) return overview.value
  const byType: Record<EventType, number> = { fire: 0, traffic: 0, building: 0, flood: 0 }
  const byDistrict = new Map<string, number>()
  for (const event of demoEvents.value) {
    byType[event.event_type]++
    const district = event.district || '未归属区域'
    byDistrict.set(district, (byDistrict.get(district) ?? 0) + 1)
  }
  const active = demoEvents.value.filter((event) => event.status !== 'resolved').length
  const severe = demoEvents.value.filter(
    (event) => event.status !== 'resolved' && (event.severity === 'critical' || event.severity === 'high')
  ).length
  const trend = overview.value.trend.map((point, index) => ({
    ...point,
    fire: index === overview.value.trend.length - 1 ? byType.fire : 0,
    traffic: index === overview.value.trend.length - 1 ? byType.traffic : 0,
    building: index === overview.value.trend.length - 1 ? byType.building : 0,
    flood: index === overview.value.trend.length - 1 ? byType.flood : 0
  }))
  return {
    ...overview.value,
    today: demoEvents.value.length,
    total: demoEvents.value.length,
    active,
    resolve_rate: 0,
    avg_response_min: active ? 6.8 : 0,
    by_type: byType,
    by_district: [...byDistrict].map(([name, count]) => ({ name, count })),
    city_index: {
      ...overview.value.city_index,
      safety_score: Math.max(62, 96 - active * 5 - severe * 4)
    },
    trend
  }
})
const displayCriticalActive = computed(() => {
  if (calmBaseline.value) return 0
  if (!demoEventIds.value.length) return criticalActive.value
  return demoEvents.value.filter(
    (event) => event.status !== 'resolved' && (event.severity === 'critical' || event.severity === 'high')
  ).length
})

function sleep(ms: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, ms))
}

function revealActiveCity(event?: CityEvent) {
  revealAnomalies()
  layers.events = true
  showResolved.value = false
  if (event) setDemoEventIds([event.id])
}

function finishAssistantDemo() {
  if (!assistantSettled) return
  const resolve = assistantSettled
  assistantSettled = null
  window.clearTimeout(assistantTimer)
  resolve()
}

function onAssistantSettled() {
  finishAssistantDemo()
}

function demoPromptFor(event: CityEvent | null): { question: string; scenario: string } {
  if (!event) {
    return {
      question: '当前城市运行状态下，研判下一小时风险需要哪些信息？',
      scenario: '武昌区发生暴雨，推演未来30分钟积水对周边人员和道路的影响。'
    }
  }
  const label = EVENT_TYPE_META[event.event_type]?.label ?? '城市异常'
  const prompts: Record<EventType, string> = {
    fire: `${event.name}火势可能扩大，推演未来30分钟烟气、疏散和周边道路影响。`,
    traffic: `${event.name}拥堵持续扩大，推演未来30分钟排队长度、波及道路和绕行方案。`,
    building: `${event.district || '武昌区'}发生中型火灾，危险半径120米，影响300人，推演人员疏散和周边道路影响。`,
    flood: `${event.name}积水继续加深，推演未来30分钟淹没范围、人员和道路影响。`
  }
  return {
    question: `这起${label}目前还有哪些未知信息？应优先核实什么，周边哪些设施需要关注？`,
    scenario: prompts[event.event_type]
  }
}

async function askAssistantDemo(context: { event: CityEvent | null }) {
  const { question } = demoPromptFor(context.event)
  assistantOpen.value = true
  await nextTick()
  await sleep(180)
  assistantRef.value?.resetAutoQuestion()
  assistantDemoQuestion.value = question
  await new Promise<void>((resolve) => {
    assistantSettled = resolve
    assistantTimer = window.setTimeout(finishAssistantDemo, 45000)
  })
  await sleep(1800)
  assistantOpen.value = false
}

async function runScenarioDemo(context: { event: CityEvent | null }) {
  scenarioMapReview.value = false
  scenarioOpen.value = true
  await nextTick()
  for (let i = 0; i < 10 && !scenarioRef.value; i++) await sleep(100)
  const { scenario } = demoPromptFor(context.event)
  if (!scenarioRef.value) {
    scenarioOpen.value = false
    return
  }
  const completed = await Promise.race([scenarioRef.value.demoStart(scenario), sleep(45000).then(() => false)])
  if (!completed) {
    ElMessage.warning('情景推演未在演示时限内完成，继续后续环节')
    scenarioRef.value?.demoStop()
    scenarioOpen.value = false
    scenarioMapReview.value = false
  }
  await sleep(1800)
}

async function runAnalysisDemo(context: { event: CityEvent | null }) {
  scenarioRef.value?.demoStop()
  scenarioOpen.value = false
  scenarioMapReview.value = false
  const type = context.event?.event_type ?? 'fire'
  await router.push({ path: `/ai-analysis/${type}`, query: { demo: '1' } })
  await sleep(10500)
}

async function showAnomalySurge(context: { event: CityEvent | null }) {
  scenarioRef.value?.demoStop()
  scenarioOpen.value = false
  scenarioMapReview.value = false
  await router.push('/dashboard')
  revealActiveCity()
  await sleep(700)
  viewerRef.value?.getCrowd()?.startAmbient(420, 120)
  const results = await Promise.allSettled([
    triggerScenario('fire'),
    triggerScenario('flood'),
    triggerScenario('traffic'),
    triggerScenario('building')
  ])
  await loadEvents()
  const surgeIds = results.flatMap((result) =>
    result.status === 'fulfilled' && result.value.event_id ? [result.value.event_id] : []
  )
  setDemoEventIds([...new Set([...(context.event ? [context.event.id] : []), ...surgeIds])])
  monitored.value = viewerRef.value?.sceneStats().monitored
  await sleep(4200)
}

const demoTourHooks: DemoTourHooks = {
  onAnomaly: (event) => revealActiveCity(event),
  askAssistant: askAssistantDemo,
  runScenario: runScenarioDemo,
  runAnalysis: runAnalysisDemo,
  showAnomalySurge
}

// ---------------- 面板折叠（窄屏自动隐藏，绝不遮挡场景中心）
const leftOpen = ref(true)
const rightOpen = ref(true)
let ro: ResizeObserver | null = null
let lastWidth = 0
function onResize(w: number) {
  const narrow = w < 1100
  const wasNarrow = lastWidth > 0 && lastWidth < 1100
  if (lastWidth === 0 || narrow !== wasNarrow) {
    leftOpen.value = !narrow
    rightOpen.value = !narrow
  }
  lastWidth = w
}

const cssVars = computed(() => ({
  '--scene-inset-left': leftOpen.value ? 'calc(var(--hud-w) + 24px)' : '16px',
  '--scene-inset-right': rightOpen.value ? 'calc(var(--hud-w) + 24px)' : '32px',
  '--scene-inset-top': '60px',
  '--scene-inset-bottom': '14px'
}))

onMounted(() => {
  resume()
  if (rootRef.value) {
    ro = new ResizeObserver((entries) => onResize(entries[0]?.contentRect.width ?? 0))
    ro.observe(rootRef.value)
  }
})
onActivated(resume)
onDeactivated(pause)
onBeforeUnmount(() => {
  ro?.disconnect()
  pause()
})
</script>

<template>
  <div
    ref="rootRef"
    class="dashboard"
    :class="{ 'is-scenario': scenarioOpen, 'is-scenario-map': scenarioMapReview }"
    :style="cssVars"
  >
    <CesiumViewer
      ref="viewerRef"
      class="dashboard__scene"
      :layers="sceneLayers"
      :basemap="basemap"
      :auto-track="autoTrack"
      :event-types="eventTypes"
      :visible-event-ids="demoEventIds"
      :show-resolved="showResolved"
      :live-alerts="!calmBaseline && !scenarioOpen && !scenarioMapReview"
      ambient-crowd
      :demo-hooks="demoTourHooks"
      @ready="onSceneReady"
      @basemap-change="(k: BasemapKey) => (basemap = k)"
      @tour-focus="(f: TourFocus | null) => (focus = f)"
      @selection="onSelection"
      @fine-district-change="onFineDistrictChange"
    />

    <!-- 左列：城市态势 -->
    <aside class="hud-col hud-col--left" :class="{ hidden: !leftOpen }">
      <HudPanel title="城市安全指数" sub="SAFETY" class="p-safety" :focus="focus === 'safety' || focus === 'traffic'">
        <template #extra
          ><span class="ce-num">更新 {{ updatedText }}</span></template
        >
        <SafetyPanel
          :score="displayOverview.city_index.safety_score"
          :tpi="displayOverview.city_index.traffic_tpi"
          :level="displayOverview.city_index.traffic_level"
          :monitored="monitored"
        />
      </HudPanel>
      <HudPanel title="核心指标" sub="KPI" class="p-kpi" :focus="focus === 'kpi'">
        <KpiGrid
          :today="displayOverview.today"
          :total="displayOverview.total"
          :active="displayOverview.active"
          :resolve-rate="displayOverview.resolve_rate"
          :avg-response="displayOverview.avg_response_min"
          :critical="displayCriticalActive"
        />
      </HudPanel>
      <HudPanel title="事件类型分布" sub="TYPES" class="p-types" :focus="focus === 'types'">
        <TypeRose :by-type="displayOverview.by_type" />
      </HudPanel>
      <HudPanel title="24 小时事件趋势" :sub="trendSub" class="p-trend" :focus="focus === 'trend'">
        <TrendChart :trend="displayOverview.trend" />
      </HudPanel>
    </aside>

    <!-- 右列：事件与感知 -->
    <aside class="hud-col hud-col--right" :class="{ hidden: !rightOpen }">
      <DataErrorNotice v-if="eventsError" :message="eventsError" :busy="eventsLoading" @retry="retryEvents" />
      <HudPanel title="实时事件流" sub="LIVE" class="p-feed" :focus="focus === 'feed'">
        <div v-if="calmBaseline" class="calm-feed">
          <span class="calm-feed__pulse"><i /></span>
          <b>城市运行正常</b>
          <p>道路通行平稳，重点区域人员持续流动，当前无新增异常事件。</p>
          <small>点击“一键演示”，观察随机异常从发现到处置的全过程</small>
        </div>
        <LiveFeed v-else :events="demoEvents" :selected-id="selectedEventId" @locate="locateEvent" />
      </HudPanel>
      <HudPanel title="区域事件排行" sub="DISTRICT" class="p-district" :focus="focus === 'district'">
        <DistrictRank :items="displayOverview.by_district" />
      </HudPanel>
      <HudPanel title="感知设备在线率" sub="SENSORS" class="p-sensor" :focus="focus === 'sensor'">
        <SensorPanel :online="overview.city_index.sensors_online" :total="overview.city_index.sensors_total" />
      </HudPanel>
    </aside>

    <!-- 折叠把手 -->
    <button
      class="hud-toggle hud-toggle--left"
      :class="{ closed: !leftOpen }"
      :title="leftOpen ? '收起左侧面板' : '展开左侧面板'"
      @click="leftOpen = !leftOpen"
    >
      <i />
    </button>
    <button
      class="hud-toggle hud-toggle--right"
      :class="{ closed: !rightOpen }"
      :title="rightOpen ? '收起右侧面板' : '展开右侧面板'"
      @click="rightOpen = !rightOpen"
    >
      <i />
    </button>

    <!-- 顶部工具条 -->
    <div class="hud-toolbar">
      <SceneToolbar
        :layers="layers"
        :basemap="basemap"
        :auto-track="autoTrack"
        :touring="touring"
        @toggle-layer="toggleLayer"
        @basemap="(k: BasemapKey) => (basemap = k)"
        @auto-track="(v: boolean) => (autoTrack = v)"
        @home="goHome"
        @tour="toggleTour"
        @parse="parseOpen = true"
        @assistant="assistantOpen = true"
        @crowd="crowdOpen = true"
        @scenario="openScenario"
      />
    </div>

    <!-- AI 任务解析弹窗（主界面唯一入口，AI 分析页不再重复） -->
    <el-dialog v-model="parseOpen" title="AI 任务解析" width="min(600px, 94vw)" align-center append-to-body>
      <TaskParsePanel compact @goto="gotoScene" />
      <template #footer>
        <span class="ai-tip">DeepSeek 大模型 · 点击「解析」才调用 · 付费 API</span>
      </template>
    </el-dialog>

    <el-dialog v-model="assistantOpen" title="城市治理助手" width="min(680px, 94vw)" align-center append-to-body>
      <AssistantChatPanel
        ref="assistantRef"
        :event-id="selectedEventId"
        :auto-question="assistantDemoQuestion"
        @settled="onAssistantSettled"
      />
      <template #footer>
        <span class="ai-tip">DeepSeek 大模型 · 发送后才调用 · 付费 API</span>
      </template>
    </el-dialog>

    <el-drawer v-model="crowdOpen" title="虚拟人群仿真" size="min(520px, 94vw)" append-to-body>
      <CrowdSimulationPanel :crowd="crowdLayer" />
    </el-drawer>

    <el-drawer
      v-model="scenarioOpen"
      title="城市智能情景推演"
      size="min(480px, 94vw)"
      :modal="false"
      :with-header="false"
      append-to-body
    >
      <ScenarioWorkspace
        ref="scenarioRef"
        :viewer="viewerRef"
        @view-map="viewScenarioMap"
        @close="scenarioOpen = false"
      />
    </el-drawer>

    <button v-if="scenarioMapReview" class="scenario-review-return" @click="reopenScenario">返回情景推演</button>

    <!-- 左下图例 -->
    <transition name="hud-fade">
      <div v-show="!touring" class="hud-legend">
        <SceneLegend
          :event-types="eventTypes"
          :show-resolved="showResolved"
          :default-open="false"
          @toggle-type="toggleType"
          @toggle-resolved="showResolved = !showResolved"
        />
      </div>
    </transition>
  </div>
</template>

<style scoped>
.dashboard {
  --hud-w: clamp(248px, 18.5vw, 276px);
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.dashboard__scene {
  position: absolute;
  inset: 0;
}
.dashboard.is-scenario .hud-col,
.dashboard.is-scenario .hud-toggle,
.dashboard.is-scenario .hud-toolbar,
.dashboard.is-scenario .hud-legend,
.dashboard.is-scenario-map .hud-col,
.dashboard.is-scenario-map .hud-toggle,
.dashboard.is-scenario-map .hud-toolbar,
.dashboard.is-scenario-map .hud-legend {
  opacity: 0;
  pointer-events: none;
}
.dashboard.is-scenario .hud-col--left,
.dashboard.is-scenario-map .hud-col--left {
  transform: translateX(calc(-100% - 24px));
}
.dashboard.is-scenario .hud-col--right,
.dashboard.is-scenario-map .hud-col--right {
  transform: translateX(calc(100% + 24px));
}
.dashboard.is-scenario .hud-toolbar,
.dashboard.is-scenario-map .hud-toolbar {
  transform: translateY(-18px);
}
.scenario-review-return {
  position: absolute;
  top: 18px;
  left: 18px;
  z-index: 8;
  height: 36px;
  padding: 0 14px;
  color: #dff8ff;
  background: rgba(7, 34, 58, 0.94);
  border: 1px solid rgba(79, 195, 247, 0.65);
  cursor: pointer;
}
.scenario-review-return:hover,
.scenario-review-return:focus-visible {
  border-color: #74e8ff;
  outline: none;
}

.hud-col {
  position: absolute;
  top: 10px;
  bottom: 10px;
  z-index: 5;
  width: var(--hud-w);
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow: hidden;
  background: var(--ce-panel-solid);
  border: 1px solid var(--ce-panel-border);
  border-radius: var(--ce-radius);
  transition:
    transform 0.45s var(--ce-ease),
    opacity 0.35s ease;
}
.hud-col--left {
  left: 24px;
}
.hud-col--right {
  right: 24px;
}
.hud-col :deep(.ce-panel) {
  border: 0;
  border-radius: 0;
  background: transparent;
}
.hud-col :deep(.ce-panel + .ce-panel) {
  border-top: 1px solid var(--ce-divider);
}
.hud-col--left.hidden {
  transform: translateX(calc(-100% - 24px));
  opacity: 0;
  pointer-events: none;
}
.hud-col--right.hidden {
  transform: translateX(calc(100% + 24px));
  opacity: 0;
  pointer-events: none;
}

/* 左列各面板高度分配 */
.p-safety {
  flex: 0 0 auto;
  min-height: 188px;
}
.p-kpi {
  flex: 0 0 auto;
}
.p-types {
  flex: 1.05 1 0;
  min-height: 190px;
}
.p-trend {
  flex: 0.95 1 0;
  min-height: 180px;
}
/* 右列 */
.p-feed {
  flex: 1.8 1 0;
  min-height: 220px;
}
.calm-feed {
  min-height: 176px;
  padding: 20px 8px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 8px;
}
.calm-feed__pulse {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  margin-bottom: 4px;
  border: 1px solid rgba(77, 217, 132, 0.42);
  border-radius: 50%;
}
.calm-feed__pulse i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ce-success);
  box-shadow: 0 0 0 0 rgba(77, 217, 132, 0.45);
  animation: calm-pulse 2s ease-out infinite;
}
.calm-feed b {
  color: var(--ce-text-strong);
  font-size: 17px;
}
.calm-feed p,
.calm-feed small {
  margin: 0;
  color: var(--ce-text-dim);
  font-size: 13px;
  line-height: 1.65;
}
.calm-feed small {
  margin-top: 5px;
  color: var(--ce-text-faint);
  font-size: 12px;
}
@keyframes calm-pulse {
  70% {
    box-shadow: 0 0 0 10px rgba(77, 217, 132, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(77, 217, 132, 0);
  }
}
.p-district {
  flex: 1 1 0;
  min-height: 158px;
}
.p-sensor {
  flex: 0 0 auto;
  min-height: 142px;
}

.hud-toggle {
  position: absolute;
  top: 50%;
  z-index: 6;
  width: 14px;
  height: 64px;
  margin-top: -32px;
  padding: 0;
  border: 1px solid var(--ce-panel-border);
  background: var(--ce-panel-solid);
  cursor: pointer;
  transition:
    left 0.45s var(--ce-ease),
    right 0.45s var(--ce-ease),
    background-color 0.2s ease;
}
.hud-toggle:hover {
  background: #242a2f;
}
.hud-toggle i {
  display: block;
  width: 6px;
  height: 6px;
  margin: 0 auto;
  border-left: 1.5px solid var(--ce-accent);
  border-bottom: 1.5px solid var(--ce-accent);
}
.hud-toggle--left {
  left: calc(var(--hud-w) + 25px);
  border-left: none;
  border-radius: 0 4px 4px 0;
}
.hud-toggle--left i {
  transform: translateX(1px) rotate(45deg);
}
.hud-toggle--left.closed {
  left: 0;
}
.hud-toggle--left.closed i {
  transform: translateX(-1px) rotate(-135deg);
}
.hud-toggle--right {
  right: calc(var(--hud-w) + 25px);
  border-right: none;
  border-radius: 4px 0 0 4px;
}
.hud-toggle--right i {
  transform: translateX(-1px) rotate(-135deg);
}
.hud-toggle--right.closed {
  right: 0;
}
.hud-toggle--right.closed i {
  transform: translateX(1px) rotate(45deg);
}

.hud-toolbar {
  container: hud-toolbar / inline-size;
  position: absolute;
  top: 10px;
  left: var(--scene-inset-left);
  right: var(--scene-inset-right);
  z-index: 6;
  display: flex;
  justify-content: center;
  pointer-events: none;
  transition:
    left 0.45s var(--ce-ease),
    right 0.45s var(--ce-ease);
}
.hud-toolbar > * {
  pointer-events: auto;
  max-width: 100%;
  overflow-x: auto;
}

.hud-legend {
  position: absolute;
  left: var(--scene-inset-left);
  bottom: 14px;
  z-index: 5;
  transition: left 0.45s var(--ce-ease);
}
.hud-fade-enter-active,
.hud-fade-leave-active {
  transition: opacity 0.3s ease;
}
.hud-fade-enter-from,
.hud-fade-leave-to {
  opacity: 0;
}

@media (max-height: 880px) {
  .p-safety {
    min-height: 172px;
  }
  .p-types,
  .p-trend {
    min-height: 168px;
  }
  .p-district {
    min-height: 140px;
  }
}
@media (max-height: 820px) {
  .p-sensor {
    display: none;
  }
}
@media (max-width: 1100px) {
  /* 平板宽度切换时立即收起侧栏，避免过渡中的面板压住地图或越过屏幕边缘。 */
  .hud-col,
  .hud-toggle,
  .hud-toolbar,
  .hud-legend {
    transition: none;
  }
}
@media (max-width: 700px) {
  .hud-col,
  .hud-toggle {
    display: none;
  }
}
/* 弹窗被 teleport 到 body，scoped 样式不生效 */
:global(.ai-tip) {
  font-size: 12px;
  color: #6f89aa;
}
</style>

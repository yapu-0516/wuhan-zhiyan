<script setup lang="ts">
// 城市总览（城市运行指挥中心大屏）
// 全屏三维数字孪生场景 + 左右 HUD 数据面板 + 顶部场景工具条 + 左下图例 + 一键演示字幕。
// 组件名 Dashboard 与 App.vue 中 <KeepAlive include="Dashboard"> 对应：切页时不销毁 Cesium Viewer。
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref } from 'vue'
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
import DataErrorNotice from '@/components/pages/DataErrorNotice.vue'
import { useOverview } from '@/composables/useOverview'
import { useCityEvents } from '@/composables/useCityEvents'
import { DEFAULT_BASEMAP, type BasemapKey } from '@/config/cesium'
import { DEFAULT_LAYERS, type EventTypeFilter, type LayerKey, type LayerVisibility, type TourFocus } from '@/components/scene/types'
import type { EventType } from '@/types/event'
import { hhmm, shortTime } from '@/utils/format'
import { apiState } from '@/api/http'

defineOptions({ name: 'Dashboard' })

const viewerRef = ref<InstanceType<typeof CesiumViewer> | null>(null)
const rootRef = ref<HTMLDivElement | null>(null)

// ---------------- 场景状态（工具条 / 图例 → CesiumViewer）
const layers = reactive<LayerVisibility>({ ...DEFAULT_LAYERS })
const basemap = ref<BasemapKey>(DEFAULT_BASEMAP)
const autoTrack = ref(false)
const eventTypes = reactive<EventTypeFilter>({ fire: true, traffic: true, building: true, flood: true })
const showResolved = ref(false)
const focus = ref<TourFocus | null>(null)
const selectedEventId = ref<string | null>(null)
const monitored = ref<number | undefined>(undefined)

const touring = computed(() => viewerRef.value?.tourState?.running ?? false)

async function toggleLayer(key: LayerKey) {
  layers[key] = !layers[key]
  if (layers[key] && key === 'buildings') layers.buildingsFine = false
  if (layers[key] && key === 'buildingsFine') {
    ElMessage.info('正在构建精细建筑模型…')
    const ok = await viewerRef.value?.loadFineBuildingLayer()
    if (ok && layers.buildingsFine) layers.buildings = false
    else if (!ok) layers.buildingsFine = false
  }
}
function toggleType(t: EventType) {
  eventTypes[t] = !eventTypes[t]
}
function goHome() {
  viewerRef.value?.closePanels()
  void viewerRef.value?.flyHome()
}
function toggleTour() {
  const v = viewerRef.value
  if (!v) return
  if (v.tourState.running) v.stopTour()
  else {
    leftOpen.value = true
    rightOpen.value = true
    void v.startTour()
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
  () => events.value.filter((e) => e.status !== 'resolved' && (e.severity === 'critical' || e.severity === 'high')).length
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
  '--scene-inset-left': leftOpen.value ? 'calc(var(--hud-w) + 24px)' : '12px',
  '--scene-inset-right': rightOpen.value ? 'calc(var(--hud-w) + 24px)' : '12px',
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
  <div ref="rootRef" class="dashboard" :style="cssVars">
    <CesiumViewer
      ref="viewerRef"
      class="dashboard__scene"
      :layers="layers"
      :basemap="basemap"
      :auto-track="autoTrack"
      :event-types="eventTypes"
      :show-resolved="showResolved"
      @ready="onSceneReady"
      @basemap-change="(k: BasemapKey) => (basemap = k)"
      @tour-focus="(f: TourFocus | null) => (focus = f)"
      @selection="onSelection"
    />

    <!-- 左列：城市态势 -->
    <aside class="hud-col hud-col--left" :class="{ hidden: !leftOpen }">
      <HudPanel title="城市安全指数" sub="SAFETY" class="p-safety" :focus="focus === 'safety' || focus === 'traffic'">
        <template #extra><span class="ce-num">更新 {{ updatedText }}</span></template>
        <SafetyPanel
          :score="overview.city_index.safety_score"
          :tpi="overview.city_index.traffic_tpi"
          :level="overview.city_index.traffic_level"
          :monitored="monitored"
        />
      </HudPanel>
      <HudPanel title="核心指标" sub="KPI" class="p-kpi" :focus="focus === 'kpi'">
        <KpiGrid
          :today="overview.today"
          :total="overview.total"
          :active="overview.active"
          :resolve-rate="overview.resolve_rate"
          :avg-response="overview.avg_response_min"
          :critical="criticalActive"
        />
      </HudPanel>
      <HudPanel title="事件类型分布" sub="TYPES" class="p-types" :focus="focus === 'types'">
        <TypeRose :by-type="overview.by_type" />
      </HudPanel>
      <HudPanel title="24 小时事件趋势" :sub="trendSub" class="p-trend" :focus="focus === 'trend'">
        <TrendChart :trend="overview.trend" />
      </HudPanel>
    </aside>

    <!-- 右列：事件与感知 -->
    <aside class="hud-col hud-col--right" :class="{ hidden: !rightOpen }">
      <DataErrorNotice v-if="eventsError" :message="eventsError" :busy="eventsLoading" @retry="retryEvents" />
      <HudPanel title="实时事件流" sub="LIVE" class="p-feed" :focus="focus === 'feed'">
        <LiveFeed :events="events" :selected-id="selectedEventId" @locate="locateEvent" />
      </HudPanel>
      <HudPanel title="区域事件排行" sub="DISTRICT" class="p-district" :focus="focus === 'district'">
        <DistrictRank :items="overview.by_district" />
      </HudPanel>
      <HudPanel title="感知设备在线率" sub="SENSORS" class="p-sensor" :focus="focus === 'sensor'">
        <SensorPanel :online="overview.city_index.sensors_online" :total="overview.city_index.sensors_total" />
      </HudPanel>
    </aside>

    <!-- 折叠把手 -->
    <button class="hud-toggle hud-toggle--left" :class="{ closed: !leftOpen }" :title="leftOpen ? '收起左侧面板' : '展开左侧面板'" @click="leftOpen = !leftOpen">
      <i />
    </button>
    <button class="hud-toggle hud-toggle--right" :class="{ closed: !rightOpen }" :title="rightOpen ? '收起右侧面板' : '展开右侧面板'" @click="rightOpen = !rightOpen">
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
      />
    </div>

    <!-- 左下图例 -->
    <transition name="hud-fade">
      <div v-show="!touring" class="hud-legend">
        <SceneLegend
          :event-types="eventTypes"
          :show-resolved="showResolved"
          @toggle-type="toggleType"
          @toggle-resolved="showResolved = !showResolved"
        />
      </div>
    </transition>
  </div>
</template>

<style scoped>
.dashboard {
  --hud-w: clamp(288px, 21vw, 352px);
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.dashboard__scene {
  position: absolute;
  inset: 0;
}

.hud-col {
  position: absolute;
  top: 12px;
  bottom: 12px;
  z-index: 5;
  width: var(--hud-w);
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition:
    transform 0.45s var(--ce-ease),
    opacity 0.35s ease;
}
.hud-col--left {
  left: 12px;
}
.hud-col--right {
  right: 12px;
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
  min-height: 196px;
}
.p-kpi {
  flex: 0 0 auto;
}
.p-types {
  flex: 1 1 0;
  min-height: 168px;
}
.p-trend {
  flex: 1.15 1 0;
  min-height: 168px;
}
/* 右列 */
.p-feed {
  flex: 1.8 1 0;
  min-height: 220px;
}
.p-district {
  flex: 1 1 0;
  min-height: 170px;
}
.p-sensor {
  flex: 0 0 auto;
  min-height: 150px;
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
  background: rgba(8, 18, 38, 0.85);
  cursor: pointer;
  transition:
    left 0.45s var(--ce-ease),
    right 0.45s var(--ce-ease),
    background 0.2s ease;
}
.hud-toggle:hover {
  background: rgba(79, 195, 247, 0.22);
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
  left: calc(var(--hud-w) + 14px);
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
  right: calc(var(--hud-w) + 14px);
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
  top: 12px;
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
    min-height: 132px;
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
</style>

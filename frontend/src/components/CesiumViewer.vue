<script setup lang="ts">
/**
 * 城市智眼三维数字孪生场景（Cesium 1.125，无 Ion 依赖）
 *
 * 图层（均为合批 Primitive / Collection，详见 ./scene/*）：
 *   建筑   BuildingLayer   OSM 轮廓拉伸 + 科技渐变/扫描光带/城市生长着色器，选中/告警/预警通过批表切换
 *   路况   RoadLayer       按路况等级着色的流光线，WS traffic.updated 实时更新
 *   事件   EventLayer      定位针 + 标签 + 地面涟漪 + 光柱，新事件强提示
 *   资源   PoiLayer        医院/消防站/派出所/学校
 *   氛围   AmbientEffects  示范区雷达扫描 + 边界发光线
 * 交互：拾取建筑/道路/事件/资源点；路由 ?eventId= / ?buildingId= 定位；新事件通知 + 自动追踪；一键演示导览。
 * KeepAlive：失活时暂停渲染循环，激活时恢复；卸载时销毁全部图层、监听与 Viewer。
 */
import { computed, h, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { BASEMAPS, CESIUM_ION_TOKEN, DEFAULT_BASEMAP, type BasemapKey } from '@/config/cesium'
import { getBuildings, getFineBuildings, getPois, getRoads } from '@/api/geo'
import { useCityEvents } from '@/composables/useCityEvents'
import { useRealtime } from '@/composables/useRealtime'
import { useSystemInfo } from '@/composables/useSystemInfo'
import { useDemoTour, type DemoTourHooks } from '@/composables/useDemoTour'
import type { CityEvent } from '@/types/event'
import { EVENT_TYPE_META, SEVERITY_META } from '@/types/event'
import type { Building, Poi } from '@/types/building'
import { POI_META, TRAFFIC_LEVEL_META } from '@/types/building'
import { hhmm } from '@/utils/format'
import EventDetail from './EventDetail.vue'
import BuildingPanel from './scene/BuildingPanel.vue'
import TourCaption from './scene/TourCaption.vue'
import { createSceneClock, type SceneClock } from './scene/shaders'
import { BasemapController, GLOBE_BASE_COLOR } from './scene/basemap'
import { CameraController } from './scene/cameraControl'
import { BuildingLayer } from './scene/buildingLayer'
import { RoadLayer } from './scene/roadLayer'
import { EventLayer } from './scene/eventLayer'
import { PoiLayer } from './scene/poiLayer'
import { AmbientEffects } from './scene/effects'
import { CrowdLayer } from './scene/crowd/crowdLayer'
import {
  DEFAULT_LAYERS,
  type EventTypeFilter,
  type FlyOptions,
  type LayerKey,
  type LayerVisibility,
  type OrbitOptions,
  type SceneApi,
  type TourFocus
} from './scene/types'

defineOptions({ name: 'CesiumViewer' })

const props = withDefaults(
  defineProps<{
    /** 图层可见性（部分覆盖默认值） */
    layers?: Partial<LayerVisibility>
    /** 底图 */
    basemap?: BasemapKey
    /** 新事件自动追踪（相机飞往） */
    autoTrack?: boolean
    /** 事件类型过滤 */
    eventTypes?: Partial<EventTypeFilter>
    /** 演示时只显示指定事件；为空时使用事件类型过滤 */
    visibleEventIds?: string[]
    /** 是否显示已办结事件（灰显） */
    showResolved?: boolean
    /** 新事件弹出通知 */
    liveAlerts?: boolean
    /** 首次加载入场动画 */
    intro?: boolean
    /** 城市总览平静基线：显示持续走动的人群与车辆 */
    ambientCrowd?: boolean
    /** 一键演示跨页面业务动作 */
    demoHooks?: DemoTourHooks
  }>(),
  {
    layers: undefined,
    basemap: undefined,
    eventTypes: undefined,
    visibleEventIds: undefined,
    autoTrack: false,
    showResolved: false,
    liveAlerts: true,
    intro: true,
    ambientCrowd: false,
    demoHooks: undefined
  }
)

const emit = defineEmits<{
  (e: 'ready'): void
  (e: 'basemap-change', key: BasemapKey): void
  (e: 'tour-focus', focus: TourFocus | null): void
  (e: 'selection', payload: { kind: 'event' | 'building' | null; id: string | null }): void
}>()

const route = useRoute()
const router = useRouter()
const { events, lastCreated, getEventById } = useCityEvents()
const realtime = useRealtime()
const systemInfo = useSystemInfo()

// ------------------------------------------------------------------ 非响应式场景对象（避免 Vue 深度代理 WebGL 资源）
const containerRef = ref<HTMLDivElement | null>(null)
const crowdLayerRef = ref<HTMLDivElement | null>(null)
const creditRef = ref<HTMLDivElement | null>(null)
let viewer: Cesium.Viewer | null = null
let clock: SceneClock | null = null
let basemapCtl: BasemapController | null = null
let cam: CameraController | null = null
let buildings: BuildingLayer | null = null
let fineBuildings: BuildingLayer | null = null
let fineBuildingsLoading: Promise<number> | null = null
let roads: RoadLayer | null = null
let eventLayer: EventLayer | null = null
let pois: PoiLayer | null = null
let effects: AmbientEffects | null = null
let crowd: CrowdLayer | null = null
let handler: Cesium.ScreenSpaceEventHandler | null = null
const disposers: Array<() => void> = []
let disposed = false

// ------------------------------------------------------------------ 响应式界面状态
const status = reactive({
  ready: false,
  loading: true,
  stage: '初始化三维引擎…',
  buildingsReady: false,
  safeMode: false,
  fatal: ''
})
const layerState = reactive<LayerVisibility>({ ...DEFAULT_LAYERS, ...(props.layers ?? {}) })
const typeFilter = reactive<EventTypeFilter>({ fire: true, traffic: true, building: true, flood: true, ...(props.eventTypes ?? {}) })
const currentBasemap = ref<BasemapKey>(props.basemap ?? DEFAULT_BASEMAP)
const active = ref(true)

const selectedEventId = ref<string | null>(null)
const selectedBuilding = shallowRef<Building | null>(null)
const selectedEvent = computed<CityEvent | null>(() => (selectedEventId.value ? getEventById(selectedEventId.value) ?? null : null))
const eventDetailRef = ref<InstanceType<typeof EventDetail> | null>(null)

const roadTip = shallowRef<{ id: string; x: number; y: number } | null>(null)
const poiTip = shallowRef<{ poi: Poi; x: number; y: number } | null>(null)
const roadVersion = ref(0)
const tipRoad = computed(() => {
  void roadVersion.value
  return roadTip.value && roads ? roads.get(roadTip.value.id) ?? null : null
})

let pendingTarget: { kind: 'event' | 'building'; id: string } | null = null

// ------------------------------------------------------------------ 场景 API
function isReady() {
  return status.ready && !!viewer && !viewer.isDestroyed()
}

function regionCenter(): [number, number] {
  return cam?.region.center ?? systemInfo.region.value.center
}

function denseCenter(): [number, number] {
  const layer = layerState.buildingsFine && (fineBuildings?.count ?? 0) > 0 ? fineBuildings : buildings
  return layer?.denseCenter() ?? regionCenter()
}

async function flyToEvent(id: string, opts: { open?: boolean } & FlyOptions = {}): Promise<boolean> {
  const e = getEventById(id)
  if (!e) {
    ElMessage.warning(`未找到事件 ${id}`)
    return false
  }
  if (opts.open !== false) openEvent(id)
  if (!cam) return false
  return cam.flyTo(e.longitude, e.latitude, {
    range: opts.range ?? 820,
    pitch: opts.pitch ?? -36,
    heading: opts.heading,
    duration: opts.duration ?? 1.8
  })
}

async function flyToBuilding(id: string, opts: { open?: boolean } & FlyOptions = {}): Promise<boolean> {
  const b = findBuildingById(id)
  if (!b) {
    if (!status.buildingsReady) {
      pendingTarget = { kind: 'building', id }
      return false
    }
    ElMessage.warning(`未找到建筑 ${id}`)
    return false
  }
  if (opts.open !== false) openBuilding(id)
  if (!cam || !Number.isFinite(b.longitude) || !Number.isFinite(b.latitude)) return false
  return cam.flyTo(b.longitude, b.latitude, {
    range: opts.range ?? Math.max(460, b.height * 4.2),
    pitch: opts.pitch ?? -28,
    heading: opts.heading,
    duration: opts.duration ?? 1.8,
    height: b.height * 0.45
  })
}

function openEvent(id: string) {
  const event = getEventById(id)
  if (!event) return
  selectedBuilding.value = null
  // 选中事件时同步高亮其关联建筑与路段，让列表、事件点和空间对象形成一条关系链。
  buildings?.setSelected(event.building_id ?? null)
  fineBuildings?.setSelected(event.building_id ?? null)
  selectedEventId.value = id
  roads?.setSelected(event.road_id ?? null)
  roadTip.value = null
  poiTip.value = null
  emit('selection', { kind: 'event', id })
}

function openBuilding(id: string) {
  const b = findBuildingById(id)
  if (!b) return
  selectedEventId.value = null
  selectedBuilding.value = b
  buildings?.setSelected(id)
  fineBuildings?.setSelected(id)
  roads?.setSelected(null)
  roadTip.value = null
  poiTip.value = null
  emit('selection', { kind: 'building', id })
}

function closePanels() {
  selectedEventId.value = null
  selectedBuilding.value = null
  buildings?.setSelected(null)
  fineBuildings?.setSelected(null)
  roads?.setSelected(null)
  roadTip.value = null
  poiTip.value = null
  emit('selection', { kind: null, id: null })
}

function setLayerVisible(layer: LayerKey, visible: boolean) {
  layerState[layer] = visible
  switch (layer) {
    case 'buildings':
      buildings?.setVisible(visible)
      break
    case 'buildingsFine':
      fineBuildings?.setVisible(visible)
      if (visible) void loadFineBuildings()
      break
    case 'roads':
      roads?.setVisible(visible)
      if (!visible) roadTip.value = null
      break
    case 'events':
      eventLayer?.setVisible(visible)
      syncEvents()
      break
    case 'pois':
      pois?.setVisible(visible)
      if (!visible) poiTip.value = null
      break
    case 'effects':
      effects?.setVisible(visible)
      eventLayer?.setEffects(visible)
      break
  }
}

function setBasemap(key: BasemapKey) {
  if (!(key in BASEMAPS)) return
  currentBasemap.value = key
  basemapCtl?.set(key)
}

function findBuildingById(id: string): Building | undefined {
  return buildings?.get(id) ?? fineBuildings?.get(id)
}

function findRiskBuilding(): Building | null {
  const layers = [fineBuildings, buildings].filter((layer): layer is BuildingLayer => !!layer)
  const list = layers.flatMap((layer) => layer.all())
  const pick = (risk: Building['risk_level']) =>
    list.filter((b) => b.monitored && b.risk_level === risk).sort((a, b) => b.height - a.height)[0]
  return pick('warning') ?? pick('watch') ?? list.filter((b) => b.monitored).sort((a, b) => b.height - a.height)[0] ?? null
}

async function demoDispatch(assignee?: string): Promise<CityEvent | null> {
  const detail = eventDetailRef.value
  if (!detail) return null
  return detail.demoDispatch(assignee)
}

async function loadFineBuildings(): Promise<number> {
  if (!fineBuildings || disposed) return 0
  if (fineBuildings.count > 0) return fineBuildings.count
  if (fineBuildingsLoading) return fineBuildingsLoading
  const showStage = status.ready && !status.loading
  if (showStage) {
    status.loading = true
    status.stage = '构建精细建筑模型…'
  }
  fineBuildingsLoading = (async () => {
    try {
      const data = await getFineBuildings()
      const count = await fineBuildings!.load(data)
      if (!disposed) fineBuildings!.setVisible(layerState.buildingsFine)
      return count
    } catch (error) {
      console.error('[buildings] 精细建筑图层加载失败', error)
      ElMessage.error('精细建筑图层加载失败，请先生成派生数据')
      return 0
    } finally {
      fineBuildingsLoading = null
      if (showStage) status.loading = false
    }
  })()
  return fineBuildingsLoading
}

async function loadFineBuildingLayer(): Promise<boolean> {
  return (await loadFineBuildings()) > 0
}

const api: SceneApi = {
  isReady,
  flyHome: (duration?: number) => cam?.flyHome(duration) ?? Promise.resolve(false),
  flySkyline: (duration?: number) => cam?.flySkyline(denseCenter(), duration) ?? Promise.resolve(false),
  flyFromSpace: () => cam?.flyFromSpace() ?? Promise.resolve(false),
  flyTo: (lon: number, lat: number, opts?: FlyOptions) => cam?.flyTo(lon, lat, opts) ?? Promise.resolve(false),
  flyToEvent,
  flyToBuilding,
  orbit: (lon: number, lat: number, opts?: OrbitOptions) => cam?.orbit(lon, lat, opts) ?? Promise.resolve(false),
  stopOrbit: () => cam?.stopOrbit(),
  cancelFlight: () => cam?.cancel(),
  setLayerVisible,
  setBuildingRiskOnly: (on: boolean) => buildings?.setRiskOnly(on),
  loadFineBuildingLayer,
  setBasemap,
  highlightCongestion: (on: boolean) => roads?.setHighlight(on),
  openEvent,
  openBuilding,
  closePanels,
  demoDispatch,
  regionCenter,
  denseCenter,
  congestedSpot: () => roads?.mostCongested() ?? null,
  cityTraffic: () => roads?.cityTraffic() ?? null,
  findRiskBuilding,
  sceneStats: () => ({
    buildings: layerState.buildingsFine && (fineBuildings?.count ?? 0) > 0 ? fineBuildings!.count : (buildings?.count ?? 0),
    roads: roads?.count ?? 0,
    pois: pois?.count ?? 0,
    monitored: (buildings?.monitoredCount ?? 0) + (layerState.buildingsFine ? (fineBuildings?.monitoredCount ?? 0) : 0)
  })
}

const tour = useDemoTour(
  () => (isReady() ? api : null),
  props.demoHooks ?? {}
)
watch(
  () => tour.state.focus,
  (f) => emit('tour-focus', f)
)

// ------------------------------------------------------------------ 事件同步
const eventSig = computed(() =>
  events.value.map((e) => `${e.id}|${e.status}|${e.severity}|${e.event_type}|${e.longitude}|${e.latitude}|${e.name}`).join(';')
)

function alarmBuildingIds(source: CityEvent[]): Set<string> {
  const s = new Set<string>()
  for (const e of source) {
    if (e.status !== 'resolved' && e.building_id && (e.event_type === 'building' || e.event_type === 'fire')) s.add(e.building_id)
  }
  return s
}

function syncEvents() {
  if (!eventLayer) return
  const visibleIds = props.visibleEventIds?.length ? new Set(props.visibleEventIds) : null
  const source = visibleIds ? events.value.filter((event) => visibleIds.has(event.id)) : events.value
  eventLayer.sync(source, { showResolved: props.showResolved, types: typeFilter, selectedId: selectedEventId.value })
  buildings?.setAlarms(alarmBuildingIds(source))
  fineBuildings?.setAlarms(alarmBuildingIds(source))
}

watch([eventSig, selectedEventId, () => props.showResolved, () => props.visibleEventIds?.join('|')], syncEvents)
watch(typeFilter, syncEvents, { deep: true })

// 选中事件被删除时关闭面板
watch(selectedEvent, (e) => {
  if (!e && selectedEventId.value) selectedEventId.value = null
})

// ------------------------------------------------------------------ 新事件：强提示 + 通知 + 自动追踪
function notify(e: CityEvent) {
  const meta = EVENT_TYPE_META[e.event_type] ?? EVENT_TYPE_META.fire
  const sev = SEVERITY_META[e.severity] ?? SEVERITY_META.medium
  const mark = { fire: '火', traffic: '堵', building: '楼', flood: '涝' }[e.event_type]
  let handle: { close: () => void } | null = null
  const locate = () => {
    handle?.close()
    if (active.value && isReady()) void flyToEvent(e.id, { open: true })
    else void router.push({ path: '/dashboard', query: { eventId: e.id } })
  }
  handle = ElNotification({
    title: '',
    customClass: `ce-notify ce-notify--${e.event_type}`,
    position: 'top-right',
    offset: 68,
    duration: 9000,
    message: h('div', { class: 'ce-notify__row' }, [
      h('div', { class: 'ce-notify__icon' }, mark),
      h('div', { class: 'ce-notify__main' }, [
        h('div', { class: 'ce-notify__title' }, [
          h('span', `新事件 · ${meta.label}`),
          h('span', { class: 'ce-notify__sev', style: { background: sev.color } }, sev.short + '级')
        ]),
        h('div', { class: 'ce-notify__name', title: e.name }, e.name),
        h('div', { class: 'ce-notify__meta' }, `${e.district || '—'} · ${hhmm(e.timestamp)} · 置信度 ${Math.round((e.confidence ?? 0) * 100)}%`)
      ]),
      h('button', { class: 'ce-notify__btn', onClick: locate }, '定位')
    ])
  })
}

watch(lastCreated, (e) => {
  if (!e) return
  eventLayer?.flash(e)
  if (props.liveAlerts) notify(e)
  if (props.autoTrack && active.value && isReady() && !tour.state.running) void flyToEvent(e.id, { open: true })
})

// ------------------------------------------------------------------ 外部属性 → 场景
watch(
  () => props.layers,
  (l) => {
    if (!l) return
    ;(Object.keys(l) as LayerKey[]).forEach((k) => {
      const v = l[k]
      if (typeof v === 'boolean' && v !== layerState[k]) setLayerVisible(k, v)
    })
  },
  { deep: true }
)
watch(
  () => props.basemap,
  (b) => {
    if (b && b !== currentBasemap.value) setBasemap(b)
  }
)
watch(
  () => props.eventTypes,
  (t) => {
    if (t) Object.assign(typeFilter, t)
  },
  { deep: true }
)

// ------------------------------------------------------------------ 路由定位 ?eventId= / ?buildingId=
function handleTarget(t: { kind: 'event' | 'building'; id: string }) {
  if (!isReady() || !active.value) {
    pendingTarget = t
    return
  }
  pendingTarget = null
  if (t.kind === 'event') void flyToEvent(t.id, { open: true })
  else void flyToBuilding(t.id, { open: true })
}

watch(
  () => [route.query.eventId, route.query.buildingId] as const,
  ([eid, bid]) => {
    if (typeof eid === 'string' && eid) handleTarget({ kind: 'event', id: eid })
    else if (typeof bid === 'string' && bid) handleTarget({ kind: 'building', id: bid })
  },
  { immediate: true }
)

function flushPending() {
  if (!pendingTarget || !isReady() || !active.value) return
  if (pendingTarget.kind === 'building' && !status.buildingsReady) return
  handleTarget(pendingTarget)
}

// ------------------------------------------------------------------ 初始化
function createViewer(el: HTMLElement): Cesium.Viewer {
  if (CESIUM_ION_TOKEN) Cesium.Ion.defaultAccessToken = CESIUM_ION_TOKEN
  const v = new Cesium.Viewer(el, {
    baseLayer: false,
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    animation: false,
    timeline: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false,
    vrButton: false,
    scene3DOnly: true,
    shadows: false,
    msaaSamples: 4,
    orderIndependentTranslucency: true,
    useBrowserRecommendedResolution: false,
    showRenderLoopErrors: false,
    creditContainer: creditRef.value ?? undefined,
    contextOptions: { webgl: { alpha: false, antialias: false, powerPreference: 'high-performance' } }
  })
  const dpr = window.devicePixelRatio || 1
  v.resolutionScale = Math.min(dpr, 1.5) / dpr

  const scene = v.scene
  scene.skyBox.show = false
  if (scene.sun) scene.sun.show = false
  if (scene.moon) scene.moon.show = false
  scene.backgroundColor = Cesium.Color.fromCssColorString('#02050d')
  if (scene.skyAtmosphere) {
    scene.skyAtmosphere.show = true
    scene.skyAtmosphere.brightnessShift = -0.52
    scene.skyAtmosphere.saturationShift = -0.32
  }
  scene.highDynamicRange = false
  scene.globe.baseColor = Cesium.Color.fromCssColorString(GLOBE_BASE_COLOR)
  scene.globe.depthTestAgainstTerrain = false
  scene.globe.showGroundAtmosphere = false
  scene.globe.enableLighting = false
  scene.globe.maximumScreenSpaceError = 1.5
  scene.fog.enabled = true
  scene.fog.density = 1.15e-4
  scene.postProcessStages.fxaa.enabled = !scene.msaaSupported
  const ctrl = scene.screenSpaceCameraController
  ctrl.minimumZoomDistance = 60
  ctrl.maximumZoomDistance = 60000
  // 移除默认的双击追踪实体
  v.cesiumWidget.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK)
  return v
}

function bindInteraction(v: Cesium.Viewer) {
  const scene = v.scene
  handler = new Cesium.ScreenSpaceEventHandler(scene.canvas)
  /** 拾取（容错：拾取通道异常不影响交互） */
  const pickId = (pos: Cesium.Cartesian2): unknown => {
    try {
      return scene.pick(pos)?.id
    } catch {
      return undefined
    }
  }

  handler.setInputAction((m: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
    const id = pickId(m.position)
    roadTip.value = null
    poiTip.value = null
    roads?.setSelected(null)
    const evId = eventLayer?.fromPick(id)
    if (evId) return openEvent(evId)
    const b = buildings?.fromPick(id) ?? fineBuildings?.fromPick(id)
    if (b) return openBuilding(b.id)
    const r = roads?.fromPick(id)
    if (r) {
      roads?.setSelected(r.id)
      roadTip.value = { id: r.id, x: m.position.x, y: m.position.y }
      return
    }
    const p = pois?.fromPick(id)
    if (p) {
      poiTip.value = { poi: p, x: m.position.x, y: m.position.y }
      return
    }
    if (selectedEventId.value || selectedBuilding.value) closePanels()
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

  handler.setInputAction((m: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
    const id = pickId(m.position)
    const evId = eventLayer?.fromPick(id)
    if (evId) return void flyToEvent(evId, { range: 520 })
    const b = buildings?.fromPick(id) ?? fineBuildings?.fromPick(id)
    if (b) return void flyToBuilding(b.id)
  }, Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK)

  // 悬停光标（节流拾取）
  let lastHover = 0
  handler.setInputAction((m: Cesium.ScreenSpaceEventHandler.MotionEvent) => {
    const now = performance.now()
    if (now - lastHover < 90) return
    lastHover = now
    const id = pickId(m.endPosition)
    const pickable = typeof id === 'string' && /^(e|b|r|p):/.test(id)
    scene.canvas.style.cursor = pickable ? 'pointer' : ''
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

  // 用户操作时中止环绕巡航
  const stop = () => cam?.stopOrbit()
  for (const t of [
    Cesium.ScreenSpaceEventType.LEFT_DOWN,
    Cesium.ScreenSpaceEventType.RIGHT_DOWN,
    Cesium.ScreenSpaceEventType.MIDDLE_DOWN,
    Cesium.ScreenSpaceEventType.WHEEL,
    Cesium.ScreenSpaceEventType.PINCH_START
  ]) {
    handler.setInputAction(stop, t)
  }
}

/** 自定义着色器在部分显卡上编译失败时，切换为 Cesium 内置外观继续渲染 */
function bindRenderErrorRecovery(v: Cesium.Viewer) {
  const off = v.scene.renderError.addEventListener((_scene: Cesium.Scene, err: unknown) => {
    console.error('[scene] 渲染错误', err)
    if (status.safeMode) {
      status.fatal = '三维渲染出现错误，请刷新页面或更换浏览器后重试。'
      return
    }
    status.safeMode = true
    buildings?.setSafeMode()
    roads?.setSafeMode()
    eventLayer?.setSafeMode()
    effects?.setSafeMode()
    ElMessage.warning('当前显卡不支持部分三维特效，已切换为兼容渲染模式')
    window.setTimeout(() => {
      if (viewer && !viewer.isDestroyed() && active.value) viewer.useDefaultRenderLoop = true
    }, 60)
  })
  disposers.push(off)
}

function retryRender() {
  status.fatal = ''
  if (viewer && !viewer.isDestroyed()) viewer.useDefaultRenderLoop = true
}

async function init() {
  const el = containerRef.value
  if (!el) return
  try {
    viewer = createViewer(el)
  } catch (e) {
    console.error('[scene] Viewer 创建失败', e)
    status.fatal = '当前浏览器不支持 WebGL 或显卡加速被禁用，三维场景无法加载。'
    status.loading = false
    return
  }
  const v = viewer
  const scene = v.scene
  clock = createSceneClock()
  const c = clock
  disposers.push(scene.preRender.addEventListener(() => c.tick()))
  bindRenderErrorRecovery(v)

  cam = new CameraController(v)
  cam.setRegion(systemInfo.region.value)
  cam.jumpHome()
  if (crowdLayerRef.value) {
    try {
      crowd = new CrowdLayer(crowdLayerRef.value, scene, systemInfo.region.value)
    } catch (error) {
      console.warn('[crowd] Three.js 人群图层初始化失败', error)
    }
  }

  basemapCtl = new BasemapController(
    v,
    () => regionCenter(),
    (from) => {
      currentBasemap.value = 'offline'
      emit('basemap-change', 'offline')
      ElMessage.warning(`${BASEMAPS[from].label}加载失败，已切换为离线底图`)
    }
  )
  basemapCtl.set(currentBasemap.value)

  effects = new AmbientEffects(scene, c)
  eventLayer = new EventLayer(scene, c)
  pois = new PoiLayer(scene)
  roads = new RoadLayer(scene, c)
  buildings = new BuildingLayer(scene, c)
  fineBuildings = new BuildingLayer(scene, c)
  if (v.scene.skyAtmosphere) {
    v.scene.skyAtmosphere.brightnessShift = -0.52
    v.scene.skyAtmosphere.saturationShift = -0.32
  }
  // 应用初始图层可见性
  ;(Object.keys(layerState) as LayerKey[]).forEach((k) => setLayerVisible(k, layerState[k]))
  bindInteraction(v)

  disposers.push(
    realtime.on('traffic.updated', (d) => {
      if (roads?.applyTraffic(d)) roadVersion.value++
    })
  )

  // 数据并行加载；系统信息（示范区范围）先到先用
  status.stage = '加载示范区配置…'
  const dataPromise = Promise.allSettled([getBuildings(), getRoads(), getPois()])
  await systemInfo.load()
  if (disposed) return
  const region = systemInfo.region.value
  cam.setRegion(region)
  crowd?.setRegion(region)
  effects.setRegion(region)
  status.ready = true
  syncEvents()

  const hasTarget = !!pendingTarget
  if (props.intro && !hasTarget) void cam.intro()
  else cam.jumpHome()
  flushPending()

  status.stage = '加载城市三维数据…'
  const [bRes, rRes, pRes] = await dataPromise
  if (disposed) return
  const failed: string[] = []
  if (rRes.status === 'fulfilled') {
    roads.load(rRes.value)
    crowd?.setRoads(rRes.value)
    if (props.ambientCrowd) crowd?.startAmbient(420, 120)
  }
  else failed.push('路网')
  if (pRes.status === 'fulfilled') pois.load(pRes.value)
  else failed.push('应急资源')
  if (bRes.status === 'fulfilled') {
    status.stage = `构建三维建筑 ${bRes.value?.features?.length ?? 0} 栋…`
    await buildings.load(bRes.value)
  } else failed.push('建筑')
  if (disposed) return
  status.buildingsReady = true
  status.loading = false
  syncEvents()
  flushPending()
  if (failed.length) ElMessage.warning(`${failed.join('、')}数据加载失败，相关图层暂不可用`)
  if (!hasTarget && !tour.state.running) {
    await cam.flySkyline(denseCenter(), 2.4)
  }
  emit('ready')
}

onMounted(() => {
  void init()
})

onActivated(() => {
  active.value = true
  if (props.ambientCrowd && (crowd?.getStats().total ?? 0) === 0) crowd?.startAmbient(420, 120)
  if (viewer && !viewer.isDestroyed()) {
    viewer.useDefaultRenderLoop = true
    viewer.resize()
  }
  flushPending()
})

onDeactivated(() => {
  active.value = false
  cam?.stopOrbit()
  if (viewer && !viewer.isDestroyed()) viewer.useDefaultRenderLoop = false
})

onBeforeUnmount(() => {
  disposed = true
  tour.stop()
  disposers.splice(0).forEach((fn) => {
    try {
      fn()
    } catch {
      /* ignore */
    }
  })
  handler?.destroy()
  handler = null
  cam?.destroy()
  basemapCtl?.destroy()
  buildings?.destroy()
  fineBuildings?.destroy()
  roads?.destroy()
  eventLayer?.destroy()
  pois?.destroy()
  effects?.destroy()
  crowd?.destroy()
  buildings = roads = null
  eventLayer = null
  pois = null
  effects = null
  crowd = null
  if (viewer && !viewer.isDestroyed()) viewer.destroy()
  viewer = null
  clock = null
})

// ------------------------------------------------------------------ 浮层定位
function closeRoadTip() {
  roadTip.value = null
  roads?.setSelected(null)
}

function tipStyle(x: number, y: number) {
  const el = containerRef.value
  const w = el?.clientWidth ?? 1200
  const hgt = el?.clientHeight ?? 800
  return { left: `${Math.min(x + 16, w - 250)}px`, top: `${Math.min(y + 16, hgt - 170)}px` }
}

defineExpose({
  ...api,
  startTour: () => tour.start(),
  stopTour: () => tour.stop(),
  tourState: tour.state,
  layers: layerState,
  getCrowd: () => crowd,
  getViewer: () => viewer
})
</script>

<template>
  <div class="cesium-viewer-root" :class="{ 'is-touring': tour.state.running }">
    <div ref="containerRef" class="cv-canvas" />
    <div ref="crowdLayerRef" class="cv-crowd-layer" />
    <div class="cv-vignette" />

    <!-- 详情停靠区：事件详情 / 建筑信息 -->
    <div class="cv-dock">
      <transition name="cv-panel" mode="out-in">
        <EventDetail
          v-if="selectedEvent"
          :key="'e' + selectedEvent.id"
          ref="eventDetailRef"
          :event="selectedEvent"
          @close="closePanels"
          @locate="(id: string) => flyToEvent(id)"
          @open-building="(id: string) => flyToBuilding(id, { open: true })"
        />
        <BuildingPanel
          v-else-if="selectedBuilding"
          :key="'b' + selectedBuilding.id"
          :building="selectedBuilding"
          @close="closePanels"
          @open-event="(id: string) => flyToEvent(id, { open: true })"
          @locate="(id: string) => flyToBuilding(id, { open: true })"
        />
      </transition>
    </div>

    <!-- 道路实时路况提示 -->
    <div v-if="tipRoad && roadTip" class="cv-tip" :style="tipStyle(roadTip.x, roadTip.y)">
      <div class="cv-tip__head">
        <i class="cv-tip__bar" :style="{ background: TRAFFIC_LEVEL_META[tipRoad.level].color }" />
        <b>{{ tipRoad.name }}</b>
        <span class="ce-tag" :style="{ color: TRAFFIC_LEVEL_META[tipRoad.level].color }">{{ TRAFFIC_LEVEL_META[tipRoad.level].label }}</span>
      </div>
      <div class="cv-tip__grid">
        <div><span class="ce-num">{{ tipRoad.speed.toFixed(1) }}</span><small>km/h</small><em>实时车速</em></div>
        <div><span class="ce-num">{{ tipRoad.tpi.toFixed(1) }}</span><em>拥堵指数 TPI</em></div>
        <div v-if="tipRoad.speed_limit"><span class="ce-num">{{ tipRoad.speed_limit }}</span><small>km/h</small><em>限速</em></div>
        <div v-if="tipRoad.length_m"><span class="ce-num">{{ (tipRoad.length_m / 1000).toFixed(2) }}</span><small>km</small><em>路段长度</em></div>
      </div>
      <button class="cv-tip__close" @click="closeRoadTip">×</button>
    </div>

    <!-- 应急资源提示 -->
    <div v-if="poiTip" class="cv-tip cv-tip--poi" :style="tipStyle(poiTip.x, poiTip.y)">
      <div class="cv-tip__head">
        <b>{{ POI_META[poiTip.poi.kind]?.icon }} {{ poiTip.poi.name }}</b>
      </div>
      <div class="cv-tip__sub">{{ POI_META[poiTip.poi.kind]?.label }} · 应急资源</div>
      <button class="cv-tip__close" @click="poiTip = null">×</button>
    </div>

    <!-- 加载状态 -->
    <transition name="cv-fade">
      <div v-if="status.loading && !status.fatal" class="cv-loading">
        <span class="cv-loading__spin" />
        <span>{{ status.stage }}</span>
      </div>
    </transition>

    <span v-if="status.safeMode && !status.fatal" class="cv-safe" title="自定义着色器不受当前显卡支持，已使用内置外观">兼容渲染模式</span>

    <div v-if="status.fatal" class="cv-fatal">
      <div class="cv-fatal__card ce-panel">
        <h4>三维场景不可用</h4>
        <p>{{ status.fatal }}</p>
        <button class="cv-fatal__btn" @click="retryRender">重试渲染</button>
      </div>
    </div>

    <!-- 演示字幕 -->
    <div class="cv-caption">
      <TourCaption :state="tour.state" @stop="tour.stop()" />
    </div>

    <div ref="creditRef" class="cv-credits" />
  </div>
</template>

<style scoped>
.cesium-viewer-root {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #02050d;
}
.cv-canvas {
  position: absolute;
  inset: 0;
}
.cv-crowd-layer {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  visibility: hidden;
}
.cv-crowd-layer :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}
.cv-canvas :deep(.cesium-viewer),
.cv-canvas :deep(.cesium-widget),
.cv-canvas :deep(.cesium-widget canvas) {
  width: 100%;
  height: 100%;
}
.cv-canvas :deep(.cesium-viewer-bottom) {
  display: none;
}
.cv-canvas :deep(canvas:focus) {
  outline: none;
}
/* 地图保持完整亮度，不使用装饰性暗角。 */
.cv-vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: transparent;
}

.cv-dock {
  position: absolute;
  top: var(--scene-inset-top, 12px);
  right: var(--scene-inset-right, 12px);
  bottom: var(--scene-inset-bottom, 12px);
  width: min(360px, calc(100% - 24px));
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  pointer-events: none;
  z-index: 6;
  transition:
    right 0.35s var(--ce-ease),
    bottom 0.35s var(--ce-ease);
}
.cv-dock > * {
  pointer-events: auto;
}
/* 演示进行中：为底部字幕条让出空间 */
.is-touring .cv-dock {
  bottom: calc(var(--scene-inset-bottom, 12px) + 118px);
}
.cv-panel-enter-active,
.cv-panel-leave-active {
  transition:
    opacity 0.22s ease,
    transform 0.28s var(--ce-ease);
}
.cv-panel-enter-from {
  opacity: 0;
  transform: translateX(24px);
}
.cv-panel-leave-to {
  opacity: 0;
  transform: translateX(12px);
}

.cv-tip {
  position: absolute;
  z-index: 7;
  min-width: 220px;
  max-width: 260px;
  padding: 10px 12px;
  border: 1px solid var(--ce-panel-border-strong);
  border-radius: 4px;
  background: rgba(6, 15, 34, 0.94);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  font-size: 12px;
}
.cv-tip__head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-right: 16px;
}
.cv-tip__head b {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13.5px;
  color: var(--ce-text-strong);
}
.cv-tip__bar {
  width: 4px;
  height: 14px;
  border-radius: 1px;
}
.cv-tip__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 10px;
  margin-top: 8px;
}
.cv-tip__grid div {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 2px;
}
.cv-tip__grid span {
  font-size: 18px;
  font-weight: 700;
  color: var(--ce-text-strong);
}
.cv-tip__grid small {
  color: var(--ce-text-dim);
}
.cv-tip__grid em {
  flex-basis: 100%;
  font-style: normal;
  font-size: 11px;
  color: var(--ce-text-faint);
}
.cv-tip__sub {
  margin-top: 4px;
  color: var(--ce-text-dim);
}
.cv-tip__close {
  position: absolute;
  top: 6px;
  right: 6px;
  border: none;
  background: transparent;
  color: var(--ce-text-dim);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}
.cv-tip__close:hover {
  color: #fff;
}

.cv-loading {
  position: absolute;
  left: 50%;
  bottom: calc(var(--scene-inset-bottom, 12px) + 64px);
  transform: translateX(-50%);
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 20px;
  background: rgba(6, 15, 34, 0.85);
  font-size: 12.5px;
  color: var(--ce-text);
  letter-spacing: 1px;
  pointer-events: none;
}
.cv-loading__spin {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(79, 195, 247, 0.25);
  border-top-color: var(--ce-accent);
  border-radius: 50%;
  animation: cv-spin 0.8s linear infinite;
}
@keyframes cv-spin {
  to {
    transform: rotate(360deg);
  }
}
.cv-fade-enter-active,
.cv-fade-leave-active {
  transition: opacity 0.4s ease;
}
.cv-fade-enter-from,
.cv-fade-leave-to {
  opacity: 0;
}

.cv-safe {
  position: absolute;
  left: 50%;
  top: calc(var(--scene-inset-top, 12px) + 52px);
  transform: translateX(-50%);
  z-index: 5;
  padding: 2px 10px;
  border: 1px solid rgba(240, 192, 80, 0.4);
  border-radius: 10px;
  background: rgba(30, 22, 4, 0.7);
  color: var(--ce-warning);
  font-size: 11px;
  pointer-events: none;
}

.cv-fatal {
  position: absolute;
  inset: 0;
  z-index: 9;
  display: grid;
  place-items: center;
  background: rgba(2, 5, 13, 0.7);
}
.cv-fatal__card {
  max-width: 380px;
  padding: 20px 22px;
  text-align: center;
}
.cv-fatal__card h4 {
  margin: 0 0 8px;
  font-size: 16px;
  color: var(--ce-text-strong);
}
.cv-fatal__card p {
  margin: 0 0 14px;
  color: var(--ce-text-dim);
  font-size: 13px;
}
.cv-fatal__btn {
  height: 30px;
  padding: 0 16px;
  border: 1px solid var(--ce-accent);
  border-radius: 3px;
  background: rgba(79, 195, 247, 0.12);
  color: var(--ce-text-strong);
  cursor: pointer;
}

.cv-caption {
  position: absolute;
  left: var(--scene-inset-left, 12px);
  right: var(--scene-inset-right, 12px);
  bottom: calc(var(--scene-inset-bottom, 12px) + 8px);
  z-index: 8;
  display: flex;
  justify-content: center;
  pointer-events: none;
  transition:
    left 0.35s var(--ce-ease),
    right 0.35s var(--ce-ease);
}

.cv-credits {
  position: absolute;
  left: 50%;
  bottom: 2px;
  transform: translateX(-50%);
  z-index: 4;
  max-width: 60%;
  white-space: nowrap;
  overflow: hidden;
  opacity: 0.5;
  font-size: 10px;
  color: #8aa3c4;
}
.cv-credits :deep(a) {
  color: #8aa3c4;
}
.cv-credits :deep(img) {
  max-height: 14px;
  vertical-align: middle;
}
</style>

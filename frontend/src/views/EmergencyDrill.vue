<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref } from 'vue'
import * as Cesium from 'cesium'
import { useRoute } from 'vue-router'
import { Aim, FirstAidKit, RefreshLeft, SwitchButton, Van, VideoPlay } from '@element-plus/icons-vue'
import CesiumViewer from '@/components/CesiumViewer.vue'
import { DRILL_SEEDS, type DrillSeed } from '@/data/drillSeeds'
import type { CrowdLayer } from '@/components/scene/crowd/crowdLayer'
import type { CrowdStats, VehicleStats } from '@/components/scene/crowd/types'
import { hazardProfile, requiresPedestrianEvacuation } from '@/components/scene/crowd/hazard'
import type { LayerVisibility } from '@/components/scene/types'

type DrillPhase = 'calm' | 'detected' | 'evacuating' | 'responding'

defineOptions({ name: 'EmergencyDrill' })

const viewerRef = ref<InstanceType<typeof CesiumViewer> | null>(null)
const route = useRoute()
const phase = ref<DrillPhase>('calm')
const seed = ref<DrillSeed | null>(null)
const selectedSeedKey = ref(DRILL_SEEDS[0].key)
const simulationSpeed = ref(4)
const initialAffected = ref(0)
const currentInRisk = ref(0)
const evacuationInside = ref(0)
const evacuated = ref(0)
const reactingPeople = ref(0)
const movingPeople = ref(0)
const waitingPeople = ref(0)
const safePeople = ref(0)
const hazardRadiusM = ref(0)
const replans = ref(0)
const trafficControlled = ref(false)
const elapsedSec = ref(0)
const peakWaiting = ref(0)
const bottleneckExit = ref('')
const activeExits = ref(0)
const closedRoads = ref(0)
const completed = ref(false)
const timelineEvents = ref<Array<{ time: number; text: string }>>([])
const responders = ref(0)
const actionText = ref('城市处于日常运行状态，可以随时开始一次异常事件演练。')
const crowdStats = ref<CrowdStats>({
  total: 0,
  moving: 0,
  byType: { resident: 0, tourist: 0, firefighter: 0, rescuer: 0 },
  byArea: {}
})
const vehicleStats = ref<VehicleStats>({
  total: 0,
  moving: 0,
  affected: 0,
  stopped: 0,
  rerouted: 0,
  averageSpeedKmh: 0
})
const layers = reactive<LayerVisibility>({
  buildings: true,
  buildingsFine: false,
  roads: true,
  events: false,
  pois: false,
  effects: false
})
let refreshTimer: number | undefined
let scene: Cesium.Viewer | null = null
let ready = false
let lastReplanCount = 0
let lastQuietRadius = 0
let queueEventShown = false
let autoStarted = false

const active = computed(() => phase.value !== 'calm' && !!seed.value)
const canEvacuate = computed(() => !!seed.value && requiresPedestrianEvacuation(seed.value.eventType))
const phaseText = computed(() => {
  if (phase.value === 'calm') return '城市运行平稳'
  if (seed.value?.eventType === 'traffic') {
    return phase.value === 'detected' ? '交通拥堵已识别' : '交通疏导进行中'
  }
  if (phase.value === 'detected') return '异常事件已识别'
  if (phase.value === 'evacuating') return '人员疏散进行中'
  return '多部门联动处置中'
})
const phaseHint = computed(() => {
  if (phase.value === 'calm') return '共享道路、建筑和应急资源均处于正常状态'
  if (phase.value === 'detected') return '系统已完成空间影响分析，等待启动疏散或处置'
  if (phase.value === 'evacuating') return '风险范围内人员正逐步响应警报并沿现有道路离开'
  if (seed.value?.eventType === 'traffic') return '事件路段车辆排队，已启动分流与疏导'
  return '救援与处置力量已进入事件影响区'
})
const accent = computed(() => seed.value?.color ?? '#72c39a')
const evacuationProgress = computed(() =>
  evacuated.value ? Math.max(0, Math.min(100, (safePeople.value / evacuated.value) * 100)) : 0
)
const selectedSeed = computed(() => DRILL_SEEDS.find((item) => item.key === selectedSeedKey.value) ?? DRILL_SEEDS[0])
const visibleTimeline = computed(() => timelineEvents.value.slice(-2))
const speedOptions = [1, 4, 8]

function formatElapsed(seconds: number): string {
  return `${Math.max(0, Math.round(seconds))}s`
}

function crowd(): CrowdLayer | null {
  return viewerRef.value?.getCrowd() ?? null
}

function pushTimeline(text: string, time = elapsedSec.value) {
  const last = timelineEvents.value[timelineEvents.value.length - 1]
  if (last?.text === text) return
  timelineEvents.value.push({ time: Math.max(0, time), text })
}

function setSimulationSpeed(speed: number) {
  simulationSpeed.value = speed
  crowd()?.setSimulationSpeed(speed)
}

function refreshStats() {
  const layer = crowd()
  if (!layer) return
  crowdStats.value = layer.getStats()
  vehicleStats.value = layer.getVehicleStats()
  if (active.value && seed.value) {
    const progress = layer.getEvacuationProgress()
    const currentRadius = progress.hazardRadiusM || seed.value.riskRadiusM
    currentInRisk.value = layer.countWithinRadius(seed.value.longitude, seed.value.latitude, currentRadius)
    evacuationInside.value = progress.inside
    reactingPeople.value = progress.reacting
    movingPeople.value = progress.moving
    waitingPeople.value = progress.waiting
    safePeople.value = progress.safe
    hazardRadiusM.value = currentRadius
    replans.value = progress.replans
    elapsedSec.value = progress.elapsedSec
    peakWaiting.value = progress.peakWaiting
    bottleneckExit.value = progress.bottleneckExitLabel
    activeExits.value = progress.activeExits
    closedRoads.value = progress.closedRoads
    if (progress.total > 0 && progress.total !== evacuated.value) {
      const added = Math.max(0, progress.total - evacuated.value)
      evacuated.value = progress.total
      actionText.value = `当前共 ${progress.total} 名模拟人员纳入疏散，剩余人员将按风险变化继续纳入。`
      if (added > 0) pushTimeline(`新增 ${added} 人进入当前风险区`)
    }
    if (progress.replans > lastReplanCount) {
      lastReplanCount = progress.replans
      if (lastReplanCount === 1) pushTimeline('风险变化后完成首轮动态重规划')
      else pushTimeline(`完成第 ${lastReplanCount} 轮动态重规划`)
    }
    if (progress.waiting > 0 && !queueEventShown) {
      queueEventShown = true
      pushTimeline('出口出现排队，系统开始统计瓶颈')
    }
    if (currentRadius >= lastQuietRadius + 20) {
      lastQuietRadius = currentRadius
      pushTimeline(`风险范围扩大至 ${Math.round(currentRadius)} 米`)
    }
    if (progress.completed && !completed.value) {
      completed.value = true
      pushTimeline(`人员疏散完成，用时 ${Math.max(1, Math.round(progress.elapsedSec))} 秒`)
    }
  }
}

function populateCalmCity() {
  const layer = crowd()
  if (!layer) return
  layer.clear()
  for (const item of DRILL_SEEDS) {
    layer.spawnAt(86, 'resident', item.longitude, item.latitude, Math.min(260, item.riskRadiusM * 1.2))
    layer.spawnAt(34, 'tourist', item.longitude, item.latitude, Math.min(220, item.riskRadiusM))
    layer.spawnVehicles(58, { lon: item.longitude, lat: item.latitude, radius: Math.max(280, item.riskRadiusM * 1.6) })
  }
  const [centerLon, centerLat] = viewerRef.value?.regionCenter() ?? [114.289, 30.592]
  layer.spawnAt(160, 'resident', centerLon, centerLat, 430)
  layer.spawnAt(60, 'tourist', centerLon, centerLat, 330)
  layer.spawnVehicles(80, { lon: centerLon, lat: centerLat, radius: 650 })
  layer.spawn(112, 'resident')
  layer.spawnVehicles(92)
  refreshStats()
}

async function resetView() {
  if (!viewerRef.value || !ready) return
  await viewerRef.value.flyTo(114.289, 30.592, { range: 2850, pitch: -62, heading: 0, duration: 1.5 })
}

function removeIncidentGraphic() {
  try {
    if (scene && !scene.isDestroyed()) scene.entities.removeAll()
  } catch {
    // Viewer 可能已先于父页面销毁，HMR 或快速路由切换时不应阻断卸载。
  }
}

function renderIncident(item: DrillSeed) {
  if (!scene) return
  scene.entities.removeAll()
  const color = Cesium.Color.fromCssColorString(item.color)
  const position = Cesium.Cartesian3.fromDegrees(item.longitude, item.latitude, 8)
  const radiusAt = () => hazardRadiusM.value || item.riskRadiusM
  const profile = hazardProfile(item.eventType)
  const innerColor = Cesium.Color.fromCssColorString(
    item.eventType === 'fire'
      ? '#ffb05c'
      : item.eventType === 'flood'
        ? '#4f9fc4'
        : item.eventType === 'building'
          ? '#9fb4b3'
          : '#d1b35f'
  )
  scene.entities.add({
    position,
    ellipse: {
      semiMajorAxis: new Cesium.CallbackProperty(() => radiusAt() * 0.56, false),
      semiMinorAxis: new Cesium.CallbackProperty(() => radiusAt() * 0.42, false),
      height: 3.2,
      material: innerColor.withAlpha(item.eventType === 'fire' ? 0.22 : 0.15)
    }
  })
  scene.entities.add({
    position,
    point: {
      pixelSize: 13,
      color,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    },
    label: {
      text: new Cesium.CallbackProperty(() => `${item.name}\n${profile.label} ${Math.round(radiusAt())} 米`, false),
      font: '600 14px "Microsoft YaHei UI","Microsoft YaHei",sans-serif',
      fillColor: Cesium.Color.WHITE,
      showBackground: true,
      backgroundColor: Cesium.Color.fromCssColorString('#111315').withAlpha(0.9),
      backgroundPadding: new Cesium.Cartesian2(9, 5),
      pixelOffset: new Cesium.Cartesian2(0, -34),
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    },
    ellipse: {
      semiMajorAxis: new Cesium.CallbackProperty(radiusAt, false),
      semiMinorAxis: new Cesium.CallbackProperty(radiusAt, false),
      height: 3,
      material: new Cesium.ColorMaterialProperty(
        new Cesium.CallbackProperty(() => {
          const wave = (Math.sin(Date.now() / 650) + 1) / 2
          return color.withAlpha(0.13 + wave * 0.06)
        }, false)
      ),
      outline: true,
      outlineColor: color.withAlpha(0.92),
      outlineWidth: 2
    }
  })
}

async function triggerIncident() {
  if (!ready || phase.value !== 'calm') return
  const layer = crowd()
  if (!layer) return
  const item = selectedSeed.value
  seed.value = item
  phase.value = 'detected'
  evacuated.value = 0
  reactingPeople.value = 0
  movingPeople.value = 0
  waitingPeople.value = 0
  safePeople.value = 0
  responders.value = 0
  trafficControlled.value = false
  elapsedSec.value = 0
  peakWaiting.value = 0
  bottleneckExit.value = ''
  activeExits.value = 0
  closedRoads.value = 0
  completed.value = false
  lastReplanCount = 0
  lastQuietRadius = item.riskRadiusM
  queueEventShown = false
  timelineEvents.value = []
  actionText.value = `已加载固定演示场景 ${item.sourceEventId}。`
  pushTimeline(`识别${item.typeLabel}：${item.name}`, 0)
  initialAffected.value = layer.countWithinRadius(item.longitude, item.latitude, item.riskRadiusM)
  currentInRisk.value = initialAffected.value
  evacuationInside.value = 0
  hazardRadiusM.value = item.riskRadiusM
  replans.value = 0
  layer.setHazardScenario(item.eventType, item.riskRadiusM)
  layer.setSimulationSpeed(simulationSpeed.value)
  layer.setVehicleIncident(item.longitude, item.latitude, item.riskRadiusM, item.eventType !== 'traffic')
  refreshStats()
  renderIncident(item)
  await nextTick()
  void viewerRef.value?.flyTo(item.longitude, item.latitude, {
    range: Math.max(560, item.riskRadiusM * 3.1),
    pitch: -42,
    heading: 18,
    duration: 1.7
  })
}

function startEvacuation() {
  const layer = crowd()
  const item = seed.value
  if (!layer || !item || !canEvacuate.value) return
  const moved = layer.evacuate(item.longitude, item.latitude, item.riskRadiusM)
  evacuated.value = moved
  phase.value = phase.value === 'responding' ? 'responding' : 'evacuating'
  actionText.value = `${moved} 名模拟人员已进入疏散队列，将按个体反应时间分批起步。`
  pushTimeline('启动人员疏散与安全出口选择')
  refreshStats()
}

function startTrafficControl() {
  const layer = crowd()
  const item = seed.value
  if (!layer || !item || item.eventType !== 'traffic' || trafficControlled.value) return
  const rerouted = layer.startTrafficControl()
  trafficControlled.value = true
  phase.value = 'responding'
  actionText.value = `已启动拥堵分流，${rerouted} 辆受影响车辆选择绕行路径。`
  pushTimeline(`启动交通疏导，${rerouted} 辆车开始分流`)
  refreshStats()
}

function dispatchResponse() {
  const layer = crowd()
  const item = seed.value
  if (!layer || !item) return
  let added = 0
  for (const group of item.responseMix) {
    added += layer.dispatchResponders(item.longitude, item.latitude, group.type, group.count)
  }
  responders.value += added
  layers.pois = true
  phase.value = 'responding'
  actionText.value = `${item.responseLabel}力量已抵达，共新增 ${added} 名模拟救援人员。`
  pushTimeline(`${item.responseLabel}力量进入现场`)
  refreshStats()
}

async function resetDrill() {
  removeIncidentGraphic()
  seed.value = null
  phase.value = 'calm'
  initialAffected.value = 0
  currentInRisk.value = 0
  evacuationInside.value = 0
  evacuated.value = 0
  reactingPeople.value = 0
  movingPeople.value = 0
  waitingPeople.value = 0
  safePeople.value = 0
  hazardRadiusM.value = 0
  replans.value = 0
  elapsedSec.value = 0
  peakWaiting.value = 0
  bottleneckExit.value = ''
  activeExits.value = 0
  closedRoads.value = 0
  completed.value = false
  timelineEvents.value = []
  responders.value = 0
  trafficControlled.value = false
  actionText.value = '演练已复位，城市恢复平静运行。'
  layers.pois = false
  const layer = crowd()
  layer?.clearVehicleIncident()
  layer?.clearHazardScenario()
  populateCalmCity()
  await resetView()
}

async function onReady() {
  ready = true
  scene = viewerRef.value?.getViewer() ?? null
  populateCalmCity()
  await resetView()
  if (autoStarted) return
  autoStarted = true
  const requested = Array.isArray(route.query.demo) ? route.query.demo[0] : route.query.demo
  const requestedSeed = DRILL_SEEDS.find((item) => item.key === requested || item.eventType === requested)
  if (!requestedSeed || route.query.autoplay !== '1') return
  selectedSeedKey.value = requestedSeed.key
  const requestedSpeed = Number(Array.isArray(route.query.speed) ? route.query.speed[0] : route.query.speed)
  setSimulationSpeed(Number.isFinite(requestedSpeed) ? requestedSpeed : 4)
  await triggerIncident()
  if (!requestedSeed.eventType || !requiresPedestrianEvacuation(requestedSeed.eventType)) return
  await new Promise((resolve) => window.setTimeout(resolve, 700))
  startEvacuation()
}

refreshTimer = window.setInterval(refreshStats, 400)
onBeforeUnmount(() => {
  if (refreshTimer) window.clearInterval(refreshTimer)
  removeIncidentGraphic()
  scene = null
})
</script>

<template>
  <div class="drill" :class="{ 'is-active': active }" :style="{ '--seed-color': accent }">
    <CesiumViewer
      ref="viewerRef"
      class="drill__scene"
      :layers="layers"
      basemap="satellite"
      :live-alerts="false"
      :intro="false"
      @ready="onReady"
    />

    <section class="drill-status" :class="{ 'is-active': active }">
      <div class="drill-status__identity">
        <span class="drill-status__mark"><Aim /></span>
        <div>
          <h2>{{ active && seed ? seed.typeLabel : '应急演练' }}</h2>
          <p>{{ active && seed ? seed.name : phaseHint }}</p>
        </div>
      </div>
      <span class="drill-status__state"><i />{{ phaseText }}</span>
      <div class="drill-status__counts">
        <span
          >人员 <b class="ce-num">{{ crowdStats.total }}</b></span
        >
        <span
          >车辆 <b class="ce-num">{{ vehicleStats.total }}</b></span
        >
        <span
          >异常 <b class="ce-num">{{ active ? 1 : 0 }}</b></span
        >
      </div>
      <div class="drill-speed" role="group" aria-label="演示倍速">
        <button
          v-for="speed in speedOptions"
          :key="speed"
          :class="{ active: simulationSpeed === speed }"
          :aria-pressed="simulationSpeed === speed"
          @click="setSimulationSpeed(speed)"
        >
          {{ speed }}×
        </button>
      </div>
      <button v-if="!active" class="drill-primary" :disabled="!ready" @click="triggerIncident">
        <VideoPlay />启动当前场景
      </button>
      <button v-else class="drill-reset" @click="resetDrill"><SwitchButton />结束并复位</button>
    </section>

    <section v-if="!active" class="calm-card">
      <div class="calm-card__head">
        <span>实时基线</span>
        <i>正常</i>
      </div>
      <strong>{{ phaseText }}</strong>
      <p>{{ actionText }}</p>
      <div class="scenario-picker" role="group" aria-label="选择演示场景">
        <button
          v-for="item in DRILL_SEEDS"
          :key="item.key"
          :class="{ active: selectedSeedKey === item.key }"
          :aria-pressed="selectedSeedKey === item.key"
          @click="selectedSeedKey = item.key"
        >
          <i :style="{ background: item.color }" />{{ item.typeLabel }}
        </button>
      </div>
      <dl>
        <div>
          <dt>模拟人员</dt>
          <dd class="ce-num">{{ crowdStats.total }}</dd>
        </div>
        <div>
          <dt>动态车辆</dt>
          <dd class="ce-num">{{ vehicleStats.total }}</dd>
        </div>
        <div>
          <dt>开放道路</dt>
          <dd class="ce-num">105</dd>
        </div>
      </dl>
      <button class="calm-card__view" @click="resetView"><RefreshLeft />回到全城视角</button>
    </section>

    <Transition name="incident">
      <aside v-if="active && seed" class="incident-card" :aria-labelledby="`incident-title-${seed.key}`">
        <div class="incident-card__content">
          <header>
            <div class="incident-card__type">
              <span>{{ seed.typeLabel }}</span>
              <b>{{ seed.severityLabel }}</b>
            </div>
            <button aria-label="结束演练并复位" @click="resetDrill"><SwitchButton /></button>
          </header>

          <div class="incident-card__title">
            <h2 :id="`incident-title-${seed.key}`">{{ seed.name }}</h2>
            <p>{{ seed.address }}</p>
          </div>

          <div class="incident-card__meta">
            <span>{{ seed.algorithm }}</span>
            <span>种子 {{ seed.sourceEventId }}</span>
            <span>置信度 {{ Math.round(seed.confidence * 100) }}%</span>
          </div>

          <p class="incident-card__desc">{{ seed.description }}</p>

          <div v-if="seed.eventType === 'traffic'" class="traffic-grid">
            <div>
              <span>平均车速</span>
              <b class="ce-num">{{ vehicleStats.averageSpeedKmh }}</b>
              <small>km/h · 路网模拟车辆</small>
            </div>
            <div>
              <span>排队车辆</span>
              <b class="ce-num">{{ vehicleStats.stopped }}</b>
              <small>事件核心区停车</small>
            </div>
            <div>
              <span>受影响车辆</span>
              <b class="ce-num">{{ vehicleStats.affected }}</b>
              <small>减速或排队</small>
            </div>
            <div>
              <span>累计绕行</span>
              <b class="ce-num">{{ vehicleStats.rerouted }}</b>
              <small>选择替代路径</small>
            </div>
          </div>
          <div v-else class="impact-grid">
            <div>
              <span>受影响人员</span>
              <b class="ce-num">{{ currentInRisk }}</b>
              <small>基线 {{ initialAffected }} · 当前风险区</small>
            </div>
            <div>
              <span>受影响车辆</span>
              <b class="ce-num">{{ vehicleStats.affected }}</b>
              <small>累计绕行 {{ vehicleStats.rerouted }}</small>
            </div>
            <div>
              <span>关联建筑</span>
              <b class="ce-num">{{ seed.affectedBuildings }}</b>
              <small>风险半径内</small>
            </div>
            <div>
              <span>疏散进度</span>
              <b class="ce-num">{{ Math.round(evacuationProgress) }}%</b>
              <small>{{ evacuated }} 人纳入疏散</small>
            </div>
          </div>

          <div
            v-if="initialAffected && canEvacuate"
            class="evac-progress"
            role="progressbar"
            aria-label="人员疏散进度"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-valuenow="Math.round(evacuationProgress)"
          >
            <i :style="{ width: `${evacuationProgress}%` }" />
          </div>

          <div class="incident-metrics">
            <div v-for="metric in seed.metrics" :key="metric.label">
              <span>{{ metric.label }}</span>
              <b>{{ metric.value }}</b>
            </div>
          </div>

          <p class="incident-card__action">{{ actionText }}</p>
        </div>

        <div class="incident-card__controls">
          <div v-if="active && seed.eventType === 'traffic'" class="mobile-traffic-summary">
            <span
              ><small>平均车速</small><b class="ce-num">{{ vehicleStats.averageSpeedKmh }}</b></span
            >
            <span
              ><small>排队车辆</small><b class="ce-num">{{ vehicleStats.stopped }}</b></span
            >
            <span
              ><small>受影响</small><b class="ce-num">{{ vehicleStats.affected }}</b></span
            >
            <span
              ><small>累计绕行</small><b class="ce-num">{{ vehicleStats.rerouted }}</b></span
            >
          </div>
          <div v-if="active && seed.eventType !== 'traffic'" class="mobile-impact-summary">
            <span
              ><small>风险人员</small><b class="ce-num">{{ currentInRisk }}</b></span
            >
            <span
              ><small>受影响车辆</small><b class="ce-num">{{ vehicleStats.affected }}</b></span
            >
            <span
              ><small>关联建筑</small><b class="ce-num">{{ seed.affectedBuildings }}</b></span
            >
            <span
              ><small>纳入疏散</small><b class="ce-num">{{ evacuated }}</b></span
            >
          </div>
          <div v-if="evacuated" class="mobile-progress">
            <span>疏散进度</span>
            <b class="ce-num">{{ Math.round(evacuationProgress) }}%</b>
            <i><em :style="{ width: `${evacuationProgress}%` }" /></i>
          </div>
          <ol v-if="visibleTimeline.length" class="event-timeline" aria-label="推演过程">
            <li v-for="item in visibleTimeline" :key="`${item.time}-${item.text}`">
              <time>{{ formatElapsed(item.time) }}</time>
              <span>{{ item.text }}</span>
            </li>
          </ol>
          <div v-if="evacuated" class="motion-state" role="group" aria-label="人员疏散状态">
            <span
              >等待反应 <b class="ce-num">{{ reactingPeople }}</b></span
            >
            <span
              >移动中 <b class="ce-num">{{ movingPeople }}</b></span
            >
            <span
              >出口排队 <b class="ce-num">{{ waitingPeople }}</b></span
            >
            <span
              >已到达 <b class="ce-num">{{ safePeople }}</b></span
            >
          </div>
          <div v-if="evacuated" class="dynamic-state">
            <span>当前风险 {{ Math.round(hazardRadiusM) }} m</span>
            <span>动态重规划 {{ replans }} 次</span>
            <span>出口 {{ activeExits }} 个</span>
            <span>封闭路段 {{ closedRoads }}</span>
          </div>
          <div v-if="completed" class="completion-summary">
            <b>疏散完成</b>
            <span>用时 {{ formatElapsed(elapsedSec) }} · 峰值排队 {{ peakWaiting }} 人</span>
            <small>{{ bottleneckExit ? `瓶颈出口 ${bottleneckExit}` : '未形成明显出口瓶颈' }}</small>
          </div>
          <div class="incident-actions">
            <button
              v-if="seed.eventType === 'traffic'"
              class="incident-actions__secondary"
              :disabled="trafficControlled"
              @click="startTrafficControl"
            >
              <Van />{{ trafficControlled ? '分流已启动' : '启动交通疏导' }}
            </button>
            <button
              v-else
              class="incident-actions__secondary"
              :disabled="evacuated > 0 || !canEvacuate"
              @click="startEvacuation"
            >
              <VideoPlay />{{ canEvacuate ? '开始疏散' : '无需人员疏散' }}
            </button>
            <button class="incident-actions__primary" :disabled="responders > 0" @click="dispatchResponse">
              <FirstAidKit />派发处置
            </button>
          </div>
          <div class="incident-card__footer">
            <span>当前风险半径 {{ Math.round(hazardRadiusM || seed.riskRadiusM) }} 米</span>
            <span>已调度 {{ responders }} 人</span>
          </div>
        </div>
      </aside>
    </Transition>

    <div class="drill-legend" role="group" aria-label="演练图例">
      <span><i class="people" />模拟人员</span>
      <span><i class="vehicles" />动态车辆</span>
      <span><i class="risk" :style="{ borderColor: accent }" />影响范围</span>
      <span><i class="route" />规划路线</span>
      <span><i class="hazard-risk" />高风险路段</span>
      <span><i class="restricted" />封闭核心</span>
      <em>演练数据</em>
    </div>
  </div>
</template>

<style scoped>
.drill {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0f1011;
}
.drill__scene {
  position: absolute;
  inset: 0;
}
.drill-status {
  position: absolute;
  z-index: 8;
  top: 14px;
  left: 50%;
  display: flex;
  align-items: center;
  gap: 18px;
  width: min(1120px, calc(100% - 48px));
  min-height: 56px;
  padding: 8px 10px 8px 12px;
  transform: translateX(-50%);
  border: 1px solid var(--ce-panel-border);
  border-radius: 6px;
  background: var(--ce-panel-solid);
}
.drill-status__identity {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 260px;
}
.drill-status__mark {
  display: grid;
  flex: none;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--ce-panel-border-strong);
  border-radius: 4px;
  color: var(--ce-text);
}
.drill-status__mark svg {
  width: 18px;
  height: 18px;
}
.drill-status h2 {
  margin: 0;
  font-size: 19px;
  font-weight: 600;
  line-height: 1.2;
  color: var(--ce-text-strong);
}
.drill-status__identity p {
  margin: 3px 0 0;
  overflow: hidden;
  font-size: 13px;
  color: var(--ce-text-dim);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.drill-status__state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 26px;
  padding: 0 9px;
  border: 1px solid #334138;
  border-radius: 4px;
  font-size: 12.5px;
  color: var(--ce-success);
  white-space: nowrap;
}
.drill-status__state i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.drill-status.is-active .drill-status__state {
  border-color: color-mix(in srgb, var(--seed-color) 55%, var(--ce-panel-border));
  color: var(--seed-color);
}
.drill-status__counts {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-left: auto;
  color: var(--ce-text-dim);
  font-size: 13px;
  white-space: nowrap;
}
.drill-status__counts span {
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
}
.drill-status__counts b {
  font-size: 16px;
  font-weight: 500;
  color: var(--ce-text-strong);
}
.drill-speed {
  display: flex;
  flex: none;
  gap: 10px;
  padding: 2px 0;
  border: 0;
}
.drill-speed button {
  position: relative;
  min-width: 34px;
  height: 26px;
  padding: 0 2px;
  border: 0;
  background: transparent;
  color: var(--ce-text-faint);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.drill-speed button.active {
  background: transparent;
  color: var(--ce-text-strong);
}
.drill-speed button.active::after {
  position: absolute;
  right: 0;
  bottom: -3px;
  left: 0;
  height: 1px;
  background: var(--ce-accent);
  content: '';
}
.drill-primary,
.drill-reset {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 36px;
  padding: 0 15px;
  border: 1px solid transparent;
  border-radius: 4px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.drill-primary {
  color: #101215;
  background: #edf1f3;
}
.drill-primary:hover {
  background: #fff;
}
.drill-primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.drill-primary svg,
.drill-reset svg,
.calm-card__view svg,
.incident-actions svg {
  width: 15px;
  height: 15px;
}
.drill-reset {
  color: #f3d9da;
  border-color: #6d4145;
  background: #2c1b1d;
}
.drill-reset:hover {
  background: #3a2023;
}
.calm-card {
  position: absolute;
  z-index: 7;
  left: 24px;
  bottom: 54px;
  width: 320px;
  padding: 18px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 6px;
  background: var(--ce-panel-solid);
}
.calm-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  color: var(--ce-text-faint);
  font-size: 13px;
}
.calm-card__head i {
  font-style: normal;
  color: var(--ce-success);
}
.calm-card > strong {
  font-size: 22px;
  font-weight: 600;
  color: var(--ce-text-strong);
}
.calm-card > p {
  margin: 6px 0 15px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--ce-text-dim);
}
.scenario-picker {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-bottom: 15px;
}
.scenario-picker button {
  position: relative;
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  height: 34px;
  padding: 0 4px;
  border: 0;
  border-bottom: 1px solid var(--ce-divider);
  border-radius: 0;
  background: transparent;
  color: var(--ce-text-dim);
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}
.scenario-picker button.active {
  border-color: color-mix(in srgb, var(--ce-accent) 54%, var(--ce-divider));
  color: var(--ce-text-strong);
  background: transparent;
}
.scenario-picker i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.calm-card dl {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin: 0;
  border-top: 1px solid var(--ce-divider);
  border-bottom: 1px solid var(--ce-divider);
}
.calm-card dl > div {
  padding: 10px 8px;
}
.calm-card dl > div + div {
  border-left: 1px solid var(--ce-divider);
}
.calm-card dt {
  font-size: 13px;
  color: var(--ce-text-faint);
}
.calm-card dd {
  margin: 4px 0 0;
  font-size: 19px;
  color: var(--ce-text-strong);
}
.calm-card__view {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ce-text-dim);
  font: inherit;
  font-size: 12.5px;
  cursor: pointer;
}
.calm-card__view:hover {
  color: var(--ce-text-strong);
}
.incident-card {
  position: absolute;
  z-index: 8;
  top: 76px;
  right: 20px;
  display: flex;
  flex-direction: column;
  width: min(384px, calc(100% - 40px));
  max-height: calc(100% - 96px);
  padding: 18px;
  overflow: hidden;
  border: 1px solid var(--ce-panel-border);
  border-left: 2px solid var(--seed-color);
  border-radius: 6px;
  background: var(--ce-panel-solid);
}
.incident-card__content {
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}
.incident-card__controls {
  flex: none;
  padding-top: 10px;
  border-top: 1px solid var(--ce-divider);
}
.mobile-progress {
  display: none;
}
.mobile-impact-summary {
  display: none;
}
.mobile-traffic-summary {
  display: none;
}
.incident-card header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.incident-card header button {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid var(--ce-panel-border);
  border-radius: 4px;
  background: transparent;
  color: var(--ce-text-dim);
  cursor: pointer;
}
.incident-card header button svg {
  width: 15px;
  height: 15px;
}
.incident-card__type {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
}
.incident-card__type span {
  color: var(--seed-color);
}
.incident-card__type b {
  padding: 1px 6px;
  border: 1px solid color-mix(in srgb, var(--seed-color) 55%, transparent);
  border-radius: 3px;
  color: var(--seed-color);
  font-weight: 500;
}
.incident-card__title {
  margin-top: 12px;
}
.incident-card__title h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--ce-text-strong);
}
.incident-card__title p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--ce-text-dim);
}
.incident-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.incident-card__meta span {
  padding: 2px 7px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 3px;
  color: var(--ce-text-dim);
  font-size: 13px;
}
.incident-card__desc {
  margin: 12px 0;
  padding: 10px 11px;
  border-left: 2px solid var(--seed-color);
  background: #141618;
  color: var(--ce-text);
  font-size: 13.5px;
  line-height: 1.65;
}
.incident-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  border: 1px solid var(--ce-divider);
}
.incident-metrics > div {
  padding: 9px;
  background: #141618;
}
.incident-metrics > div + div {
  border-left: 1px solid var(--ce-divider);
}
.incident-metrics span {
  display: block;
  font-size: 13px;
  color: var(--ce-text-faint);
}
.incident-metrics b {
  display: block;
  margin-top: 4px;
  font-size: 17px;
  font-weight: 500;
  color: var(--ce-text-strong);
}
.impact-grid,
.traffic-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  margin-top: 12px;
  border: 1px solid var(--ce-divider);
  background: var(--ce-divider);
}
.impact-grid > div,
.traffic-grid > div {
  padding: 10px 11px;
  background: #141618;
}
.impact-grid span,
.traffic-grid span {
  display: block;
  font-size: 13px;
  color: var(--ce-text-faint);
}
.impact-grid b,
.traffic-grid b {
  display: inline-block;
  margin-top: 3px;
  font-size: 25px;
  font-weight: 500;
  color: var(--ce-text-strong);
}
.impact-grid small,
.traffic-grid small {
  display: block;
  margin-top: 1px;
  font-size: 13px;
  color: var(--ce-text-dim);
}
.evac-progress {
  height: 4px;
  margin-top: 12px;
  overflow: hidden;
  background: var(--ce-divider);
}
.evac-progress i {
  display: block;
  height: 100%;
  background: var(--seed-color);
  transition: width 0.35s linear;
}
.incident-card__action {
  min-height: 36px;
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--ce-text-dim);
}
.event-timeline {
  display: grid;
  gap: 8px;
  margin: 12px 0 2px;
  padding: 10px 0 0;
  border-top: 1px solid var(--ce-divider);
  list-style: none;
}
.incident-card__controls > .event-timeline {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
}
.event-timeline li {
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 8px;
  font-size: 13px;
  line-height: 1.45;
  color: var(--ce-text-dim);
}
.event-timeline time {
  font-variant-numeric: tabular-nums;
  color: var(--ce-text-faint);
}
.motion-state {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 9px;
  color: var(--ce-text-faint);
  font-size: 13px;
}
.motion-state b {
  margin-left: 3px;
  font-weight: 500;
  color: var(--ce-text-strong);
}
.dynamic-state {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px 12px;
  margin-bottom: 9px;
  color: var(--ce-text-faint);
  font-size: 13px;
}
.completion-summary {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px 10px;
  margin-bottom: 9px;
  padding: 8px 10px;
  border-left: 2px solid var(--ce-success);
  background: var(--ce-active);
  font-size: 13px;
  color: var(--ce-text-dim);
}
.completion-summary b {
  grid-row: span 2;
  color: var(--ce-success);
  font-weight: 600;
}
.completion-summary small {
  font-size: 12.5px;
  color: var(--ce-text-faint);
}
.incident-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.incident-actions button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 36px;
  border-radius: 4px;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.incident-actions button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.incident-actions__secondary {
  color: var(--ce-text);
  border: 1px solid var(--ce-panel-border-strong);
  background: transparent;
}
.incident-actions__primary {
  color: #101215;
  border: 1px solid transparent;
  background: var(--seed-color);
}
.incident-card__footer {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
  font-size: 13px;
  color: var(--ce-text-faint);
}
.drill-legend {
  position: absolute;
  z-index: 7;
  right: 20px;
  bottom: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 10px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 4px;
  background: var(--ce-panel-solid);
  color: var(--ce-text-dim);
  font-size: 13px;
}
.drill-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.drill-legend i {
  display: inline-block;
  width: 12px;
  height: 4px;
  border-radius: 1px;
}
.drill-legend .people {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #4fc3f7;
}
.drill-legend .vehicles {
  background: #c6cdd1;
}
.drill-legend .risk {
  width: 12px;
  height: 8px;
  border: 1px solid;
  border-radius: 50%;
  background: transparent;
}
.drill-legend .route {
  background: #5ddcff;
}
.drill-legend .hazard-risk {
  background: #d9a45d;
}
.drill-legend .restricted {
  background: #ff5b5b;
}
.drill-legend em {
  font-style: normal;
  color: var(--ce-warning);
}
.drill.is-active .drill-legend {
  right: 424px;
}
.incident-enter-active,
.incident-leave-active {
  transition:
    opacity 0.24s ease,
    transform 0.28s var(--ce-ease);
}
.incident-enter-from,
.incident-leave-to {
  opacity: 0;
  transform: translateX(24px);
}
.drill-speed button:focus-visible,
.scenario-picker button:focus-visible,
.incident-actions button:focus-visible,
.drill-primary:focus-visible,
.drill-reset:focus-visible,
.calm-card__view:focus-visible {
  outline: 2px solid var(--ce-accent);
  outline-offset: 2px;
}
@media (max-width: 900px) {
  .drill-status {
    flex-wrap: wrap;
    gap: 8px 12px;
  }
  .drill-status__identity {
    flex: 1;
    min-width: 200px;
  }
  .drill-status__counts {
    order: 3;
    width: 100%;
    margin-left: 0;
    padding-top: 7px;
    border-top: 1px solid var(--ce-divider);
  }
  .drill-speed {
    margin-left: auto;
  }
  .calm-card {
    left: 16px;
    bottom: 48px;
  }
  .drill-legend {
    display: none;
  }
}
@media (max-width: 700px) {
  .drill-status {
    top: 10px;
    width: calc(100% - 24px);
    padding: 9px;
  }
  .drill-status__identity p {
    display: none;
  }
  .drill-status h2 {
    font-size: 17px;
  }
  .drill-status__state {
    order: 4;
    margin-left: 0;
  }
  .drill-status__counts {
    gap: 10px;
  }
  .drill-speed {
    order: 3;
    margin-left: 0;
  }
  .drill-primary,
  .drill-reset {
    height: 34px;
    padding-inline: 11px;
    font-size: 12px;
  }
  .calm-card {
    right: 12px;
    bottom: 52px;
    left: 12px;
    width: auto;
  }
  .calm-card > p {
    margin-bottom: 10px;
  }
  .incident-card {
    top: auto;
    right: 12px;
    bottom: 12px;
    left: 12px;
    width: auto;
    max-height: calc(100% - 212px);
    padding: 13px;
  }
  .incident-card__title h2 {
    font-size: 20px;
  }
  .incident-card__desc {
    display: -webkit-box;
    margin-block: 8px;
    padding-block: 0;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }
  .incident-card__controls > .event-timeline li:nth-last-child(n + 2) {
    display: none;
  }
  .impact-grid {
    display: none;
  }
  .traffic-grid {
    display: none;
  }
  .mobile-impact-summary {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    margin-bottom: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--ce-divider);
  }
  .mobile-impact-summary span {
    min-width: 0;
    padding: 0 7px;
    border-left: 1px solid var(--ce-divider);
  }
  .mobile-impact-summary span:first-child {
    padding-left: 0;
    border-left: 0;
  }
  .mobile-impact-summary small {
    display: block;
    font-size: 12px;
    color: var(--ce-text-faint);
    white-space: nowrap;
  }
  .mobile-impact-summary b {
    display: block;
    margin-top: 2px;
    font-size: 20px;
    font-weight: 500;
    color: var(--ce-text-strong);
  }
  .mobile-traffic-summary {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    margin-bottom: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--ce-divider);
  }
  .mobile-traffic-summary span {
    min-width: 0;
    padding: 0 7px;
    border-left: 1px solid var(--ce-divider);
  }
  .mobile-traffic-summary span:first-child {
    padding-left: 0;
    border-left: 0;
  }
  .mobile-traffic-summary small {
    display: block;
    overflow: hidden;
    font-size: 12px;
    color: var(--ce-text-faint);
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .mobile-traffic-summary b {
    display: block;
    margin-top: 2px;
    font-size: 20px;
    font-weight: 500;
    color: var(--ce-text-strong);
  }
  .mobile-progress {
    display: grid;
    grid-template-columns: auto auto;
    align-items: baseline;
    gap: 4px 8px;
    margin-bottom: 9px;
    font-size: 13px;
    color: var(--ce-text-dim);
  }
  .mobile-progress b {
    justify-self: end;
    color: var(--ce-text-strong);
    font-weight: 500;
  }
  .mobile-progress i {
    grid-column: 1 / -1;
    height: 3px;
    overflow: hidden;
    background: var(--ce-divider);
  }
  .mobile-progress em {
    display: block;
    height: 100%;
    background: var(--seed-color);
  }
  .drill-legend {
    display: none;
  }
}
</style>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Delete, Position, VideoPlay } from '@element-plus/icons-vue'
import type { CrowdLayer } from '@/components/scene/crowd/crowdLayer'
import { PERSON_META, type CrowdBenchmarkRow, type CrowdStats, type SpawnType } from '@/components/scene/crowd/types'

const props = defineProps<{ crowd: CrowdLayer | null }>()

const count = ref(100)
const type = ref<SpawnType>('mixed')
const dangerRadius = ref(260)
const busy = ref(false)
const message = ref('')
const benchmark = ref<CrowdBenchmarkRow[]>([])
const emptyStats: CrowdStats = {
  total: 0,
  moving: 0,
  byType: { resident: 0, tourist: 0, firefighter: 0, rescuer: 0 },
  byArea: {}
}
const emptyEvacuation = {
  total: 0,
  inside: 0,
  escaped: 0,
  reacting: 0,
  moving: 0,
  waiting: 0,
  safe: 0,
  hazardRadiusM: 0,
  replans: 0,
  elapsedSec: 0,
  peakWaiting: 0,
  bottleneckExitLabel: '',
  activeExits: 0,
  closedRoads: 0,
  completed: false
}
const stats = ref<CrowdStats>(emptyStats)
const evacuation = ref(emptyEvacuation)
let timer = 0

const typeOptions = [
  { value: 'mixed', label: '混合人群' },
  ...Object.entries(PERSON_META).map(([value, meta]) => ({ value, label: meta.label }))
]
const ready = computed(() => !!props.crowd)

function refreshStats() {
  stats.value = props.crowd?.getStats() ?? emptyStats
  evacuation.value = props.crowd?.getEvacuationProgress() ?? emptyEvacuation
}

function generate() {
  if (!props.crowd) return
  props.crowd.clear()
  const added = props.crowd.spawn(count.value, type.value)
  message.value = `已生成 ${added} 人`
  refreshStats()
}

function gatherTourists() {
  if (!props.crowd) return
  const [lon, lat] = props.crowd.regionCenter()
  const added = props.crowd.spawnAt(count.value, 'tourist', lon, lat, 150)
  message.value = `区域中心新增 ${added} 名游客`
  refreshStats()
}

function evacuate() {
  if (!props.crowd) return
  const [lon, lat] = props.crowd.regionCenter()
  const moved = props.crowd.evacuate(lon, lat, dangerRadius.value)
  message.value = moved ? `${moved} 人开始沿道路疏散` : '危险区内没有人员，请先生成或聚集人群'
  refreshStats()
}

function clearPeople() {
  if (!props.crowd) return
  props.crowd.clear()
  message.value = '人群已清空'
  refreshStats()
}

function focusPeople() {
  if (props.crowd?.focus()) message.value = '已定位到人群中心'
}

function walkFirstPerson() {
  if (!props.crowd) return
  const [lon, lat] = props.crowd.regionCenter()
  message.value = props.crowd.walkFirstTo(lon, lat) ? '第一个人正在向区域中心行走' : '请先生成人员'
}

function scaleFirstPerson() {
  const id = props.crowd?.firstPersonId()
  const person = id ? props.crowd?.getPerson(id) : null
  if (!id || !person || !props.crowd) return
  props.crowd.setScale(id, person.scale >= 2 ? 1 : person.scale + 0.5)
  message.value = '首个人员缩放已调整'
}

function rotateFirstPerson() {
  const id = props.crowd?.firstPersonId()
  const person = id ? props.crowd?.getPerson(id) : null
  if (!id || !person || !props.crowd) return
  props.crowd.setHeading(id, person.heading + Math.PI / 4)
  message.value = '首个人员已旋转 45°'
}

async function runBenchmark() {
  if (!props.crowd || busy.value) return
  busy.value = true
  message.value = '正在运行 1 → 1000 人性能测试…'
  try {
    benchmark.value = await props.crowd.benchmark()
    message.value = '性能测试完成'
  } finally {
    busy.value = false
    refreshStats()
  }
}

onMounted(() => {
  refreshStats()
  timer = window.setInterval(refreshStats, 500)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <section class="crowd-panel">
    <div class="cp-summary">
      <div><b>{{ stats.total }}</b><span>总人数</span></div>
      <div><b>{{ stats.moving }}</b><span>移动中</span></div>
      <div v-for="(meta, key) in PERSON_META" :key="key">
        <b :style="{ color: meta.color }">{{ stats.byType[key] }}</b><span>{{ meta.label }}</span>
      </div>
    </div>

    <div class="cp-controls">
      <label>人数</label>
      <el-input-number v-model="count" :min="1" :max="1000" :step="1" :disabled="!ready || busy" />
      <label>类型</label>
      <el-select v-model="type" :disabled="!ready || busy">
        <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <label>危险半径</label>
      <el-input-number v-model="dangerRadius" :min="50" :max="1500" :step="50" :disabled="!ready || busy" />
    </div>

    <div class="cp-actions">
      <el-button type="primary" :disabled="!ready || busy" @click="generate">生成 / 重置人群</el-button>
      <el-button :disabled="!ready || busy" @click="gatherTourists">中心聚集游客</el-button>
      <el-button type="danger" plain :icon="Position" :disabled="!ready || busy" @click="evacuate">开始疏散</el-button>
      <el-button :disabled="!ready || busy || stats.total === 0" @click="walkFirstPerson">单人行进</el-button>
      <el-button :disabled="!ready || busy || stats.total === 0" @click="scaleFirstPerson">首人缩放</el-button>
      <el-button :disabled="!ready || busy || stats.total === 0" @click="rotateFirstPerson">首人旋转</el-button>
      <el-button :disabled="!ready || busy || stats.total === 0" @click="focusPeople">定位人群</el-button>
      <el-button :icon="Delete" :disabled="!ready || busy || stats.total === 0" @click="clearPeople">
        清空
      </el-button>
    </div>

    <p class="cp-message">{{ message || (ready ? '人群图层已就绪，点击生成才会创建对象。' : '正在初始化 Three.js 人群图层…') }}</p>
    <p v-if="evacuation.total" class="cp-evacuation">
      疏散状态：反应 {{ evacuation.reacting }} · 移动 {{ evacuation.moving }} · 出口排队
      {{ evacuation.waiting }} · 安全 {{ evacuation.safe }} · 风险半径
      {{ Math.round(evacuation.hazardRadiusM) }} m · 动态重规划 {{ evacuation.replans }} 次 ·
      出口 {{ evacuation.activeExits }} · 封路 {{ evacuation.closedRoads }}
    </p>

    <div v-if="Object.keys(stats.byArea).length" class="cp-areas">
      <span class="cp-subtitle">区域人数</span>
      <div class="cp-area-list">
        <span v-for="(value, key) in stats.byArea" :key="key">{{ key }} <b>{{ value }}</b></span>
      </div>
    </div>

    <div class="cp-benchmark">
      <div class="cp-benchmark__head">
        <span class="cp-subtitle">性能测试</span>
        <el-button :icon="VideoPlay" size="small" :loading="busy" :disabled="!ready" @click="runBenchmark">
          运行 1 → 1000
        </el-button>
      </div>
      <el-table v-if="benchmark.length" :data="benchmark" size="small">
        <el-table-column prop="people" label="人数" width="70" />
        <el-table-column prop="fps" label="渲染吞吐/s" width="95" />
        <el-table-column prop="frameMs" label="帧耗时(ms)" width="95" />
        <el-table-column prop="drawCalls" label="Draw Calls" width="90" />
        <el-table-column prop="triangles" label="三角形" />
      </el-table>
    </div>
  </section>
</template>

<style scoped>
.crowd-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.cp-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.cp-summary > div {
  padding: 10px 8px;
  border: 1px solid rgba(64, 120, 180, 0.28);
  border-radius: 6px;
  background: rgba(8, 22, 46, 0.72);
}
.cp-summary b {
  display: block;
  font-size: 20px;
  color: #d6eeff;
}
.cp-summary span {
  font-size: 11px;
  color: #7891b1;
}
.cp-controls {
  display: grid;
  grid-template-columns: 72px 1fr;
  align-items: center;
  gap: 10px 12px;
}
.cp-controls label {
  font-size: 12px;
  color: #8fa7c4;
}
.cp-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.cp-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}
.cp-message {
  min-height: 20px;
  margin: 0;
  font-size: 12px;
  color: #7f9bbb;
}
.cp-evacuation {
  margin: 0;
  padding: 9px 10px;
  border: 1px solid rgba(64, 120, 180, 0.24);
  border-radius: 4px;
  background: rgba(8, 22, 46, 0.5);
  font-size: 12px;
  color: #aabdd7;
}
.cp-subtitle {
  display: block;
  margin-bottom: 8px;
  font-size: 11px;
  letter-spacing: 1px;
  color: #7891b1;
}
.cp-area-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.cp-area-list span {
  padding: 4px 8px;
  font-size: 11.5px;
  color: #aabdd7;
  border: 1px solid rgba(64, 120, 180, 0.24);
  border-radius: 4px;
}
.cp-area-list b {
  color: #66dbff;
}
.cp-benchmark__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.cp-benchmark__head .cp-subtitle {
  margin: 0;
}
</style>

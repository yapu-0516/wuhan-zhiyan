<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  Clock,
  Delete,
  Download,
  Document,
  Edit,
  FullScreen,
  RefreshLeft,
  Setting,
  Tickets,
  VideoPause,
  VideoPlay
} from '@element-plus/icons-vue'
import type CesiumViewer from '@/components/CesiumViewer.vue'
import { getEvents } from '@/api/event'
import { getRoads } from '@/api/geo'
import {
  compareScenarioRuns,
  createScenarioTemplate,
  createScenarioSession,
  deleteScenarioTemplate,
  getScenarioTemplates,
  getScenarioTemplateRevisions,
  generateScenarioReport,
  patchScenarioTemplate,
  runCurrentScenarioVariants,
  scenarioExportUrl,
  sendScenarioMessage,
  setScenarioResources
} from '@/api/scenario'
import { getEmergencyResources } from '@/api/support'
import { dispatchScenarioRun } from '@/api/workflow'
import { errMsg } from '@/composables/pages/format'
import type {
  ScenarioComparison,
  ScenarioFrame,
  ScenarioReport,
  ScenarioRun,
  ScenarioSessionView,
  ScenarioTemplate,
  ScenarioTemplateRevision
} from '@/types/scenario'
import { SCENARIO_LABEL } from '@/types/scenario'
import { ScenarioLayer } from '@/components/scene/scenario/scenarioLayer'
import type { CityEvent } from '@/types/event'
import type { WorkOrder } from '@/types/workflow'
import type { EmergencyResource } from '@/types/support'

const props = defineProps<{
  viewer: InstanceType<typeof CesiumViewer> | null
  embedded?: boolean
  sourceEventId?: string
}>()
const emit = defineEmits<{ (event: 'view-map'): void; (event: 'close'): void }>()
const router = useRouter()

const session = ref<ScenarioSessionView | null>(null)
const input = ref('')
const busy = ref(false)
const error = ref('')
const run = ref<ScenarioRun | null>(null)
const variants = ref<ScenarioRun[]>([])
const frameIndex = ref(0)
const playing = ref(false)
const report = ref<ScenarioReport | null>(null)
const comparison = ref<ScenarioComparison | null>(null)
const mapVisible = ref(true)
const businessEvents = ref<CityEvent[]>([])
const dispatchVisible = ref(false)
const dispatchBusy = ref(false)
const dispatchError = ref('')
const dispatchEventId = ref('')
const dispatchedOrders = ref<WorkOrder[]>([])
const templates = ref<ScenarioTemplate[]>([])
const templateVisible = ref(false)
const templateName = ref('')
const templateDescription = ref('')
const templateBusy = ref(false)
const templateManageVisible = ref(false)
const editingTemplateId = ref('')
const templateEditName = ref('')
const templateEditDescription = ref('')
const templateEditType = ref<ScenarioTemplate['scenario_type']>('flood')
const templateEditParameters = ref('{}')
const templateHistoryVisible = ref(false)
const templateHistory = ref<ScenarioTemplateRevision[]>([])
const resourceVisible = ref(false)
const resourceBusy = ref(false)
const resources = ref<EmergencyResource[]>([])
const selectedResourceIds = ref<string[]>([])
let layer: ScenarioLayer | null = null
let timer = 0

const currentFrame = computed<ScenarioFrame | null>(() => run.value?.frames[frameIndex.value] ?? null)
const previousFrame = computed<ScenarioFrame | null>(() =>
  frameIndex.value > 0 ? (run.value?.frames[frameIndex.value - 1] ?? null) : null
)
const dataClassLabel = computed(() => (run.value ? classLabel(run.value.data_classification) : ''))
const currentRadius = computed(() => currentFrame.value?.zones[0]?.radius_m ?? null)
const impactArea = computed(() => {
  const radius = currentRadius.value
  return radius === null ? '—' : `${(Math.PI * (radius / 1000) ** 2).toFixed(2)} km²`
})
const extentChange = computed(() => {
  const current = currentRadius.value
  const previous = previousFrame.value?.zones[0]?.radius_m
  if (current === null) return '—'
  if (previous === null || previous === undefined) return '起始帧'
  const delta = Math.round(current - previous)
  if (delta === 0) return '与上一帧相同'
  return `${delta > 0 ? '扩大' : '收缩'} ${Math.abs(delta)} m`
})
const riskLabel = computed(
  () =>
    ({
      unknown: '未知',
      low: '低',
      medium: '中',
      high: '高',
      critical: '严重'
    })[currentFrame.value?.risk_level ?? 'unknown']
)
const extracted = computed(() => session.value?.parameters ?? {})
const extractedItems = computed(() => {
  const p = extracted.value
  return [
    p.location_name ? `地点 ${p.location_name}` : '',
    p.start_time ? `时间 ${p.start_time}` : '',
    p.duration_min ? `${p.duration_min} 分钟` : '',
    p.rainfall_mm_h ? `降雨 ${p.rainfall_mm_h} mm/h` : '',
    p.people_count ? `人口 ${p.people_count} 人` : '',
    p.settlement_rate_mm_month ? `沉降 ${p.settlement_rate_mm_month} mm/月` : '',
    p.affected_building_id ? `建筑 ${p.affected_building_id}` : '',
    p.response_delay_min !== undefined && p.response_delay_min !== null ? `响应 ${p.response_delay_min} 分钟` : '',
    p.available_resource_count !== undefined && p.available_resource_count !== null
      ? `可用资源 ${p.available_resource_count} 项`
      : '',
    p.source_event_id ? `来源事件 ${p.source_event_id}` : ''
  ].filter(Boolean)
})
const affectedCounts = computed(() => ({
  buildings: currentFrame.value?.affected_building_ids.length ?? 0,
  roads: currentFrame.value?.affected_road_ids.length ?? 0
}))
const prompts = [
  '武昌区发生暴雨，推演积水对周边人员和道路的影响。',
  '中山大道从 2026-10-31 17:30 起发生严重拥堵，持续60分钟，原因为交通事故，请推演。',
  '武昌区在 2026-10-31 18:00 发生中型火灾，危险半径200米，影响200人，持续30分钟，请开始推演。',
  '武昌区某高层建筑沉降速率4.5毫米每月，影响120人，请推演建筑异常发展。'
]
const dispatchCandidates = computed(() => {
  const type = run.value?.scenario_type
  return businessEvents.value
    .filter((item) => item.status !== 'resolved' && (!type || item.event_type === type))
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
})
const dispatchActionTitles = computed(() => {
  if (!run.value) return []
  return (
    {
      flood: ['现场核查积水边界与雨水口状态', '实施抽排并落实道路通行管控'],
      traffic: ['核查拥堵原因与排队范围', '落实分流引导与节点管控'],
      fire: ['实施危险区警戒与人员疏散', '核查消防通道与周边道路条件'],
      building: ['开展建筑沉降复核与结构检查', '设置警戒范围并跟踪周边建筑']
    }[run.value.scenario_type] ?? []
  )
})
const METRIC_META: Record<string, { label: string; unit?: string }> = {
  water_depth_cm: { label: '积水深度', unit: 'cm' },
  rainfall_mm_h: { label: '降雨强度', unit: 'mm/h' },
  tpi: { label: '拥堵指数' },
  duration_min: { label: '持续时间', unit: 'min' },
  people: { label: '人员数量', unit: '人' },
  evacuated: { label: '已疏散', unit: '人' },
  queued: { label: '排队人数', unit: '人' },
  corridor_lanes: { label: '通道数', unit: '条' },
  capacity_per_min: { label: '通行能力', unit: '人/min' },
  collision_adjustments: { label: '间距修正', unit: '次' },
  danger_radius_m: { label: '风险半径', unit: 'm' },
  settlement_rate_mm_month: { label: '沉降速率', unit: 'mm/月' },
  inspection_progress: { label: '核查进度' },
  response_delay_min: { label: '响应延迟', unit: 'min' },
  closed_exit_count: { label: '封闭出口', unit: '个' }
}

function metricLabel(key: string): string {
  return METRIC_META[key]?.label ?? key
}

function metricValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return '—'
  const unit = METRIC_META[key]?.unit
  const shown = typeof value === 'number' && !Number.isInteger(value) ? Math.round(value * 10) / 10 : value
  return unit ? `${shown} ${unit}` : String(shown)
}

function variantPeakQueue(item: ScenarioRun): number {
  return Math.max(0, ...item.frames.map((frame) => Number(frame.metrics.queued) || 0))
}

function variantSafe(item: ScenarioRun): number {
  return Number(item.frames.at(-1)?.metrics.evacuated) || 0
}

function variantPrimary(item: ScenarioRun): string {
  const metrics = item.frames.at(-1)?.metrics
  if (typeof metrics?.water_depth_cm === 'number') return `峰值积水 ${metrics.water_depth_cm} cm`
  if (typeof metrics?.tpi === 'number') return `峰值 TPI ${metrics.tpi}`
  if (typeof metrics?.settlement_rate_mm_month === 'number') return `沉降速率 ${metrics.settlement_rate_mm_month} mm/月`
  return `安全 ${variantSafe(item)} 人`
}

function variantSecondary(item: ScenarioRun): string {
  const frame = item.frames.at(-1)
  const radius = frame?.zones[0]?.radius_m
  if (item.scenario_type === 'flood' && typeof radius === 'number') {
    return `最大范围 ${Math.round(radius)} m`
  }
  return `峰值排队 ${variantPeakQueue(item)} 人`
}

function classLabel(value: string): string {
  return (
    {
      real: '真实数据',
      professional_analysis: '专业分析',
      simulated: '模拟数据',
      llm_inference: '大模型推断',
      unknown: '未知'
    }[value] ?? value
  )
}

async function ensureSession() {
  if (!session.value) session.value = await createScenarioSession(props.sourceEventId)
  return session.value
}

function exportResult() {
  if (run.value) window.open(scenarioExportUrl(run.value.run_id), '_blank', 'noopener')
}

function openDrill() {
  if (!session.value) return
  void router.push({
    path: '/drill',
    query: { scenarioSessionId: session.value.session_id }
  })
}

async function openResources() {
  try {
    resources.value = await getEmergencyResources()
    selectedResourceIds.value = [...(session.value?.parameters.resource_ids ?? [])]
    resourceVisible.value = true
  } catch (error) {
    ElMessage.error(errMsg(error, '应急资源加载失败'))
  }
}

async function saveResources() {
  if (!session.value || resourceBusy.value) return
  resourceBusy.value = true
  try {
    session.value = await setScenarioResources(session.value.session_id, selectedResourceIds.value)
    resourceVisible.value = false
    ElMessage.success('情景资源预留已更新')
  } catch (error) {
    ElMessage.error(errMsg(error, '情景资源预留失败'))
  } finally {
    resourceBusy.value = false
  }
}

async function useTemplate(template: ScenarioTemplate) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const current = await createScenarioSession(undefined, template.id)
    session.value = current
    variants.value = []
    run.value = null
    const result = await runCurrentScenarioVariants(current.session_id)
    variants.value = result.variant_runs
    await loadRun(result.latest_run)
    session.value = {
      ...current,
      latest_run: result.latest_run,
      variant_runs: result.variant_runs,
      run_ids: result.variant_runs.map((item) => item.run_id)
    }
  } catch (e) {
    error.value = errMsg(e, '情景模板运行失败')
  } finally {
    busy.value = false
  }
}

function openSaveTemplate() {
  if (!session.value?.scenario_type || !session.value.parameters) {
    ElMessage.warning('请先形成有效情景参数')
    return
  }
  templateName.value = `${session.value.title || '情景'}模板`
  templateDescription.value = '保存当前情景参数，供后续直接复用。'
  templateVisible.value = true
}

async function saveScenarioTemplate() {
  if (!session.value?.scenario_type || !templateName.value.trim() || templateBusy.value) return
  templateBusy.value = true
  try {
    const row = await createScenarioTemplate({
      name: templateName.value.trim(),
      description: templateDescription.value.trim(),
      scenario_type: session.value.scenario_type,
      parameters: session.value.parameters
    })
    templates.value = [row, ...templates.value]
    templateVisible.value = false
    ElMessage.success(`情景模板 ${row.id} 已保存`)
  } catch (e) {
    ElMessage.error(errMsg(e, '情景模板保存失败'))
  } finally {
    templateBusy.value = false
  }
}

function openTemplateManage() {
  templateManageVisible.value = true
  void getScenarioTemplates()
    .then((items) => (templates.value = items))
    .catch((error) => ElMessage.error(errMsg(error, '情景模板加载失败')))
}

function editScenarioTemplate(template: ScenarioTemplate) {
  editingTemplateId.value = template.id
  templateEditName.value = template.name
  templateEditDescription.value = template.description
  templateEditType.value = template.scenario_type
  templateEditParameters.value = JSON.stringify(template.parameters, null, 2)
}

async function saveScenarioTemplateEdit() {
  if (!editingTemplateId.value || !templateEditName.value.trim() || templateBusy.value) return
  let parameters: Record<string, unknown>
  try {
    parameters = JSON.parse(templateEditParameters.value || '{}') as Record<string, unknown>
  } catch {
    ElMessage.warning('情景参数必须是合法 JSON')
    return
  }
  templateBusy.value = true
  try {
    const updated = await patchScenarioTemplate(editingTemplateId.value, {
      name: templateEditName.value.trim(),
      description: templateEditDescription.value.trim(),
      scenario_type: templateEditType.value,
      parameters
    })
    templates.value = templates.value.map((item) => (item.id === updated.id ? updated : item))
    editingTemplateId.value = ''
    ElMessage.success(`情景模板已更新为 ${updated.id}`)
  } catch (error) {
    ElMessage.error(errMsg(error, '情景模板更新失败'))
  } finally {
    templateBusy.value = false
  }
}

async function removeScenarioTemplate(template: ScenarioTemplate) {
  try {
    await ElMessageBox.confirm(
      `删除后会同时移除该模板的修订历史，已运行的推演结果不受影响。确认删除「${template.name}」？`,
      '删除情景模板',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteScenarioTemplate(template.id)
    templates.value = templates.value.filter((item) => item.id !== template.id)
    if (editingTemplateId.value === template.id) editingTemplateId.value = ''
    ElMessage.success(`情景模板 ${template.id} 已删除`)
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(errMsg(error, '情景模板删除失败'))
  }
}

async function showScenarioTemplateHistory(template: ScenarioTemplate) {
  try {
    templateHistory.value = await getScenarioTemplateRevisions(template.id)
    templateHistoryVisible.value = true
  } catch (error) {
    ElMessage.error(errMsg(error, '情景模板修订历史加载失败'))
  }
}

async function ensureLayer(): Promise<ScenarioLayer | null> {
  if (layer) return layer
  const cesiumViewer = props.viewer?.getViewer()
  if (!cesiumViewer) return null
  layer = new ScenarioLayer(cesiumViewer)
  try {
    layer.setRoads(await getRoads())
  } catch {
    /* 道路高亮是可选展示 */
  }
  return layer
}

async function send(text = input.value) {
  const message = text.trim()
  if (!message || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const current = await ensureSession()
    const next = await sendScenarioMessage(current.session_id, message)
    session.value = next
    variants.value = next.variant_runs ?? []
    input.value = ''
    if (next.latest_run && next.latest_run.run_id !== run.value?.run_id) await loadRun(next.latest_run)
    if (next.last_comparison) comparison.value = next.last_comparison
  } catch (e) {
    error.value = errMsg(e, '情景 Agent 调用失败')
  } finally {
    busy.value = false
  }
}

async function runAgain() {
  if (!session.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await runCurrentScenarioVariants(session.value.session_id)
    variants.value = result.variant_runs
    await loadRun(result.latest_run)
    session.value = {
      ...session.value,
      latest_run: result.latest_run,
      variant_runs: result.variant_runs,
      run_ids: [...result.variant_runs.map((item) => item.run_id), ...session.value.run_ids]
    }
  } catch (e) {
    error.value = errMsg(e, '情景推演失败')
  } finally {
    busy.value = false
  }
}

async function loadRun(next: ScenarioRun) {
  run.value = next
  frameIndex.value = 0
  report.value = null
  comparison.value = null
  if (next.frames[0]) {
    const map = await ensureLayer()
    map?.render(next.frames[0], next.scenario_type)
    map?.focus(next.frames[0])
    await applyPeople(next.frames[0])
  }
}

async function applyPeople(frame: ScenarioFrame) {
  if (!props.viewer) return
  const crowd = props.viewer.getCrowd()
  if (!crowd) return
  crowd.setFramePeople(frame.people, frame.people.length ? 'tourist' : 'resident')
}

async function showFrame(index: number) {
  if (!run.value?.frames[index]) return
  const previous = run.value.frames[frameIndex.value]
  frameIndex.value = index
  const frame = run.value.frames[index]
  const map = await ensureLayer()
  map?.render(frame, run.value.scenario_type, previous.offset_min < frame.offset_min ? previous : undefined)
  await applyPeople(frame)
}

async function setMapVisible(visible: boolean) {
  mapVisible.value = visible
  if (!visible) {
    layer?.clear()
    props.viewer?.getCrowd()?.clear()
  } else if (currentFrame.value) {
    await showFrame(frameIndex.value)
  }
}

function togglePlay() {
  if (!run.value) return
  if (playing.value) {
    pause()
    return
  }
  playing.value = true
  timer = window.setInterval(() => {
    if (!run.value) return
    const next = frameIndex.value + 1
    if (next >= run.value.frames.length) {
      pause()
      return
    }
    void showFrame(next)
  }, 1400)
}

function pause() {
  playing.value = false
  window.clearInterval(timer)
}

async function reset() {
  pause()
  frameIndex.value = 0
  layer?.clear()
  props.viewer?.getCrowd()?.clear()
  if (run.value?.frames[0]) await showFrame(0)
}

async function compare() {
  if (!session.value || session.value.run_ids.length < 2 || busy.value) return
  busy.value = true
  try {
    comparison.value = await compareScenarioRuns(
      session.value.session_id,
      session.value.run_ids[1],
      session.value.run_ids[0]
    )
  } catch (e) {
    error.value = errMsg(e, '情景对比失败')
  } finally {
    busy.value = false
  }
}

async function makeReport() {
  if (!run.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    report.value = await generateScenarioReport(run.value.run_id)
  } catch (e) {
    error.value = errMsg(e, '情景报告生成失败')
  } finally {
    busy.value = false
  }
}

function openDispatch() {
  dispatchError.value = ''
  dispatchedOrders.value = []
  dispatchEventId.value = dispatchCandidates.value[0]?.id ?? ''
  dispatchVisible.value = true
}

async function confirmDispatch() {
  if (!run.value || !dispatchEventId.value || dispatchBusy.value) return
  dispatchBusy.value = true
  dispatchError.value = ''
  try {
    dispatchedOrders.value = await dispatchScenarioRun(run.value.run_id, {
      event_id: dispatchEventId.value
    })
    ElMessage.success(`已生成 ${dispatchedOrders.value.length} 张协同处置工单`)
  } catch (error) {
    dispatchError.value = errMsg(error, '方案转工单失败')
  } finally {
    dispatchBusy.value = false
  }
}

/** 一键演示：自动提交一句话、等待三方案生成，并短暂展示结果后切到地图。 */
async function demoStart(prompt: string): Promise<boolean> {
  input.value = prompt
  await send(prompt)
  if (!run.value) return false
  await new Promise((resolve) => window.setTimeout(resolve, 6500))
  emit('view-map')
  return true
}

function demoStop(): void {
  pause()
  layer?.clear()
  props.viewer?.getCrowd()?.clear()
}

defineExpose({ demoStart, demoStop })

onMounted(() => {
  void getEvents({ limit: 500 })
    .then((items) => (businessEvents.value = items))
    .catch(() => undefined)
  void ensureSession()
    .then(async (current) => {
      variants.value = current.variant_runs ?? []
      if (current.latest_run) await loadRun(current.latest_run)
    })
    .catch((e) => (error.value = errMsg(e, '无法创建情景会话')))
  void getScenarioTemplates().then((items) => (templates.value = items)).catch(() => undefined)
})
onBeforeUnmount(() => {
  pause()
  layer?.destroy()
  layer = null
})
</script>

<template>
  <section class="sw" :class="{ 'is-embedded': embedded }">
    <div v-if="!embedded" class="sw__head">
      <h2>城市智能情景推演</h2>
      <button type="button" aria-label="关闭情景推演" @click="emit('close')">×</button>
    </div>
    <div v-if="!run" class="sw__intro">
      <h3>输入意外事件</h3>
      <p>输入一句话描述意外事件。Agent 提取关键信息，演示模式自动补全合理假设，并生成常规、不利、干预三种可能结果。</p>
      <p v-if="sourceEventId" class="sw__source">已从事件 {{ sourceEventId }} 建立情景上下文，可继续补充假设并运行。</p>
    </div>

    <template v-if="run">
      <div v-if="extractedItems.length" class="sw__spec" role="group" aria-label="系统理解的情景参数">
        <span v-for="item in extractedItems" :key="item">{{ item }}</span>
      </div>
      <div v-if="variants.length" class="sw__variants-wrap">
        <div class="sw__variants-head">
          <b>三种可能结果</b>
          <span>点击切换三维回放</span>
        </div>
        <div class="sw__variants" role="group" aria-label="三种可能结果">
          <button
            v-for="item in variants"
            :key="item.run_id"
            type="button"
            :class="{ 'is-active': item.run_id === run.run_id }"
            @click="loadRun(item)"
          >
            <b>{{ item.variant_label || '方案' }}</b>
            <span>{{ variantPrimary(item) }}</span>
            <small>{{ variantSecondary(item) }}</small>
          </button>
        </div>
      </div>
      <div class="sw__run-head">
        <div>
          <b>{{ SCENARIO_LABEL[run.scenario_type] }}</b>
          <span class="sw__tag">{{ dataClassLabel }}</span>
          <span class="sw__tag">{{ run.provider }}</span>
          <span v-if="run.model_version" class="sw__tag">{{ run.model_version }}</span>
        </div>
        <div class="sw__run-actions">
          <el-button size="small" :icon="FullScreen" @click="emit('view-map')">查看地图</el-button>
          <el-button size="small" :loading="busy" @click="compare">对比最近两次</el-button>
          <el-button size="small" :icon="Document" :loading="busy" @click="makeReport">生成报告</el-button>
          <el-button size="small" :icon="Setting" @click="openResources">资源约束</el-button>
          <el-button size="small" :icon="Download" @click="exportResult">导出结果</el-button>
          <el-button size="small" :icon="VideoPlay" @click="openDrill">进入演练</el-button>
          <el-button size="small" type="primary" :icon="Tickets" @click="openDispatch">转为处置工单</el-button>
          <el-button size="small" @click="openSaveTemplate">保存模板</el-button>
          <el-button size="small" @click="openTemplateManage">模板管理</el-button>
          <el-button size="small" :loading="busy" @click="runAgain">重新运行</el-button>
        </div>
      </div>

      <div class="sw__impact">
        <div>
          <span>当前影响半径</span>
          <strong>{{ currentRadius === null ? '—' : `${Math.round(currentRadius)} m` }}</strong>
        </div>
        <div>
          <span>估算影响面积</span>
          <strong>{{ impactArea }}</strong>
        </div>
        <div>
          <span>范围变化</span>
          <strong>{{ extentChange }}</strong>
        </div>
        <div>
          <span>风险等级</span>
          <strong>{{ riskLabel }}</strong>
        </div>
      </div>

      <div class="sw__timeline">
        <div class="sw__timeline-head">
          <b>推演时间轴</b>
          <span>+{{ currentFrame?.offset_min ?? 0 }} 分钟 · 虚线为上帧范围</span>
        </div>
        <el-slider
          :model-value="frameIndex"
          :min="0"
          :max="Math.max(0, run.frames.length - 1)"
          :step="1"
          show-stops
          @update:model-value="(value: number | number[]) => showFrame(Number(value))"
        />
        <div class="sw__controls">
          <el-button :icon="playing ? VideoPause : VideoPlay" @click="togglePlay">{{
            playing ? '暂停' : '播放'
          }}</el-button>
          <el-button :icon="RefreshLeft" @click="reset">重置</el-button>
          <el-switch
            v-model="mapVisible"
            active-text="地图联动"
            aria-label="地图联动"
            @change="(value: boolean | string | number) => setMapVisible(Boolean(value))"
          />
        </div>
        <dl v-if="currentFrame" class="sw__metrics">
          <template v-for="(value, key) in currentFrame.metrics" :key="key">
            <dt>{{ metricLabel(key) }}</dt>
            <dd>{{ metricValue(key, value) }}</dd>
          </template>
        </dl>
        <p class="sw__limits">{{ currentFrame?.limitations.join('；') }}</p>
        <div class="sw__affected">
          <span>当前受影响对象</span>
          <b>{{ affectedCounts.buildings }} 栋建筑</b>
          <b>{{ affectedCounts.roads }} 条道路</b>
        </div>
      </div>
    </template>

    <details v-if="run" class="sw__transcript">
      <summary>对话记录 · {{ session?.messages.length ?? 0 }} 条</summary>
      <div class="sw__messages">
        <div v-for="(message, i) in session?.messages ?? []" :key="i" class="sw__message" :class="`is-${message.role}`">
          <span>{{ message.role === 'user' ? '你' : 'Agent' }}</span>
          <p>{{ message.content }}</p>
        </div>
      </div>
    </details>

    <div v-else class="sw__messages">
      <div v-for="(message, i) in session?.messages ?? []" :key="i" class="sw__message" :class="`is-${message.role}`">
        <span>{{ message.role === 'user' ? '你' : 'Agent' }}</span>
        <p>{{ message.content }}</p>
      </div>
    </div>
    <div v-if="busy" class="sw__message is-assistant">
      <span>Agent</span>
      <p>正在理解情景并组织推演…</p>
    </div>

    <div v-if="!run" class="sw__quick">
      <div v-if="templates.length" class="sw__template-list">
        <span>
          情景模板
          <button type="button" class="sw__template-open" @click="openTemplateManage">管理</button>
        </span>
        <button v-for="template in templates" :key="template.id" @click="useTemplate(template)">
          <b>{{ template.name }}</b>
          <small>{{ template.description }}</small>
        </button>
      </div>
      <span class="sw__quick-label">输入示例</span>
      <button v-for="(prompt, i) in prompts" :key="i" @click="send(prompt)">{{ prompt }}</button>
    </div>

    <div class="sw__input">
      <el-input
        v-model="input"
        type="textarea"
        :rows="run ? 1 : 2"
        placeholder="描述事件，或要求修改/运行/比较情景"
        @keydown.ctrl.enter.prevent="send()"
      />
      <el-button type="primary" :icon="ChatDotRound" :loading="busy" @click="send()">发送</el-button>
    </div>
    <p v-if="error" class="sw__error">{{ error }}</p>

    <div v-if="comparison" class="sw__block">
      <h4>方案对比</h4>
      <p>{{ comparison.summary }}</p>
      <ul>
        <li v-for="item in comparison.parameter_changes" :key="item.field">
          {{ item.field }}：{{ item.before ?? '未知' }} → {{ item.after ?? '未知' }}
        </li>
      </ul>
    </div>

    <div v-if="report" class="sw__block sw__report">
      <h4>{{ report.report_title }}</h4>
      <p class="sw__tag">{{ report.data_classification }}</p>
      <p>{{ report.event_summary }}</p>
      <h5>数据与方法</h5>
      <ul>
        <li v-for="item in report.data_and_methods" :key="item">{{ item }}</li>
      </ul>
      <h5>发展过程</h5>
      <ul>
        <li v-for="item in report.development_process" :key="item">{{ item }}</li>
      </ul>
      <h5>风险判断</h5>
      <p>{{ report.risk_assessment }}</p>
      <h5>建议</h5>
      <ul>
        <li v-for="item in report.recommendations" :key="item">{{ item }}</li>
      </ul>
      <h5>不确定性</h5>
      <ul>
        <li v-for="item in report.uncertainties" :key="item">{{ item }}</li>
      </ul>
    </div>

    <el-dialog
      v-model="dispatchVisible"
      title="将选定方案转为协同处置"
      width="min(620px, 94vw)"
      append-to-body
    >
      <div v-if="run" class="dispatch">
        <p class="dispatch__summary">
          当前选择「{{ run.variant_label || '常规响应' }}」。确认后会生成可接单、执行、复核的工单，并保留本次推演结果编号
          <b>{{ run.run_id }}</b> 作为方案依据。
        </p>
        <el-form label-position="top">
          <el-form-item label="关联风险事件" required>
            <el-select
              v-model="dispatchEventId"
              filterable
              placeholder="选择与本次推演对应的未办结事件"
              style="width: 100%"
            >
              <el-option
                v-for="item in dispatchCandidates"
                :key="item.id"
                :value="item.id"
                :label="`${item.id} ${item.name} · ${item.district || item.address}`"
              />
            </el-select>
          </el-form-item>
        </el-form>
        <el-empty
          v-if="!dispatchCandidates.length"
          :image-size="56"
          description="当前没有同类型的未办结事件，请先在事件中心上报或确认事件"
        />
        <section v-else class="dispatch__actions">
          <h4>将生成的处置动作</h4>
          <ol>
            <li v-for="title in dispatchActionTitles" :key="title">{{ title }}</li>
          </ol>
          <p>工单优先级、责任单位和办理时限会依据末帧风险等级自动填写，可在协同处置中继续转派和修改。</p>
        </section>
        <section v-if="dispatchedOrders.length" class="dispatch__result">
          <b>已生成 {{ dispatchedOrders.length }} 张工单</b>
          <span v-for="item in dispatchedOrders" :key="item.id">{{ item.id }} · {{ item.title }}</span>
          <el-button type="primary" plain @click="router.push('/workflow/orders')">查看协同处置</el-button>
        </section>
        <p v-if="dispatchError" class="sw__error">{{ dispatchError }}</p>
      </div>
      <template #footer>
        <el-button @click="dispatchVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="dispatchBusy"
          :disabled="!dispatchEventId || !!dispatchedOrders.length"
          @click="confirmDispatch"
        >
          确认并生成工单
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="templateVisible" title="保存情景模板" width="min(520px, 94vw)" append-to-body>
      <el-form label-position="top">
        <el-form-item label="模板名称" required>
          <el-input v-model="templateName" maxlength="128" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="templateDescription" type="textarea" :rows="3" maxlength="1000" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="templateVisible = false">取消</el-button>
        <el-button type="primary" :loading="templateBusy" @click="saveScenarioTemplate">保存模板</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resourceVisible" title="情景资源约束" width="min(640px, 94vw)" append-to-body>
      <p class="resource-dialog-hint">
        选择后会从应急资源库存预留具体资源；变更选择会先释放本情景此前的预留。
      </p>
      <el-select
        v-model="selectedResourceIds"
        multiple
        filterable
        collapse-tags
        collapse-tags-tooltip
        placeholder="选择可用应急资源"
        style="width: 100%"
      >
        <el-option
          v-for="resource in resources"
          :key="resource.id"
          :value="resource.id"
          :disabled="resource.status === 'unavailable' || (resource.available <= 0 && !(session?.parameters.resource_ids ?? []).includes(resource.id))"
          :label="`${resource.name} · ${resource.capability} · 可用 ${resource.available}`"
        />
      </el-select>
      <div class="resource-selection-summary">
        已选 <b>{{ selectedResourceIds.length }}</b> 项；推演引擎将按资源数量计算演示处置能力。
      </div>
      <template #footer>
        <el-button @click="resourceVisible = false">取消</el-button>
        <el-button type="primary" :loading="resourceBusy" @click="saveResources">保存资源约束</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="templateManageVisible"
      title="情景模板管理"
      width="min(900px, 96vw)"
      append-to-body
    >
      <div class="template-manage">
        <section class="template-manage__list">
          <article
            v-for="template in templates"
            :key="template.id"
            :class="{ active: editingTemplateId === template.id }"
          >
            <button type="button" @click="editScenarioTemplate(template)">
              <b>{{ template.name }}</b>
              <small>{{ template.id }} · {{ SCENARIO_LABEL[template.scenario_type] }}</small>
              <em>{{ template.description || '未填写说明' }}</em>
            </button>
            <div>
              <el-button link type="primary" :icon="Edit" @click="editScenarioTemplate(template)" />
              <el-button link type="info" :icon="Clock" @click="showScenarioTemplateHistory(template)" />
              <el-button link type="danger" :icon="Delete" @click="removeScenarioTemplate(template)" />
            </div>
          </article>
          <el-empty v-if="!templates.length" :image-size="56" description="暂无情景模板" />
        </section>
        <section v-if="editingTemplateId" class="template-manage__editor">
          <el-form label-position="top">
            <el-form-item label="模板名称">
              <el-input v-model="templateEditName" maxlength="128" />
            </el-form-item>
            <div class="template-manage__row">
              <el-form-item label="情景类型">
                <el-select v-model="templateEditType">
                  <el-option
                    v-for="(label, key) in SCENARIO_LABEL"
                    :key="key"
                    :value="key"
                    :label="label"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="说明">
                <el-input v-model="templateEditDescription" maxlength="1000" />
              </el-form-item>
            </div>
            <el-form-item label="完整情景参数 JSON">
              <el-input v-model="templateEditParameters" type="textarea" :rows="13" />
            </el-form-item>
            <div class="template-manage__actions">
              <span>保存后会生成新的不可变修订版本。</span>
              <el-button type="primary" :icon="Edit" :loading="templateBusy" @click="saveScenarioTemplateEdit">
                保存并生成修订
              </el-button>
            </div>
          </el-form>
        </section>
        <el-empty v-else :image-size="64" description="选择左侧模板进行编辑" />
      </div>
    </el-dialog>

    <el-drawer
      v-model="templateHistoryVisible"
      title="情景模板修订历史"
      size="min(620px, 96vw)"
      append-to-body
    >
      <el-empty v-if="!templateHistory.length" description="暂无修订记录" />
      <article v-for="item in templateHistory" :key="item.id" class="template-revision">
        <header>
          <b>v{{ item.version_no }}</b>
          <span>{{ item.name }} · {{ SCENARIO_LABEL[item.scenario_type] }}</span>
          <time>{{ item.created_at }}</time>
        </header>
        <p>{{ item.description || '未填写说明' }}</p>
        <pre>{{ JSON.stringify(item.parameters, null, 2) }}</pre>
        <small>{{ item.operator }}</small>
      </article>
    </el-drawer>
  </section>
</template>

<style scoped>
.sw {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.sw.is-embedded {
  padding: 16px;
}
.sw__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.sw__head h2 {
  margin: 0;
  font-size: 19px;
  font-weight: 600;
  color: var(--ce-text-strong);
}
.sw__head button {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid var(--ce-panel-border);
  border-radius: 4px;
  background: transparent;
  color: var(--ce-text-dim);
  font-size: 19px;
  line-height: 1;
  cursor: pointer;
}
.sw__head button:hover {
  color: var(--ce-text-strong);
}
.sw__head button:focus-visible {
  outline: 2px solid var(--ce-accent);
  outline-offset: 2px;
}
.sw__intro {
  padding: 14px;
  border-top: 2px solid var(--ce-accent);
  background: var(--ce-panel-solid);
}
.sw__intro h3 {
  margin: 0 0 6px;
  font-size: 18px;
  color: var(--ce-text-strong);
}
.sw__intro p {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--ce-text-dim);
}
.sw__intro .sw__source {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--ce-divider);
  color: var(--ce-accent);
}
.sw__messages {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 240px;
  overflow: auto;
}
.sw__message {
  max-width: 94%;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
}
.sw__message > span {
  display: block;
  margin-bottom: 3px;
  font-size: 12px;
  color: var(--ce-text-faint);
}
.sw__message p {
  margin: 0;
  white-space: pre-wrap;
}
.sw__message.is-user {
  align-self: flex-end;
  background: #1c2225;
  color: var(--ce-text-strong);
}
.sw__message.is-assistant {
  background: #1a1c1e;
  color: var(--ce-text);
}
.sw__quick {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.sw__quick-label {
  margin: 5px 0 0;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.sw__template-list {
  display: grid;
  gap: 5px;
  margin-bottom: 5px;
}
.sw__template-list > span {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.sw__template-list > span .sw__template-open {
  width: auto;
  margin-left: 8px;
  padding: 1px 6px;
  border: 1px solid var(--ce-panel-border);
  color: var(--ce-accent);
  font-size: 10px;
}
.sw__template-list button {
  display: grid;
  gap: 2px;
  padding: 8px 10px;
  border: 1px solid var(--ce-panel-border);
  background: transparent;
  color: var(--ce-text-dim);
  text-align: left;
  cursor: pointer;
}
.sw__template-list button:hover {
  border-color: var(--ce-accent);
  color: var(--ce-text-strong);
}
.sw__template-list b,
.sw__template-list small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sw__template-list b {
  font-size: 12px;
}
.sw__template-list small {
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.resource-dialog-hint {
  margin: 0 0 12px;
  color: var(--ce-text-dim);
  font-size: 12px;
  line-height: 1.6;
}
.resource-selection-summary {
  margin-top: 10px;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.resource-selection-summary b {
  color: var(--ce-accent);
}
.sw__quick button {
  padding: 8px 10px;
  text-align: left;
  font-size: 13px;
  color: var(--ce-text-dim);
  border: 1px solid var(--ce-panel-border);
  background: transparent;
  cursor: pointer;
}
.sw__quick button:hover {
  color: var(--ce-text-strong);
  border-color: var(--ce-accent);
}
.sw__input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.sw__error {
  margin: 0;
  font-size: 12px;
  color: #ff9a7a;
}
.sw__run-head {
  display: grid;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--ce-divider);
}
.sw__spec {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.sw__spec span {
  padding: 2px 7px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 3px;
  font-size: 12px;
  color: var(--ce-text-dim);
}
.sw__variants-wrap {
  display: grid;
  gap: 6px;
}
.sw__variants-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}
.sw__variants-head b {
  font-size: 13px;
  color: var(--ce-text-strong);
}
.sw__variants-head span {
  font-size: 12px;
  color: var(--ce-text-faint);
}
.sw__variants {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}
.sw__variants button {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
  padding: 9px 10px;
  text-align: left;
  border: 1px solid var(--ce-panel-border);
  border-left: 2px solid transparent;
  background: transparent;
  color: var(--ce-text-dim);
  cursor: pointer;
}
.sw__variants button.is-active {
  border-left-color: var(--ce-accent);
  color: var(--ce-text-strong);
  background: var(--ce-active);
}
.sw__variants button:focus-visible {
  outline: 2px solid var(--ce-accent);
  outline-offset: 2px;
}
.sw__variants b {
  overflow: hidden;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.sw__variants span,
.sw__variants small {
  overflow: hidden;
  font-size: 12px;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.sw__variants small {
  color: var(--ce-text-faint);
}
.sw__run-head > div {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.sw__run-actions {
  justify-content: flex-end;
}
.sw__run-actions > :deep(.el-button + .el-button) {
  margin-left: 0;
}
.sw__tag {
  display: inline-block;
  padding: 1px 7px;
  font-size: 12px;
  color: var(--ce-text-dim);
  border: 1px solid var(--ce-panel-border);
  border-radius: 4px;
}
.sw__impact {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  background: var(--ce-panel-solid);
  border-left: 2px solid var(--ce-accent);
}
.sw__impact > div {
  min-width: 0;
  padding: 9px 10px;
}
.sw__impact > div + div {
  border-left: 1px solid var(--ce-divider);
}
.sw__impact span {
  display: block;
  overflow: hidden;
  font-size: 12px;
  color: var(--ce-text-dim);
  white-space: nowrap;
  text-overflow: ellipsis;
}
.sw__impact strong {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  font-size: 15px;
  color: var(--ce-text-strong);
  white-space: nowrap;
  text-overflow: ellipsis;
}
.sw__timeline,
.sw__block {
  padding: 12px;
  border: 1px solid var(--ce-panel-border);
  background: var(--ce-panel-solid);
}
.sw__timeline-head,
.sw__controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sw__timeline-head span,
.sw__controls span {
  font-size: 12px;
  color: var(--ce-text-dim);
}
.sw__metrics {
  display: grid;
  grid-template-columns: auto 1fr auto 1fr;
  gap: 4px 8px;
  font-size: 13px;
}
.sw__metrics dt {
  color: var(--ce-text-dim);
}
.sw__metrics dd {
  margin: 0;
  color: var(--ce-text);
}
.sw__limits {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--ce-warning);
}
.sw__affected {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 9px;
  padding-top: 9px;
  border-top: 1px solid var(--ce-divider);
  color: var(--ce-text-faint);
  font-size: 12px;
}
.sw__affected b {
  color: var(--ce-text-strong);
  font-weight: 500;
}
.sw__block h4 {
  margin: 0 0 8px;
  color: var(--ce-text-strong);
}
.sw__block h5 {
  margin: 10px 0 4px;
  font-size: 12px;
  color: var(--ce-text-dim);
}
.sw__block p,
.sw__block li {
  font-size: 13px;
  line-height: 1.65;
  color: var(--ce-text);
}
.sw__block ul {
  margin: 0;
  padding-left: 18px;
}
.dispatch {
  display: grid;
  gap: 14px;
}
.dispatch__summary {
  margin: 0;
  padding: 10px 12px;
  border-left: 2px solid var(--ce-accent);
  background: rgba(103, 198, 223, 0.06);
  line-height: 1.7;
}
.dispatch__summary b {
  color: var(--ce-text-strong);
  font-family: var(--ce-font-num);
}
.dispatch__actions {
  padding: 12px;
  border: 1px solid var(--ce-divider);
}
.dispatch__actions h4 {
  margin: 0 0 8px;
  color: var(--ce-text-strong);
  font-size: 13px;
}
.dispatch__actions ol {
  margin: 0;
  padding-left: 20px;
  line-height: 1.8;
}
.dispatch__actions p {
  margin: 9px 0 0;
  color: var(--ce-text-faint);
  font-size: 12px;
}
.dispatch__result {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid rgba(114, 195, 154, 0.45);
  background: rgba(114, 195, 154, 0.06);
}
.dispatch__result b {
  color: var(--ce-success);
}
.dispatch__result span {
  color: var(--ce-text-dim);
  font-size: 12px;
}
.template-manage {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 14px;
  min-height: 470px;
}
.template-manage__list {
  overflow-y: auto;
  border: 1px solid var(--ce-divider);
}
.template-manage__list article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px;
  padding: 7px;
  border-bottom: 1px solid var(--ce-divider);
}
.template-manage__list article.active {
  background: var(--ce-active);
}
.template-manage__list article > button {
  display: grid;
  min-width: 0;
  gap: 2px;
  padding: 5px;
  border: 0;
  background: transparent;
  color: var(--ce-text-dim);
  text-align: left;
  cursor: pointer;
}
.template-manage__list b,
.template-manage__list small,
.template-manage__list em {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.template-manage__list b {
  color: var(--ce-text-strong);
  font-size: 12px;
}
.template-manage__list small,
.template-manage__list em {
  color: var(--ce-text-faint);
  font-size: 10.5px;
  font-style: normal;
}
.template-manage__list article > div {
  display: flex;
  align-items: center;
}
.template-manage__editor {
  padding: 2px 4px;
}
.template-manage__row {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 12px;
}
.template-manage__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.template-manage__actions span {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.template-revision {
  margin-bottom: 10px;
  padding: 10px;
  border: 1px solid var(--ce-divider);
}
.template-revision header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ce-text-dim);
  font-size: 11px;
}
.template-revision header b {
  color: var(--ce-accent);
  font-family: var(--ce-font-num);
}
.template-revision header time {
  margin-left: auto;
  color: var(--ce-text-faint);
}
.template-revision p {
  margin: 7px 0;
  color: var(--ce-text-dim);
  font-size: 12px;
}
.template-revision pre {
  max-height: 260px;
  margin: 0;
  padding: 9px;
  overflow: auto;
  color: #bfd2df;
  background: #0b1118;
  font: 10.5px/1.55 var(--ce-font-num);
}
.template-revision small {
  display: block;
  margin-top: 6px;
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.sw__transcript {
  border: 1px solid var(--ce-panel-border);
  background: #141618;
}
.sw__transcript summary {
  padding: 8px 10px;
  font-size: 12px;
  color: var(--ce-text-dim);
  cursor: pointer;
}
.sw__transcript[open] summary {
  border-bottom: 1px solid var(--ce-divider);
}
.sw__transcript .sw__messages {
  max-height: 210px;
  padding: 8px;
}
@media (max-width: 520px) {
  .sw__impact {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .sw__impact > div:nth-child(3) {
    border-left: none;
    border-top: 1px solid rgba(94, 154, 205, 0.2);
  }
  .sw__impact > div:nth-child(4) {
    border-top: 1px solid rgba(94, 154, 205, 0.2);
  }
  .sw__variants {
    grid-template-columns: 1fr;
  }
  .template-manage,
  .template-manage__row {
    grid-template-columns: 1fr;
  }
  .template-manage__list {
    max-height: 230px;
  }
  .template-manage__actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>

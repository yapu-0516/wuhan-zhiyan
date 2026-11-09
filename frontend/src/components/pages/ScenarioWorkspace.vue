<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ChatDotRound, Document, FullScreen, RefreshLeft, VideoPause, VideoPlay } from '@element-plus/icons-vue'
import type CesiumViewer from '@/components/CesiumViewer.vue'
import { getRoads } from '@/api/geo'
import {
  compareScenarioRuns,
  createScenarioSession,
  generateScenarioReport,
  runCurrentScenarioVariants,
  sendScenarioMessage
} from '@/api/scenario'
import { errMsg } from '@/composables/pages/format'
import type {
  ScenarioComparison,
  ScenarioFrame,
  ScenarioReport,
  ScenarioRun,
  ScenarioSessionView
} from '@/types/scenario'
import { SCENARIO_LABEL } from '@/types/scenario'
import { ScenarioLayer } from '@/components/scene/scenario/scenarioLayer'

const props = defineProps<{ viewer: InstanceType<typeof CesiumViewer> | null }>()
const emit = defineEmits<{ (event: 'view-map'): void; (event: 'close'): void }>()

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
    p.response_delay_min !== undefined && p.response_delay_min !== null ? `响应 ${p.response_delay_min} 分钟` : ''
  ].filter(Boolean)
})
const prompts = [
  '武昌区发生暴雨，推演积水对周边人员和道路的影响。',
  '中山大道从 2026-10-31 17:30 起发生严重拥堵，持续60分钟，原因为交通事故，请推演。',
  '武昌区在 2026-10-31 18:00 发生中型火灾，危险半径200米，影响200人，持续30分钟，请开始推演。'
]
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
  if (!session.value) session.value = await createScenarioSession()
  return session.value
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
  void ensureSession()
    .then(async (current) => {
      variants.value = current.variant_runs ?? []
      if (current.latest_run) await loadRun(current.latest_run)
    })
    .catch((e) => (error.value = errMsg(e, '无法创建情景会话')))
})
onBeforeUnmount(() => {
  pause()
  layer?.destroy()
  layer = null
})
</script>

<template>
  <section class="sw">
    <div class="sw__head">
      <h2>城市智能情景推演</h2>
      <button type="button" aria-label="关闭情景推演" @click="emit('close')">×</button>
    </div>
    <div v-if="!run" class="sw__intro">
      <h3>输入意外事件</h3>
      <p>输入一句话描述意外事件。Agent 提取关键信息，演示模式自动补全合理假设，并生成常规、不利、干预三种可能结果。</p>
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
        </div>
        <div class="sw__run-actions">
          <el-button size="small" :icon="FullScreen" @click="emit('view-map')">查看地图</el-button>
          <el-button size="small" :loading="busy" @click="compare">对比最近两次</el-button>
          <el-button size="small" :icon="Document" :loading="busy" @click="makeReport">生成报告</el-button>
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
  </section>
</template>

<style scoped>
.sw {
  display: flex;
  flex-direction: column;
  gap: 14px;
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
}
</style>

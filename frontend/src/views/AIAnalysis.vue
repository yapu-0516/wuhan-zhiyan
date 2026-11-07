<script setup lang="ts">
// AI 智能分析 —— 真实算法在线运行（按分析类型拆分为独立页面）
// 路由 /ai-analysis/:type：每页只承载一种风险分析（火灾 / 拥堵 / 建筑异常 / 内涝）。
// 选择示例 / 上传数据 → 提交任务 → WebSocket + 轮询跟踪进度 → 展示标注图、检测目标、指标与时序曲线。
// 诚信原则：离线 / 静态模式下后端返回 prototype 任务，仅提示需要后端，绝不伪造分析结果。
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { Sunny, Van, OfficeBuilding, Umbrella, Connection } from '@element-plus/icons-vue'
import { getSystemInfo } from '@/api/system'
import { createTask, getSamples, getTask, getTasks, uploadTask } from '@/api/task'
import { apiState } from '@/api/http'
import { useRealtime } from '@/composables/useRealtime'
import { useTaskRunner } from '@/composables/pages/useTaskRunner'
import { errMsg } from '@/composables/pages/format'
import { typeMeta } from '@/composables/pages/aiMeta'
import type { SubmitPayload } from '@/composables/pages/aiMeta'
import PageShell from '@/components/pages/PageShell.vue'
import TaskInputPanel from '@/components/pages/TaskInputPanel.vue'
import TaskProgress from '@/components/pages/TaskProgress.vue'
import TaskResultView from '@/components/pages/TaskResultView.vue'
import TaskHistory from '@/components/pages/TaskHistory.vue'
import type { AnalysisTask, SystemInfo } from '@/types/api'
import type { EventType } from '@/types/event'

const route = useRoute()
const router = useRouter()
const rt = useRealtime()
const { connected } = rt

const info = ref<SystemInfo | null>(null)
const infoLoading = ref(true)
const tasks = ref<AnalysisTask[]>([])
const tasksLoading = ref(false)
const submitting = ref(false)
const prototype = ref<AnalysisTask | null>(null)
const resultEl = ref<HTMLElement>()

/** 当前页面对应的分析类型（由路由参数决定，非法值回退火灾） */
const selectedType = computed<EventType>(() => {
  const t = route.params.type
  return typeof t === 'string' && typeMeta(t) ? (t as EventType) : 'fire'
})
const center = computed<[number, number]>(() => info.value?.region?.center ?? [114.2955, 30.5895])
const algorithms = computed(() => info.value?.algorithms ?? [])
const curMeta = computed(() => typeMeta(selectedType.value)!)
const typeAlgo = computed(() => algorithms.value.find((a) => a.type === selectedType.value))
const typeIcons = { fire: Sunny, traffic: Van, building: OfficeBuilding, flood: Umbrella }

// ---------- 任务列表（仅当前分析类型） ----------
function upsertTask(t: AnalysisTask) {
  if (t.status === 'prototype' || t.type !== selectedType.value) return
  const i = tasks.value.findIndex((x) => x.id === t.id)
  if (i >= 0) tasks.value.splice(i, 1, { ...tasks.value[i], ...t })
  else tasks.value.unshift(t)
}

function notifyDone(t: AnalysisTask) {
  if (t.status === 'failed') {
    ElMessage.error(`任务 ${t.id} 分析失败${t.error ? `：${t.error}` : ''}`)
    return
  }
  const r = t.result
  if (r?.detected) {
    ElNotification({
      title: `${typeMeta(t.type)?.label ?? '分析'}：检测到异常`,
      message: r.summary + (r.event_ids?.length ? `（已生成事件 ${r.event_ids.join('、')}）` : ''),
      type: 'warning',
      duration: 6000
    })
  } else {
    ElMessage.success(`任务 ${t.id} 分析完成：未发现异常`)
  }
}

const runner = useTaskRunner({
  onAnyUpdate: upsertTask,
  onTerminal: (t) => {
    upsertTask(t)
    notifyDone(t)
  }
})
const { current, active, elapsedMs, stalled } = runner

async function loadTasks(manual = false) {
  tasksLoading.value = true
  try {
    tasks.value = (await getTasks()).filter((t) => t.status !== 'prototype' && t.type === selectedType.value)
    if (manual) ElMessage.success('任务历史已刷新')
  } catch (e) {
    ElMessage.error(errMsg(e, '任务历史加载失败'))
  } finally {
    tasksLoading.value = false
  }
}

async function scrollToResult() {
  await nextTick()
  resultEl.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}

async function selectTask(t: AnalysisTask) {
  prototype.value = null
  let full = t
  if (t.status === 'done' && !t.result) {
    try {
      full = await getTask(t.id)
    } catch {
      /* 使用列表中的精简数据 */
    }
  }
  runner.track(full)
  void scrollToResult()
}

// ---------- 提交 ----------
async function submit(p: SubmitPayload) {
  submitting.value = true
  prototype.value = null
  try {
    const task = p.files.length
      ? await uploadTask(p.type, p.files, { longitude: p.longitude, latitude: p.latitude, create_event: p.createEvent })
      : await createTask(p.type, 0, {
          sample_id: p.sampleId,
          longitude: p.longitude,
          latitude: p.latitude,
          create_event: p.createEvent
        })
    if (task.status === 'prototype') {
      // 后端不可用：不伪造结果，仅提示
      runner.clear()
      prototype.value = task
      ElMessage.warning('离线演示模式：请启动后端以运行真实算法')
    } else {
      upsertTask(task)
      runner.track(task)
      ElMessage.success(`任务 ${task.id} 已提交`)
    }
    void scrollToResult()
  } catch (e) {
    ElMessage.error(errMsg(e, '提交分析任务失败'))
  } finally {
    submitting.value = false
  }
}

async function runDemoAnalysis() {
  try {
    const samples = await getSamples(selectedType.value)
    const sample =
      samples.find((item) => !/(无火情|正常|未发现|误报)/.test(`${item.name}${item.description}`)) ?? samples[0]
    if (!sample) return
    await submit({
      type: selectedType.value,
      sampleId: sample.id,
      files: [],
      longitude: sample.longitude ?? center.value[0],
      latitude: sample.latitude ?? center.value[1],
      createEvent: true
    })
  } catch (e) {
    ElMessage.warning(errMsg(e, '自动演示分析任务提交失败'))
  }
}

const status = computed(() => current.value?.status)

// 切换分析类型（路由参数变化）：清空上一个类型的结果，只保留本类型任务
watch(selectedType, () => {
  prototype.value = null
  runner.clear()
  tasks.value = []
  void loadTasks()
})

onMounted(async () => {
  rt.start()
  void loadTasks()
  try {
    info.value = await getSystemInfo()
  } catch {
    /* 算法信息缺失时显示"不可用" */
  } finally {
    infoLoading.value = false
  }
  // 深链：/ai-analysis/fire?task=T0003（任务类型不一致时跳到对应页面）
  const id = typeof route.query.task === 'string' ? route.query.task : ''
  if (id) {
    try {
      const t = await getTask(id)
      if (typeMeta(t.type) && t.type !== selectedType.value) {
        await router.replace({ path: `/ai-analysis/${t.type}`, query: { task: id } })
        await nextTick()
      }
      await selectTask(t)
    } catch (e) {
      ElMessage.warning(errMsg(e, `任务 ${id} 不存在`))
    }
  }
  if (route.query.demo === '1') void runDemoAnalysis()
})
</script>

<template>
  <PageShell
    :title="curMeta.label"
    hint="选择分析场景与数据 → 配置参数并运行 → 查看结果与历史记录"
    banner-detail="AI 分析需要后端算法服务。"
  >
    <template #actions>
      <span class="chan" :class="{ 'is-on': connected }">
        <i
          class="cp-dot"
          :class="{ 'cp-dot--pulse': connected }"
          :style="{ '--c': connected ? '#4dd984' : '#8aa3c4' }"
        ></i>
        {{ connected ? '实时通道已连接' : apiState.mode === 'live' ? '实时通道重连中 · 轮询兜底' : '实时通道未启用' }}
      </span>
    </template>

    <div class="ai">
      <!-- 当前分析类型标识 -->
      <section class="ai-hero cp-panel" :style="{ '--c': curMeta.color }">
        <span class="ai-hero__icon"
          ><el-icon><component :is="typeIcons[selectedType]" /></el-icon
        ></span>
        <div class="ai-hero__txt">
          <b>{{ curMeta.label }}</b>
          <p>{{ curMeta.blurb }}</p>
          <div class="ai-hero__inputs">
            <span v-for="i in curMeta.inputs" :key="i" class="ai-hero__chip">{{ i }}</span>
          </div>
        </div>
        <div class="ai-hero__algo">
          <template v-if="typeAlgo">
            <span class="cp-label">算法</span>
            <b class="cp-mono">{{ typeAlgo.name }}</b>
            <i>v{{ typeAlgo.version }}</i>
            <p>{{ typeAlgo.method }}</p>
          </template>
          <el-skeleton v-else-if="infoLoading" animated :rows="1" />
          <p v-else class="ai-hero__na">算法信息由后端提供（当前不可用）</p>
        </div>
      </section>

      <section class="cp-panel ai__input">
        <div class="cp-panel__header">
          <h3 class="cp-panel__title">分析数据输入</h3>
          <span class="cp-panel__sub">{{ curMeta.label }}</span>
        </div>
        <div class="cp-panel__body">
          <TaskInputPanel :type="selectedType" :center="center" :busy="submitting || active" @submit="submit" />
        </div>
      </section>

      <section ref="resultEl" class="ai__result">
        <Transition name="swap" mode="out-in">
          <!-- 离线：原型任务，不展示任何结果 -->
          <div v-if="prototype" key="proto" class="proto cp-panel">
            <div class="proto__icon">
              <el-icon><Connection /></el-icon>
            </div>
            <div>
              <h3>离线演示模式：请启动后端以运行真实算法</h3>
              <p>
                AI 分析（{{
                  typeMeta(prototype.type)?.label
                }}）由后端算法服务执行。当前未连接后端，平台<b>不会</b>生成任何模拟或虚构的分析结果。
                启动后端服务后刷新本页即可使用示例数据与文件上传分析。
              </p>
            </div>
          </div>
          <TaskProgress
            v-else-if="current && (status === 'pending' || status === 'running' || status === 'failed')"
            key="prog"
            :task="current"
            :elapsed-ms="elapsedMs"
            :stalled="stalled"
          />
          <TaskResultView v-else-if="current && status === 'done'" :key="`res-${current.id}`" :task="current" />
          <div v-else key="empty" class="idle cp-panel">
            <div class="idle__title">分析结果将在此处呈现</div>
            <p>选择左侧示例数据或上传文件，点击「开始分析」。真实算法在后端异步执行，进度实时推送。</p>
            <ol class="idle__flow">
              <li><b>01</b>提交任务</li>
              <li><b>02</b>数据预处理</li>
              <li><b>03</b>模型推理</li>
              <li><b>04</b>结果后处理</li>
              <li><b>05</b>标注 · 指标 · 事件</li>
            </ol>
            <dl class="idle__facts">
              <div>
                <dt>输入约束</dt>
                <dd>{{ curMeta.rule }}</dd>
              </div>
              <div>
                <dt>标准输出</dt>
                <dd>标注影像、检测框、算法指标、事件记录</dd>
              </div>
              <div>
                <dt>当前算法</dt>
                <dd>{{ typeAlgo?.name ?? '等待后端算法信息' }}</dd>
              </div>
              <div>
                <dt>判定原则</dt>
                <dd>算法未检出时不会生成城市事件</dd>
              </div>
            </dl>
            <div class="idle__output">
              <b>任务完成后可核对</b>
              <ul>
                <li><span>标注影像</span><em>算法在原图上的检测结果</em></li>
                <li><span>检测目标</span><em>位置、类别与置信度</em></li>
                <li><span>算法指标</span><em>面积占比、数量或时序结论</em></li>
                <li><span>城市事件</span><em>仅在实际检出时进入事件中心</em></li>
              </ul>
            </div>
          </div>
        </Transition>
      </section>
    </div>

    <TaskHistory
      :tasks="tasks"
      :current-id="current?.id ?? ''"
      :loading="tasksLoading"
      @select="selectTask"
      @refresh="loadTasks(true)"
    />
  </PageShell>
</template>

<style scoped>
.ai {
  display: grid;
  grid-template-columns: minmax(340px, 440px) minmax(0, 1fr);
  grid-template-areas:
    'hero hero'
    'input result';
  gap: 16px;
  align-items: stretch;
}
.ai-hero {
  grid-area: hero;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 16px 20px;
  border-color: var(--ce-panel-border);
  background: var(--ce-panel-solid);
  border-left: 2px solid var(--c);
}
.ai-hero__icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 54px;
  height: 54px;
  font-size: 24px;
  border-radius: 4px;
  color: var(--c);
  background: #1d1f22;
  border: 1px solid var(--ce-panel-border);
}
.ai-hero__txt {
  flex: 1 1 auto;
  min-width: 0;
}
.ai-hero__txt b {
  font-size: 18px;
  color: var(--ce-text-strong);
}
.ai-hero__txt p {
  margin: 4px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ce-text-dim);
}
.ai-hero__inputs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.ai-hero__chip {
  padding: 0 8px;
  line-height: 20px;
  font-size: 12px;
  border-radius: 4px;
  color: var(--ce-text-dim);
  background: #1d1f22;
  border: 1px solid var(--ce-panel-border);
}
.ai-hero__algo {
  flex: 0 1 320px;
  min-width: 0;
  padding: 10px 12px;
  border-radius: 4px;
  background: #141618;
  border: 1px solid var(--ce-panel-border);
}
.ai-hero__algo .cp-label {
  margin-right: 6px;
}
.ai-hero__algo b {
  font-size: 13px;
  color: var(--c);
}
.ai-hero__algo i {
  margin-left: 6px;
  font-style: normal;
  font-size: 12px;
  color: var(--ce-text-faint);
}
.ai-hero__algo p {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--ce-text-dim);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ai-hero__na {
  margin: 0;
  font-size: 12px;
  color: #5d748f;
}
.ai__input {
  grid-area: input;
  min-width: 0;
}
.ai__result {
  grid-area: result;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.ai__result > * {
  flex: 1;
}
@media (max-width: 1360px) {
  .ai {
    grid-template-columns: 1fr;
    grid-template-areas:
      'hero'
      'input'
      'result';
  }
  .ai-hero {
    flex-wrap: wrap;
  }
  .ai-hero__algo {
    flex-basis: 100%;
  }
}
.chan {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 28px;
  padding: 0 12px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--ce-text-dim);
  background: transparent;
  border: 1px solid var(--ce-panel-border);
}
.chan.is-on {
  color: #7be8aa;
  border-color: var(--ce-success);
}
.proto {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 26px 30px;
  border-color: var(--ce-panel-border);
  background: var(--ce-panel-solid);
}
.proto__icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 64px;
  height: 64px;
  font-size: 24px;
  border-radius: 4px;
  color: var(--ce-warning);
  background: #1d1f22;
  border: 1px solid var(--ce-panel-border);
}
.proto h3 {
  margin: 0 0 8px;
  font-size: 17px;
  color: var(--ce-text-strong);
}
.proto p {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.8;
  color: var(--ce-text);
}
.proto b {
  color: #ffd98a;
}
.idle {
  padding: 28px 30px 30px;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 8px;
  background: var(--ce-panel-solid);
}
.idle__title {
  font-size: 18px;
  letter-spacing: 0;
  color: var(--ce-text-strong);
}
.idle p {
  margin: 0 0 14px;
  font-size: 13.5px;
  color: var(--ce-text-dim);
}
.idle__flow {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 0;
  padding: 0;
}
.idle__flow li {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px 8px 10px;
  font-size: 13px;
  color: var(--ce-text);
  border-radius: 4px;
  background: #1a1c1e;
  border: 1px solid var(--ce-panel-border);
}
.idle__flow li:not(:last-child)::after {
  content: '›';
  position: absolute;
  right: -10px;
  top: 50%;
  transform: translateY(-52%);
  font-size: 18px;
  color: #4a6a8f;
}
.idle__flow li b {
  font-size: 12px;
  letter-spacing: 0;
  padding: 1px 6px;
  border-radius: 4px;
  color: #06101f;
  background: var(--ce-accent, #4fc3f7);
}
.idle__facts {
  display: grid;
  grid-template-columns: 1fr;
  grid-auto-rows: 80px;
  gap: 1px;
  margin: 14px 0;
  background: var(--ce-divider);
  border: 1px solid var(--ce-divider);
}
.idle__facts > div {
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr);
  align-items: center;
  min-width: 0;
  padding: 9px 14px;
  background: #1a1c1e;
}
.idle__facts dt {
  margin: 0;
  font-size: 12px;
  color: var(--ce-text-faint);
}
.idle__facts dd {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--ce-text);
}
.idle__output {
  padding: 12px 14px;
  border: 1px solid var(--ce-panel-border);
  background: #141618;
}
.idle__output > b {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--ce-text-strong);
}
.idle__output ul {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  margin: 0;
  padding: 1px;
  list-style: none;
  background: var(--ce-divider);
}
.idle__output li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  background: #1a1c1e;
}
.idle__output span {
  font-size: 13px;
  color: var(--ce-text);
}
.idle__output em {
  font-style: normal;
  font-size: 12px;
  color: var(--ce-text-faint);
}
.swap-enter-active,
.swap-leave-active {
  transition:
    opacity 0.22s ease,
    transform 0.22s ease;
}
.swap-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.swap-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .swap-enter-active,
  .swap-leave-active {
    transition: none;
  }
}
</style>

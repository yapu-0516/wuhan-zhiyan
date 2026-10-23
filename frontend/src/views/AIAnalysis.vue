<script setup lang="ts">
// AI 智能分析 —— 真实算法在线运行
// 选择分析类型 → 选择示例 / 上传数据 → 提交任务 → WebSocket + 轮询跟踪进度 → 展示标注图、检测目标、指标与时序曲线。
// 诚信原则：离线 / 静态模式下后端返回 prototype 任务，仅提示需要后端，绝不伪造分析结果。
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { getSystemInfo } from '@/api/system'
import { createTask, getTask, getTasks, uploadTask } from '@/api/task'
import { apiState } from '@/api/http'
import { useRealtime } from '@/composables/useRealtime'
import { useTaskRunner } from '@/composables/pages/useTaskRunner'
import { errMsg } from '@/composables/pages/format'
import { typeMeta } from '@/composables/pages/aiMeta'
import type { SubmitPayload } from '@/composables/pages/aiMeta'
import PageShell from '@/components/pages/PageShell.vue'
import AnalysisTypeCards from '@/components/pages/AnalysisTypeCards.vue'
import TaskInputPanel from '@/components/pages/TaskInputPanel.vue'
import TaskProgress from '@/components/pages/TaskProgress.vue'
import TaskResultView from '@/components/pages/TaskResultView.vue'
import TaskHistory from '@/components/pages/TaskHistory.vue'
import type { AnalysisTask, SystemInfo } from '@/types/api'
import type { EventType } from '@/types/event'

const route = useRoute()
const rt = useRealtime()
const { connected } = rt

const info = ref<SystemInfo | null>(null)
const infoLoading = ref(true)
const selectedType = ref<EventType>('fire')
const tasks = ref<AnalysisTask[]>([])
const tasksLoading = ref(false)
const submitting = ref(false)
const prototype = ref<AnalysisTask | null>(null)
const resultEl = ref<HTMLElement>()

const center = computed<[number, number]>(() => info.value?.region?.center ?? [114.2955, 30.5895])
const algorithms = computed(() => info.value?.algorithms ?? [])
const curMeta = computed(() => typeMeta(selectedType.value)!)

// ---------- 任务列表 ----------
function upsertTask(t: AnalysisTask) {
  if (t.status === 'prototype') return
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
    tasks.value = (await getTasks()).filter((t) => t.status !== 'prototype')
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

function onSelectType(t: EventType) {
  selectedType.value = t
}

const status = computed(() => current.value?.status)

onMounted(async () => {
  rt.start()
  void loadTasks()
  try {
    info.value = await getSystemInfo()
  } catch {
    /* 算法信息缺失时卡片显示"不可用" */
  } finally {
    infoLoading.value = false
  }
  // 深链：/ai-analysis?task=T0003
  const id = typeof route.query.task === 'string' ? route.query.task : ''
  if (id) {
    try {
      const t = await getTask(id)
      if (typeMeta(t.type)) selectedType.value = t.type as EventType
      await selectTask(t)
    } catch (e) {
      ElMessage.warning(errMsg(e, `任务 ${id} 不存在`))
    }
  }
})
</script>

<template>
  <PageShell title="AI 智能分析" hint="四类城市风险的真实算法在线分析：火灾识别、交通拥堵、建筑异常、内涝积水" banner-detail="AI 分析需要后端算法服务。">
    <template #actions>
      <span class="chan" :class="{ 'is-on': connected }">
        <i class="cp-dot" :class="{ 'cp-dot--pulse': connected }" :style="{ '--c': connected ? '#4dd984' : '#8aa3c4' }"></i>
        {{ connected ? '实时通道已连接' : apiState.mode === 'live' ? '实时通道重连中 · 轮询兜底' : '实时通道未启用' }}
      </span>
    </template>

    <div class="ai">
      <section class="ai__types">
        <h3 class="sec-label">选择分析类型</h3>
        <AnalysisTypeCards :selected="selectedType" :algorithms="algorithms" :loading="infoLoading" @select="onSelectType" />
      </section>

      <section class="cp-panel ai__input">
        <div class="cp-panel__header">
          <h3 class="cp-panel__title">分析数据输入</h3>
          <span class="cp-panel__sub">{{ curMeta.icon }} {{ curMeta.label }}</span>
        </div>
        <div class="cp-panel__body">
          <TaskInputPanel :type="selectedType" :center="center" :busy="submitting || active" @submit="submit" />
        </div>
      </section>

      <section ref="resultEl" class="ai__result">
        <Transition name="swap" mode="out-in">
          <!-- 离线：原型任务，不展示任何结果 -->
          <div v-if="prototype" key="proto" class="proto cp-panel">
            <div class="proto__icon">🔌</div>
            <div>
              <h3>离线演示模式：请启动后端以运行真实算法</h3>
              <p>
                AI 分析（{{ typeMeta(prototype.type)?.label }}）由后端算法服务执行。当前未连接后端，平台<b>不会</b>生成任何模拟或虚构的分析结果。
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
            <p>选择左侧分析类型，挑选示例数据或上传文件，点击「开始分析」。真实算法在后端异步执行，进度实时推送。</p>
            <ol class="idle__flow">
              <li><b>01</b>提交任务</li>
              <li><b>02</b>数据预处理</li>
              <li><b>03</b>模型推理</li>
              <li><b>04</b>结果后处理</li>
              <li><b>05</b>标注 · 指标 · 事件</li>
            </ol>
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
  grid-template-columns: 310px minmax(0, 1fr);
  grid-template-areas:
    'types input'
    'result result';
  gap: 16px;
  align-items: start;
}
.ai__types {
  grid-area: types;
  min-width: 0;
}
.ai__input {
  grid-area: input;
}
.ai__result {
  grid-area: result;
  min-width: 0;
}
@media (min-width: 2200px) {
  .ai {
    grid-template-columns: 330px minmax(440px, 600px) minmax(0, 1fr);
    grid-template-areas: 'types input result';
  }
}
@media (max-width: 1360px) {
  .ai {
    grid-template-columns: 1fr;
    grid-template-areas:
      'types'
      'input'
      'result';
  }
  .ai__types :deep(.tcs) {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.sec-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #a9cdf0;
}
.sec-label::before {
  content: '';
  width: 6px;
  height: 6px;
  background: var(--ce-accent, #4fc3f7);
  box-shadow: 0 0 8px var(--ce-accent, #4fc3f7);
  transform: rotate(45deg);
}
.chan {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  color: #8aa3c4;
  background: rgba(9, 16, 34, 0.6);
  border: 1px solid rgba(64, 120, 180, 0.28);
}
.chan.is-on {
  color: #7be8aa;
  border-color: rgba(77, 217, 132, 0.4);
}
.proto {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 26px 30px;
  border-color: rgba(240, 192, 80, 0.4);
  background: linear-gradient(90deg, rgba(240, 192, 80, 0.1), var(--ce-panel, rgba(16, 26, 48, 0.72)) 60%);
}
.proto__icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 64px;
  height: 64px;
  font-size: 32px;
  border-radius: 18px;
  background: rgba(240, 192, 80, 0.12);
  border: 1px solid rgba(240, 192, 80, 0.45);
}
.proto h3 {
  margin: 0 0 8px;
  font-size: 17px;
  color: #f6d78a;
}
.proto p {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.8;
  color: #c9d6ea;
}
.proto b {
  color: #ffd98a;
}
.idle {
  padding: 28px 30px 30px;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  background:
    radial-gradient(500px 200px at 100% 100%, rgba(79, 195, 247, 0.07), transparent 70%),
    var(--ce-panel, rgba(16, 26, 48, 0.72));
}
.idle__title {
  font-size: 18px;
  letter-spacing: 3px;
  color: #cfe3fb;
}
.idle p {
  margin: 0 0 14px;
  font-size: 13.5px;
  color: #8aa3c4;
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
  color: #b9cdec;
  border-radius: 8px;
  background: rgba(9, 16, 34, 0.55);
  border: 1px solid rgba(64, 120, 180, 0.3);
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
  font-size: 11px;
  letter-spacing: 1px;
  padding: 1px 6px;
  border-radius: 4px;
  color: #06101f;
  background: var(--ce-accent, #4fc3f7);
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

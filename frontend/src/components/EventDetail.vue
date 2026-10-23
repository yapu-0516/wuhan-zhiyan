<script setup lang="ts">
// 事件详情面板：等级/类型/状态、置信度、位置、证据图、算法指标、处置记录，以及按状态机提供的处置操作。
// 处置操作统一走 useCityEvents().updateEvent（PATCH /api/events/{id}）；离线模式下仅本地生效。
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { CityEvent, EventLog, EventStatus } from '@/types/event'
import {
  EVENT_STATUS_COLOR,
  EVENT_STATUS_LABEL,
  EVENT_TYPE_META,
  SEVERITY_META,
  SOURCE_META,
  STATUS_TRANSITIONS
} from '@/types/event'
import { useCityEvents } from '@/composables/useCityEvents'
import { getEventLogs } from '@/api/event'
import { apiState } from '@/api/http'
import { fileUrl } from '@/config/api'
import { metricLabel, metricValue, shortTime } from '@/utils/format'

const props = defineProps<{ event: CityEvent }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'locate', id: string): void
  (e: 'open-building', id: string): void
}>()

const router = useRouter()
const { updateEvent } = useCityEvents()

const typeMeta = computed(() => EVENT_TYPE_META[props.event.event_type] ?? EVENT_TYPE_META.fire)
const sevMeta = computed(() => SEVERITY_META[props.event.severity] ?? SEVERITY_META.medium)
const sourceMeta = computed(() => SOURCE_META[props.event.source] ?? { label: props.event.source || '—', icon: '📍' })
const statusColor = computed(() => EVENT_STATUS_COLOR[props.event.status] ?? '#8aa3c4')
const confidence = computed(() => Math.round(Math.max(0, Math.min(1, props.event.confidence ?? 0)) * 100))
const evidence = computed(() => fileUrl(props.event.evidence_url))
const metrics = computed(() =>
  Object.entries(props.event.metrics ?? {})
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .slice(0, 8)
    .map(([k, v]) => ({ key: k, label: metricLabel(k), value: metricValue(k, v) }))
)
const transitions = computed<EventStatus[]>(() => STATUS_TRANSITIONS[props.event.status] ?? [])

// ---------------- 处置记录
const logs = ref<EventLog[]>([])
async function loadLogs() {
  const id = props.event.id
  try {
    const list = await getEventLogs(id)
    if (id === props.event.id) logs.value = Array.isArray(list) ? list.slice(-4).reverse() : []
  } catch {
    logs.value = []
  }
}
watch(() => [props.event.id, props.event.updated_at], loadLogs, { immediate: true })

const LOG_ACTION: Record<string, string> = {
  created: '事件创建',
  status_changed: '状态变更',
  assigned: '派单指派',
  comment: '处置备注',
  ai_detected: 'AI 识别'
}

// ---------------- 处置操作
const busy = ref(false)
const dispatchOpen = ref(false)
const dispatchTarget = ref<EventStatus>('processing')
const assignee = ref('')
const note = ref('')
const highlight = ref(false)

const assigneeOptions = computed(() => {
  const d = props.event.district || '属地'
  const map: Record<CityEvent['event_type'], string[]> = {
    fire: [`${d}消防救援大队`, `${d}应急管理局`, '武汉市消防救援支队特勤大队'],
    traffic: [`${d}交警大队`, `${d}城管执法局`, '武汉市交通运输局路网中心'],
    building: [`${d}住房和城市更新局`, `${d}应急管理局`, '武汉市建设工程质量安全监督站'],
    flood: [`${d}水务和湖泊局`, `${d}城管执法局`, '武汉市排水泵站运营中心']
  }
  const list = map[props.event.event_type] ?? [`${d}应急管理局`]
  return props.event.assignee && !list.includes(props.event.assignee) ? [props.event.assignee, ...list] : list
})

watch(
  () => props.event.id,
  () => {
    dispatchOpen.value = false
    highlight.value = false
  }
)

function openDispatch(target: EventStatus = 'processing', prefill?: string) {
  dispatchTarget.value = target
  assignee.value = prefill ?? props.event.assignee ?? assigneeOptions.value[0] ?? ''
  note.value = target === 'processing' && props.event.status === 'resolved' ? '事件复发，重新打开处置' : '请立即赶赴现场核查处置'
  dispatchOpen.value = true
}

async function patch(status: EventStatus, extra: { assignee?: string; note?: string } = {}): Promise<CityEvent | null> {
  if (busy.value) return null
  busy.value = true
  try {
    const updated = await updateEvent(props.event.id, { status, operator: '指挥中心值班员', ...extra })
    const offline = apiState.mode !== 'live' ? '（离线演示，仅本地生效）' : ''
    const msg =
      status === 'processing'
        ? `已派单至「${updated.assignee ?? extra.assignee ?? '处置单位'}」${offline}`
        : status === 'resolved'
          ? `事件已办结${offline}`
          : `事件已转为「${EVENT_STATUS_LABEL[status]}」${offline}`
    ElMessage.success(msg)
    dispatchOpen.value = false
    return updated
  } catch (e) {
    ElMessage.error((e as Error)?.message || '操作失败，请稍后重试')
    return null
  } finally {
    busy.value = false
  }
}

function submitDispatch() {
  if (!assignee.value.trim()) {
    ElMessage.warning('请选择处置单位')
    return Promise.resolve(null)
  }
  return patch(dispatchTarget.value, { assignee: assignee.value.trim(), note: note.value.trim() || undefined })
}

function actionLabel(s: EventStatus): string {
  if (s === 'processing') return props.event.status === 'resolved' ? '重新打开' : '派单处置'
  if (s === 'resolved') return '标记办结'
  if (s === 'monitoring') return '转入监测'
  return EVENT_STATUS_LABEL[s]
}

function onAction(s: EventStatus) {
  if (s === 'processing') openDispatch('processing')
  else if (s === 'monitoring') void patch('monitoring', { note: '转入持续监测' })
}

function viewInCenter() {
  void router.push({ path: '/event-center', query: { id: props.event.id } })
}

/** 演示导览：展开派单表单并高亮，再自动提交 */
async function demoDispatch(prefill?: string): Promise<CityEvent | null> {
  if (!transitions.value.includes('processing')) return null
  openDispatch('processing', prefill)
  highlight.value = true
  await nextTick()
  await new Promise((r) => window.setTimeout(r, 1600))
  const res = await submitDispatch()
  highlight.value = false
  return res
}

defineExpose({ openDispatch, submitDispatch, demoDispatch })
</script>

<template>
  <section class="event-detail ce-panel" :style="{ '--type-color': typeMeta.color, '--sev-color': sevMeta.color }">
    <header class="ed-head">
      <div class="ed-icon">{{ typeMeta.icon }}</div>
      <div class="ed-title">
        <h3 :title="event.name">{{ event.name }}</h3>
        <p>
          <span class="ce-num">{{ event.id }}</span>
          <span class="sep">·</span>{{ typeMeta.label }}
          <span class="sep">·</span>{{ sourceMeta.icon }} {{ sourceMeta.label }}
        </p>
      </div>
      <button class="ed-close" title="关闭" @click="emit('close')">×</button>
    </header>

    <div class="ed-body">
      <div class="ed-badges">
        <span class="ed-sev">{{ sevMeta.label }}</span>
        <span class="ce-tag" :style="{ color: statusColor }"><i class="ce-dot" :class="{ 'ce-dot--pulse': event.status !== 'resolved' }" />{{ EVENT_STATUS_LABEL[event.status] }}</span>
        <span v-if="event.task_id" class="ce-tag ed-task">AI 任务 {{ event.task_id }}</span>
      </div>

      <div class="ed-conf">
        <span class="ed-conf__label">AI 置信度</span>
        <div class="ed-conf__bar"><i :style="{ width: confidence + '%' }" /></div>
        <span class="ed-conf__value ce-num">{{ confidence }}%</span>
      </div>

      <div v-if="evidence" class="ed-evidence">
        <el-image
          :src="evidence"
          :preview-src-list="[evidence]"
          fit="cover"
          preview-teleported
          hide-on-click-modal
          class="ed-evidence__img"
        >
          <template #error>
            <div class="ed-evidence__err">证据图暂不可用</div>
          </template>
        </el-image>
        <span class="ed-evidence__cap">算法标注证据 · 点击放大</span>
      </div>

      <dl class="ed-grid">
        <div><dt>发现时间</dt><dd class="ce-num">{{ shortTime(event.timestamp) }}</dd></div>
        <div><dt>最近更新</dt><dd class="ce-num">{{ shortTime(event.updated_at) }}</dd></div>
        <div><dt>行政区</dt><dd>{{ event.district || '—' }}</dd></div>
        <div><dt>网格编号</dt><dd class="ce-num">{{ event.grid || '—' }}</dd></div>
        <div class="span2"><dt>地址</dt><dd>{{ event.address || '—' }}</dd></div>
        <div><dt>坐标</dt><dd class="ce-num">{{ event.longitude.toFixed(4) }}, {{ event.latitude.toFixed(4) }}</dd></div>
        <div>
          <dt>处置单位</dt>
          <dd :class="{ dim: !event.assignee }">{{ event.assignee || '未指派' }}</dd>
        </div>
        <div v-if="event.building_id" class="span2">
          <dt>关联建筑</dt>
          <dd><a class="ed-link" @click="emit('open-building', event.building_id!)">{{ event.building_id }} · 查看建筑与沉降监测 →</a></dd>
        </div>
      </dl>

      <p v-if="event.description" class="ed-desc">{{ event.description }}</p>

      <div v-if="metrics.length" class="ed-metrics">
        <div v-for="m in metrics" :key="m.key" class="ed-metric">
          <span class="ed-metric__v ce-num">{{ m.value }}</span>
          <span class="ed-metric__k">{{ m.label }}</span>
        </div>
      </div>

      <div v-if="logs.length" class="ed-logs">
        <div class="ed-sub">处置记录</div>
        <ol>
          <li v-for="l in logs" :key="l.id">
            <span class="ed-logs__t ce-num">{{ shortTime(l.timestamp) }}</span>
            <span class="ed-logs__a">{{ LOG_ACTION[l.action] ?? l.action }}</span>
            <span class="ed-logs__n">{{ l.note || (l.to_status ? EVENT_STATUS_LABEL[l.to_status] : '') }}</span>
          </li>
        </ol>
      </div>

      <transition name="ed-fold">
        <div v-if="dispatchOpen" class="ed-dispatch" :class="{ 'is-demo': highlight }">
          <div class="ed-sub">{{ dispatchTarget === 'processing' && event.status === 'resolved' ? '重新打开并派单' : '派单处置' }}</div>
          <el-select v-model="assignee" filterable allow-create default-first-option placeholder="选择处置单位" size="small" teleported>
            <el-option v-for="o in assigneeOptions" :key="o" :label="o" :value="o" />
          </el-select>
          <el-input v-model="note" size="small" placeholder="派单说明（可选）" maxlength="60" />
          <div class="ed-dispatch__btns">
            <el-button size="small" type="primary" :loading="busy" @click="submitDispatch">确认派单</el-button>
            <el-button size="small" @click="dispatchOpen = false">取消</el-button>
          </div>
        </div>
      </transition>
    </div>

    <footer class="ed-actions">
      <template v-for="s in transitions" :key="s">
        <el-popconfirm
          v-if="s === 'resolved'"
          title="确认该事件已处置完毕并办结？"
          confirm-button-text="确认办结"
          cancel-button-text="取消"
          width="220"
          @confirm="patch('resolved', { note: '现场处置完毕，事件办结' })"
        >
          <template #reference>
            <button class="ed-btn ed-btn--ok" :disabled="busy">✓ {{ actionLabel(s) }}</button>
          </template>
        </el-popconfirm>
        <button
          v-else
          class="ed-btn"
          :class="{ 'ed-btn--primary': s === 'processing', 'is-active': dispatchOpen && s === 'processing' }"
          :disabled="busy"
          @click="onAction(s)"
        >
          {{ s === 'processing' ? '➤' : '◎' }} {{ actionLabel(s) }}
        </button>
      </template>
      <span class="ed-actions__spacer" />
      <button class="ed-btn ed-btn--ghost" title="定位到事件" @click="emit('locate', event.id)">定位</button>
      <button class="ed-btn ed-btn--ghost" @click="viewInCenter">事件中心查看</button>
    </footer>
  </section>
</template>

<style scoped>
.event-detail {
  width: 100%;
  max-height: 100%;
  overflow: hidden;
  border-top: 2px solid var(--type-color);
}
.ed-head {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 12px 10px;
  border-bottom: 1px solid var(--ce-divider);
  background: linear-gradient(90deg, color-mix(in srgb, var(--type-color) 16%, transparent), transparent 70%);
}
.ed-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  font-size: 19px;
  background: var(--type-color);
  background: radial-gradient(circle at 35% 30%, color-mix(in srgb, var(--type-color) 75%, #fff), color-mix(in srgb, var(--type-color) 35%, #050a17));
  box-shadow:
    0 0 0 2px var(--sev-color),
    0 0 16px color-mix(in srgb, var(--type-color) 60%, transparent);
}
.ed-title {
  flex: 1;
  min-width: 0;
}
.ed-title h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--ce-text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ed-title p {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--ce-text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sep {
  margin: 0 5px;
  color: var(--ce-text-faint);
}
.ed-close {
  flex: none;
  width: 26px;
  height: 26px;
  border: 1px solid transparent;
  border-radius: 3px;
  background: transparent;
  color: var(--ce-text-dim);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}
.ed-close:hover {
  color: #fff;
  border-color: var(--ce-panel-border);
  background: rgba(79, 195, 247, 0.1);
}

.ed-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ed-badges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.ed-sev {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 700;
  color: #0a0f1c;
  background: var(--sev-color);
  box-shadow: 0 0 12px color-mix(in srgb, var(--sev-color) 55%, transparent);
}
.ed-task {
  color: var(--ce-text-dim);
}
.ed-conf {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.ed-conf__label {
  color: var(--ce-text-dim);
  white-space: nowrap;
}
.ed-conf__bar {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: rgba(79, 195, 247, 0.1);
  overflow: hidden;
}
.ed-conf__bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #1f78d1, var(--ce-accent-2));
  box-shadow: 0 0 8px var(--ce-accent-glow);
  transition: width 0.6s var(--ce-ease);
}
.ed-conf__value {
  min-width: 36px;
  text-align: right;
  font-size: 14px;
  color: var(--ce-text-strong);
}

.ed-evidence {
  position: relative;
  border: 1px solid var(--ce-divider);
  border-radius: 3px;
  overflow: hidden;
}
.ed-evidence__img {
  display: block;
  width: 100%;
  height: 150px;
  cursor: zoom-in;
}
.ed-evidence__err {
  display: grid;
  place-items: center;
  height: 100%;
  font-size: 12px;
  color: var(--ce-text-faint);
  background: rgba(79, 195, 247, 0.04);
}
.ed-evidence__cap {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 14px 8px 4px;
  font-size: 11px;
  color: #dbe9ff;
  pointer-events: none;
  background: linear-gradient(transparent, rgba(3, 8, 18, 0.85));
}

.ed-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 12px;
  margin: 0;
}
.ed-grid > div {
  min-width: 0;
}
.ed-grid .span2 {
  grid-column: 1 / -1;
}
.ed-grid dt {
  font-size: 11px;
  color: var(--ce-text-faint);
  letter-spacing: 1px;
}
.ed-grid dd {
  margin: 0;
  font-size: 13px;
  color: var(--ce-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ed-grid dd.dim {
  color: var(--ce-text-faint);
}
.ed-link {
  color: var(--ce-accent);
  cursor: pointer;
}
.ed-link:hover {
  text-decoration: underline;
}
.ed-desc {
  margin: 0;
  padding: 8px 10px;
  font-size: 12.5px;
  line-height: 1.6;
  color: #c3d6f2;
  border-left: 2px solid var(--type-color);
  background: rgba(79, 195, 247, 0.05);
}
.ed-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}
.ed-metric {
  display: flex;
  flex-direction: column;
  padding: 6px 8px;
  border: 1px solid var(--ce-divider);
  border-radius: 3px;
  background: rgba(79, 195, 247, 0.04);
}
.ed-metric__v {
  font-size: 15px;
  font-weight: 700;
  color: var(--ce-text-strong);
}
.ed-metric__k {
  font-size: 11px;
  color: var(--ce-text-dim);
}
.ed-sub {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ce-text-dim);
  letter-spacing: 1px;
}
.ed-logs ol {
  margin: 0;
  padding: 0;
  list-style: none;
  border-left: 1px solid var(--ce-panel-border);
}
.ed-logs li {
  position: relative;
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 8px;
  padding: 3px 0 3px 12px;
  font-size: 12px;
}
.ed-logs li::before {
  content: '';
  position: absolute;
  left: -4px;
  top: 9px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ce-accent);
  box-shadow: 0 0 6px var(--ce-accent);
}
.ed-logs__t {
  color: var(--ce-text-faint);
}
.ed-logs__a {
  color: var(--ce-accent);
}
.ed-logs__n {
  color: var(--ce-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ed-dispatch {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 3px;
  background: rgba(79, 195, 247, 0.06);
}
.ed-dispatch.is-demo {
  animation: ed-glow 1s ease-in-out infinite alternate;
}
@keyframes ed-glow {
  from {
    box-shadow: 0 0 0 0 rgba(79, 195, 247, 0);
  }
  to {
    box-shadow: 0 0 18px 2px rgba(79, 195, 247, 0.45);
    border-color: var(--ce-accent);
  }
}
.ed-dispatch__btns {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
.ed-fold-enter-active,
.ed-fold-leave-active {
  transition: all 0.25s var(--ce-ease);
}
.ed-fold-enter-from,
.ed-fold-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.ed-actions {
  flex: none;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-top: 1px solid var(--ce-divider);
  background: rgba(3, 8, 18, 0.35);
}
.ed-actions__spacer {
  flex: 1;
}
.ed-btn {
  height: 28px;
  padding: 0 12px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 3px;
  background: rgba(79, 195, 247, 0.06);
  color: var(--ce-text);
  font-size: 12.5px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}
.ed-btn:hover:not(:disabled) {
  border-color: var(--ce-accent);
  color: #fff;
  background: rgba(79, 195, 247, 0.16);
}
.ed-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ed-btn--primary {
  border-color: transparent;
  background: linear-gradient(90deg, #1f8fe0, #36c8f0);
  color: #03111f;
  font-weight: 600;
  box-shadow: 0 0 14px rgba(79, 195, 247, 0.35);
}
.ed-btn--primary:hover:not(:disabled),
.ed-btn--primary.is-active {
  color: #03111f;
  background: linear-gradient(90deg, #36a6f0, #5fe0ff);
}
.ed-btn--ok {
  color: var(--ce-success);
  border-color: color-mix(in srgb, var(--ce-success) 50%, transparent);
  background: color-mix(in srgb, var(--ce-success) 10%, transparent);
}
.ed-btn--ghost {
  background: transparent;
  color: var(--ce-text-dim);
}
</style>

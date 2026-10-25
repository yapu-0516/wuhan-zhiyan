<script setup lang="ts">
// 事件详情抽屉：信息总览 / AI 描述 / 证据图 / 指标 / 处置流程时间线 / 状态流转与指派
// 数据以 useCityEvents 共享 store 为准（WebSocket 实时更新），store 中缺失时回退到 GET /api/events/{id}。
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Aim,
  ChatLineSquare,
  Close,
  CopyDocument,
  MagicStick,
  Picture as PictureIcon,
  Plus,
  Refresh,
  Switch,
  User
} from '@element-plus/icons-vue'
import type { Component } from 'vue'
import { getEvent, getEventLogs } from '@/api/event'
import { apiState } from '@/api/http'
import { fileUrl } from '@/config/api'
import { useCityEvents } from '@/composables/useCityEvents'
import { describeMetrics } from '@/composables/pages/metrics'
import { errMsg, fmtCoord, pct100 } from '@/composables/pages/format'
import type { CityEvent, EventLog, EventLogAction, EventPatch, EventStatus } from '@/types/event'
import {
  EVENT_STATUS_COLOR,
  EVENT_STATUS_LABEL,
  EVENT_TYPE_META,
  SEVERITY_META,
  SOURCE_META,
  STATUS_TRANSITIONS
} from '@/types/event'

const props = defineProps<{ modelValue: boolean; eventId: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const router = useRouter()
const store = useCityEvents()

// 关闭动画期间保留最近一次的 id，避免内容闪空
const currentId = ref('')
const fetched = ref<CityEvent | undefined>()
const fetching = ref(false)
const notFound = ref(false)
const logs = ref<EventLog[]>([])
const logsLoading = ref(false)

const event = computed<CityEvent | undefined>(() => store.getEventById(currentId.value) ?? fetched.value)
const meta = computed(() => (event.value ? EVENT_TYPE_META[event.value.event_type] : null))
const sev = computed(() => (event.value ? SEVERITY_META[event.value.severity] : null))
const source = computed(() => (event.value ? SOURCE_META[event.value.source] : null))
const metrics = computed(() => describeMetrics(event.value?.metrics))
const evidence = computed(() => fileUrl(event.value?.evidence_url))
const timelineLogs = computed(() => [...logs.value].reverse())

// ---------- 处置表单 ----------
const ASSIGNEES = [
  '江汉区消防救援大队',
  '江岸区消防救援大队',
  '武汉市公安局交通管理局江汉大队',
  '武汉市水务局排水中心',
  '江岸区住建局房屋安全鉴定站',
  '江汉区城管执法局',
  '江岸区城管执法局'
]
const form = reactive({ assignee: '', operator: '值班员', note: '' })
const submitting = ref<EventStatus | 'note' | null>(null)

const suggestion = computed(() => {
  const e = event.value
  if (!e) return ''
  const south = e.district?.includes('江岸')
  switch (e.event_type) {
    case 'fire':
      return south ? '江岸区消防救援大队' : '江汉区消防救援大队'
    case 'traffic':
      return '武汉市公安局交通管理局江汉大队'
    case 'flood':
      return '武汉市水务局排水中心'
    case 'building':
      return '江岸区住建局房屋安全鉴定站'
    default:
      return ''
  }
})

const transitions = computed<EventStatus[]>(() => (event.value ? STATUS_TRANSITIONS[event.value.status] : []))

function actionLabel(from: EventStatus, to: EventStatus): string {
  if (from === 'resolved' && to === 'processing') return '重新打开'
  return to === 'monitoring' ? '转入监测' : to === 'processing' ? '派单处置' : '办结'
}

// ---------- 日志时间线 ----------
const ACTION_META: Record<EventLogAction, { label: string; color: string; icon: Component }> = {
  created: { label: '事件创建', color: '#4fc3f7', icon: Plus },
  ai_detected: { label: 'AI 研判', color: '#4dd984', icon: MagicStick },
  status_changed: { label: '状态变更', color: '#f0c050', icon: Switch },
  assigned: { label: '指派处置单位', color: '#9b8fff', icon: User },
  comment: { label: '备注', color: '#8aa3c4', icon: ChatLineSquare }
}
function logMeta(l: EventLog) {
  const base = ACTION_META[l.action] ?? ACTION_META.comment
  return l.action === 'status_changed' && l.to_status ? { ...base, color: EVENT_STATUS_COLOR[l.to_status] } : base
}

// ---------- 加载 ----------
async function loadLogs() {
  const id = currentId.value
  if (!id) return
  logsLoading.value = true
  try {
    const list = await getEventLogs(id)
    if (id === currentId.value) logs.value = list
  } catch (e) {
    if (id === currentId.value) logs.value = []
    ElMessage.warning(errMsg(e, '处置日志加载失败'))
  } finally {
    logsLoading.value = false
  }
}

async function ensureEvent() {
  const id = currentId.value
  fetched.value = undefined
  notFound.value = false
  if (!id || store.getEventById(id)) return
  fetching.value = true
  try {
    const e = await getEvent(id)
    if (id !== currentId.value) return
    fetched.value = e
    notFound.value = !e
  } catch {
    if (id === currentId.value) notFound.value = true
  } finally {
    fetching.value = false
  }
}

function resetForm() {
  form.assignee = event.value?.assignee ?? ''
  form.note = ''
}

watch(
  () => [props.modelValue, props.eventId] as const,
  async ([open, id]) => {
    if (id) currentId.value = id
    if (!open || !currentId.value) return
    logs.value = []
    await ensureEvent()
    resetForm()
    void loadLogs()
  },
  { immediate: true }
)

// 他处（WebSocket）更新了该事件 → 刷新日志；指派被外部改变 → 同步下拉
watch(
  () => event.value?.updated_at,
  (now, prev) => {
    if (props.modelValue && prev !== undefined && now !== prev) {
      void loadLogs()
      if (!form.assignee || form.assignee === (store.getEventById(currentId.value)?.assignee ?? '')) {
        form.assignee = event.value?.assignee ?? form.assignee
      }
    }
  }
)

// ---------- 动作 ----------
async function submit(status?: EventStatus) {
  const e = event.value
  if (!e) return
  if (status === 'processing' && !form.assignee.trim() && !e.assignee) {
    ElMessage.warning('派单处置前请先选择处置单位')
    return
  }
  const patch: EventPatch = { operator: form.operator.trim() || '值班员' }
  if (status) patch.status = status
  const a = form.assignee.trim()
  if (a && a !== (e.assignee ?? '')) patch.assignee = a
  const note = form.note.trim()
  if (note) patch.note = note
  if (!patch.status && !patch.assignee && !patch.note) {
    ElMessage.info('请填写备注，或选择新的处置单位')
    return
  }
  submitting.value = status ?? 'note'
  try {
    const updated = await store.updateEvent(e.id, patch)
    ElMessage.success(status ? `${e.id} 已${actionLabel(e.status, status)}（${EVENT_STATUS_LABEL[updated.status]}）` : '已记录')
    form.note = ''
    form.assignee = updated.assignee ?? form.assignee
    await loadLogs()
  } catch (err) {
    ElMessage.error(errMsg(err, '处置失败'))
  } finally {
    submitting.value = null
  }
}

function locate() {
  if (!event.value) return
  void router.push({ path: '/dashboard', query: { eventId: event.value.id } })
}
function gotoBuilding(id: string) {
  void router.push({ path: '/dashboard', query: { buildingId: id } })
}
function gotoTask(id: string) {
  const type = event.value?.event_type ?? 'fire'
  void router.push({ path: `/ai-analysis/${type}`, query: { task: id } })
}
async function copyCoord() {
  if (!event.value) return
  try {
    await navigator.clipboard.writeText(fmtCoord(event.value.longitude, event.value.latitude, 6))
    ElMessage.success('坐标已复制')
  } catch {
    ElMessage.info(fmtCoord(event.value.longitude, event.value.latitude, 6))
  }
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    direction="rtl"
    size="min(600px, 100vw)"
    :with-header="false"
    modal-class="cp-overlay"
    append-to-body
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <div class="dr">
      <!-- 头部 -->
      <header v-if="event && meta && sev" class="dr__head" :style="{ '--tc': meta.color }">
        <div class="dr__headrow">
          <span class="dr__ring">{{ meta.icon }}</span>
          <div class="dr__titles">
            <h3 class="dr__name">{{ event.name }}</h3>
            <div class="dr__sub">
              <span class="cp-mono dr__id">{{ event.id }}</span>
              <span class="cp-pill cp-pill--sm" :style="{ '--c': meta.color }">{{ meta.label }}</span>
              <span class="cp-pill cp-pill--sm" :style="{ '--c': sev.color }">{{ sev.label }}</span>
              <span class="cp-pill cp-pill--sm" :style="{ '--c': EVENT_STATUS_COLOR[event.status] }">
                <i class="cp-dot" :class="{ 'cp-dot--pulse': event.status === 'pending' }"></i>{{ EVENT_STATUS_LABEL[event.status] }}
              </span>
            </div>
          </div>
          <button class="dr__close" type="button" aria-label="关闭" @click="emit('update:modelValue', false)">
            <el-icon><Close /></el-icon>
          </button>
        </div>
        <el-button class="dr__locate" type="primary" plain :icon="Aim" @click="locate">在三维场景中定位</el-button>
      </header>
      <header v-else class="dr__head">
        <div class="dr__headrow">
          <div class="dr__titles"><h3 class="dr__name">事件详情</h3></div>
          <button class="dr__close" type="button" aria-label="关闭" @click="emit('update:modelValue', false)">
            <el-icon><Close /></el-icon>
          </button>
        </div>
      </header>

      <!-- 正文 -->
      <div class="dr__body">
        <el-skeleton v-if="!event && fetching" animated :rows="9" />
        <el-empty v-else-if="!event" :image-size="90" :description="notFound ? `未找到事件 ${currentId}，可能已被删除` : '暂无数据'" />

        <template v-else>
          <section class="sec">
            <h4 class="sec__t">基本信息</h4>
            <dl class="grid">
              <div class="cell"><dt>事件编号</dt><dd class="cp-mono">{{ event.id }}</dd></div>
              <div class="cell">
                <dt>事件类型</dt>
                <dd>{{ meta?.icon }} {{ meta?.label }}</dd>
              </div>
              <div class="cell">
                <dt>发现来源</dt>
                <dd>{{ source?.icon }} {{ source?.label ?? event.source }}</dd>
              </div>
              <div class="cell">
                <dt>AI 置信度</dt>
                <dd>
                  <span class="conf">
                    <b>{{ pct100(event.confidence) }}%</b>
                    <span class="cp-bar"><i :style="{ width: `${pct100(event.confidence)}%` }"></i></span>
                  </span>
                </dd>
              </div>
              <div class="cell"><dt>所属区域</dt><dd>{{ event.district || '—' }}</dd></div>
              <div class="cell"><dt>管理网格</dt><dd class="cp-mono">{{ event.grid || '—' }}</dd></div>
              <div class="cell cell--wide"><dt>事件地址</dt><dd>{{ event.address || '—' }}</dd></div>
              <div class="cell cell--wide">
                <dt>地理坐标</dt>
                <dd class="coord">
                  <span class="cp-mono">{{ fmtCoord(event.longitude, event.latitude, 6) }}</span>
                  <button class="coord__copy" type="button" title="复制坐标" @click="copyCoord">
                    <el-icon><CopyDocument /></el-icon>
                  </button>
                </dd>
              </div>
              <div class="cell"><dt>发现时间</dt><dd class="cp-mono">{{ event.timestamp }}</dd></div>
              <div class="cell"><dt>最近更新</dt><dd class="cp-mono">{{ event.updated_at }}</dd></div>
              <div class="cell cell--wide">
                <dt>处置单位</dt>
                <dd>
                  <span v-if="event.assignee">{{ event.assignee }}</span>
                  <span v-else class="dim">尚未指派</span>
                </dd>
              </div>
              <div v-if="event.building_id" class="cell">
                <dt>关联建筑</dt>
                <dd><a class="cp-link cp-mono" @click="gotoBuilding(event.building_id)">{{ event.building_id }} ↗</a></dd>
              </div>
              <div v-if="event.road_id" class="cell"><dt>关联道路</dt><dd class="cp-mono">{{ event.road_id }}</dd></div>
              <div v-if="event.task_id" class="cell">
                <dt>关联 AI 任务</dt>
                <dd><a class="cp-link cp-mono" @click="gotoTask(event.task_id)">{{ event.task_id }} ↗</a></dd>
              </div>
            </dl>
          </section>

          <section v-if="event.description" class="sec">
            <h4 class="sec__t">{{ event.source === 'citizen' ? '上报描述' : 'AI 研判描述' }}</h4>
            <blockquote class="quote">{{ event.description }}</blockquote>
          </section>

          <section v-if="evidence" class="sec">
            <h4 class="sec__t">证据图像 <small>算法标注结果 · 点击放大</small></h4>
            <el-image
              class="evidence"
              :src="evidence"
              :preview-src-list="[evidence]"
              fit="cover"
              preview-teleported
              hide-on-click-modal
            >
              <template #error>
                <div class="evidence__err"><el-icon><PictureIcon /></el-icon>证据图加载失败</div>
              </template>
            </el-image>
          </section>

          <section v-if="metrics.length" class="sec">
            <h4 class="sec__t">算法指标</h4>
            <div class="metrics">
              <el-tooltip v-for="m in metrics" :key="m.key" :disabled="!m.hint" :content="m.hint" placement="top" popper-class="cp-popper">
                <div class="metric">
                  <span class="metric__l">{{ m.label }}</span>
                  <span class="metric__v">{{ m.value }}<small>{{ m.unit }}</small></span>
                </div>
              </el-tooltip>
            </div>
          </section>

          <section class="sec">
            <h4 class="sec__t">
              处置流程
              <el-button class="sec__refresh" link :icon="Refresh" :loading="logsLoading" @click="loadLogs">刷新</el-button>
            </h4>
            <el-skeleton v-if="logsLoading && !logs.length" animated :rows="4" />
            <el-empty v-else-if="!logs.length" :image-size="64" description="暂无处置记录" />
            <el-timeline v-else class="tl">
              <el-timeline-item
                v-for="l in timelineLogs"
                :key="l.id"
                :timestamp="l.timestamp"
                :color="logMeta(l).color"
                :icon="logMeta(l).icon"
                size="large"
                placement="top"
              >
                <div class="tl__item" :style="{ '--c': logMeta(l).color }">
                  <div class="tl__title">
                    <b>{{ logMeta(l).label }}</b>
                    <template v-if="l.action === 'status_changed' && l.to_status">
                      <span v-if="l.from_status" class="tl__chip" :style="{ '--c': EVENT_STATUS_COLOR[l.from_status] }">
                        {{ EVENT_STATUS_LABEL[l.from_status] }}
                      </span>
                      <span v-if="l.from_status" class="tl__arrow">→</span>
                      <span class="tl__chip" :style="{ '--c': EVENT_STATUS_COLOR[l.to_status] }">{{ EVENT_STATUS_LABEL[l.to_status] }}</span>
                    </template>
                    <span class="tl__op">{{ l.operator }}</span>
                  </div>
                  <p v-if="l.note" class="tl__note">{{ l.note }}</p>
                </div>
              </el-timeline-item>
            </el-timeline>
          </section>
        </template>
      </div>

      <!-- 处置操作 -->
      <footer v-if="event" class="dr__foot">
        <div class="ops__row">
          <label class="ops__f ops__f--grow">
            <span class="cp-label">处置单位</span>
            <el-select
              v-model="form.assignee"
              filterable
              allow-create
              default-first-option
              clearable
              placeholder="选择或输入处置单位"
              popper-class="cp-popper"
              size="default"
            >
              <el-option v-for="a in ASSIGNEES" :key="a" :value="a" :label="a" />
            </el-select>
          </label>
          <label class="ops__f">
            <span class="cp-label">操作人</span>
            <el-input v-model="form.operator" maxlength="20" placeholder="值班员" />
          </label>
        </div>
        <div v-if="suggestion && !form.assignee && event.status !== 'resolved'" class="ops__suggest">
          推荐单位：{{ suggestion }}
          <a class="cp-link" @click="form.assignee = suggestion">采用</a>
        </div>
        <el-input v-model="form.note" type="textarea" :rows="2" maxlength="200" resize="none" placeholder="处置备注（选填，将写入处置日志）" />
        <div class="ops__btns">
          <button
            v-for="t in transitions"
            :key="t"
            type="button"
            class="act"
            :class="{ 'act--solid': t === 'processing' || (t === 'resolved' && transitions.length === 1) }"
            :style="{ '--c': EVENT_STATUS_COLOR[t] }"
            :disabled="submitting !== null"
            @click="submit(t)"
          >
            <span v-if="submitting === t" class="act__spin"></span>
            {{ actionLabel(event.status, t) }}
          </button>
          <button type="button" class="act act--ghost" :disabled="submitting !== null" @click="submit()">
            <span v-if="submitting === 'note'" class="act__spin"></span>仅记录备注/指派
          </button>
        </div>
        <p v-if="apiState.mode !== 'live'" class="ops__offline">离线演示：处置仅在当前页面本地生效，不写入处置日志。</p>
      </footer>
    </div>
  </el-drawer>
</template>

<style scoped>
.dr {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.dr__head {
  --tc: #4fc3f7;
  flex: none;
  padding: 18px 20px 14px;
  background:
    radial-gradient(420px 120px at 0% 0%, color-mix(in srgb, var(--tc) 22%, transparent), transparent 70%),
    linear-gradient(180deg, rgba(79, 195, 247, 0.06), transparent);
  border-bottom: 1px solid var(--ce-panel-border, rgba(64, 120, 180, 0.28));
}
.dr__headrow {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.dr__ring {
  flex: none;
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  font-size: 24px;
  border-radius: 14px;
  background: color-mix(in srgb, var(--tc) 16%, rgba(9, 16, 34, 0.8));
  border: 1px solid color-mix(in srgb, var(--tc) 55%, transparent);
  box-shadow: 0 0 20px color-mix(in srgb, var(--tc) 35%, transparent);
}
.dr__titles {
  flex: 1;
  min-width: 0;
}
.dr__name {
  margin: 0 0 8px;
  font-size: 17px;
  line-height: 1.35;
  font-weight: 600;
  color: #f0f6ff;
}
.dr__sub {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.dr__id {
  font-size: 12.5px;
  color: #9fc4ea;
  padding-right: 2px;
}
.dr__close {
  flex: none;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--ce-text-dim, #8aa3c4);
  cursor: pointer;
  transition: all 0.15s;
}
.dr__close:hover {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.06);
}
.dr__locate {
  margin-top: 14px;
  width: 100%;
}
.dr__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  padding: 6px 20px 16px;
}
.sec {
  padding: 14px 0 6px;
}
.sec + .sec {
  border-top: 1px dashed rgba(64, 120, 180, 0.2);
}
.sec__t {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #8fb0d3;
}
.sec__t::before {
  content: '';
  width: 3px;
  height: 12px;
  border-radius: 2px;
  background: var(--ce-accent, #4fc3f7);
  box-shadow: 0 0 8px var(--ce-accent, #4fc3f7);
}
.sec__t small {
  font-weight: 400;
  letter-spacing: 0.5px;
  color: #5d748f;
}
.sec__refresh {
  margin-left: auto;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  margin: 0;
  background: rgba(64, 120, 180, 0.14);
  border: 1px solid rgba(64, 120, 180, 0.2);
  border-radius: 8px;
  overflow: hidden;
}
.cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 9px 12px;
  background: #0c1630;
  min-width: 0;
}
.cell--wide {
  grid-column: 1 / -1;
}
.cell dt {
  font-size: 11px;
  letter-spacing: 1px;
  color: #6f89aa;
}
.cell dd {
  margin: 0;
  font-size: 13px;
  color: #dbe8ff;
  word-break: break-all;
}
.dim {
  color: #5d748f;
}
.conf {
  display: flex;
  align-items: center;
  gap: 10px;
}
.conf b {
  color: var(--ce-accent, #4fc3f7);
  font-weight: 600;
}
.conf .cp-bar {
  flex: 1;
}
.coord {
  display: flex;
  align-items: center;
  gap: 8px;
}
.coord__copy {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--ce-text-dim, #8aa3c4);
  cursor: pointer;
}
.coord__copy:hover {
  color: var(--ce-accent, #4fc3f7);
  border-color: rgba(79, 195, 247, 0.4);
}
.quote {
  margin: 0;
  padding: 11px 14px;
  font-size: 13.5px;
  line-height: 1.75;
  color: #cfe0fa;
  background: linear-gradient(90deg, rgba(79, 195, 247, 0.1), rgba(79, 195, 247, 0.02));
  border-left: 3px solid var(--ce-accent, #4fc3f7);
  border-radius: 0 8px 8px 0;
}
.evidence {
  width: 100%;
  height: 230px;
  border-radius: 8px;
  border: 1px solid var(--ce-panel-border, rgba(64, 120, 180, 0.28));
  overflow: hidden;
  background: #060b1a;
}
.evidence__err {
  display: flex;
  height: 100%;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #5d748f;
  font-size: 13px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}
.metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(79, 195, 247, 0.06);
  border: 1px solid rgba(64, 120, 180, 0.22);
}
.metric__l {
  font-size: 11.5px;
  color: #8aa3c4;
}
.metric__v {
  font-size: 19px;
  font-weight: 600;
  color: #e8f3ff;
  font-variant-numeric: tabular-nums;
}
.metric__v small {
  margin-left: 3px;
  font-size: 11px;
  font-weight: 400;
  color: #8aa3c4;
}
.tl {
  padding-left: 4px;
  margin-top: 4px;
}
.tl :deep(.el-timeline-item__timestamp) {
  font-size: 11.5px;
  color: #6f89aa;
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.tl :deep(.el-timeline-item__node--large) {
  width: 22px;
  height: 22px;
  left: -6px;
}
.tl :deep(.el-timeline-item__icon) {
  color: #06101f;
  font-size: 13px;
}
.tl__item {
  --c: #4fc3f7;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(79, 195, 247, 0.045);
  border: 1px solid rgba(64, 120, 180, 0.18);
  border-left: 3px solid var(--c);
}
.tl__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #dbe8ff;
}
.tl__chip {
  --c: #4fc3f7;
  padding: 0 7px;
  line-height: 18px;
  font-size: 11.5px;
  border-radius: 4px;
  color: var(--c);
  background: color-mix(in srgb, var(--c) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--c) 40%, transparent);
}
.tl__arrow {
  color: #5d748f;
}
.tl__op {
  margin-left: auto;
  font-size: 12px;
  color: #8aa3c4;
}
.tl__note {
  margin: 6px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #a9bdd9;
}
.dr__foot {
  flex: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 20px 16px;
  background: linear-gradient(0deg, #0a1226, #0d1730);
  border-top: 1px solid var(--ce-panel-border, rgba(64, 120, 180, 0.28));
  box-shadow: 0 -10px 24px rgba(0, 0, 0, 0.3);
}
.ops__row {
  display: flex;
  gap: 12px;
}
.ops__f {
  display: flex;
  flex-direction: column;
  gap: 5px;
  width: 130px;
}
.ops__f--grow {
  flex: 1;
  width: auto;
  min-width: 0;
}
.ops__suggest {
  margin-top: -4px;
  font-size: 12px;
  color: #8aa3c4;
}
.ops__suggest .cp-link {
  margin-left: 6px;
}
.ops__btns {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.act {
  --c: #4fc3f7;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  padding: 0 16px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  color: var(--c);
  background: color-mix(in srgb, var(--c) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--c) 55%, transparent);
  transition: all 0.16s;
}
.act:hover:not(:disabled) {
  background: color-mix(in srgb, var(--c) 24%, transparent);
  box-shadow: 0 0 16px color-mix(in srgb, var(--c) 35%, transparent);
}
.act--solid {
  color: #06101f;
  background: var(--c);
  border-color: var(--c);
}
.act--solid:hover:not(:disabled) {
  background: color-mix(in srgb, var(--c) 82%, #fff);
}
.act--ghost {
  --c: #8aa3c4;
  margin-left: auto;
  font-weight: 500;
  background: transparent;
  border-color: rgba(138, 163, 196, 0.35);
}
.act:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.act__spin {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: act-spin 0.7s linear infinite;
}
@keyframes act-spin {
  to {
    transform: rotate(360deg);
  }
}
.ops__offline {
  margin: 0;
  font-size: 12px;
  color: #d9b45a;
}
</style>

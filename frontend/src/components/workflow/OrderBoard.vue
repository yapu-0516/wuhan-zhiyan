<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, type UploadUserFile } from 'element-plus'
import { Location, Plus, UploadFilled } from '@element-plus/icons-vue'
import {
  assessWorkOrderFeedback,
  createWorkOrder,
  patchWorkOrder,
  useWorkOrderResource,
  uploadWorkOrderFeedback
} from '@/api/workflow'
import { getEmergencyResources } from '@/api/support'
import { fileUrl } from '@/config/api'
import { useOperator } from '@/composables/useOperator'
import type { Assessment, WorkOrder, WorkOrderCreate, WorkOrderSla, WorkOrderStatus } from '@/types/workflow'
import { ORDER_STATUS_META, ORDER_TRANSITIONS } from '@/types/workflow'
import type { CityEvent } from '@/types/event'
import { SEVERITY_META } from '@/types/event'
import type { EmergencyResource } from '@/types/support'

const props = defineProps<{ events: CityEvent[]; assessments: Assessment[]; orders: WorkOrder[] }>()
const emit = defineEmits<{ (e: 'refresh'): void }>()
const { currentName, load: loadOperator } = useOperator()
onMounted(() => void loadOperator())

const filter = ref<'all' | WorkOrderStatus>('all')
const selectedId = ref('')
const createVisible = ref(false)
const feedbackVisible = ref(false)
const transferVisible = ref(false)
const resourceVisible = ref(false)
const followVisible = ref(false)
const submitting = ref(false)
const feedbackBusy = ref(false)
const busy = ref(false)
const feedbackNote = ref('')
const feedbackOperator = ref('现场处置人员')
const feedbackLongitude = ref<number | null>(null)
const feedbackLatitude = ref<number | null>(null)
const feedbackFiles = ref<UploadUserFile[]>([])
const transferTarget = ref('')
const transferNote = ref('')
const resourceForm = reactive({
  resource_id: '',
  quantity: 1,
  note: ''
})
const availableResources = ref<EmergencyResource[]>([])
const followForm = reactive({
  kind: 'reinspection' as 'reinspection' | 'refly',
  note: ''
})
const form = reactive<WorkOrderCreate>({
  event_id: '',
  assessment_id: null,
  title: '',
  unit: '',
  assignee: '',
  priority: 'medium',
  description: ''
})
const filtered = computed(() =>
  props.orders.filter((item) => filter.value === 'all' || item.status === filter.value)
)
const selected = computed(() => props.orders.find((item) => item.id === selectedId.value) ?? filtered.value[0] ?? null)
const relatedEvent = computed(() => props.events.find((item) => item.id === selected.value?.event_id) ?? null)
const availableAssessments = computed(() => props.assessments.filter((item) => item.event_id === form.event_id))
const sla = computed(() => selected.value?.sla ?? null)
const fieldFeedbackCount = computed(
  () => (selected.value?.feedback ?? []).filter((item) => item.action === 'field_feedback').length
)

type FeedbackAttachment = { name: string; url: string }
type FeedbackItem = {
  at?: string
  operator?: string
  action?: string
  to?: WorkOrderStatus
  note?: string
  location?: { longitude: number; latitude: number }
  attachments?: FeedbackAttachment[]
}
const feedbackItems = computed(() => (selected.value?.feedback ?? []) as FeedbackItem[])

watch(
  () => filtered.value,
  (list) => {
    if (!selectedId.value || !props.orders.some((item) => item.id === selectedId.value)) selectedId.value = list[0]?.id ?? ''
  },
  { immediate: true }
)

const filters = [
  { value: 'all' as const, label: '全部', count: computed(() => props.orders.length) },
  ...(['pending', 'accepted', 'in_progress', 'completed', 'verified', 'rejected'] as WorkOrderStatus[]).map((status) => ({
    value: status,
    label: ORDER_STATUS_META[status].label,
    count: computed(() => props.orders.filter((item) => item.status === status).length)
  }))
]

function openCreate() {
  const event = props.events.find((item) => item.status !== 'resolved') ?? props.events[0]
  form.event_id = event?.id ?? ''
  form.assessment_id = props.assessments.find((item) => item.event_id === form.event_id)?.id ?? null
  form.title = ''
  form.unit = ''
  form.assignee = ''
  form.priority = event?.severity ?? 'medium'
  form.description = ''
  createVisible.value = true
}

async function submit() {
  if (!form.event_id || !form.title.trim()) {
    ElMessage.warning('请选择事件并填写工单标题')
    return
  }
  submitting.value = true
  try {
    const row = await createWorkOrder({ ...form, title: form.title.trim() })
    selectedId.value = row.id
    createVisible.value = false
    emit('refresh')
    ElMessage.success(`工单 ${row.id} 已创建`)
  } catch (error) {
    ElMessage.error((error as Error).message || '工单创建失败')
  } finally {
    submitting.value = false
  }
}

async function advance(status: WorkOrderStatus) {
  if (!selected.value || busy.value) return
  busy.value = true
  try {
    await patchWorkOrder(selected.value.id, {
      status,
      operator: currentName.value,
      note: `工单状态更新为${ORDER_STATUS_META[status].label}`
    })
    emit('refresh')
    ElMessage.success(`工单已更新为${ORDER_STATUS_META[status].label}`)
  } catch (error) {
    ElMessage.error((error as Error).message || '工单更新失败')
  } finally {
    busy.value = false
  }
}

function openTransfer() {
  if (!selected.value) return
  transferTarget.value = selected.value.assignee || selected.value.unit
  transferNote.value = ''
  transferVisible.value = true
}

async function submitTransfer() {
  if (!selected.value || !transferTarget.value.trim() || busy.value) return
  busy.value = true
  try {
    await patchWorkOrder(selected.value.id, {
      assignee: transferTarget.value.trim(),
      operator: currentName.value,
      note: `工单转派至 ${transferTarget.value.trim()}${transferNote.value.trim() ? `：${transferNote.value.trim()}` : ''}`
    })
    transferVisible.value = false
    emit('refresh')
    ElMessage.success('工单已转派')
  } catch (error) {
    ElMessage.error((error as Error).message || '工单转派失败')
  } finally {
    busy.value = false
  }
}

async function openResource() {
  resourceForm.resource_id = ''
  resourceForm.quantity = 1
  resourceForm.note = ''
  if (!availableResources.value.length) {
    try {
      availableResources.value = (await getEmergencyResources()).filter((item) => item.status !== 'unavailable' && item.available > 0)
    } catch {
      availableResources.value = []
    }
  }
  resourceForm.resource_id = availableResources.value[0]?.id ?? ''
  resourceVisible.value = true
}

async function submitResource() {
  if (!selected.value || !resourceForm.resource_id || busy.value) return
  busy.value = true
  try {
    await useWorkOrderResource(selected.value.id, {
      resource_id: resourceForm.resource_id,
      quantity: resourceForm.quantity,
      note: resourceForm.note,
      operator: currentName.value,
    })
    availableResources.value = availableResources.value
      .map((item) =>
        item.id === resourceForm.resource_id
          ? { ...item, available: Math.max(0, item.available - resourceForm.quantity) }
          : item
      )
      .filter((item) => item.available > 0)
    resourceVisible.value = false
    emit('refresh')
    ElMessage.success('资源使用记录已保存')
  } catch (error) {
    ElMessage.error((error as Error).message || '资源记录保存失败')
  } finally {
    busy.value = false
  }
}

function openFollowUp() {
  followForm.kind = relatedEvent.value?.event_type === 'building' ? 'reinspection' : 'refly'
  followForm.note = ''
  followVisible.value = true
}

async function submitFollowUp() {
  if (!selected.value || busy.value) return
  const kindLabel = followForm.kind === 'reinspection' ? '复测' : '复飞'
  busy.value = true
  try {
    await createWorkOrder({
      event_id: selected.value.event_id,
      assessment_id: selected.value.assessment_id,
      scenario_run_id: selected.value.scenario_run_id,
      title: `${kindLabel}申请 · ${selected.value.title}`,
      unit: selected.value.unit,
      assignee: selected.value.assignee,
      priority: selected.value.priority,
      description: followForm.note.trim() || `对工单 ${selected.value.id} 申请${kindLabel}复核。`
    })
    followVisible.value = false
    emit('refresh')
    ElMessage.success(`${kindLabel}工单已创建`)
  } catch (error) {
    ElMessage.error((error as Error).message || `${kindLabel}申请失败`)
  } finally {
    busy.value = false
  }
}

function openFeedback() {
  if (!selected.value) return
  feedbackNote.value = ''
  feedbackOperator.value = currentName.value || selected.value.assignee || '现场处置人员'
  feedbackLongitude.value = relatedEvent.value?.longitude ?? null
  feedbackLatitude.value = relatedEvent.value?.latitude ?? null
  feedbackFiles.value = []
  feedbackVisible.value = true
}

async function submitFeedback() {
  if (!selected.value || feedbackBusy.value) return
  const files = feedbackFiles.value.flatMap((item) => (item.raw ? [item.raw] : []))
  if (!feedbackNote.value.trim() && !files.length) {
    ElMessage.warning('请填写现场情况或至少上传一张照片')
    return
  }
  feedbackBusy.value = true
  try {
    await uploadWorkOrderFeedback(selected.value.id, {
      note: feedbackNote.value.trim(),
      longitude: feedbackLongitude.value,
      latitude: feedbackLatitude.value,
      operator: feedbackOperator.value.trim() || currentName.value || '现场处置人员',
      files
    })
    feedbackVisible.value = false
    emit('refresh')
    ElMessage.success('现场反馈已记录')
  } catch (error) {
    ElMessage.error((error as Error).message || '现场反馈提交失败')
  } finally {
    feedbackBusy.value = false
  }
}

async function toAssessment(index: number, item: FeedbackItem) {
  if (!selected.value || busy.value) return
  busy.value = true
  try {
    const row = await assessWorkOrderFeedback(
      selected.value.id,
      index,
      currentName.value || item.operator || '现场处置人员',
      item.note || ''
    )
    ElMessage.success(`已转入研判 ${row.id}`)
  } catch (error) {
    ElMessage.error((error as Error).message || '现场反馈转研判失败')
  } finally {
    busy.value = false
  }
}

function minutesText(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : `${value} 分钟`
}

function deadlineFor(value: WorkOrderSla | null | undefined): string {
  if (!value || (value.remaining_min === null && !value.overdue)) return '未设置时限'
  if (value.overdue) return `已超时 ${Math.abs(value.remaining_min ?? 0)} 分钟`
  return `剩余 ${value.remaining_min ?? 0} 分钟`
}

function deadlineText(): string {
  return deadlineFor(sla.value)
}

function feedbackAttachments(item: FeedbackItem): FeedbackAttachment[] {
  return item.attachments ?? []
}
</script>

<template>
  <div class="orders-layout">
    <section class="cp-panel">
      <div class="cp-panel__header">
        <div class="filter-row">
          <button
            v-for="item in filters"
            :key="item.value"
            type="button"
            :class="{ on: filter === item.value }"
            @click="filter = item.value"
          >
            {{ item.label }} <span>{{ item.count.value }}</span>
          </button>
        </div>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建工单</el-button>
      </div>
      <el-table
        :data="filtered"
        row-key="id"
        highlight-current-row
        :current-row-key="selected?.id"
        @current-change="(row: WorkOrder | null) => (selectedId = row?.id ?? '')"
      >
        <template #empty><el-empty :image-size="72" description="当前筛选下暂无工单" /></template>
        <el-table-column label="工单" min-width="250">
          <template #default="{ row }">
            <div class="order-name">
              <b>{{ (row as WorkOrder).title }}</b>
              <span>{{ (row as WorkOrder).id }} · {{ (row as WorkOrder).event_id }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="104">
          <template #default="{ row }">
            <span :style="{ color: SEVERITY_META[(row as WorkOrder).priority].color }">
              {{ SEVERITY_META[(row as WorkOrder).priority].label }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="执行单位" prop="unit" min-width="170" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="order-status" :style="{ '--c': ORDER_STATUS_META[(row as WorkOrder).status].color }">
              {{ ORDER_STATUS_META[(row as WorkOrder).status].label }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="时限" width="118">
          <template #default="{ row }">
            <span :class="{ 'deadline-overdue': (row as WorkOrder).sla?.overdue }">
              {{ deadlineFor((row as WorkOrder).sla) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" prop="updated_at" width="158" />
      </el-table>
    </section>

    <aside class="cp-panel detail">
      <template v-if="selected">
        <div class="cp-panel__header">
          <div>
            <h3 class="cp-panel__title">{{ selected.title }}</h3>
            <span class="sub">{{ selected.id }} · {{ relatedEvent?.name || selected.event_id }}</span>
          </div>
          <span class="order-status" :style="{ '--c': ORDER_STATUS_META[selected.status].color }">
            {{ ORDER_STATUS_META[selected.status].label }}
          </span>
        </div>
        <div class="cp-panel__body detail-body">
          <div class="hint">{{ ORDER_STATUS_META[selected.status].hint }}</div>
          <section class="sla-board" :class="{ overdue: sla?.overdue }" aria-label="工单时限指标">
            <div>
              <span>办理时限</span>
              <strong>{{ deadlineText() }}</strong>
            </div>
            <div>
              <span>已用时间</span>
              <strong>{{ minutesText(sla?.elapsed_min) }}</strong>
            </div>
            <div>
              <span>接单响应</span>
              <strong>{{ minutesText(sla?.response_min) }}</strong>
            </div>
            <div>
              <span>现场反馈</span>
              <strong>{{ fieldFeedbackCount }} 次</strong>
            </div>
          </section>
          <dl>
            <div><dt>责任单位</dt><dd>{{ selected.unit || '未指定' }}</dd></div>
            <div><dt>执行人员</dt><dd>{{ selected.assignee || '待接单' }}</dd></div>
            <div><dt>关联研判</dt><dd>{{ selected.assessment_id || '—' }}</dd></div>
            <div><dt>方案来源</dt><dd>{{ selected.scenario_run_id || '—' }}</dd></div>
          </dl>
          <p class="description">{{ selected.description || '暂无处置说明' }}</p>
          <section>
            <h4>执行反馈 <span>{{ selected.feedback.length }}</span></h4>
            <el-empty v-if="!selected.feedback.length" :image-size="48" description="暂无现场反馈" />
            <div v-for="(item, index) in feedbackItems" :key="index" class="feedback">
              <time>{{ item.at }}</time>
              <p>{{ item.note || ORDER_STATUS_META[item.to || selected.status]?.label }}</p>
              <small>{{ item.operator }}</small>
              <el-button
                v-if="item.action === 'field_feedback'"
                link
                type="primary"
                @click="toAssessment(index, item)"
                >转入研判</el-button
              >
              <div v-if="item.location" class="feedback__location">
                <el-icon><Location /></el-icon>
                {{ item.location.longitude.toFixed(5) }}, {{ item.location.latitude.toFixed(5) }}
              </div>
              <div v-if="feedbackAttachments(item).length" class="feedback__photos">
                <el-image
                  v-for="photo in feedbackAttachments(item)"
                  :key="photo.url"
                  :src="fileUrl(photo.url)"
                  :preview-src-list="feedbackAttachments(item).map((entry) => fileUrl(entry.url))"
                  fit="cover"
                  preview-teleported
                />
              </div>
            </div>
          </section>
        </div>
        <footer class="actions">
          <el-button
            :disabled="selected.status === 'verified' || selected.status === 'cancelled'"
            @click="openTransfer"
            >转派</el-button
          >
          <el-button
            :disabled="selected.status === 'verified' || selected.status === 'cancelled'"
            @click="openResource"
            >资源记录</el-button
          >
          <el-button @click="openFollowUp">复测 / 复飞</el-button>
          <el-button
            :icon="UploadFilled"
            :disabled="selected.status === 'verified' || selected.status === 'cancelled'"
            @click="openFeedback"
            >现场反馈</el-button
          >
          <el-button
            v-for="status in ORDER_TRANSITIONS[selected.status]"
            :key="status"
            :type="status === 'verified' ? 'primary' : 'default'"
            :loading="busy"
            @click="advance(status)"
            >{{ ORDER_STATUS_META[status].label }}</el-button
          >
        </footer>
      </template>
      <el-empty v-else description="选择一张工单查看执行情况" />
    </aside>
  </div>

  <el-dialog v-model="createVisible" title="新建处置工单" width="min(600px, 94vw)" append-to-body>
    <el-form label-position="top">
      <div class="form-grid">
        <el-form-item label="关联事件" required>
          <el-select v-model="form.event_id" filterable @change="form.assessment_id = availableAssessments[0]?.id ?? null">
            <el-option
              v-for="event in events"
              :key="event.id"
              :value="event.id"
              :label="`${event.id} ${event.name}`"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="依据研判">
          <el-select v-model="form.assessment_id" clearable>
            <el-option
              v-for="item in availableAssessments"
              :key="item.id"
              :value="item.id"
              :label="`${item.id} ${item.decision}`"
            />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item label="工单标题" required>
        <el-input v-model.trim="form.title" maxlength="128" placeholder="例如：积水抽排与道路管控" />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="执行单位">
          <el-input v-model.trim="form.unit" placeholder="例如：武汉市水务局排水中心" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority">
            <el-option v-for="(meta, key) in SEVERITY_META" :key="key" :value="key" :label="meta.label" />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item label="工作说明">
        <el-input v-model="form.description" type="textarea" :rows="3" maxlength="4000" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">创建工单</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="feedbackVisible" title="提交现场反馈" width="min(620px, 94vw)" append-to-body>
    <el-form label-position="top">
      <el-form-item label="现场情况" required>
        <el-input
          v-model="feedbackNote"
          type="textarea"
          :rows="3"
          maxlength="2000"
          show-word-limit
          placeholder="记录现场状态、处置进度、遗留问题或需要复核的事项"
        />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="反馈人员">
          <el-input v-model="feedbackOperator" maxlength="64" />
        </el-form-item>
        <el-form-item label="现场位置（可选）">
          <div class="coordinate-row">
            <el-input-number
              v-model="feedbackLongitude"
              :precision="6"
              :min="-180"
              :max="180"
              :controls="false"
              placeholder="经度"
            />
            <el-input-number
              v-model="feedbackLatitude"
              :precision="6"
              :min="-90"
              :max="90"
              :controls="false"
              placeholder="纬度"
            />
          </div>
        </el-form-item>
      </div>
      <el-form-item label="现场照片（最多 5 张）">
        <el-upload
          v-model:file-list="feedbackFiles"
          class="feedback-upload"
          accept=".jpg,.jpeg,.png,.webp"
          list-type="picture-card"
          :auto-upload="false"
          :limit="5"
          multiple
        >
          <el-icon><UploadFilled /></el-icon>
        </el-upload>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="feedbackVisible = false">取消</el-button>
      <el-button type="primary" :loading="feedbackBusy" @click="submitFeedback">提交反馈</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="transferVisible" title="转派工单" width="min(520px, 94vw)" append-to-body>
    <el-form label-position="top">
      <el-form-item label="接单单位或人员" required>
        <el-input v-model="transferTarget" maxlength="64" />
      </el-form-item>
      <el-form-item label="转派说明">
        <el-input v-model="transferNote" type="textarea" :rows="3" maxlength="2000" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="transferVisible = false">取消</el-button>
      <el-button type="primary" :loading="busy" @click="submitTransfer">确认转派</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="resourceVisible" title="资源使用记录" width="min(520px, 94vw)" append-to-body>
    <el-form label-position="top">
      <el-form-item label="选择可调度资源" required>
        <el-select v-model="resourceForm.resource_id" filterable style="width: 100%" placeholder="从应急资源库存选择">
          <el-option
            v-for="resource in availableResources"
            :key="resource.id"
            :value="resource.id"
            :label="`${resource.name} · ${resource.capability} · 可用 ${resource.available}`"
          />
        </el-select>
        <p v-if="!availableResources.length" class="resource-empty">当前没有可用资源，请先在数据资源中维护资源状态。</p>
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="数量">
          <el-input-number v-model="resourceForm.quantity" :min="1" :max="999" />
        </el-form-item>
        <el-form-item label="库存校验">
          <span class="resource-hint">
            {{ availableResources.find((item) => item.id === resourceForm.resource_id)?.available ?? 0 }} 可用
          </span>
        </el-form-item>
      </div>
      <el-form-item label="使用说明">
        <el-input v-model="resourceForm.note" type="textarea" :rows="3" maxlength="2000" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="resourceVisible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="busy"
        :disabled="!resourceForm.resource_id"
        @click="submitResource"
        >登记使用</el-button
      >
    </template>
  </el-dialog>

  <el-dialog v-model="followVisible" title="申请复测或复飞" width="min(520px, 94vw)" append-to-body>
    <el-form label-position="top">
      <el-form-item label="申请类型">
        <el-select v-model="followForm.kind">
          <el-option value="reinspection" label="现场复测" />
          <el-option value="refly" label="无人机复飞" />
        </el-select>
      </el-form-item>
      <el-form-item label="申请说明">
        <el-input
          v-model="followForm.note"
          type="textarea"
          :rows="3"
          maxlength="2000"
          placeholder="说明需要复测或复飞核查的范围与原因"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="followVisible = false">取消</el-button>
      <el-button type="primary" :loading="busy" @click="submitFollowUp">创建申请工单</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.orders-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) 380px;
  gap: 14px;
  min-height: 560px;
}
.cp-panel {
  min-width: 0;
}
.filter-row {
  display: flex;
  gap: 4px;
  overflow-x: auto;
}
.filter-row button {
  height: 26px;
  padding: 0 8px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--ce-text-dim);
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
}
.filter-row button.on {
  border-bottom-color: var(--ce-accent);
  color: var(--ce-text-strong);
}
.filter-row span {
  margin-left: 4px;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.order-name b,
.order-name span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.order-name b {
  color: var(--ce-text-strong);
  font-size: 13px;
}
.order-name span,
.sub {
  margin-top: 2px;
  color: var(--ce-text-faint);
  font-size: 11.5px;
}
.order-status {
  --c: var(--ce-text-faint);
  color: var(--c);
  font-size: 12px;
  white-space: nowrap;
}
.deadline-overdue {
  color: var(--ce-danger);
  font-size: 12px;
}
.detail {
  min-height: 520px;
}
.detail-body {
  overflow-y: auto;
}
.hint {
  padding: 8px 10px;
  border-left: 2px solid var(--ce-accent);
  color: var(--ce-text-dim);
  background: rgba(103, 198, 223, 0.06);
  font-size: 12px;
}
.sla-board {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 10px;
  border: 1px solid var(--ce-divider);
}
.sla-board > div {
  min-width: 0;
  padding: 9px 10px;
}
.sla-board > div + div {
  border-left: 1px solid var(--ce-divider);
}
.sla-board span,
.sla-board strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sla-board span {
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.sla-board strong {
  margin-top: 3px;
  color: var(--ce-text-strong);
  font-size: 12px;
}
.sla-board.overdue {
  border-color: rgba(228, 119, 123, 0.55);
}
.sla-board.overdue strong {
  color: var(--ce-danger);
}
.detail dl {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 14px 0;
}
.detail dt {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.detail dd {
  margin: 2px 0 0;
  color: var(--ce-text);
  font-size: 12.5px;
}
.description {
  padding: 10px 0;
  border-top: 1px solid var(--ce-divider);
  border-bottom: 1px solid var(--ce-divider);
  line-height: 1.7;
}
.detail h4,
.detail h4 span {
  margin: 0 0 8px;
  color: var(--ce-text-strong);
  font-size: 13px;
}
.detail h4 span {
  color: var(--ce-text-faint);
  font-weight: 400;
}
.feedback {
  padding: 8px 0;
  border-top: 1px solid var(--ce-divider);
}
.feedback time,
.feedback small {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.feedback p {
  margin: 3px 0;
}
.feedback__location {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 5px;
  color: var(--ce-text-faint);
  font: 11px var(--ce-font-num);
}
.feedback__photos {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 7px;
}
.feedback__photos :deep(.el-image) {
  width: 64px;
  height: 48px;
  border: 1px solid var(--ce-divider);
  border-radius: 3px;
}
.coordinate-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  width: 100%;
}
.coordinate-row :deep(.el-input-number) {
  width: 100%;
}
.resource-empty {
  margin: 6px 0 0;
  color: var(--ce-warning);
  font-size: 11px;
}
.resource-hint {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  color: var(--ce-accent);
  font-size: 12px;
}
.feedback-upload {
  width: 100%;
}
.feedback-upload :deep(.el-upload--picture-card),
.feedback-upload :deep(.el-upload-list__item) {
  width: 82px;
  height: 62px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
  padding: 10px 14px;
  border-top: 1px solid var(--ce-divider);
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}
@media (max-width: 1100px) {
  .orders-layout {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 700px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .sla-board {
    grid-template-columns: 1fr 1fr;
  }
  .sla-board > div:nth-child(3) {
    border-left: 0;
    border-top: 1px solid var(--ce-divider);
  }
  .sla-board > div:nth-child(4) {
    border-top: 1px solid var(--ce-divider);
  }
}
</style>

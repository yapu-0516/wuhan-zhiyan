<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Download, Plus, Promotion } from '@element-plus/icons-vue'
import {
  applyReviewToTemplate,
  createReview,
  getReviewCases,
  getReviewDraft,
  getTaskTemplates,
  reviewExportUrl,
  updateReview
} from '@/api/workflow'
import { getDrillRuns } from '@/api/drills'
import type {
  MonitoringTask,
  MonitoringTaskTemplate,
  ReviewCreate,
  ReviewDraft,
  ReviewEntityType,
  ReviewRecord,
  ReviewStatus
} from '@/types/workflow'
import type { DrillRun } from '@/types/workflow'
import type { CityEvent } from '@/types/event'

const props = defineProps<{ reviews: ReviewRecord[]; events: CityEvent[]; tasks: MonitoringTask[] }>()
const emit = defineEmits<{ (e: 'refresh'): void }>()
const route = useRoute()

const selectedId = ref('')
const createVisible = ref(false)
const submitting = ref(false)
const draftLoading = ref(false)
const draft = ref<ReviewDraft | null>(null)
const caseMode = ref(false)
const caseKeyword = ref('')
const cases = ref<ReviewRecord[]>([])
const approvalBusy = ref(false)
const applyVisible = ref(false)
const applyBusy = ref(false)
const templates = ref<MonitoringTaskTemplate[]>([])
const drills = ref<DrillRun[]>([])
const applyTemplateId = ref('')
const applyRuleJson = ref('')
const displayed = computed(() => (caseMode.value ? cases.value : props.reviews))
const selected = computed(() => displayed.value.find((item) => item.id === selectedId.value) ?? displayed.value[0] ?? null)
const form = reactive({
  entity_type: 'event' as ReviewEntityType,
  entity_id: '',
  status: 'draft' as ReviewStatus,
  summary: '',
  findings: '',
  recommendations: '',
  response: '',
  resolve: ''
})
const entityOptions = computed(() =>
  form.entity_type === 'event'
    ? props.events.map((item) => ({ id: item.id, label: `${item.id} ${item.name}` }))
    : form.entity_type === 'monitoring_task'
      ? props.tasks.map((item) => ({ id: item.id, label: `${item.id} ${item.name}` }))
      : drills.value.map((item) => ({ id: item.id, label: `${item.id} ${item.title}` }))
)

function entityLabel(type: ReviewEntityType, id: string): string {
  if (type === 'event') return props.events.find((item) => item.id === id)?.name ?? id
  if (type === 'monitoring_task') return props.tasks.find((item) => item.id === id)?.name ?? id
  return drills.value.find((item) => item.id === id)?.title ?? id
}

function openCreate() {
  form.entity_type = 'event'
  form.entity_id = props.events[0]?.id ?? props.tasks[0]?.id ?? drills.value[0]?.id ?? ''
  form.status = 'draft'
  form.summary = ''
  form.findings = ''
  form.recommendations = ''
  form.response = ''
  form.resolve = ''
  draft.value = null
  createVisible.value = true
}

function switchType(type: ReviewEntityType) {
  form.entity_type = type
  form.entity_id =
    type === 'event'
      ? (props.events[0]?.id ?? '')
      : type === 'monitoring_task'
        ? (props.tasks[0]?.id ?? '')
        : (drills.value[0]?.id ?? '')
  draft.value = null
}

async function submit() {
  if (!form.entity_id || !form.summary.trim()) {
    ElMessage.warning('请选择复盘对象并填写复盘摘要')
    return
  }
  const metrics: Record<string, unknown> = { ...(draft.value?.metrics ?? {}) }
  if (Number(form.response) > 0) metrics.response_min = Number(form.response)
  if (Number(form.resolve) > 0) metrics.resolve_min = Number(form.resolve)
  submitting.value = true
  try {
    const body: ReviewCreate = {
      entity_type: form.entity_type,
      entity_id: form.entity_id,
      status: form.status,
      summary: form.summary.trim(),
      metrics,
      findings: form.findings.split('\n').map((item) => item.trim()).filter(Boolean),
      recommendations: form.recommendations.split('\n').map((item) => item.trim()).filter(Boolean)
    }
    const row = await createReview(body)
    selectedId.value = row.id
    createVisible.value = false
    emit('refresh')
    ElMessage.success(`复盘记录 ${row.id} 已创建`)
  } catch (error) {
    ElMessage.error((error as Error).message || '复盘创建失败')
  } finally {
    submitting.value = false
  }
}

async function autofillDraft() {
  if (!form.entity_id) {
    ElMessage.warning('请先选择复盘对象')
    return
  }
  draftLoading.value = true
  try {
    draft.value = await getReviewDraft(form.entity_type, form.entity_id)
    form.summary = draft.value.summary
    form.findings = draft.value.findings.join('\n')
    form.recommendations = draft.value.recommendations.join('\n')
    const response = Number(draft.value.metrics.avg_response_min)
    const execution = Number(draft.value.metrics.avg_execution_min)
    form.response = Number.isFinite(response) ? String(response) : ''
    form.resolve = Number.isFinite(execution) ? String(execution) : ''
    ElMessage.success(`已汇总 ${draft.value.timeline.length} 条过程记录`)
  } catch (error) {
    ElMessage.error((error as Error).message || '过程汇总失败')
  } finally {
    draftLoading.value = false
  }
}

async function toggleCaseMode() {
  caseMode.value = !caseMode.value
  selectedId.value = ''
  if (caseMode.value) {
    try {
      cases.value = await getReviewCases(caseKeyword.value)
    } catch (error) {
      cases.value = props.reviews.filter((item) => item.status === 'confirmed')
      ElMessage.warning((error as Error).message || '案例库加载失败，已使用当前列表')
    }
  }
}

async function loadCaseResults() {
  try {
    cases.value = await getReviewCases(caseKeyword.value)
  } catch (error) {
    ElMessage.error((error as Error).message || '案例检索失败')
  }
}

async function approveReview() {
  if (!selected.value || approvalBusy.value) return
  approvalBusy.value = true
  try {
    const updated = await updateReview(selected.value.id, { status: 'confirmed' })
    emit('refresh')
    ElMessage.success(`复盘 ${updated.id} 已确认并进入案例库`)
  } catch (error) {
    ElMessage.error((error as Error).message || '复盘确认失败')
  } finally {
    approvalBusy.value = false
  }
}

function exportReport() {
  if (selected.value) window.open(reviewExportUrl(selected.value.id), '_blank', 'noopener')
}

function openApply() {
  if (!selected.value || selected.value.status !== 'confirmed') {
    ElMessage.warning('请先确认复盘记录')
    return
  }
  applyTemplateId.value = templates.value[0]?.id ?? ''
  applyRuleJson.value = JSON.stringify({ source_review_id: selected.value.id }, null, 2)
  applyVisible.value = true
}

async function applyRule() {
  if (!selected.value || !applyTemplateId.value || applyBusy.value) return
  let ruleConfig: Record<string, unknown>
  try {
    ruleConfig = JSON.parse(applyRuleJson.value) as Record<string, unknown>
  } catch {
    ElMessage.warning('规则配置必须是合法 JSON')
    return
  }
  applyBusy.value = true
  try {
    const revision = await applyReviewToTemplate(selected.value.id, {
      template_id: applyTemplateId.value,
      rule_config: ruleConfig,
      operator: '复盘审核员'
    })
    applyVisible.value = false
    ElMessage.success(`已生成任务模板修订版本 v${revision.version_no}`)
  } catch (error) {
    ElMessage.error((error as Error).message || '规则应用失败')
  } finally {
    applyBusy.value = false
  }
}

onMounted(() => {
  void getTaskTemplates().then((items) => (templates.value = items)).catch(() => undefined)
  void getDrillRuns()
    .then((items) => {
      drills.value = items
      applyReviewQuery()
    })
    .catch(() => undefined)
})

function applyReviewQuery() {
  const requestedReview = Array.isArray(route.query.reviewId)
    ? route.query.reviewId[0]
    : route.query.reviewId
  if (requestedReview && props.reviews.some((item) => item.id === requestedReview)) {
    selectedId.value = requestedReview
  }
}

watch(() => props.reviews, applyReviewQuery, { immediate: true })
</script>

<template>
  <div class="review-layout">
    <section class="cp-panel">
      <div class="cp-panel__header">
        <h3 class="cp-panel__title">{{ caseMode ? '复盘案例库' : '复盘记录' }}</h3>
        <div class="review-head-actions">
          <el-button :class="{ 'is-on': caseMode }" @click="toggleCaseMode">
            {{ caseMode ? '返回记录' : '案例库' }}
          </el-button>
          <el-button v-if="caseMode" @click="loadCaseResults"
            >检索</el-button
          >
          <el-button v-else type="primary" :icon="Plus" @click="openCreate">新建复盘</el-button>
        </div>
      </div>
      <el-input
        v-if="caseMode"
        v-model="caseKeyword"
        clearable
        placeholder="搜索案例编号、对象或摘要"
        @keyup.enter="loadCaseResults"
      />
      <div class="review-list">
        <el-empty v-if="!displayed.length" :image-size="72" :description="caseMode ? '暂无已确认案例' : '暂无复盘记录'" />
        <button
          v-for="item in displayed"
          :key="item.id"
          type="button"
          class="review-item"
          :class="{ active: selected?.id === item.id }"
          @click="selectedId = item.id"
        >
          <i :class="item.status" />
          <span>
            <b>{{ entityLabel(item.entity_type, item.entity_id) }}</b>
            <small>{{ item.id }} · {{ item.entity_type }} · {{ item.created_at }}</small>
          </span>
          <em>{{ item.status === 'confirmed' ? '已确认' : '草稿' }}</em>
        </button>
      </div>
    </section>

    <aside class="cp-panel detail">
      <template v-if="selected">
        <div class="cp-panel__header">
          <div>
            <h3 class="cp-panel__title">{{ entityLabel(selected.entity_type, selected.entity_id) }}</h3>
            <span class="sub">{{ selected.id }} · {{ selected.updated_at }}</span>
          </div>
          <span class="review-status" :class="selected.status">{{ selected.status === 'confirmed' ? '已确认' : '草稿' }}</span>
        </div>
        <div class="cp-panel__body detail-body">
          <p class="summary">{{ selected.summary || '尚无复盘摘要' }}</p>
          <section>
            <h4>评价指标</h4>
            <div v-if="!Object.keys(selected.metrics).length" class="empty-line">未登记指标</div>
            <div v-else class="metrics">
              <div v-for="(value, key) in selected.metrics" :key="key">
                <b>{{ value }}</b><span>{{ key }}</span>
              </div>
            </div>
          </section>
          <section>
            <h4>发现</h4>
            <ul v-if="selected.findings.length">
              <li v-for="item in selected.findings" :key="item">{{ item }}</li>
            </ul>
            <div v-else class="empty-line">暂无发现记录</div>
          </section>
          <section>
            <h4>改进建议</h4>
            <ul v-if="selected.recommendations.length">
              <li v-for="item in selected.recommendations" :key="item">{{ item }}</li>
            </ul>
            <div v-else class="empty-line">暂无改进建议</div>
          </section>
        </div>
        <footer class="detail-actions">
          <el-button v-if="selected.status === 'draft'" :icon="CircleCheck" :loading="approvalBusy" @click="approveReview"
            >确认复盘</el-button
          >
          <el-button :icon="Download" @click="exportReport">导出报告</el-button>
          <el-button :icon="Promotion" @click="openApply">应用到任务模板</el-button>
        </footer>
      </template>
      <el-empty v-else description="选择一条复盘记录查看详情" />
    </aside>
  </div>

  <el-dialog v-model="createVisible" title="新建复盘记录" width="min(600px, 94vw)" append-to-body>
    <el-form label-position="top">
      <div class="form-grid">
        <el-form-item label="复盘对象">
          <el-select :model-value="form.entity_type" @update:model-value="switchType">
            <el-option value="event" label="事件" />
            <el-option value="monitoring_task" label="监测任务" />
            <el-option value="drill" label="演练" />
          </el-select>
        </el-form-item>
        <el-form-item label="记录状态">
          <el-select v-model="form.status">
            <el-option value="draft" label="草稿" />
            <el-option value="confirmed" label="已确认" />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item :label="form.entity_type === 'drill' ? '演练记录' : '关联记录'" required>
        <el-select
          v-model="form.entity_id"
          filterable
          @change="draft = null"
        >
          <el-option v-for="item in entityOptions" :key="item.id" :value="item.id" :label="item.label" />
        </el-select>
      </el-form-item>
      <div class="draft-actions">
        <el-button :loading="draftLoading" @click="autofillDraft">自动汇总过程与指标</el-button>
        <span v-if="draft">已汇总 {{ draft.timeline.length }} 条过程记录</span>
      </div>
      <section v-if="draft" class="draft-timeline">
        <h4>过程时间线</h4>
        <div v-for="(item, index) in draft.timeline.slice(0, 12)" :key="`${item.ref}-${index}`">
          <time>{{ item.at }}</time>
          <b>{{ item.kind }}</b>
          <span>{{ item.text }}</span>
          <small>{{ item.operator }}</small>
        </div>
      </section>
      <el-form-item label="复盘摘要" required>
        <el-input v-model="form.summary" type="textarea" :rows="3" maxlength="4000" show-word-limit />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="响应时间（分钟）">
          <el-input v-model.number="form.response" type="number" min="0" />
        </el-form-item>
        <el-form-item label="办结时间（分钟）">
          <el-input v-model.number="form.resolve" type="number" min="0" />
        </el-form-item>
      </div>
      <el-form-item label="发现">
        <el-input v-model="form.findings" type="textarea" :rows="3" placeholder="每行一项" />
      </el-form-item>
      <el-form-item label="改进建议">
        <el-input v-model="form.recommendations" type="textarea" :rows="3" placeholder="每行一项" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存复盘</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="applyVisible" title="应用复盘建议到任务模板" width="min(600px, 94vw)" append-to-body>
    <el-form label-position="top">
      <el-form-item label="目标任务模板" required>
        <el-select v-model="applyTemplateId" style="width: 100%">
          <el-option
            v-for="template in templates"
            :key="template.id"
            :value="template.id"
            :label="`${template.id} ${template.name}`"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="审核后的规则配置（JSON）" required>
        <el-input v-model="applyRuleJson" type="textarea" :rows="7" />
      </el-form-item>
      <p class="apply-note">应用后会更新模板规则，并保留一条不可覆盖的修订版本记录。</p>
    </el-form>
    <template #footer>
      <el-button @click="applyVisible = false">取消</el-button>
      <el-button type="primary" :loading="applyBusy" @click="applyRule">应用并生成版本</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.review-layout {
  display: grid;
  grid-template-columns: minmax(340px, 0.8fr) minmax(0, 1.2fr);
  gap: 14px;
  min-height: 520px;
}
.review-head-actions {
  display: flex;
  gap: 6px;
}
.review-head-actions .is-on {
  border-color: var(--ce-accent);
  color: var(--ce-accent);
}
.review-list {
  overflow-y: auto;
  max-height: 650px;
}
.review-item {
  display: grid;
  grid-template-columns: 5px minmax(0, 1fr) auto;
  gap: 10px;
  width: 100%;
  min-height: 62px;
  padding: 10px 14px;
  border: 0;
  border-top: 1px solid var(--ce-divider);
  background: transparent;
  color: var(--ce-text);
  text-align: left;
  cursor: pointer;
}
.review-item:first-child {
  border-top: 0;
}
.review-item:hover,
.review-item.active {
  background: #1d2226;
}
.review-item > i {
  align-self: stretch;
  border-radius: 3px;
  background: var(--ce-text-faint);
}
.review-item > i.confirmed {
  background: var(--ce-success);
}
.review-item span {
  min-width: 0;
}
.review-item b,
.review-item small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.review-item b {
  color: var(--ce-text-strong);
  font-size: 13px;
}
.review-item small,
.review-item em,
.sub {
  color: var(--ce-text-faint);
  font-size: 11.5px;
  font-style: normal;
}
.review-status {
  padding: 3px 8px;
  border: 1px solid currentColor;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.review-status.confirmed {
  color: var(--ce-success);
}
.detail {
  min-height: 500px;
}
.detail-body {
  overflow-y: auto;
}
.detail-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
  padding: 10px 14px;
  border-top: 1px solid var(--ce-divider);
}
.apply-note {
  margin: 0;
  color: var(--ce-text-faint);
  font-size: 11px;
  line-height: 1.6;
}
.summary {
  margin: 0 0 18px;
  padding: 10px 12px;
  border-left: 2px solid var(--ce-accent);
  background: rgba(103, 198, 223, 0.05);
  line-height: 1.75;
}
.detail section + section {
  margin-top: 18px;
}
.detail h4 {
  margin: 0 0 8px;
  color: var(--ce-text-strong);
  font-size: 13px;
}
.detail ul {
  margin: 0;
  padding-left: 18px;
  color: var(--ce-text);
  line-height: 1.8;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
}
.metrics div {
  padding: 10px;
  border: 1px solid var(--ce-divider);
}
.metrics b,
.metrics span {
  display: block;
}
.metrics b {
  color: var(--ce-text-strong);
  font: 600 20px var(--ce-font-num);
}
.metrics span,
.empty-line {
  color: var(--ce-text-faint);
  font-size: 11.5px;
}
.draft-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: -4px 0 12px;
}
.draft-actions span {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.draft-timeline {
  max-height: 210px;
  margin-bottom: 14px;
  padding: 10px;
  overflow-y: auto;
  border: 1px solid var(--ce-divider);
}
.draft-timeline h4 {
  margin: 0 0 8px;
  color: var(--ce-text-strong);
  font-size: 12px;
}
.draft-timeline > div {
  display: grid;
  grid-template-columns: 132px 64px minmax(0, 1fr) auto;
  gap: 8px;
  padding: 6px 0;
  border-top: 1px solid var(--ce-divider);
  color: var(--ce-text-dim);
  font-size: 11px;
}
.draft-timeline time,
.draft-timeline small {
  color: var(--ce-text-faint);
  font: 10.5px var(--ce-font-num);
}
.draft-timeline b {
  color: var(--ce-accent);
  font-weight: 500;
}
.draft-timeline span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}
@media (max-width: 1100px) {
  .review-layout {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 700px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .draft-timeline > div {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>

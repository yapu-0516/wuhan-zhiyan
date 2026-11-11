<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Clock, Delete, Edit, Plus } from '@element-plus/icons-vue'
import {
  createMonitoringTask,
  createTaskTemplate,
  deleteTaskTemplate,
  executeMonitoringTask,
  getTaskTemplateRevisions,
  getTaskTemplates,
  patchTaskTemplate,
  patchMonitoringTask
} from '@/api/workflow'
import { getDataList } from '@/api/data'
import type { DataItem } from '@/types/api'
import { RUN_STATUS_META, SCHEDULE_META, TASK_STATUS_META, TASK_TRANSITIONS } from '@/types/workflow'
import type {
  MonitoringRun,
  MonitoringTask,
  MonitoringTaskCreate,
  MonitoringTaskStatus,
  MonitoringTaskTemplate
} from '@/types/workflow'
import { EVENT_TYPE_META, type EventType } from '@/types/event'

const props = defineProps<{ tasks: MonitoringTask[]; runs: MonitoringRun[] }>()
const emit = defineEmits<{ (e: 'refresh'): void }>()

const selectedId = ref('')
const createVisible = ref(false)
const submitting = ref(false)
const busy = ref(false)
const executing = ref(false)
const periodicMinutes = ref(60)
const nextRunAt = ref('')
const startAt = ref('')
const endAt = ref('')
const triggerThreshold = ref<number | null>(null)
const notifyTargetsText = ref('')
const algorithmParamsText = ref('{}')
const dataAssets = ref<DataItem[]>([])
const templates = ref<MonitoringTaskTemplate[]>([])
const selectedTemplate = ref('')
const templateVisible = ref(false)
const templateName = ref('')
const templateDescription = ref('')
const templateBusy = ref(false)
const templateManageVisible = ref(false)
const editingTemplateId = ref('')
const templateEditName = ref('')
const templateEditDescription = ref('')
const templateEditOwner = ref('')
const templateEditRules = ref('')
const historyVisible = ref(false)
const templateHistory = ref<Array<{ id: number; version_no: number; rule_config: Record<string, unknown>; source_review_id: string | null; operator: string; created_at: string }>>([])
const readyAssets = computed(() => dataAssets.value.filter((item) => item.analysis_status === 'ready'))
const selected = computed(() => props.tasks.find((item) => item.id === selectedId.value) ?? props.tasks[0] ?? null)
const taskRuns = computed(() => props.runs.filter((item) => item.monitoring_task_id === selected.value?.id))
const createForm = reactive<MonitoringTaskCreate>({
  name: '',
  event_type: 'flood',
  schedule_type: 'instant',
  area_name: '武汉中心城区',
  data_source_ids: [],
  rule_config: {},
  owner: '',
  notify_targets: []
})

function localDateTime(offsetMinutes: number): string {
  const date = new Date(Date.now() + offsetMinutes * 60_000)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:00`
}

function openCreate() {
  createForm.name = ''
  createForm.event_type = 'flood'
  createForm.schedule_type = 'instant'
  createForm.area_name = '武汉中心城区'
  createForm.owner = ''
  createForm.data_source_ids = []
  createForm.rule_config = {}
  createForm.notify_targets = []
  periodicMinutes.value = 60
  nextRunAt.value = ''
  startAt.value = ''
  endAt.value = ''
  triggerThreshold.value = null
  notifyTargetsText.value = ''
  algorithmParamsText.value = '{}'
  selectedTemplate.value = ''
  createVisible.value = true
}

function applyTemplate(templateId: string) {
  const template = templates.value.find((item) => item.id === templateId)
  if (!template) return
  selectedTemplate.value = template.id
  createForm.name = template.name
  createForm.event_type = template.event_type
  createForm.schedule_type = template.schedule_type
  createForm.area_name = template.area_name
  createForm.owner = template.owner
  createForm.data_source_ids = [...template.data_source_ids]
  createForm.notify_targets = [...template.notify_targets]
  notifyTargetsText.value = template.notify_targets.join('、')
  createForm.rule_config = { ...template.rule_config }
  triggerThreshold.value = Number(template.rule_config.threshold ?? template.rule_config.rainfall_mm_h ?? template.rule_config.tpi_threshold ?? NaN) || null
  algorithmParamsText.value = JSON.stringify(template.rule_config.algorithm_params ?? {}, null, 2)
  periodicMinutes.value = Number(template.rule_config.interval_minutes) || 60
  nextRunAt.value =
    template.schedule_type === 'periodic' ? localDateTime(periodicMinutes.value) : ''
}

function openSaveTemplate() {
  if (!selected.value) return
  templateName.value = `${selected.value.name}模板`
  templateDescription.value = `复用 ${selected.value.name} 的区域、数据源、责任人和触发规则。`
  templateVisible.value = true
}

async function saveTemplate() {
  if (!selected.value || !templateName.value.trim() || templateBusy.value) return
  templateBusy.value = true
  try {
    const row = await createTaskTemplate({
      name: templateName.value.trim(),
      description: templateDescription.value.trim(),
      event_type: selected.value.event_type,
      schedule_type: selected.value.schedule_type,
      area_name: selected.value.area_name,
      bbox: selected.value.bbox,
      data_source_ids: selected.value.data_source_ids,
      rule_config: selected.value.rule_config,
      owner: selected.value.owner,
      notify_targets: selected.value.notify_targets
    })
    templates.value = [row, ...templates.value]
    templateVisible.value = false
    ElMessage.success(`任务模板 ${row.id} 已保存`)
  } catch (error) {
    ElMessage.error((error as Error).message || '任务模板保存失败')
  } finally {
    templateBusy.value = false
  }
}

function openTemplateManage() {
  templateManageVisible.value = true
  void getTaskTemplates().then((items) => (templates.value = items)).catch(() => undefined)
}

function editTemplate(template: MonitoringTaskTemplate) {
  editingTemplateId.value = template.id
  templateEditName.value = template.name
  templateEditDescription.value = template.description
  templateEditOwner.value = template.owner
  templateEditRules.value = JSON.stringify(template.rule_config, null, 2)
}

async function saveTemplateEdit() {
  if (!editingTemplateId.value || !templateEditName.value.trim() || templateBusy.value) return
  let rules: Record<string, unknown>
  try {
    rules = JSON.parse(templateEditRules.value || '{}') as Record<string, unknown>
  } catch {
    ElMessage.warning('触发规则必须是合法 JSON')
    return
  }
  templateBusy.value = true
  try {
    const updated = await patchTaskTemplate(editingTemplateId.value, {
      name: templateEditName.value.trim(),
      description: templateEditDescription.value.trim(),
      owner: templateEditOwner.value.trim(),
      rule_config: rules
    })
    templates.value = templates.value.map((item) => (item.id === updated.id ? updated : item))
    editingTemplateId.value = ''
    ElMessage.success('任务模板已更新并记录修订')
  } catch (error) {
    ElMessage.error((error as Error).message || '模板更新失败')
  } finally {
    templateBusy.value = false
  }
}

async function removeTemplate(template: MonitoringTaskTemplate) {
  try {
    await deleteTaskTemplate(template.id)
    templates.value = templates.value.filter((item) => item.id !== template.id)
    ElMessage.success(`模板 ${template.id} 已删除`)
  } catch (error) {
    ElMessage.error((error as Error).message || '模板删除失败')
  }
}

async function showTemplateHistory(template: MonitoringTaskTemplate) {
  try {
    templateHistory.value = await getTaskTemplateRevisions(template.id)
    historyVisible.value = true
  } catch (error) {
    ElMessage.error((error as Error).message || '修订历史加载失败')
  }
}

function onScheduleChange(value: string) {
  if (value === 'periodic' && !nextRunAt.value) nextRunAt.value = localDateTime(periodicMinutes.value)
}

watch(
  () => props.tasks,
  (list) => {
    if (!selectedId.value || !list.some((item) => item.id === selectedId.value)) selectedId.value = list[0]?.id ?? ''
  },
  { immediate: true }
)

async function submit() {
  if (!createForm.name.trim()) {
    ElMessage.warning('请填写监测任务名称')
    return
  }
  submitting.value = true
  try {
    const interval = Math.max(1, Math.min(10080, Number(periodicMinutes.value) || 60))
    const ruleConfig = { ...createForm.rule_config }
    try {
      const algorithmParams = JSON.parse(algorithmParamsText.value || '{}') as Record<string, unknown>
      if (Object.keys(algorithmParams).length) ruleConfig.algorithm_params = algorithmParams
    } catch {
      ElMessage.warning('算法参数必须是合法 JSON')
      return
    }
    if (triggerThreshold.value !== null && triggerThreshold.value !== undefined) {
      const key = {
        flood: 'water_level_threshold_cm',
        traffic: 'tpi_threshold',
        building: 'settlement_rate_mm_month',
        fire: 'confidence_threshold'
      }[createForm.event_type]
      if (key) ruleConfig[key] = triggerThreshold.value
    }
    const row = await createMonitoringTask({
      ...createForm,
      name: createForm.name.trim(),
      owner: createForm.owner?.trim(),
      data_source_ids: createForm.data_source_ids?.filter(Boolean),
      rule_config:
        createForm.schedule_type === 'periodic'
          ? { ...ruleConfig, interval_minutes: interval }
          : ruleConfig,
      start_at: startAt.value || null,
      end_at: endAt.value || null,
      notify_targets: notifyTargetsText.value.split(/[、,，]/).map((item) => item.trim()).filter(Boolean),
      next_run_at:
        createForm.schedule_type === 'periodic'
          ? nextRunAt.value || localDateTime(interval)
          : null,
      template_key: selectedTemplate.value || null
    })
    selectedId.value = row.id
    createVisible.value = false
    emit('refresh')
    ElMessage.success(`监测任务 ${row.id} 已创建`)
  } catch (error) {
    ElMessage.error((error as Error).message || '任务创建失败')
  } finally {
    submitting.value = false
  }
}

async function advance(status: MonitoringTaskStatus) {
  if (!selected.value || busy.value) return
  busy.value = true
  try {
    await patchMonitoringTask(selected.value.id, { status })
    emit('refresh')
    ElMessage.success(`任务状态已更新为${TASK_STATUS_META[status].label}`)
  } catch (error) {
    ElMessage.error((error as Error).message || '状态更新失败')
  } finally {
    busy.value = false
  }
}

async function execute() {
  if (!selected.value || executing.value) return
  executing.value = true
  try {
    const result = await executeMonitoringTask(selected.value.id)
    emit('refresh')
    window.setTimeout(() => emit('refresh'), 2500)
    ElMessage.success(`已提交算法作业 ${result.analysis_task.id}`)
  } catch (error) {
    ElMessage.error((error as Error).message || '任务执行失败')
  } finally {
    executing.value = false
  }
}

function intervalText(task: MonitoringTask): string {
  const interval = Number(task.rule_config?.interval_minutes)
  return Number.isFinite(interval) && interval > 0 ? `${interval} 分钟` : '未设置'
}

function dataSourceText(task: MonitoringTask): string {
  return task.data_source_ids.map((id) => {
    const asset = dataAssets.value.find((item) => item.id === id)
    return asset ? `${asset.id} ${asset.name}` : id
  }).join(' / ') || '未绑定'
}

onMounted(() => {
  void getDataList().then((items) => (dataAssets.value = items)).catch(() => undefined)
  void getTaskTemplates().then((items) => (templates.value = items)).catch(() => undefined)
})
</script>

<template>
  <div class="queue-layout">
    <section class="cp-panel">
      <div class="cp-panel__header">
        <h3 class="cp-panel__title">监测任务</h3>
        <div class="task-head-actions">
          <el-button @click="openTemplateManage">模板管理</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate">新建任务</el-button>
        </div>
      </div>
      <el-table
        :data="tasks"
        highlight-current-row
        :current-row-key="selected?.id"
        row-key="id"
        class="task-table"
        @current-change="(row: MonitoringTask | null) => (selectedId = row?.id ?? '')"
      >
        <template #empty>
          <el-empty :image-size="72" description="暂无监测任务" />
        </template>
        <el-table-column label="任务" min-width="260">
          <template #default="{ row }">
            <div class="task-name">
              <i :style="{ background: TASK_STATUS_META[(row as MonitoringTask).status].color }" />
              <div>
                <b>{{ (row as MonitoringTask).name }}</b>
                <span>{{ (row as MonitoringTask).id }} · {{ EVENT_TYPE_META[(row as MonitoringTask).event_type].label }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="78">
          <template #default="{ row }">{{ SCHEDULE_META[(row as MonitoringTask).schedule_type] }}</template>
        </el-table-column>
        <el-table-column label="责任人" prop="owner" min-width="110" show-overflow-tooltip />
        <el-table-column label="状态" width="92">
          <template #default="{ row }">
            <span class="status-dot" :style="{ '--c': TASK_STATUS_META[(row as MonitoringTask).status].color }">
              {{ TASK_STATUS_META[(row as MonitoringTask).status].label }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="最近运行" prop="last_run_at" width="158">
          <template #default="{ row }"><span class="ce-num">{{ (row as MonitoringTask).last_run_at || '—' }}</span></template>
        </el-table-column>
      </el-table>
    </section>

    <aside class="cp-panel detail">
      <template v-if="selected">
        <div class="cp-panel__header">
          <div>
            <h3 class="cp-panel__title">{{ selected.name }}</h3>
            <span class="detail-id">{{ selected.id }}</span>
          </div>
          <span class="status-dot" :style="{ '--c': TASK_STATUS_META[selected.status].color }">
            {{ TASK_STATUS_META[selected.status].label }}
          </span>
        </div>
        <div class="cp-panel__body detail-body">
          <dl>
            <div><dt>监测类型</dt><dd>{{ EVENT_TYPE_META[selected.event_type].label }}</dd></div>
            <div><dt>执行方式</dt><dd>{{ SCHEDULE_META[selected.schedule_type] }}</dd></div>
            <div v-if="selected.schedule_type === 'periodic'"><dt>执行周期</dt><dd>{{ intervalText(selected) }}</dd></div>
            <div><dt>覆盖区域</dt><dd>{{ selected.area_name }}</dd></div>
            <div><dt>时间范围</dt><dd>{{ selected.start_at || '—' }} 至 {{ selected.end_at || '—' }}</dd></div>
            <div><dt>责任人</dt><dd>{{ selected.owner || '未指定' }}</dd></div>
            <div><dt>数据资源</dt><dd>{{ dataSourceText(selected) }}</dd></div>
            <div><dt>通知对象</dt><dd>{{ selected.notify_targets.join(' / ') || '未指定' }}</dd></div>
            <div><dt>下次运行</dt><dd>{{ selected.next_run_at || '未排程' }}</dd></div>
          </dl>
          <section class="detail-section">
            <h4>触发规则</h4>
            <pre>{{ JSON.stringify(selected.rule_config, null, 2) }}</pre>
          </section>
          <section class="detail-section">
            <h4>运行记录 <span>{{ taskRuns.length }}</span></h4>
            <el-empty v-if="!taskRuns.length" :image-size="52" description="尚未执行" />
            <div v-for="run in taskRuns" :key="run.id" class="run-row">
              <div>
                <b>{{ run.id }}</b>
                <small>{{ run.started_at || run.created_at }}</small>
              </div>
              <span :style="{ color: RUN_STATUS_META[run.status].color }">
                {{ RUN_STATUS_META[run.status].label }} · {{ run.event_ids.length }} 个事件
              </span>
              <small v-if="run.failure_reason" class="run-error">{{ run.failure_reason }}</small>
            </div>
          </section>
        </div>
        <footer class="detail-actions">
          <el-button type="primary" :loading="executing" @click="execute">立即运行</el-button>
          <el-button @click="openSaveTemplate">保存为模板</el-button>
          <el-button
            v-for="status in TASK_TRANSITIONS[selected.status]"
            :key="status"
            :loading="busy"
            @click="advance(status)"
            >转为{{ TASK_STATUS_META[status].label }}</el-button
          >
        </footer>
      </template>
      <el-empty v-else description="请选择一个监测任务" />
    </aside>
  </div>

  <el-dialog v-model="createVisible" title="新建监测任务" width="min(560px, 94vw)" append-to-body>
    <el-form label-position="top">
      <el-form-item label="从模板创建（可选）">
        <el-select
          v-model="selectedTemplate"
          clearable
          placeholder="选择任务模板后自动填入配置"
          style="width: 100%"
          @change="applyTemplate"
        >
          <el-option
            v-for="template in templates"
            :key="template.id"
            :value="template.id"
            :label="`${template.id} ${template.name}`"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="任务名称" required>
        <el-input v-model.trim="createForm.name" maxlength="128" placeholder="例如：强降雨道路积水专项监测" />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="风险类型">
          <el-select v-model="createForm.event_type">
            <el-option
              v-for="(meta, key) in EVENT_TYPE_META"
              :key="key"
              :value="key as EventType"
              :label="meta.label"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="执行方式">
          <el-select v-model="createForm.schedule_type" @change="onScheduleChange">
            <el-option v-for="(label, key) in SCHEDULE_META" :key="key" :value="key" :label="label" />
          </el-select>
        </el-form-item>
        <el-form-item label="责任人">
          <el-input v-model.trim="createForm.owner" placeholder="例如：防汛值班组" />
        </el-form-item>
        <el-form-item label="覆盖区域">
          <el-input v-model.trim="createForm.area_name" />
        </el-form-item>
        <el-form-item label="可分析数据资源" class="full-row">
          <el-select
            v-model="createForm.data_source_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="仅可选择已完成校验的数据资源"
            style="width: 100%"
          >
            <el-option
              v-for="asset in readyAssets"
              :key="asset.id"
              :value="asset.id!"
              :label="`${asset.id} ${asset.name}`"
            />
          </el-select>
        </el-form-item>
        <template v-if="createForm.schedule_type === 'periodic'">
          <el-form-item label="执行周期（分钟）">
            <el-input-number v-model="periodicMinutes" :min="1" :max="10080" :step="15" controls-position="right" />
          </el-form-item>
          <el-form-item label="下次运行">
            <el-date-picker
              v-model="nextRunAt"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm:ss"
              placeholder="选择下次运行时间"
              style="width: 100%"
            />
          </el-form-item>
        </template>
        <el-form-item label="任务开始时间">
          <el-date-picker
            v-model="startAt"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="可选"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="任务结束时间">
          <el-date-picker
            v-model="endAt"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="可选"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="触发阈值">
          <el-input-number
            v-model="triggerThreshold"
            :min="0"
            :step="1"
            controls-position="right"
            placeholder="按风险类型填写"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="通知对象">
          <el-input v-model="notifyTargetsText" placeholder="多个对象用逗号分隔" />
        </el-form-item>
        <el-form-item label="算法参数 JSON" class="full-row">
          <el-input
            v-model="algorithmParamsText"
            type="textarea"
            :rows="3"
            placeholder='例如 {"forecast_min": 30}'
          />
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="createVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">创建任务</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="templateVisible" title="保存任务模板" width="min(520px, 94vw)" append-to-body>
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
      <el-button type="primary" :loading="templateBusy" @click="saveTemplate">保存模板</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="templateManageVisible" title="任务模板管理" width="min(860px, 96vw)" append-to-body>
    <div class="template-manage">
      <section class="template-list-panel">
        <button
          v-for="template in templates"
          :key="template.id"
          type="button"
          :class="{ active: editingTemplateId === template.id }"
          @click="editTemplate(template)"
        >
          <span>
            <b>{{ template.name }}</b>
            <small>{{ template.id }} · {{ EVENT_TYPE_META[template.event_type].label }} · {{ SCHEDULE_META[template.schedule_type] }}</small>
          </span>
          <span class="template-buttons">
            <el-button link type="primary" :icon="Clock" @click.stop="showTemplateHistory(template)" />
            <el-button link type="danger" :icon="Delete" @click.stop="removeTemplate(template)" />
          </span>
        </button>
        <el-empty v-if="!templates.length" :image-size="56" description="暂无模板" />
      </section>
      <section v-if="editingTemplateId" class="template-editor">
        <el-form label-position="top">
          <el-form-item label="模板名称">
            <el-input v-model="templateEditName" maxlength="128" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item label="责任人">
              <el-input v-model="templateEditOwner" maxlength="64" />
            </el-form-item>
            <el-form-item label="说明">
              <el-input v-model="templateEditDescription" maxlength="1000" />
            </el-form-item>
          </div>
          <el-form-item label="触发规则 JSON">
            <el-input v-model="templateEditRules" type="textarea" :rows="8" />
          </el-form-item>
          <el-button type="primary" :icon="Edit" :loading="templateBusy" @click="saveTemplateEdit">
            保存并生成修订
          </el-button>
        </el-form>
      </section>
      <el-empty v-else description="选择左侧模板进行编辑" />
    </div>
  </el-dialog>

  <el-drawer v-model="historyVisible" title="模板修订历史" size="min(520px, 94vw)" append-to-body>
    <el-empty v-if="!templateHistory.length" description="暂无修订记录" />
    <article v-for="item in templateHistory" :key="item.id" class="revision-card">
      <header>
        <b>v{{ item.version_no }}</b>
        <span>{{ item.operator }}</span>
        <time>{{ item.created_at }}</time>
      </header>
      <pre>{{ JSON.stringify(item.rule_config, null, 2) }}</pre>
      <small v-if="item.source_review_id">来源复盘 {{ item.source_review_id }}</small>
    </article>
  </el-drawer>
</template>

<style scoped>
.queue-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 14px;
  min-height: 520px;
}
.cp-panel {
  min-width: 0;
}
.task-table {
  width: 100%;
}
.task-name {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.task-head-actions {
  display: flex;
  gap: 6px;
}
.task-name > i {
  width: 6px;
  height: 30px;
  margin-top: 2px;
  border-radius: 3px;
}
.task-name > div {
  min-width: 0;
}
.task-name b,
.task-name span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-name b {
  color: var(--ce-text-strong);
  font-size: 13px;
}
.task-name span,
.detail-id {
  color: var(--ce-text-faint);
  font-size: 11.5px;
}
.status-dot {
  --c: var(--ce-text-faint);
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--c);
  font-size: 12px;
  white-space: nowrap;
}
.status-dot::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: '';
}
.detail {
  min-height: 480px;
}
.detail-body {
  overflow-y: auto;
}
.detail dl {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 0;
}
.detail dt {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.detail dd {
  margin: 3px 0 0;
  color: var(--ce-text);
  font-size: 13px;
  overflow-wrap: anywhere;
}
.detail-section {
  margin-top: 18px;
}
.detail-section h4 {
  margin: 0 0 8px;
  color: var(--ce-text-strong);
  font-size: 13px;
}
.detail-section h4 span {
  color: var(--ce-text-faint);
  font-weight: 400;
}
.detail-section pre {
  margin: 0;
  padding: 10px;
  overflow-x: auto;
  border: 1px solid var(--ce-divider);
  color: #bfd2df;
  background: #101214;
  font: 11.5px/1.55 var(--ce-font);
}
.run-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-top: 1px solid var(--ce-divider);
}
.run-row b,
.run-row small {
  display: block;
}
.run-row small,
.run-row span {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.run-row .run-error {
  flex-basis: 100%;
  color: var(--ce-danger);
}
.detail-actions {
  display: flex;
  gap: 6px;
  padding: 10px 14px;
  border-top: 1px solid var(--ce-divider);
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}
.template-manage {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 14px;
  min-height: 400px;
}
.template-list-panel {
  overflow-y: auto;
  border: 1px solid var(--ce-divider);
}
.template-list-panel > button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 10px;
  border: 0;
  border-bottom: 1px solid var(--ce-divider);
  background: transparent;
  color: var(--ce-text-dim);
  text-align: left;
  cursor: pointer;
}
.template-list-panel > button:hover,
.template-list-panel > button.active {
  color: var(--ce-text-strong);
  background: var(--ce-active);
}
.template-list-panel button span {
  min-width: 0;
}
.template-list-panel b,
.template-list-panel small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.template-list-panel b {
  font-size: 12.5px;
}
.template-list-panel small {
  margin-top: 3px;
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.template-buttons {
  display: flex;
  flex: none;
}
.template-editor {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--ce-divider);
}
.revision-card {
  padding: 10px 0;
  border-bottom: 1px solid var(--ce-divider);
}
.revision-card header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.revision-card time,
.revision-card small {
  color: var(--ce-text-faint);
  font-size: 10.5px;
}
.revision-card time {
  margin-left: auto;
}
.revision-card pre {
  margin: 8px 0 0;
  padding: 9px;
  overflow-x: auto;
  color: var(--ce-text-dim);
  background: #101214;
  font: 11px/1.55 var(--ce-font-num);
}
.full-row {
  grid-column: 1 / -1;
}
@media (max-width: 1100px) {
  .queue-layout {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 700px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .template-manage {
    grid-template-columns: 1fr;
  }
}
</style>

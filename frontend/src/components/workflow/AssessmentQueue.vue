<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Aim, DataAnalysis, DocumentChecked } from '@element-plus/icons-vue'
import { createAssessment, getAssessmentContext, mergeCandidateEvents } from '@/api/workflow'
import { fileUrl } from '@/config/api'
import { useOperator } from '@/composables/useOperator'
import { useCityEvents } from '@/composables/useCityEvents'
import type { Assessment, AssessmentContext, AssessmentDecision, MonitoringRun } from '@/types/workflow'
import { DECISION_META } from '@/types/workflow'
import type { CityEvent, Severity } from '@/types/event'
import { EVENT_STATUS_COLOR, EVENT_STATUS_LABEL, EVENT_TYPE_META, SEVERITY_META } from '@/types/event'

const props = defineProps<{ events: CityEvent[]; assessments: Assessment[]; runs: MonitoringRun[] }>()
const emit = defineEmits<{ (e: 'refresh'): void; (e: 'locate', eventId: string): void }>()
const { currentName, load: loadOperator } = useOperator()
const { upsert } = useCityEvents()
const router = useRouter()
onMounted(() => void loadOperator())

const selectedId = ref('')
const formVisible = ref(false)
const submitting = ref(false)
const contextLoading = ref(false)
const context = ref<AssessmentContext | null>(null)
const relatedIds = ref<string[]>([])
const queue = computed(() => props.events.filter((item) => item.status !== 'resolved').slice(0, 80))
const selected = computed(() => queue.value.find((item) => item.id === selectedId.value) ?? queue.value[0] ?? null)
const history = computed(() => props.assessments.filter((item) => item.event_id === selected.value?.id))
const nearbyCandidates = computed(() => {
  const current = selected.value
  if (!current) return []
  const currentTime = Date.parse(current.timestamp.replace(' ', 'T'))
  return props.events
    .filter((item) => {
      if (item.id === current.id || item.status === 'resolved' || item.event_type !== current.event_type) return false
      const time = Date.parse(item.timestamp.replace(' ', 'T'))
      if (Number.isFinite(currentTime) && Number.isFinite(time) && Math.abs(currentTime - time) > 2 * 60 * 60 * 1000) {
        return false
      }
      return distanceMeters(current.longitude, current.latitude, item.longitude, item.latitude) <= 1000
    })
    .sort(
      (a, b) =>
        distanceMeters(current.longitude, current.latitude, a.longitude, a.latitude) -
        distanceMeters(current.longitude, current.latitude, b.longitude, b.latitude)
    )
    .slice(0, 6)
})
const form = reactive({
  decision: 'confirmed' as AssessmentDecision,
  summary: '',
  missing: '',
  priority: 'medium' as Severity,
  operator: currentName.value
})

watch(
  () => queue.value,
  (list) => {
    if (!selectedId.value || !list.some((item) => item.id === selectedId.value)) selectedId.value = list[0]?.id ?? ''
  },
  { immediate: true }
)

watch(
  () => selected.value?.id,
  async (eventId) => {
    context.value = null
    relatedIds.value = []
    if (!eventId) return
    contextLoading.value = true
    try {
      context.value = await getAssessmentContext(eventId, 300)
    } catch {
      context.value = null
    } finally {
      contextLoading.value = false
    }
  },
  { immediate: true }
)

function openForm() {
  if (!selected.value) return
  form.decision = 'confirmed'
  form.summary = `结合任务运行、算法证据与空间背景，确认「${selected.value.name}」需要进入处置。`
  form.missing = ''
  form.priority = selected.value.severity
  form.operator = currentName.value
  formVisible.value = true
}

function toggleCandidate(id: string) {
  relatedIds.value = relatedIds.value.includes(id)
    ? relatedIds.value.filter((item) => item !== id)
    : [...relatedIds.value, id]
}

function distanceMeters(lon1: number, lat1: number, lon2: number, lat2: number): number {
  const dx = (lon2 - lon1) * 111320 * Math.cos((lat1 * Math.PI) / 180)
  const dy = (lat2 - lat1) * 110540
  return Math.hypot(dx, dy)
}

async function mergeCandidate(item: CityEvent) {
  if (!selected.value) return
  try {
    const result = await mergeCandidateEvents(selected.value.id, item.id, currentName.value, '研判合并相近告警')
    upsert(result.primary)
    upsert(result.merged)
    relatedIds.value = relatedIds.value.filter((id) => id !== item.id)
    ElMessage.success(`已将 ${item.id} 合并到 ${selected.value.id}`)
  } catch (error) {
    ElMessage.error((error as Error).message || '相近告警合并失败')
  }
}

function openScenario() {
  if (!selected.value) return
  void router.push({ path: '/scenario', query: { eventId: selected.value.id } })
}

async function submit() {
  if (!selected.value) return
  if (!form.summary.trim()) {
    ElMessage.warning('请填写研判结论')
    return
  }
  const event = selected.value
  const run = props.runs.find((item) => item.event_ids.includes(event.id))
  submitting.value = true
  try {
    await createAssessment({
      event_id: event.id,
      monitoring_run_id: run?.id ?? null,
      decision: form.decision,
      summary: form.summary.trim(),
      evidence: [
        { kind: 'event', id: event.id, url: event.evidence_url },
        ...(run ? [{ kind: 'monitoring_run', id: run.id }] : []),
        ...relatedIds.value.map((id) => ({ kind: 'related_event', id }))
      ],
      impact: {
        district: event.district,
        address: event.address,
        road_id: event.road_id,
        building_id: event.building_id,
        related_event_ids: relatedIds.value,
        nearby_buildings: context.value?.buildings.length ?? 0,
        nearby_roads: context.value?.roads.length ?? 0,
        nearby_facilities: context.value?.pois.length ?? 0
      },
      missing_information: form.missing.split('\n').map((item) => item.trim()).filter(Boolean),
      priority: form.priority,
      operator: form.operator.trim() || currentName.value
    })
    formVisible.value = false
    emit('refresh')
    ElMessage.success('研判记录已保存')
  } catch (error) {
    ElMessage.error((error as Error).message || '研判保存失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="assessment-layout">
    <section class="cp-panel">
      <div class="cp-panel__header">
        <h3 class="cp-panel__title">待研判事件</h3>
        <span>{{ queue.length }} 项活跃事件</span>
      </div>
      <div class="event-list">
        <el-empty v-if="!queue.length" :image-size="72" description="当前没有待研判事件" />
        <button
          v-for="event in queue"
          :key="event.id"
          type="button"
          class="event-item"
          :class="{ active: selected?.id === event.id }"
          @click="selectedId = event.id"
        >
          <i :style="{ background: EVENT_TYPE_META[event.event_type].color }" />
          <span class="event-main">
            <b>{{ event.name }}</b>
            <small>{{ event.id }} · {{ event.district }} · {{ event.address }}</small>
          </span>
          <span class="event-status" :style="{ color: EVENT_STATUS_COLOR[event.status] }">
            {{ EVENT_STATUS_LABEL[event.status] }}
          </span>
        </button>
      </div>
    </section>

    <aside class="cp-panel dossier">
      <template v-if="selected">
        <div class="cp-panel__header">
          <div>
            <h3 class="cp-panel__title">{{ selected.name }}</h3>
            <span class="sub">{{ selected.id }} · {{ selected.timestamp }}</span>
          </div>
          <div class="dossier-tools">
            <el-button :icon="DataAnalysis" @click="openScenario">转入推演</el-button>
            <el-button :icon="Aim" @click="emit('locate', selected.id)">地图定位</el-button>
          </div>
        </div>
        <div class="cp-panel__body dossier-body">
          <div class="case-meta">
            <span :style="{ color: SEVERITY_META[selected.severity].color }">
              {{ SEVERITY_META[selected.severity].label }}
            </span>
            <span>{{ EVENT_TYPE_META[selected.event_type].label }}</span>
            <span>置信度 {{ Math.round(selected.confidence * 100) }}%</span>
          </div>
          <p>{{ selected.description }}</p>
          <div class="evidence">
            <img v-if="selected.evidence_url" :src="fileUrl(selected.evidence_url)" alt="事件证据" />
            <dl>
              <div><dt>行政区</dt><dd>{{ selected.district }}</dd></div>
              <div><dt>网格</dt><dd>{{ selected.grid }}</dd></div>
              <div><dt>来源</dt><dd>{{ selected.source }}</dd></div>
              <div><dt>关联对象</dt><dd>{{ selected.building_id || selected.road_id || '—' }}</dd></div>
            </dl>
          </div>
          <section v-loading="contextLoading" class="spatial-context">
            <header>
              <div>
                <h4>周边影响对象</h4>
                <p>事件点 {{ context?.radius_m ?? 300 }} m 范围内的城市对象</p>
              </div>
              <span v-if="context">
                建筑 {{ context.buildings.length }} · 道路 {{ context.roads.length }} · 设施 {{ context.pois.length }}
              </span>
            </header>
            <div v-if="context" class="spatial-context__grid">
              <div>
                <b>建筑</b>
                <p v-if="!context.buildings.length">范围内无建筑</p>
                <small v-for="item in context.buildings.slice(0, 4)" :key="item.id">
                  {{ item.name }} · {{ Math.round(item.distance_m) }} m
                </small>
              </div>
              <div>
                <b>道路</b>
                <p v-if="!context.roads.length">范围内无道路</p>
                <small v-for="item in context.roads.slice(0, 4)" :key="item.id">
                  {{ item.name }} · {{ Math.round(item.distance_m) }} m
                </small>
              </div>
              <div>
                <b>敏感设施</b>
                <p v-if="!context.pois.length">范围内无已知设施</p>
                <small v-for="item in context.pois.slice(0, 4)" :key="item.id">
                  {{ item.name }} · {{ Math.round(item.distance_m) }} m
                </small>
              </div>
            </div>
            <p v-else-if="!contextLoading" class="spatial-context__empty">周边对象查询失败或当前无空间数据。</p>
          </section>
          <section class="related-candidates">
            <header>
              <div>
                <h4>相近告警</h4>
                <p>同类型、1 km 内且两小时内的未办结事件，可关联到本次研判。</p>
              </div>
              <span>{{ relatedIds.length }} 项已选</span>
            </header>
            <p v-if="!nearbyCandidates.length" class="related-candidates__empty">未发现可关联的相近告警。</p>
            <template v-else>
              <div
                v-for="item in nearbyCandidates"
                :key="item.id"
                class="related-candidate-row"
              >
                <button
                  type="button"
                  :class="{ selected: relatedIds.includes(item.id) }"
                  @click="toggleCandidate(item.id)"
                >
                  <span>
                    <b>{{ item.name }}</b>
                    <small>{{ item.id }} · {{ item.district }} · {{ item.timestamp }}</small>
                  </span>
                  <em>
                    {{ Math.round(distanceMeters(selected.longitude, selected.latitude, item.longitude, item.latitude)) }} m
                  </em>
                </button>
                <el-button link type="danger" @click="mergeCandidate(item)">合并</el-button>
              </div>
            </template>
          </section>
          <section class="history">
            <h4>研判记录 <span>{{ history.length }}</span></h4>
            <el-empty v-if="!history.length" :image-size="52" description="尚未形成研判记录" />
            <article v-for="item in history" :key="item.id">
              <header>
                <b>{{ item.id }}</b>
                <span :style="{ color: DECISION_META[item.decision].color }">{{ DECISION_META[item.decision].label }}</span>
                <time>{{ item.created_at }}</time>
              </header>
              <p>{{ item.summary }}</p>
              <small v-if="item.missing_information.length">待补信息：{{ item.missing_information.join('；') }}</small>
            </article>
          </section>
        </div>
        <footer class="dossier-actions">
          <el-button type="primary" :icon="DocumentChecked" @click="openForm">形成研判</el-button>
        </footer>
      </template>
      <el-empty v-else description="选择一个事件查看证据" />
    </aside>
  </div>

  <el-dialog v-model="formVisible" title="形成研判记录" width="min(560px, 94vw)" append-to-body>
    <el-form label-position="top">
      <div class="form-grid">
        <el-form-item label="研判结论">
          <el-select v-model="form.decision">
            <el-option v-for="(meta, key) in DECISION_META" :key="key" :value="key" :label="meta.label" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority">
            <el-option v-for="(meta, key) in SEVERITY_META" :key="key" :value="key" :label="meta.label" />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item label="研判结论说明" required>
        <el-input v-model="form.summary" type="textarea" :rows="4" maxlength="4000" show-word-limit />
      </el-form-item>
      <el-form-item label="仍需核实的信息">
        <el-input v-model="form.missing" type="textarea" :rows="2" placeholder="每行一项，可选" />
      </el-form-item>
      <el-form-item label="研判人">
        <el-input v-model.trim="form.operator" maxlength="64" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="formVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存研判</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.assessment-layout {
  display: grid;
  grid-template-columns: minmax(360px, 0.82fr) minmax(0, 1.18fr);
  gap: 14px;
  min-height: 560px;
}
.cp-panel {
  min-width: 0;
}
.cp-panel__header > span,
.sub {
  color: var(--ce-text-faint);
  font-size: 11.5px;
}
.dossier-tools {
  display: flex;
  gap: 6px;
}
.event-list {
  overflow-y: auto;
  max-height: 650px;
}
.event-item {
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
.event-item:first-child {
  border-top: 0;
}
.event-item:hover,
.event-item.active {
  background: #1d2226;
}
.event-item > i {
  align-self: stretch;
  border-radius: 3px;
}
.event-main {
  min-width: 0;
}
.event-main b,
.event-main small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-main b {
  color: var(--ce-text-strong);
  font-size: 13px;
}
.event-main small,
.event-status {
  margin-top: 3px;
  color: var(--ce-text-faint);
  font-size: 11.5px;
}
.dossier {
  min-height: 560px;
}
.dossier-body {
  overflow-y: auto;
}
.case-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  color: var(--ce-text-dim);
  font-size: 12px;
}
.dossier-body > p {
  margin: 14px 0;
  line-height: 1.75;
  color: var(--ce-text);
}
.evidence {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 0.7fr);
  gap: 14px;
}
.evidence img {
  width: 100%;
  max-height: 260px;
  object-fit: cover;
  border: 1px solid var(--ce-divider);
}
.evidence dl {
  margin: 0;
}
.evidence dl div {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 7px 0;
  border-bottom: 1px solid var(--ce-divider);
}
.evidence dt {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.evidence dd {
  margin: 0;
  color: var(--ce-text);
  font-size: 12px;
  text-align: right;
  overflow-wrap: anywhere;
}
.spatial-context {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--ce-divider);
}
.spatial-context > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
.spatial-context h4 {
  margin: 0 0 3px;
  color: var(--ce-text-strong);
  font-size: 13px;
}
.spatial-context header p,
.spatial-context header span {
  margin: 0;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.spatial-context__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.spatial-context__grid > div {
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid var(--ce-divider);
}
.spatial-context__grid b,
.spatial-context__grid small,
.spatial-context__grid p {
  display: block;
}
.spatial-context__grid b {
  margin-bottom: 6px;
  color: var(--ce-text-strong);
  font-size: 12px;
}
.spatial-context__grid small,
.spatial-context__grid p {
  overflow: hidden;
  margin: 3px 0 0;
  color: var(--ce-text-dim);
  font-size: 10.5px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.spatial-context__empty {
  margin: 10px 0 0;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.related-candidates {
  margin-top: 14px;
  padding-top: 13px;
  border-top: 1px solid var(--ce-divider);
}
.related-candidates > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.related-candidates h4 {
  margin: 0 0 3px;
  color: var(--ce-text-strong);
  font-size: 13px;
}
.related-candidates header p,
.related-candidates header span,
.related-candidates__empty {
  margin: 0;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.related-candidate-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--ce-divider);
}
.related-candidate-row > button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  padding: 8px 0;
  border: 0;
  border: 0;
  background: transparent;
  color: var(--ce-text-dim);
  text-align: left;
  cursor: pointer;
}
.related-candidate-row > button:hover,
.related-candidate-row > button.selected {
  color: var(--ce-text-strong);
  background: var(--ce-active);
}
.related-candidate-row > button.selected {
  box-shadow: inset 2px 0 var(--ce-accent);
}
.related-candidate-row button span,
.related-candidate-row button b,
.related-candidate-row button small {
  display: block;
  min-width: 0;
}
.related-candidate-row button b,
.related-candidate-row button small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.related-candidate-row button b {
  font-size: 12px;
}
.related-candidate-row button small,
.related-candidate-row button em {
  color: var(--ce-text-faint);
  font-size: 10.5px;
  font-style: normal;
  white-space: nowrap;
}
.related-candidate-row button em {
  color: var(--ce-accent);
}
.history {
  margin-top: 18px;
}
.history h4,
.history h4 span {
  margin: 0 0 8px;
  color: var(--ce-text-strong);
  font-size: 13px;
}
.history h4 span {
  color: var(--ce-text-faint);
  font-weight: 400;
}
.history article {
  padding: 10px 0;
  border-top: 1px solid var(--ce-divider);
}
.history article header {
  display: flex;
  align-items: center;
  gap: 10px;
}
.history article time {
  margin-left: auto;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.history article p {
  margin: 6px 0;
  line-height: 1.65;
}
.history article small {
  color: var(--ce-warning);
}
.dossier-actions {
  display: flex;
  justify-content: flex-end;
  padding: 10px 14px;
  border-top: 1px solid var(--ce-divider);
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}
@media (max-width: 1100px) {
  .assessment-layout {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 700px) {
  .evidence,
  .form-grid,
  .spatial-context__grid {
    grid-template-columns: 1fr;
  }
}
</style>

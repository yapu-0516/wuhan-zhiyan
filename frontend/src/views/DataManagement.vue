<script setup lang="ts">
// 数据管理 —— 空间数据资产总览
// KPI + 类型 / 状态分布 + 过滤工具栏 + 资产表格 + 数据上传（POST /api/data/upload）
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { Document, Download, FirstAidKit, Refresh, Search, UploadFilled, View } from '@element-plus/icons-vue'
import {
  autoCheckDataAsset,
  getDataList,
  getDataStats,
  getDataValidations,
  uploadData,
  validateDataAsset
} from '@/api/data'
import type { DataItem, DataStats, DataValidation, DataValidationDecision } from '@/api/data'
import { getEmergencyResources, patchEmergencyResource } from '@/api/support'
import type { EmergencyResource } from '@/types/support'
import { apiState } from '@/api/http'
import { fileUrl } from '@/config/api'
import { DATA_TYPES, dataStatusMeta, dataTypeMeta } from '@/composables/pages/dataMeta'
import { errMsg, fmtBytes, isImageUrl } from '@/composables/pages/format'
import { useViewportWidth } from '@/composables/pages/viewport'
import { useOperator } from '@/composables/useOperator'
import PageShell from '@/components/pages/PageShell.vue'
import KpiCard from '@/components/pages/KpiCard.vue'
import DataTypeDistribution from '@/components/pages/DataTypeDistribution.vue'
import DataStatusChart from '@/components/pages/DataStatusChart.vue'

const vw = useViewportWidth()
const router = useRouter()
const showFormat = computed(() => vw.value >= 1600)
const showMore = computed(() => vw.value >= 1400)
const drawerSize = computed(() => (vw.value < 620 ? '94vw' : '560px'))
const resourceVisible = ref(false)
const resourceLoading = ref(false)
const resourceRows = ref<EmergencyResource[]>([])
const resourceKind = ref('')
const resourceStatus = ref('')
const rowKey = (r: DataItem): string => r.id ?? r.name

const loading = ref(true)
const refreshing = ref(false)
const list = ref<DataItem[]>([])
const stats = ref<DataStats | null>(null)
const detailVisible = ref(false)
const detailRow = ref<DataItem | null>(null)
const timeRange = ref<[string, string] | null>(null)
const locationLongitude = ref<number | null>(null)
const locationLatitude = ref<number | null>(null)
const locationRadius = ref(1000)
const validations = ref<DataValidation[]>([])
const validationBusy = ref(false)
const autoChecking = ref(false)
const { currentName, load: loadOperator } = useOperator()
const validationForm = reactive({
  decision: 'pass' as DataValidationDecision,
  coordinate_check: true,
  time_check: true,
  fields_check: true,
  notes: '',
  operator: ''
})
const VALIDATION_META: Record<DataValidationDecision, { label: string; color: string }> = {
  pass: { label: '通过', color: '#72c39a' },
  needs_repair: { label: '待修复', color: '#f0c050' },
  reject: { label: '不可用', color: '#e4777b' }
}

const ANALYSIS_META: Record<string, { label: string; color: string }> = {
  ready: { label: '可分析', color: '#72c39a' },
  pending: { label: '待校验', color: '#f0c050' },
  unavailable: { label: '暂不可用', color: '#7f8ea6' },
  unknown: { label: '状态未知', color: '#8aa3c4' }
}

// ---------- 加载 ----------
async function load(silent = false) {
  if (!silent) loading.value = true
  const [l, s] = await Promise.allSettled([getDataList(), getDataStats()])
  if (l.status === 'fulfilled') list.value = l.value
  else ElMessage.error(errMsg(l.reason, '数据清单加载失败'))
  stats.value = s.status === 'fulfilled' ? s.value : null
  loading.value = false
}

async function refresh() {
  refreshing.value = true
  await load(true)
  refreshing.value = false
  ElMessage.success('数据清单已刷新')
}

onMounted(() => {
  void loadOperator()
  void load()
})

// ---------- 统计（优先使用后端 stats，缺失时由清单推导） ----------
const derivedByType = computed(() => {
  const m = new Map<string, number>()
  for (const d of list.value) m.set(d.type, (m.get(d.type) ?? 0) + 1)
  return [...m.entries()].map(([type, count]) => ({ type, count }))
})
const byType = computed(() => {
  const src = stats.value?.by_type?.length ? stats.value.by_type : derivedByType.value
  const order = (t: string) => {
    const i = (DATA_TYPES as readonly string[]).indexOf(t)
    return i < 0 ? 99 : i
  }
  return [...src].sort((a, b) => order(a.type) - order(b.type))
})
const totalCount = computed(() => stats.value?.total ?? list.value.length)
const totalSize = computed(() => {
  if (stats.value?.total_size) return stats.value.total_size
  const bytes = list.value.reduce((s, d) => s + (d.size_bytes ?? 0), 0)
  return bytes ? fmtBytes(bytes) : '—'
})
const statusCounts = computed(() => {
  const m: Record<string, number> = {}
  for (const d of list.value) m[d.status] = (m[d.status] ?? 0) + 1
  return m
})
const analyzableCount = computed(
  () => stats.value?.analyzable ?? list.value.filter((item) => item.analysis_status === 'ready').length
)
const pendingCount = computed(() => list.value.filter((item) => item.analysis_status === 'pending').length)
const averageQuality = computed(() => {
  const scored = list.value.filter((item) => Number(item.quality_score) > 0)
  if (!scored.length) return 0
  return Math.round(scored.reduce((sum, item) => sum + Number(item.quality_score || 0), 0) / scored.length)
})

// ---------- 过滤 / 排序 / 分页 ----------
const typeFilter = ref('')
const statusFilter = ref('')
const analysisFilter = ref('')
const keyword = ref('')
const sortProp = ref<'time' | 'size_bytes'>('time')
const sortOrder = ref<'ascending' | 'descending'>('descending')
const page = ref(1)
const pageSize = ref(10)

const filtered = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  return list.value.filter((d) => {
    if (typeFilter.value && d.type !== typeFilter.value) return false
    if (statusFilter.value && d.status !== statusFilter.value) return false
    if (analysisFilter.value && (d.analysis_status ?? 'unknown') !== analysisFilter.value) return false
    if (timeRange.value?.length === 2) {
      const from = Date.parse(timeRange.value[0].replace(' ', 'T'))
      const to = Date.parse(timeRange.value[1].replace(' ', 'T'))
      const start = d.time_start ? Date.parse(d.time_start.replace(' ', 'T')) : null
      const end = d.time_end ? Date.parse(d.time_end.replace(' ', 'T')) : null
      if (start !== null && start > to) return false
      if (end !== null && end < from) return false
    }
    if (
      locationLongitude.value !== null &&
      locationLatitude.value !== null &&
      !matchesRadius(d, locationLongitude.value, locationLatitude.value, locationRadius.value)
    ) return false
    if (
      q &&
      !`${d.name} ${d.description ?? ''} ${d.source ?? ''} ${d.format ?? ''} ${d.id ?? ''}`.toLowerCase().includes(q)
    )
      return false
    return true
  })
})
const sorted = computed(() => {
  const dir = sortOrder.value === 'ascending' ? 1 : -1
  return [...filtered.value].sort((a, b) => {
    if (sortProp.value === 'size_bytes') return ((a.size_bytes ?? 0) - (b.size_bytes ?? 0)) * dir
    return a.time.localeCompare(b.time) * dir
  })
})
const pageRows = computed(() => sorted.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
watch(
  [typeFilter, statusFilter, analysisFilter, keyword, pageSize, timeRange, locationLongitude, locationLatitude, locationRadius],
  () => (page.value = 1)
)
watch(
  () => sorted.value.length,
  (n) => {
    const max = Math.max(1, Math.ceil(n / pageSize.value))
    if (page.value > max) page.value = max
  }
)

function onSortChange(p: { prop?: string; order?: 'ascending' | 'descending' | null }) {
  if (!p.order || (p.prop !== 'time' && p.prop !== 'size_bytes')) {
    sortProp.value = 'time'
    sortOrder.value = 'descending'
    return
  }
  sortProp.value = p.prop
  sortOrder.value = p.order
}

const statusOptions = ['已入库', '处理中', '采集中', '待接入']
const analysisOptions = Object.entries(ANALYSIS_META).map(([value, meta]) => ({ value, ...meta }))

async function loadValidations(assetId: string) {
  try {
    validations.value = await getDataValidations(assetId)
  } catch {
    validations.value = []
  }
}

function openDetail(row: DataItem) {
  detailRow.value = row
  detailVisible.value = true
  validations.value = []
  validationForm.decision = row.analysis_status === 'ready' ? 'pass' : 'needs_repair'
  validationForm.coordinate_check = row.analysis_status === 'ready'
  validationForm.time_check = row.analysis_status === 'ready'
  validationForm.fields_check = row.analysis_status === 'ready'
  validationForm.notes = ''
  validationForm.operator = currentName.value || '数据管理员'
  void loadValidations(row.id ?? '')
}

function spatialText(row: DataItem): string {
  return row.spatial_extent?.label || '尚未登记空间范围'
}

function bboxText(row: DataItem): string {
  const bbox = row.spatial_extent?.bbox
  return bbox?.length === 4 ? bbox.map((item) => Number(item).toFixed(5)).join(' / ') : '—'
}

function timeRangeText(row: DataItem): string {
  if (!row.time_start && !row.time_end) return '尚未登记时相范围'
  return `${row.time_start || '未知起点'} 至 ${row.time_end || '实时延续'}`
}

function qualityTone(score: number): string {
  if (score >= 85) return '#72c39a'
  if (score >= 60) return '#f0c050'
  return '#8aa3c4'
}

function matchesRadius(row: DataItem, longitude: number, latitude: number, radiusM: number): boolean {
  const bbox = row.spatial_extent?.bbox
  if (!bbox || bbox.length !== 4) return false
  const lonDelta = radiusM / Math.max(1, 111320 * Math.cos((latitude * Math.PI) / 180))
  const latDelta = radiusM / 110540
  const [west, south, east, north] = bbox
  return !(
    east < longitude - lonDelta ||
    west > longitude + lonDelta ||
    north < latitude - latDelta ||
    south > latitude + latDelta
  )
}

function resetAdvancedSearch() {
  timeRange.value = null
  locationLongitude.value = null
  locationLatitude.value = null
  locationRadius.value = 1000
}

function locateAsset(row: DataItem) {
  const bbox = row.spatial_extent?.bbox
  if (!bbox || bbox.length !== 4) {
    ElMessage.warning('该数据资源尚未登记空间范围')
    return
  }
  const longitude = (bbox[0] + bbox[2]) / 2
  const latitude = (bbox[1] + bbox[3]) / 2
  void router.push({ path: '/dashboard', query: { lon: longitude.toFixed(6), lat: latitude.toFixed(6) } })
}

async function submitValidation() {
  if (!detailRow.value?.id || validationBusy.value) return
  if (
    validationForm.decision === 'pass' &&
    !(validationForm.coordinate_check && validationForm.time_check && validationForm.fields_check)
  ) {
    ElMessage.warning('校验通过前必须完成坐标、时相和字段三项检查')
    return
  }
  validationBusy.value = true
  try {
    await validateDataAsset(detailRow.value.id, {
      decision: validationForm.decision,
      coordinate_check: validationForm.coordinate_check,
      time_check: validationForm.time_check,
      fields_check: validationForm.fields_check,
      notes: validationForm.notes.split('\n').map((item) => item.trim()).filter(Boolean),
      operator: validationForm.operator.trim() || currentName.value || '数据管理员'
    })
    await load(true)
    detailRow.value = list.value.find((item) => item.id === detailRow.value?.id) ?? detailRow.value
    await loadValidations(detailRow.value?.id ?? '')
    ElMessage.success('数据校验已完成，可分析状态已更新')
  } catch (error) {
    ElMessage.error((error as Error).message || '数据校验失败')
  } finally {
    validationBusy.value = false
  }
}

async function autoCheck() {
  if (!detailRow.value?.id || autoChecking.value) return
  autoChecking.value = true
  try {
    await autoCheckDataAsset(detailRow.value.id)
    await load(true)
    detailRow.value = list.value.find((item) => item.id === detailRow.value?.id) ?? detailRow.value
    await loadValidations(detailRow.value?.id ?? '')
    ElMessage.success('自动预检完成，请人工确认结论')
  } catch (error) {
    ElMessage.error((error as Error).message || '自动预检失败')
  } finally {
    autoChecking.value = false
  }
}

async function loadEmergencyResources() {
  resourceLoading.value = true
  try {
    resourceRows.value = await getEmergencyResources(resourceKind.value || undefined, resourceStatus.value || undefined)
  } catch (error) {
    ElMessage.error((error as Error).message || '应急资源加载失败')
  } finally {
    resourceLoading.value = false
  }
}

function openEmergencyResources() {
  resourceVisible.value = true
  void loadEmergencyResources()
}

async function saveEmergencyResource(row: EmergencyResource) {
  try {
    const updated = await patchEmergencyResource(row.id, {
      capacity: row.capacity,
      available: row.available,
      status: row.status,
      contact: row.contact,
      capability: row.capability,
      notes: row.notes
    })
    resourceRows.value = resourceRows.value.map((item) => (item.id === updated.id ? updated : item))
    ElMessage.success(`${updated.name} 状态已更新`)
  } catch (error) {
    ElMessage.error((error as Error).message || '资源状态更新失败')
  }
}

function resourceStatusLabel(status: EmergencyResource['status']): string {
  return { available: '可调度', limited: '受限', unavailable: '不可用' }[status]
}

// ---------- 预览 / 下载 ----------
const previewList = ref<string[]>([])
function preview(row: DataItem) {
  if (!row.url) return
  const url = fileUrl(row.url)
  if (isImageUrl(row.url)) previewList.value = [url]
  else window.open(url, '_blank', 'noopener')
}

// ---------- 上传 ----------
const uploadType = ref('')
const uploading = ref(0)
let reloadTimer: number | undefined

async function doUpload(opts: UploadRequestOptions): Promise<void> {
  const file = opts.file as File
  uploading.value++
  try {
    const items = await uploadData([file], uploadType.value || undefined)
    opts.onSuccess(items)
    const got = items[0]
    ElMessage.success(got ? `${file.name} 上传成功：${got.type}，${got.status}` : `${file.name} 上传成功`)
    window.clearTimeout(reloadTimer)
    reloadTimer = window.setTimeout(() => void load(true), 400)
  } catch (e) {
    ElMessage.error(`${file.name}：${errMsg(e, '上传失败')}`)
    opts.onError(e as never)
  } finally {
    uploading.value--
  }
}

onBeforeUnmount(() => window.clearTimeout(reloadTimer))
</script>

<template>
  <PageShell
    title="数据资源"
    hint="登记数据覆盖范围、时相、版本与质量；只有在完成校验并标记为可分析后，才作为任务与推演输入"
  >
    <template #actions>
      <el-button :icon="FirstAidKit" @click="openEmergencyResources">应急资源状态</el-button>
      <el-button :icon="Refresh" :loading="refreshing" @click="refresh">刷新</el-button>
    </template>

    <!-- KPI -->
    <section class="kpis">
      <KpiCard
        label="数据资产总数"
        :value="totalCount"
        unit="项"
        color="#67c6df"
        :hint="`涵盖 ${byType.length} 个数据类别`"
      />
      <KpiCard
        label="可分析资产"
        :value="analyzableCount"
        unit="项"
        color="#72c39a"
        :hint="`${pendingCount} 项仍在等待校验`"
      />
      <KpiCard
        label="质量检查均分"
        :value="averageQuality"
        unit="分"
        color="#f0c050"
        hint="仅统计已登记质量评分的资产"
      />
      <KpiCard label="总存储容量" :value="totalSize" color="#9ab0ba" hint="含上传、采集与目录资产" />
    </section>

    <!-- 分布 -->
    <section class="charts">
      <div class="cp-panel">
        <div class="cp-panel__header">
          <h3 class="cp-panel__title">数据类型分布</h3>
          <span class="cp-panel__sub">点击图例可按类型筛选</span>
        </div>
        <div class="cp-panel__body">
          <el-skeleton v-if="loading" animated :rows="5" />
          <DataTypeDistribution
            v-else
            :items="byType"
            :selected="typeFilter"
            @select="(t: string) => (typeFilter = t)"
          />
        </div>
      </div>
      <div class="cp-panel">
        <div class="cp-panel__header">
          <h3 class="cp-panel__title">入库状态分布</h3>
          <span class="cp-panel__sub">共 {{ list.length }} 项</span>
        </div>
        <div class="cp-panel__body">
          <el-skeleton v-if="loading" animated :rows="5" />
          <DataStatusChart v-else :counts="statusCounts" />
        </div>
      </div>
    </section>

    <!-- 工具栏 -->
    <section class="cp-panel toolbar">
      <div class="chips">
        <button type="button" class="chip" :class="{ 'is-on': !typeFilter }" @click="typeFilter = ''">
          全部<em>{{ list.length }}</em>
        </button>
        <button
          v-for="t in byType"
          :key="t.type"
          type="button"
          class="chip"
          :class="{ 'is-on': typeFilter === t.type }"
          :style="{ '--c': dataTypeMeta(t.type).color }"
          @click="typeFilter = typeFilter === t.type ? '' : t.type"
        >
          <i class="chip__dot" />{{ t.type }}<em>{{ t.count }}</em>
        </button>
      </div>
      <div class="toolbar__right">
        <el-select
          v-model="statusFilter"
          clearable
          placeholder="全部状态"
          style="width: 124px"
          popper-class="cp-popper"
        >
          <el-option v-for="s in statusOptions" :key="s" :value="s" :label="s">
            <span class="opt"
              ><i
                class="cp-dot"
                :class="{ 'cp-dot--pulse': dataStatusMeta(s).pulse }"
                :style="{ '--c': dataStatusMeta(s).color }"
              ></i
              >{{ s }}</span
            >
          </el-option>
        </el-select>
        <el-select
          v-model="analysisFilter"
          clearable
          placeholder="全部可分析状态"
          style="width: 150px"
          popper-class="cp-popper"
        >
          <el-option
            v-for="item in analysisOptions"
            :key="item.value"
            :value="item.value"
            :label="item.label"
          >
            <span class="opt"><i class="cp-dot" :style="{ '--c': item.color }"></i>{{ item.label }}</span>
          </el-option>
        </el-select>
        <el-input
          v-model="keyword"
          clearable
          placeholder="搜索名称 / 来源 / 格式"
          :prefix-icon="Search"
          style="width: 240px"
        />
        <el-select
          v-model="uploadType"
          clearable
          placeholder="入库类型：自动识别"
          style="width: 170px"
          popper-class="cp-popper"
        >
          <el-option v-for="t in DATA_TYPES" :key="t" :value="t" :label="t" />
        </el-select>
        <el-upload
          :http-request="doUpload"
          :show-file-list="false"
          multiple
          :disabled="apiState.mode !== 'live'"
          action="#"
        >
          <el-button type="primary" :icon="UploadFilled" :loading="uploading > 0" :disabled="apiState.mode !== 'live'">
            {{ uploading > 0 ? `上传中 (${uploading})` : '上传数据' }}
          </el-button>
        </el-upload>
      </div>
      <div class="advanced-search">
        <span>时空检索</span>
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          value-format="YYYY-MM-DD HH:mm:ss"
          range-separator="至"
          start-placeholder="覆盖开始"
          end-placeholder="覆盖结束"
          style="width: 330px"
        />
        <el-input-number v-model="locationLongitude" :precision="5" :min="-180" :max="180" :controls="false" placeholder="经度" />
        <el-input-number v-model="locationLatitude" :precision="5" :min="-90" :max="90" :controls="false" placeholder="纬度" />
        <el-input-number v-model="locationRadius" :min="50" :max="20000" :step="100" controls-position="right" />
        <span class="advanced-search__unit">m</span>
        <el-button @click="resetAdvancedSearch">清除时空条件</el-button>
      </div>
    </section>

    <!-- 表格 -->
    <section class="cp-panel table-panel">
      <el-table
        v-loading="loading"
        :data="pageRows"
        :row-key="rowKey"
        :default-sort="{ prop: 'time', order: 'descending' }"
        @sort-change="onSortChange"
      >
        <template #empty>
          <el-empty
            :image-size="84"
            :description="list.length ? '没有符合条件的数据资产' : '暂无数据资产，点击右上方「上传数据」入库'"
          />
        </template>

        <el-table-column label="数据名称" min-width="260">
          <template #default="{ row }">
            <div class="dname">
              <span class="dname__dot" :style="{ '--c': dataTypeMeta((row as DataItem).type).color }" />
              <div class="dname__txt">
                <span class="dname__t">{{ (row as DataItem).name }}</span>
                <span v-if="(row as DataItem).description" class="dname__d">{{ (row as DataItem).description }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="类型" width="130">
          <template #default="{ row }">
            <span class="cp-pill cp-pill--sm" :style="{ '--c': dataTypeMeta((row as DataItem).type).color }">
              {{ (row as DataItem).type }}
            </span>
          </template>
        </el-table-column>

        <el-table-column v-if="showMore" label="来源" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ (row as DataItem).source || '—' }}</template>
        </el-table-column>

        <el-table-column v-if="showFormat" label="格式" width="104">
          <template #default="{ row }">
            <span v-if="(row as DataItem).format" class="fmt cp-mono">{{ (row as DataItem).format }}</span>
            <span v-else class="dim">—</span>
          </template>
        </el-table-column>

        <el-table-column label="大小" prop="size_bytes" width="110" sortable="custom" align="right">
          <template #default="{ row }"
            ><span class="num">{{
              (row as DataItem).size && (row as DataItem).size !== '0 B' ? (row as DataItem).size : '—'
            }}</span></template
          >
        </el-table-column>

        <el-table-column v-if="showMore" label="记录数" width="96" align="right">
          <template #default="{ row }">
            <span class="num">{{
              (row as DataItem).records !== undefined ? (row as DataItem).records!.toLocaleString('zh-CN') : '—'
            }}</span>
          </template>
        </el-table-column>

        <el-table-column label="获取时间" prop="time" width="150" sortable="custom">
          <template #default="{ row }"
            ><span class="num">{{ (row as DataItem).time }}</span></template
          >
        </el-table-column>

        <el-table-column v-if="showMore" label="质量" width="88" align="right">
          <template #default="{ row }">
            <span
              v-if="Number((row as DataItem).quality_score) > 0"
              class="quality"
              :style="{ color: qualityTone(Number((row as DataItem).quality_score)) }"
            >
              {{ Math.round(Number((row as DataItem).quality_score)) }}
            </span>
            <span v-else class="dim">—</span>
          </template>
        </el-table-column>

        <el-table-column label="可分析" width="108">
          <template #default="{ row }">
            <span
              class="cp-pill cp-pill--sm"
              :style="{ '--c': ANALYSIS_META[(row as DataItem).analysis_status ?? 'unknown'].color }"
            >
              {{ ANALYSIS_META[(row as DataItem).analysis_status ?? 'unknown'].label }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="106">
          <template #default="{ row }">
            <span class="cp-pill cp-pill--sm" :style="{ '--c': dataStatusMeta((row as DataItem).status).color }">
              <i class="cp-dot" :class="{ 'cp-dot--pulse': dataStatusMeta((row as DataItem).status).pulse }"></i>
              {{ (row as DataItem).status }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="196" fixed="right" align="center">
          <template #default="{ row }">
            <div class="ops">
              <el-button link type="primary" :icon="Document" @click.stop="openDetail(row)">详情</el-button>
              <el-tooltip
                :disabled="!!(row as DataItem).url"
                content="该资产暂无可预览的文件"
                placement="top"
                popper-class="cp-popper"
              >
                <span>
                  <el-button link type="primary" :icon="View" :disabled="!(row as DataItem).url" @click="preview(row)"
                    >预览</el-button
                  >
                </span>
              </el-tooltip>
              <el-tooltip
                :disabled="!!(row as DataItem).url"
                content="该资产暂无可下载的文件"
                placement="top"
                popper-class="cp-popper"
              >
                <span>
                  <el-button v-if="!(row as DataItem).url" link type="primary" :icon="Download" disabled
                    >下载</el-button
                  >
                  <el-button
                    v-else
                    link
                    type="primary"
                    tag="a"
                    :icon="Download"
                    :href="fileUrl((row as DataItem).url)"
                    :download="(row as DataItem).name"
                    target="_blank"
                    rel="noopener"
                    >下载</el-button
                  >
                </span>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="foot">
        <span class="foot__total"
          >共 <b>{{ sorted.length }}</b> 项</span
        >
        <el-pagination
          background
          layout="sizes, prev, pager, next"
          :total="sorted.length"
          :page-size="pageSize"
          :current-page="page"
          :page-sizes="[10, 20, 50]"
          popper-class="cp-popper"
          @update:current-page="(v: number) => (page = v)"
          @update:page-size="(v: number) => (pageSize = v)"
        />
      </div>
    </section>

    <el-image-viewer
      v-if="previewList.length"
      :url-list="previewList"
      teleported
      hide-on-click-modal
      @close="previewList = []"
    />

    <el-drawer
      v-model="detailVisible"
      title="数据资源详情"
      :size="drawerSize"
      append-to-body
    >
      <div v-if="detailRow" class="resource-detail">
        <header>
          <span class="resource-detail__type" :style="{ '--c': dataTypeMeta(detailRow.type).color }">
            {{ detailRow.type }}
          </span>
          <h2>{{ detailRow.name }}</h2>
          <p>{{ detailRow.description || '暂无说明' }}</p>
          <el-button class="resource-detail__locate" size="small" @click="locateAsset(detailRow)">
            地图定位
          </el-button>
        </header>

        <section class="resource-detail__readiness">
          <div>
            <span>可分析状态</span>
            <strong :style="{ color: ANALYSIS_META[detailRow.analysis_status ?? 'unknown'].color }">
              {{ ANALYSIS_META[detailRow.analysis_status ?? 'unknown'].label }}
            </strong>
          </div>
          <div>
            <span>质量检查</span>
            <strong :style="{ color: qualityTone(Number(detailRow.quality_score)) }">
              {{
                Number(detailRow.quality_score) > 0
                  ? `${Math.round(Number(detailRow.quality_score))} 分`
                  : '未评分'
              }}
            </strong>
          </div>
          <div>
            <span>数据版本</span>
            <strong>{{ detailRow.version || '未登记' }}</strong>
          </div>
        </section>

        <dl>
          <div>
            <dt>空间范围</dt>
            <dd>{{ spatialText(detailRow) }}</dd>
          </div>
          <div>
            <dt>覆盖边界</dt>
            <dd class="resource-detail__mono">{{ bboxText(detailRow) }}</dd>
          </div>
          <div>
            <dt>时相范围</dt>
            <dd>{{ timeRangeText(detailRow) }}</dd>
          </div>
          <div>
            <dt>坐标参考系</dt>
            <dd>{{ detailRow.crs || '未登记' }}</dd>
          </div>
          <div>
            <dt>来源</dt>
            <dd>{{ detailRow.source || '未登记' }}</dd>
          </div>
          <div>
            <dt>格式 / 记录数</dt>
            <dd>{{ detailRow.format || '—' }} / {{ detailRow.records?.toLocaleString('zh-CN') ?? '—' }}</dd>
          </div>
        </dl>

        <section class="resource-detail__notes">
          <h3>质量与使用限制</h3>
          <ul v-if="detailRow.quality_notes?.length">
            <li v-for="item in detailRow.quality_notes" :key="item">{{ item }}</li>
          </ul>
          <p v-else>尚未登记质量说明。该资产不应直接作为风险研判或推演的唯一依据。</p>
        </section>

        <section class="validation-panel">
          <header>
            <div>
              <h3>数据校验</h3>
              <p>校验通过后，该资源才能被新监测任务绑定并用于分析。</p>
            </div>
            <span>{{ validations.length }} 条记录</span>
          </header>
          <div class="validation-form">
            <div class="validation-checks">
              <el-checkbox v-model="validationForm.coordinate_check">坐标有效</el-checkbox>
              <el-checkbox v-model="validationForm.time_check">时相有效</el-checkbox>
              <el-checkbox v-model="validationForm.fields_check">字段完整</el-checkbox>
            </div>
            <div class="validation-row">
              <el-select v-model="validationForm.decision" aria-label="校验结论">
                <el-option value="pass" label="校验通过" />
                <el-option value="needs_repair" label="需要修复" />
                <el-option value="reject" label="判定不可用" />
              </el-select>
              <el-input v-model="validationForm.operator" placeholder="校验人" />
            </div>
            <el-input
              v-model="validationForm.notes"
              type="textarea"
              :rows="2"
              placeholder="校验说明或待修复项，每行一项"
            />
            <div class="validation-actions">
              <el-button :loading="autoChecking" :disabled="apiState.mode !== 'live'" @click="autoCheck">
                自动预检
              </el-button>
              <el-button
                type="primary"
                :loading="validationBusy"
                :disabled="apiState.mode !== 'live'"
                @click="submitValidation"
              >
                提交人工校验
              </el-button>
            </div>
          </div>
          <div v-if="validations.length" class="validation-history">
            <article v-for="item in validations" :key="item.id">
              <header>
                <b>{{ item.id }}</b>
                <span :style="{ color: VALIDATION_META[item.decision].color }">
                  {{ VALIDATION_META[item.decision].label }}
                </span>
                <time>{{ item.created_at }}</time>
              </header>
              <p>
                坐标 {{ item.checks.coordinate ? '通过' : '未通过' }} · 时相
                {{ item.checks.time ? '通过' : '未通过' }} · 字段
                {{ item.checks.fields ? '通过' : '未通过' }} · 质量 {{ item.quality_score }} 分
              </p>
              <small>{{ item.operator }}{{ item.notes.length ? ` · ${item.notes.join('；')}` : '' }}</small>
            </article>
          </div>
        </section>
      </div>
    </el-drawer>

    <el-drawer v-model="resourceVisible" title="应急资源可调度能力" :size="drawerSize" append-to-body>
      <div class="resource-status-toolbar">
        <el-select
          v-model="resourceKind"
          clearable
          placeholder="全部资源类型"
          @change="loadEmergencyResources"
        >
          <el-option value="hospital" label="医院" />
          <el-option value="fire_station" label="消防站" />
          <el-option value="police" label="派出所" />
          <el-option value="school" label="学校" />
        </el-select>
        <el-select
          v-model="resourceStatus"
          clearable
          placeholder="全部可用状态"
          @change="loadEmergencyResources"
        >
          <el-option value="available" label="可调度" />
          <el-option value="limited" label="受限" />
          <el-option value="unavailable" label="不可用" />
        </el-select>
        <span>{{ resourceRows.length }} 处</span>
      </div>
      <el-table v-loading="resourceLoading" :data="resourceRows" row-key="id" max-height="560">
        <el-table-column label="资源点" min-width="180">
          <template #default="{ row }">
            <b>{{ (row as EmergencyResource).name }}</b>
            <small class="resource-id">{{ (row as EmergencyResource).id }}</small>
          </template>
        </el-table-column>
        <el-table-column label="能力" min-width="150">
          <template #default="{ row }">
            <el-input v-model="row.capability" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="容量 / 可用" width="150">
          <template #default="{ row }">
            <div class="resource-counts">
              <el-input-number v-model="row.capacity" size="small" :min="0" :controls="false" />
              <span>/</span>
              <el-input-number v-model="row.available" size="small" :min="0" :controls="false" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="112">
          <template #default="{ row }">
            <el-select v-model="row.status" size="small">
              <el-option value="available" :label="resourceStatusLabel('available')" />
              <el-option value="limited" :label="resourceStatusLabel('limited')" />
              <el-option value="unavailable" :label="resourceStatusLabel('unavailable')" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="联系人" width="150">
          <template #default="{ row }">
            <el-input v-model="row.contact" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="72" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="saveEmergencyResource(row as EmergencyResource)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>
      <p class="resource-disclaimer">资源点存在不代表当前可调度；容量和可用状态以责任单位确认结果为准。</p>
    </el-drawer>
  </PageShell>
</template>

<style scoped>
.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.charts {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: 14px;
}
.charts > .cp-panel {
  display: flex;
  flex-direction: column;
}
.charts > .cp-panel :deep(.cp-panel__body) {
  flex: 1;
}
@media (max-width: 1400px) {
  .charts {
    grid-template-columns: 1fr;
  }
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px 16px;
  padding: 12px 16px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  --c: #4fc3f7;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border-radius: 4px;
  font: inherit;
  font-size: 13px;
  color: var(--ce-text-dim);
  background: transparent;
  border: 1px solid var(--ce-panel-border);
  cursor: pointer;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease;
}
.chip em {
  font-style: normal;
  font-size: 11.5px;
  padding: 0 6px;
  line-height: 17px;
  border-radius: 9px;
  background: #2a2c2f;
  color: var(--ce-text-dim);
}
.chip:hover {
  border-color: var(--c);
  color: var(--ce-text-strong);
}
.chip.is-on {
  color: var(--c);
  border-color: var(--c);
  background: #1d1f22;
}
.chip.is-on em {
  background: #2a2c2f;
  color: var(--c);
}
.chip__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c);
}
.toolbar__right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.advanced-search {
  display: flex;
  flex-basis: 100%;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 10px;
  padding-top: 10px;
  border-top: 1px solid var(--ce-divider);
}
.advanced-search > span:first-child {
  color: var(--ce-text-dim);
  font-size: 12px;
}
.advanced-search :deep(.el-input-number) {
  width: 112px;
}
.advanced-search__unit {
  margin-left: -6px;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.resource-status-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.resource-status-toolbar :deep(.el-select) {
  width: 150px;
}
.resource-status-toolbar > span {
  margin-left: auto;
  color: var(--ce-text-faint);
  font-size: 11px;
}
.resource-id {
  display: block;
  color: var(--ce-text-faint);
  font-size: 10px;
}
.resource-counts {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 4px;
}
.resource-counts :deep(.el-input-number) {
  width: 58px;
}
.resource-counts span {
  color: var(--ce-text-faint);
}
.resource-disclaimer {
  margin: 12px 0 0;
  color: var(--ce-text-faint);
  font-size: 11px;
  line-height: 1.6;
}
.opt {
  display: flex;
  align-items: center;
  gap: 8px;
}
.table-panel {
  overflow: hidden;
}
.dname {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.dname__dot {
  --c: #4fc3f7;
  flex: none;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--c);
}
.dname__txt {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  line-height: 1.4;
}
.dname__t {
  color: var(--ce-text);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dname__d {
  font-size: 12px;
  color: var(--ce-text-dim, #8aa3c4);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fmt {
  display: inline-block;
  padding: 0 7px;
  line-height: 20px;
  font-size: 11.5px;
  border-radius: 4px;
  color: var(--ce-text-dim);
  background: transparent;
  border: 1px solid var(--ce-panel-border);
}
.num {
  font-size: 12.5px;
  color: var(--ce-text);
  font-variant-numeric: tabular-nums;
}
.dim {
  color: var(--ce-text-faint);
}
.ops {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  border-top: 1px solid var(--ce-divider);
  flex-wrap: wrap;
}
.foot__total {
  font-size: 12.5px;
  color: var(--ce-text-dim, #8aa3c4);
}
.foot__total b {
  padding: 0 2px;
  color: var(--ce-accent, #4fc3f7);
  font-weight: 600;
}
.quality {
  font: 600 13px var(--ce-font-num);
}
.resource-detail {
  display: grid;
  gap: 18px;
}
.resource-detail header {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--ce-divider);
}
.resource-detail__locate {
  margin-top: 10px;
}
.resource-detail__type {
  --c: var(--ce-accent);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--c);
  font-size: 12px;
}
.resource-detail__type::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: '';
}
.resource-detail h2 {
  margin: 8px 0 6px;
  color: var(--ce-text-strong);
  font-size: 20px;
  font-weight: 600;
  line-height: 1.35;
}
.resource-detail header p {
  margin: 0;
  color: var(--ce-text-dim);
  font-size: 13px;
  line-height: 1.7;
}
.resource-detail__readiness {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-left: 2px solid var(--ce-accent);
  background: rgba(103, 198, 223, 0.05);
}
.resource-detail__readiness > div {
  min-width: 0;
  padding: 12px;
}
.resource-detail__readiness > div + div {
  border-left: 1px solid var(--ce-divider);
}
.resource-detail__readiness span,
.resource-detail__readiness strong {
  display: block;
}
.resource-detail__readiness span {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.resource-detail__readiness strong {
  margin-top: 4px;
  color: var(--ce-text-strong);
  font: 600 16px var(--ce-font);
}
.resource-detail dl {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin: 0;
}
.resource-detail dt {
  color: var(--ce-text-faint);
  font-size: 11px;
}
.resource-detail dd {
  margin: 3px 0 0;
  color: var(--ce-text);
  font-size: 13px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}
.resource-detail__mono {
  font-family: var(--ce-font-num);
  font-size: 12px !important;
}
.resource-detail__notes {
  padding: 12px;
  border: 1px solid var(--ce-divider);
}
.resource-detail__notes h3 {
  margin: 0 0 8px;
  color: var(--ce-text-strong);
  font-size: 13px;
}
.resource-detail__notes ul {
  margin: 0;
  padding-left: 18px;
  color: var(--ce-text);
  font-size: 13px;
  line-height: 1.8;
}
.resource-detail__notes p {
  margin: 0;
  color: var(--ce-text-dim);
  font-size: 13px;
  line-height: 1.7;
}
.validation-panel {
  padding-top: 16px;
  border-top: 1px solid var(--ce-divider);
}
.validation-panel > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.validation-panel h3 {
  margin: 0 0 4px;
  color: var(--ce-text-strong);
  font-size: 13px;
}
.validation-panel header p,
.validation-panel header > span {
  margin: 0;
  color: var(--ce-text-faint);
  font-size: 11px;
  line-height: 1.55;
}
.validation-form {
  display: grid;
  gap: 9px;
  margin-top: 11px;
  padding: 11px;
  border: 1px solid var(--ce-divider);
}
.validation-checks,
.validation-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
}
.validation-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
}
.validation-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
.validation-history {
  margin-top: 12px;
}
.validation-history article {
  padding: 9px 0;
  border-top: 1px solid var(--ce-divider);
}
.validation-history article header {
  display: flex;
  align-items: center;
  gap: 9px;
}
.validation-history time {
  margin-left: auto;
  color: var(--ce-text-faint);
  font: 10.5px var(--ce-font-num);
}
.validation-history p {
  margin: 5px 0;
  color: var(--ce-text-dim);
  font-size: 12px;
}
.validation-history small {
  color: var(--ce-text-faint);
  font-size: 11px;
}
@media (max-width: 560px) {
  .resource-detail__readiness,
  .resource-detail dl {
    grid-template-columns: 1fr;
  }
  .resource-detail__readiness > div + div {
    border-top: 1px solid var(--ce-divider);
    border-left: 0;
  }
  .validation-row {
    grid-template-columns: 1fr;
  }
  .advanced-search :deep(.el-date-editor) {
    width: 100% !important;
  }
}
</style>

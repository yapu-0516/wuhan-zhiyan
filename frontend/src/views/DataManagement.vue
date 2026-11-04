<script setup lang="ts">
// 数据管理 —— 空间数据资产总览
// KPI + 类型 / 状态分布 + 过滤工具栏 + 资产表格 + 数据上传（POST /api/data/upload）
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { Download, Refresh, Search, UploadFilled, View } from '@element-plus/icons-vue'
import { getDataList, getDataStats, uploadData } from '@/api/data'
import type { DataItem, DataStats } from '@/api/data'
import { apiState } from '@/api/http'
import { fileUrl } from '@/config/api'
import { DATA_TYPES, dataStatusMeta, dataTypeMeta } from '@/composables/pages/dataMeta'
import { errMsg, fmtBytes, isImageUrl } from '@/composables/pages/format'
import { useViewportWidth } from '@/composables/pages/viewport'
import PageShell from '@/components/pages/PageShell.vue'
import KpiCard from '@/components/pages/KpiCard.vue'
import DataTypeDistribution from '@/components/pages/DataTypeDistribution.vue'
import DataStatusChart from '@/components/pages/DataStatusChart.vue'

const vw = useViewportWidth()
const showFormat = computed(() => vw.value >= 1600)
const showMore = computed(() => vw.value >= 1400)
const rowKey = (r: DataItem): string => r.id ?? r.name

const loading = ref(true)
const refreshing = ref(false)
const list = ref<DataItem[]>([])
const stats = ref<DataStats | null>(null)

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

onMounted(() => void load())

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
const storedCount = computed(() => statusCounts.value['已入库'] ?? 0)
const storedRate = computed(() => (list.value.length ? Math.round((storedCount.value / list.value.length) * 100) : 0))

// ---------- 过滤 / 排序 / 分页 ----------
const typeFilter = ref('')
const statusFilter = ref('')
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
    if (q && !`${d.name} ${d.description ?? ''} ${d.source ?? ''} ${d.format ?? ''} ${d.id ?? ''}`.toLowerCase().includes(q)) return false
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
watch([typeFilter, statusFilter, keyword, pageSize], () => (page.value = 1))
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
  <PageShell title="数据管理" hint="汇聚遥感影像、无人机影像、视频流、三维模型、传感器与矢量数据，统一纳管与入库">
    <template #actions>
      <el-button :icon="Refresh" :loading="refreshing" @click="refresh">刷新</el-button>
    </template>

    <!-- KPI -->
    <section class="kpis">
      <KpiCard label="数据资产总数" :value="totalCount" unit="项" color="#67c6df" :hint="`涵盖 ${byType.length} 个数据类别`" />
      <KpiCard label="总存储容量" :value="totalSize" color="#9ab0ba" hint="含上传与采集数据" />
      <KpiCard label="数据类型数" :value="byType.length" unit="类" color="#72c39a" hint="遥感 / 无人机 / 视频 / 三维 / 传感 / 矢量" />
      <KpiCard
        label="入库率"
        :value="storedRate"
        unit="%"
        color="#4dd984"
        :hint="`已入库 ${storedCount} / ${list.length} 项`"
      />
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
          <DataTypeDistribution v-else :items="byType" :selected="typeFilter" @select="(t: string) => (typeFilter = t)" />
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
        <button type="button" class="chip" :class="{ 'is-on': !typeFilter }" @click="typeFilter = ''">全部<em>{{ list.length }}</em></button>
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
        <el-select v-model="statusFilter" clearable placeholder="全部状态" style="width: 124px" popper-class="cp-popper">
          <el-option v-for="s in statusOptions" :key="s" :value="s" :label="s">
            <span class="opt"><i class="cp-dot" :class="{ 'cp-dot--pulse': dataStatusMeta(s).pulse }" :style="{ '--c': dataStatusMeta(s).color }"></i>{{ s }}</span>
          </el-option>
        </el-select>
        <el-input v-model="keyword" clearable placeholder="搜索名称 / 来源 / 格式" :prefix-icon="Search" style="width: 240px" />
        <el-select v-model="uploadType" clearable placeholder="入库类型：自动识别" style="width: 170px" popper-class="cp-popper">
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
          <el-empty :image-size="84" :description="list.length ? '没有符合条件的数据资产' : '暂无数据资产，点击右上方「上传数据」入库'" />
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
          <template #default="{ row }"><span class="num">{{ (row as DataItem).size && (row as DataItem).size !== '0 B' ? (row as DataItem).size : '—' }}</span></template>
        </el-table-column>

        <el-table-column v-if="showMore" label="记录数" width="96" align="right">
          <template #default="{ row }">
            <span class="num">{{ (row as DataItem).records !== undefined ? (row as DataItem).records!.toLocaleString('zh-CN') : '—' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="获取时间" prop="time" width="150" sortable="custom">
          <template #default="{ row }"><span class="num">{{ (row as DataItem).time }}</span></template>
        </el-table-column>

        <el-table-column label="状态" width="106">
          <template #default="{ row }">
            <span class="cp-pill cp-pill--sm" :style="{ '--c': dataStatusMeta((row as DataItem).status).color }">
              <i class="cp-dot" :class="{ 'cp-dot--pulse': dataStatusMeta((row as DataItem).status).pulse }"></i>
              {{ (row as DataItem).status }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <div class="ops">
              <el-tooltip :disabled="!!(row as DataItem).url" content="该资产暂无可预览的文件" placement="top" popper-class="cp-popper">
                <span>
                  <el-button link type="primary" :icon="View" :disabled="!(row as DataItem).url" @click="preview(row)">预览</el-button>
                </span>
              </el-tooltip>
              <el-tooltip :disabled="!!(row as DataItem).url" content="该资产暂无可下载的文件" placement="top" popper-class="cp-popper">
                <span>
                  <el-button v-if="!(row as DataItem).url" link type="primary" :icon="Download" disabled>下载</el-button>
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
                  >下载</el-button>
                </span>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="foot">
        <span class="foot__total">共 <b>{{ sorted.length }}</b> 项</span>
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

    <el-image-viewer v-if="previewList.length" :url-list="previewList" teleported hide-on-click-modal @close="previewList = []" />
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
</style>

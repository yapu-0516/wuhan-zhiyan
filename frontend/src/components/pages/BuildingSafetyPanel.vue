<script setup lang="ts">
// 建筑安全监测：接入沉降监测的建筑列表（按风险排序）+ 沉降曲线 / 趋势 / 阈值参考 / 研判结论
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Aim } from '@element-plus/icons-vue'
import EChart from '@/components/charts/EChart.vue'
import { getBuilding } from '@/api/geo'
import { errMsg } from '@/composables/pages/format'
import { EVENT_STATUS_COLOR, EVENT_STATUS_LABEL, EVENT_TYPE_META, SEVERITY_META } from '@/types/event'
import { RISK_LEVEL_META } from '@/types/building'
import type { Building, BuildingDetail, RiskLevel } from '@/types/building'

const props = defineProps<{ buildings: Building[]; loading?: boolean }>()
const router = useRouter()

const RANK: Record<RiskLevel, number> = { warning: 0, watch: 1, normal: 2 }
const CATEGORY: Record<string, string> = {
  residential: '住宅',
  commercial: '商业',
  office: '办公',
  public: '公共建筑',
  industrial: '工业',
  other: '其他'
}

const riskFilter = ref<RiskLevel | ''>('')
const sorted = computed(() =>
  [...props.buildings].sort(
    (a, b) => RANK[a.risk_level ?? 'normal'] - RANK[b.risk_level ?? 'normal'] || (a.name || a.id).localeCompare(b.name || b.id, 'zh-CN')
  )
)
const shown = computed(() => (riskFilter.value ? sorted.value.filter((b) => (b.risk_level ?? 'normal') === riskFilter.value) : sorted.value))
const counts = computed(() => {
  const c: Record<RiskLevel, number> = { warning: 0, watch: 0, normal: 0 }
  for (const b of props.buildings) c[b.risk_level ?? 'normal']++
  return c
})

// ---------- 详情 ----------
const selectedId = ref('')
const detail = ref<BuildingDetail | null>(null)
const detailLoading = ref(false)
let reqSeq = 0

async function select(id: string) {
  selectedId.value = id
  const seq = ++reqSeq
  detailLoading.value = true
  detail.value = null
  try {
    const d = await getBuilding(id)
    if (seq === reqSeq) detail.value = d
  } catch (e) {
    if (seq === reqSeq) ElMessage.error(errMsg(e, '建筑监测详情加载失败'))
  } finally {
    if (seq === reqSeq) detailLoading.value = false
  }
}

watch(
  sorted,
  (list) => {
    if (!list.length) return
    if (!selectedId.value || !list.some((b) => b.id === selectedId.value)) void select(list[0].id)
  },
  { immediate: true }
)
onBeforeUnmount(() => reqSeq++)

const bProps = computed(() => detail.value?.properties)
const mon = computed(() => detail.value?.monitoring ?? null)
const risk = computed(() => RISK_LEVEL_META[mon.value?.risk_level ?? bProps.value?.risk_level ?? 'normal'])

// ---------- 沉降曲线：线性趋势 + 阈值参考线（阈值取自后端研判文本，不臆造） ----------
const DAY = 86400000
const MONTH_DAYS = 30.4375

function parseThresholds(text: string): { label: string; value: number; color: string }[] {
  const out: { label: string; value: number; color: string }[] = []
  const re = /(\d+(?:\.\d+)?)\s*mm\s*\/\s*月\s*(关注|预警)阈值/g
  let m: RegExpExecArray | null
  while ((m = re.exec(text))) {
    out.push({ label: `${m[2]}速率 ${m[1]} mm/月`, value: Number(m[1]), color: m[2] === '预警' ? '#ff4d4f' : '#f0c050' })
  }
  return out
}

const chart = computed(() => {
  const m = mon.value
  if (!m || m.series.length < 2) return null
  const pts = m.series.map((p) => ({ d: p.date, t: new Date(p.date).getTime(), v: p.displacement_mm }))
  const t0 = pts[0].t
  const xs = pts.map((p) => (p.t - t0) / DAY)
  const ys = pts.map((p) => p.v)
  const n = pts.length
  const mx = xs.reduce((a, b) => a + b, 0) / n
  const my = ys.reduce((a, b) => a + b, 0) / n
  const sxx = xs.reduce((s, x) => s + (x - mx) ** 2, 0)
  const slope = sxx > 0 ? xs.reduce((s, x, i) => s + (x - mx) * (ys[i] - my), 0) / sxx : 0
  const icpt = my - slope * mx
  const trend = xs.map((x) => Number((icpt + slope * x).toFixed(2)))
  const sign = (m.rate_mm_per_month || slope) < 0 ? -1 : 1
  const refs = parseThresholds(m.analysis).map((th) => ({
    ...th,
    data: xs.map((x) => Number((ys[0] + sign * th.value * (x / MONTH_DAYS)).toFixed(2)))
  }))
  const axis = { color: '#8aa3c4', fontSize: 11 }
  const mainColor = risk.value.color
  return {
    color: [mainColor, '#9fd8ff', ...refs.map((r) => r.color)],
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v: unknown) => (typeof v === 'number' ? `${v.toFixed(2)} mm` : String(v))
    },
    legend: { top: 0, right: 4, itemWidth: 14, itemHeight: 3, textStyle: { color: '#b9cdec', fontSize: 11 } },
    grid: { left: 6, right: 14, top: 34, bottom: 4, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: pts.map((p) => p.d.slice(5)),
      axisLine: { lineStyle: { color: 'rgba(120,160,210,0.35)' } },
      axisTick: { show: false },
      axisLabel: { ...axis, hideOverlap: true }
    },
    yAxis: {
      type: 'value',
      name: '位移 (mm)',
      nameTextStyle: { color: '#8aa3c4', align: 'left' },
      scale: true,
      axisLabel: axis,
      splitLine: { lineStyle: { color: 'rgba(120,160,210,0.12)', type: 'dashed' } }
    },
    series: [
      {
        name: '实测位移',
        type: 'line',
        smooth: 0.15,
        showSymbol: pts.length <= 45,
        symbolSize: 5,
        lineStyle: { width: 2.4, shadowBlur: 10, shadowColor: mainColor },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: `${mainColor}44` },
              { offset: 1, color: `${mainColor}00` }
            ]
          }
        },
        data: ys
      },
      { name: '线性趋势', type: 'line', showSymbol: false, lineStyle: { width: 1.6, type: 'dashed' }, data: trend },
      ...refs.map((r) => ({
        name: `${r.label} 参考线`,
        type: 'line',
        showSymbol: false,
        lineStyle: { width: 1.2, type: 'dotted' },
        data: r.data
      }))
    ]
  }
})

const stats = computed(() => {
  const m = mon.value
  if (!m) return []
  return [
    { label: '沉降速率', value: m.rate_mm_per_month.toFixed(2), unit: 'mm/月', color: risk.value.color },
    { label: '累计位移', value: m.cumulative_mm.toFixed(1), unit: 'mm', color: '#9fd8ff' },
    { label: '加速度', value: m.acceleration.toFixed(2), unit: 'mm/月²', color: '#b8a9ff' },
    { label: '监测样本', value: String(m.series.length), unit: '期', color: '#5eead4' }
  ]
})

function locate() {
  if (selectedId.value) void router.push({ path: '/dashboard', query: { buildingId: selectedId.value } })
}
function openEvent(id: string) {
  void router.push({ path: '/event-center', query: { id } })
}
</script>

<template>
  <section class="bs cp-panel">
    <div class="cp-panel__header">
      <h3 class="cp-panel__title">建筑安全监测</h3>
      <span class="cp-panel__sub">接入沉降监测 {{ buildings.length }} 栋</span>
    </div>

    <div class="cp-panel__body">
      <el-skeleton v-if="loading && !buildings.length" animated :rows="8" />
      <el-empty v-else-if="!buildings.length" :image-size="72" description="当前区域暂无接入沉降监测的建筑" />
      <div v-else class="bs__grid">
        <!-- 列表 -->
        <aside class="list">
          <div class="list__sum">
            <button
              v-for="r in (['warning', 'watch', 'normal'] as RiskLevel[])"
              :key="r"
              type="button"
              class="list__chip"
              :class="{ 'is-on': riskFilter === r }"
              :style="{ '--c': RISK_LEVEL_META[r].color }"
              @click="riskFilter = riskFilter === r ? '' : r"
            >
              <i class="cp-dot" :class="{ 'cp-dot--pulse': r === 'warning' && counts[r] > 0 }"></i>{{ RISK_LEVEL_META[r].label }}<b>{{ counts[r] }}</b>
            </button>
          </div>
          <ul class="list__ul">
            <li
              v-for="b in shown"
              :key="b.id"
              class="item"
              :class="{ 'is-on': b.id === selectedId }"
              :style="{ '--c': RISK_LEVEL_META[b.risk_level ?? 'normal'].color }"
              @click="select(b.id)"
            >
              <div class="item__txt">
                <b class="cp-ellipsis">{{ b.name || b.id }}</b>
                <small class="cp-ellipsis">{{ b.id }} · {{ b.district || '—' }}<template v-if="b.grid"> · {{ b.grid }}</template></small>
              </div>
              <span class="cp-pill cp-pill--sm" :style="{ '--c': RISK_LEVEL_META[b.risk_level ?? 'normal'].color }">
                {{ RISK_LEVEL_META[b.risk_level ?? 'normal'].label }}
              </span>
            </li>
            <li v-if="!shown.length" class="item item--none">该风险等级下暂无建筑</li>
          </ul>
        </aside>

        <!-- 详情 -->
        <div class="detail" v-loading="detailLoading">
          <template v-if="bProps">
            <header class="detail__head">
              <div class="detail__ttl">
                <h4>{{ bProps.name || bProps.id }}</h4>
                <p>
                  <span class="cp-mono">{{ bProps.id }}</span>
                  <span v-if="bProps.category">{{ CATEGORY[bProps.category] ?? bProps.category }}</span>
                  <span v-if="bProps.levels">{{ bProps.levels }} 层</span>
                  <span>高 {{ bProps.height }} m</span>
                  <span v-if="bProps.district">{{ bProps.district }}</span>
                </p>
              </div>
              <span class="cp-pill" :style="{ '--c': risk.color }"><i class="cp-dot" :class="{ 'cp-dot--pulse': mon?.risk_level === 'warning' }"></i>{{ risk.label }}</span>
              <el-button type="primary" plain :icon="Aim" @click="locate">三维定位</el-button>
            </header>

            <template v-if="mon">
              <div class="stats">
                <div v-for="s in stats" :key="s.label" class="stat" :style="{ '--c': s.color }">
                  <span class="cp-label">{{ s.label }}</span>
                  <b>{{ s.value }}<small>{{ s.unit }}</small></b>
                </div>
              </div>

              <EChart v-if="chart" :key="selectedId" :option="chart" style="height: 260px" />
              <el-empty v-else :image-size="60" description="监测数据不足 2 期，无法绘制曲线" />

              <blockquote class="analysis" :style="{ '--c': risk.color }">
                <span class="cp-label">研判结论</span>
                <p>{{ mon.analysis }}</p>
              </blockquote>
            </template>
            <el-empty v-else :image-size="64" description="该建筑暂无沉降监测数据" />

            <div v-if="detail?.events?.length" class="rel">
              <span class="cp-label">关联事件</span>
              <button v-for="e in detail.events" :key="e.id" type="button" class="rel__item" @click="openEvent(e.id)">
                <span>{{ EVENT_TYPE_META[e.event_type].icon }}</span>
                <b class="cp-ellipsis">{{ e.name }}</b>
                <span class="cp-pill cp-pill--sm" :style="{ '--c': SEVERITY_META[e.severity].color }">{{ SEVERITY_META[e.severity].short }}级</span>
                <span class="cp-pill cp-pill--sm" :style="{ '--c': EVENT_STATUS_COLOR[e.status] }">{{ EVENT_STATUS_LABEL[e.status] }}</span>
              </button>
            </div>
          </template>
          <el-empty v-else-if="!detailLoading" :image-size="64" description="请从左侧选择建筑查看沉降监测详情" />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.bs__grid {
  display: grid;
  grid-template-columns: minmax(240px, 290px) minmax(0, 1fr);
  gap: 18px;
}
@media (max-width: 1100px) {
  .bs__grid {
    grid-template-columns: 1fr;
  }
}
.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
.list__sum {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.list__chip {
  --c: #4dd984;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  font: inherit;
  font-size: 12px;
  border-radius: 999px;
  color: #b9cdec;
  background: rgba(9, 16, 34, 0.55);
  border: 1px solid rgba(64, 120, 180, 0.3);
  cursor: pointer;
  transition: all 0.15s;
}
.list__chip .cp-dot {
  --c: inherit;
  background: var(--c);
  width: 7px;
  height: 7px;
}
.list__chip b {
  color: #fff;
  font-variant-numeric: tabular-nums;
}
.list__chip.is-on {
  color: var(--c);
  border-color: var(--c);
  background: color-mix(in srgb, var(--c) 14%, rgba(9, 16, 34, 0.55));
}
.list__ul {
  list-style: none;
  margin: 0;
  padding: 0 2px 0 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
  max-height: 520px;
  overflow: auto;
}
.item {
  --c: #4dd984;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  cursor: pointer;
  background: rgba(9, 16, 34, 0.45);
  border: 1px solid rgba(64, 120, 180, 0.2);
  border-left: 3px solid color-mix(in srgb, var(--c) 70%, transparent);
  transition: all 0.15s;
}
.item:hover {
  background: color-mix(in srgb, var(--c) 8%, rgba(9, 16, 34, 0.45));
  border-color: color-mix(in srgb, var(--c) 45%, transparent);
}
.item.is-on {
  background: color-mix(in srgb, var(--c) 13%, rgba(9, 16, 34, 0.5));
  border-color: var(--c);
  box-shadow: 0 0 14px color-mix(in srgb, var(--c) 22%, transparent);
}
.item--none {
  justify-content: center;
  cursor: default;
  font-size: 12.5px;
  color: #5d748f;
  border-left-width: 1px;
}
.item__txt {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.item__txt b {
  font-size: 13.5px;
  font-weight: 500;
  color: #e6f0ff;
}
.item__txt small {
  font-size: 11.5px;
  color: #6f89aa;
}
.detail {
  position: relative;
  min-width: 0;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.detail__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.detail__ttl {
  flex: 1;
  min-width: 200px;
}
.detail__ttl h4 {
  margin: 0 0 4px;
  font-size: 18px;
  color: #f0f6ff;
}
.detail__ttl p {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 14px;
  margin: 0;
  font-size: 12.5px;
  color: #7f98b8;
}
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
}
.stat {
  --c: #4fc3f7;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  border-radius: 9px;
  background: color-mix(in srgb, var(--c) 7%, rgba(9, 16, 34, 0.6));
  border: 1px solid color-mix(in srgb, var(--c) 28%, transparent);
}
.stat b {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.15;
  color: color-mix(in srgb, var(--c) 40%, #fff);
  font-variant-numeric: tabular-nums;
}
.stat b small {
  margin-left: 4px;
  font-size: 11.5px;
  font-weight: 400;
  color: #7f98b8;
}
.analysis {
  --c: #4dd984;
  margin: 0;
  padding: 10px 16px;
  border-radius: 0 9px 9px 0;
  background: linear-gradient(90deg, color-mix(in srgb, var(--c) 11%, transparent), transparent);
  border-left: 3px solid var(--c);
}
.analysis p {
  margin: 4px 0 0;
  font-size: 13.5px;
  line-height: 1.75;
  color: #d6e4ff;
}
.rel {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.rel__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 12px;
  font: inherit;
  text-align: left;
  color: #cfe0fa;
  border-radius: 8px;
  cursor: pointer;
  background: rgba(9, 16, 34, 0.5);
  border: 1px solid rgba(64, 120, 180, 0.25);
  transition: all 0.15s;
}
.rel__item b {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 500;
}
.rel__item:hover {
  border-color: rgba(79, 195, 247, 0.5);
  background: rgba(79, 195, 247, 0.08);
}
</style>

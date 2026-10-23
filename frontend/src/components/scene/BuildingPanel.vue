<script setup lang="ts">
// 建筑信息面板：基础属性 + 沉降监测（GET /api/buildings/{id}）曲线与研判结论 + 关联事件
import { computed, ref, shallowRef, watch } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import { getBuilding } from '@/api/geo'
import type { Building, BuildingDetail } from '@/types/building'
import { RISK_LEVEL_META } from '@/types/building'
import { EVENT_STATUS_LABEL, EVENT_TYPE_META } from '@/types/event'
import { fixed, thousands } from '@/utils/format'
import { rgba } from '@/utils/color'

const props = defineProps<{ building: Building }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'open-event', id: string): void; (e: 'locate', id: string): void }>()

const CATEGORY: Record<string, string> = {
  residential: '住宅',
  commercial: '商业',
  office: '办公',
  public: '公共建筑',
  industrial: '工业',
  other: '其他'
}
const HEIGHT_SOURCE: Record<string, string> = { osm: 'OSM 实测', levels: '楼层推算', estimated: '面积估算' }

const detail = shallowRef<BuildingDetail | null>(null)
const loading = ref(false)
const error = ref('')

async function load() {
  const id = props.building.id
  loading.value = true
  error.value = ''
  detail.value = null
  try {
    const d = await getBuilding(id)
    if (id === props.building.id) detail.value = d
  } catch (e) {
    if (id === props.building.id) error.value = (e as Error)?.message || '加载失败'
  } finally {
    if (id === props.building.id) loading.value = false
  }
}
watch(() => props.building.id, load, { immediate: true })

const b = computed<Building>(() => ({ ...props.building, ...(detail.value?.properties ?? {}) }))
const monitoring = computed(() => detail.value?.monitoring ?? null)
const risk = computed(() => RISK_LEVEL_META[monitoring.value?.risk_level ?? b.value.risk_level ?? 'normal'] ?? RISK_LEVEL_META.normal)
const relatedEvents = computed(() => (detail.value?.events ?? []).slice(0, 4))

const chartOption = computed(() => {
  const series = monitoring.value?.series ?? []
  const color = risk.value.color
  return {
    grid: { left: 40, right: 12, top: 18, bottom: 22 },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v: number) => `${Number(v).toFixed(2)} mm`
    },
    xAxis: {
      type: 'category',
      data: series.map((p) => p.date.slice(5)),
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(79,195,247,0.25)' } },
      axisTick: { show: false },
      axisLabel: { color: '#6f87a8', fontSize: 10, hideOverlap: true }
    },
    yAxis: {
      type: 'value',
      name: 'mm',
      nameTextStyle: { color: '#6f87a8', fontSize: 10, padding: [0, 0, 0, -20] },
      splitNumber: 3,
      axisLabel: { color: '#6f87a8', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(79,195,247,0.08)' } }
    },
    series: [
      {
        name: '累计位移',
        type: 'line',
        data: series.map((p) => p.displacement_mm),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color },
        itemStyle: { color },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(79,195,247,0.02)' },
              { offset: 1, color: rgba(color, 0.35) }
            ]
          }
        },
        markLine: {
          symbol: 'none',
          silent: true,
          lineStyle: { color: 'rgba(214,228,255,0.25)', type: 'dashed' },
          label: { show: false },
          data: [{ yAxis: 0 }]
        }
      }
    ]
  }
})
</script>

<template>
  <section class="building-panel ce-panel" :style="{ '--risk-color': risk.color }">
    <header class="bp-head">
      <div class="bp-icon">🏢</div>
      <div class="bp-title">
        <h3 :title="b.name">{{ b.name }}</h3>
        <p>
          <span class="ce-num">{{ b.id }}</span>
          <span class="sep">·</span>{{ CATEGORY[b.category ?? 'other'] ?? '其他' }}
          <template v-if="b.district"><span class="sep">·</span>{{ b.district }}</template>
        </p>
      </div>
      <button class="bp-close" title="关闭" @click="emit('close')">×</button>
    </header>

    <div class="bp-body">
      <div class="bp-hero">
        <div class="bp-hero__item">
          <span class="bp-hero__v ce-num">{{ fixed(b.height, 0) }}<small>m</small></span>
          <span class="bp-hero__k">建筑高度</span>
        </div>
        <div class="bp-hero__item">
          <span class="bp-hero__v ce-num">{{ b.levels ?? '—' }}<small v-if="b.levels">层</small></span>
          <span class="bp-hero__k">楼层数</span>
        </div>
        <div class="bp-hero__item">
          <span class="bp-hero__v ce-num">{{ b.area_m2 ? thousands(Math.round(b.area_m2)) : '—' }}<small v-if="b.area_m2">m²</small></span>
          <span class="bp-hero__k">占地面积</span>
        </div>
      </div>

      <dl class="bp-grid">
        <div><dt>高度来源</dt><dd>{{ HEIGHT_SOURCE[b.height_source ?? 'estimated'] ?? '—' }}</dd></div>
        <div><dt>网格编号</dt><dd class="ce-num">{{ b.grid || '—' }}</dd></div>
        <div><dt>建筑类别</dt><dd>{{ CATEGORY[b.category ?? 'other'] ?? '其他' }}</dd></div>
        <div>
          <dt>坐标</dt>
          <dd class="ce-num">{{ Number.isFinite(b.longitude) ? b.longitude.toFixed(4) : '—' }}, {{ Number.isFinite(b.latitude) ? b.latitude.toFixed(4) : '—' }}</dd>
        </div>
      </dl>

      <div class="bp-monitor">
        <div class="bp-sub">
          <span>沉降监测</span>
          <span v-if="b.monitored || monitoring" class="ce-tag" :style="{ color: risk.color }">
            <i class="ce-dot" :class="{ 'ce-dot--pulse': risk.label !== '正常' }" />{{ risk.label }}
          </span>
          <span v-else class="ce-tag bp-off">未接入</span>
        </div>
        <div v-if="loading" class="bp-skeleton">
          <i /><i /><i />
        </div>
        <template v-else-if="monitoring">
          <div class="bp-stats">
            <div>
              <b class="ce-num">{{ fixed(monitoring.cumulative_mm, 1) }}</b><small>mm</small>
              <span>累计沉降</span>
            </div>
            <div>
              <b class="ce-num">{{ fixed(monitoring.rate_mm_per_month, 2) }}</b><small>mm/月</small>
              <span>沉降速率</span>
            </div>
            <div>
              <b class="ce-num">{{ fixed(monitoring.acceleration, 2) }}</b>
              <span>加速度</span>
            </div>
          </div>
          <EChart v-if="monitoring.series?.length" :option="chartOption" class="bp-chart" />
          <p v-if="monitoring.analysis" class="bp-analysis">{{ monitoring.analysis }}</p>
        </template>
        <p v-else-if="error" class="bp-empty">监测数据加载失败：{{ error }}</p>
        <p v-else class="bp-empty">该建筑暂未接入沉降监测，可在"AI 分析"中上传沉降时序 CSV 进行分析。</p>
      </div>

      <div v-if="relatedEvents.length" class="bp-events">
        <div class="bp-sub"><span>关联事件</span></div>
        <button v-for="e in relatedEvents" :key="e.id" class="bp-event" @click="emit('open-event', e.id)">
          <span class="bp-event__icon" :style="{ color: EVENT_TYPE_META[e.event_type]?.color }">{{ EVENT_TYPE_META[e.event_type]?.icon }}</span>
          <span class="bp-event__name">{{ e.name }}</span>
          <span class="bp-event__status">{{ EVENT_STATUS_LABEL[e.status] }}</span>
        </button>
      </div>
    </div>

    <footer class="bp-actions">
      <button class="bp-btn" @click="emit('locate', b.id)">定位建筑</button>
    </footer>
  </section>
</template>

<style scoped>
.building-panel {
  width: 100%;
  max-height: 100%;
  overflow: hidden;
  border-top: 2px solid var(--risk-color);
}
.bp-head {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 12px 10px;
  border-bottom: 1px solid var(--ce-divider);
  background: linear-gradient(90deg, rgba(79, 195, 247, 0.14), transparent 70%);
}
.bp-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 6px;
  font-size: 19px;
  background: linear-gradient(160deg, #1f6fc0, #0b2a55);
  box-shadow:
    0 0 0 1px rgba(79, 195, 247, 0.5),
    0 0 14px rgba(79, 195, 247, 0.35);
}
.bp-title {
  flex: 1;
  min-width: 0;
}
.bp-title h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--ce-text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bp-title p {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--ce-text-dim);
}
.sep {
  margin: 0 5px;
  color: var(--ce-text-faint);
}
.bp-close {
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
.bp-close:hover {
  color: #fff;
  border-color: var(--ce-panel-border);
  background: rgba(79, 195, 247, 0.1);
}
.bp-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bp-hero {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}
.bp-hero__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 4px;
  border: 1px solid var(--ce-divider);
  border-radius: 3px;
  background: linear-gradient(180deg, rgba(79, 195, 247, 0.1), rgba(79, 195, 247, 0.02));
}
.bp-hero__v {
  font-size: 20px;
  font-weight: 700;
  color: var(--ce-text-strong);
  text-shadow: 0 0 10px rgba(79, 195, 247, 0.35);
}
.bp-hero__v small {
  margin-left: 2px;
  font-size: 11px;
  font-weight: 400;
  color: var(--ce-text-dim);
}
.bp-hero__k {
  font-size: 11px;
  color: var(--ce-text-dim);
}
.bp-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 12px;
  margin: 0;
}
.bp-grid dt {
  font-size: 11px;
  color: var(--ce-text-faint);
  letter-spacing: 1px;
}
.bp-grid dd {
  margin: 0;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bp-sub {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ce-text-dim);
  letter-spacing: 1px;
}
.bp-off {
  color: var(--ce-text-faint);
}
.bp-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-bottom: 6px;
}
.bp-stats > div {
  display: flex;
  flex-direction: column;
  padding: 6px 8px;
  border-left: 2px solid var(--risk-color);
  background: rgba(79, 195, 247, 0.04);
}
.bp-stats b {
  font-size: 17px;
  color: var(--ce-text-strong);
}
.bp-stats small {
  font-size: 10px;
  color: var(--ce-text-dim);
}
.bp-stats span {
  font-size: 11px;
  color: var(--ce-text-dim);
}
.bp-chart {
  height: 150px;
}
.bp-analysis {
  margin: 6px 0 0;
  padding: 8px 10px;
  font-size: 12.5px;
  line-height: 1.6;
  color: #c3d6f2;
  border-left: 2px solid var(--risk-color);
  background: color-mix(in srgb, var(--risk-color) 8%, transparent);
}
.bp-empty {
  margin: 0;
  font-size: 12px;
  color: var(--ce-text-faint);
}
.bp-skeleton {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bp-skeleton i {
  height: 14px;
  border-radius: 2px;
  background: linear-gradient(90deg, rgba(79, 195, 247, 0.05), rgba(79, 195, 247, 0.15), rgba(79, 195, 247, 0.05));
  background-size: 200% 100%;
  animation: bp-shimmer 1.2s linear infinite;
}
.bp-skeleton i:nth-child(2) {
  width: 80%;
}
.bp-skeleton i:nth-child(3) {
  width: 60%;
}
@keyframes bp-shimmer {
  to {
    background-position: -200% 0;
  }
}
.bp-events {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.bp-event {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--ce-divider);
  border-radius: 3px;
  background: rgba(79, 195, 247, 0.03);
  color: var(--ce-text);
  font-size: 12.5px;
  text-align: left;
  cursor: pointer;
}
.bp-event:hover {
  border-color: var(--ce-panel-border-strong);
  background: rgba(79, 195, 247, 0.1);
}
.bp-event__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bp-event__status {
  color: var(--ce-text-dim);
  font-size: 11px;
}
.bp-actions {
  flex: none;
  display: flex;
  justify-content: flex-end;
  padding: 8px 12px;
  border-top: 1px solid var(--ce-divider);
  background: rgba(3, 8, 18, 0.35);
}
.bp-btn {
  height: 28px;
  padding: 0 12px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 3px;
  background: rgba(79, 195, 247, 0.06);
  color: var(--ce-text);
  font-size: 12.5px;
  cursor: pointer;
}
.bp-btn:hover {
  border-color: var(--ce-accent);
  color: #fff;
  background: rgba(79, 195, 247, 0.16);
}
</style>

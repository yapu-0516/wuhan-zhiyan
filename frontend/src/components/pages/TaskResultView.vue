<script setup lang="ts">
// 分析结果视图：结论横幅 / 标注图与原图对比 / 检测目标 / 指标 / 时序图 / 关联事件
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Document, Download, Picture as PictureIcon, Position, Tickets } from '@element-plus/icons-vue'
import { fileUrl } from '@/config/api'
import { useCityEvents } from '@/composables/useCityEvents'
import { describeMetrics } from '@/composables/pages/metrics'
import { detectionLabel, typeMeta } from '@/composables/pages/aiMeta'
import { fmtDuration, isImageUrl, parseTs, pct100 } from '@/composables/pages/format'
import { EVENT_STATUS_COLOR, EVENT_STATUS_LABEL, EVENT_TYPE_META, SEVERITY_META } from '@/types/event'
import type { AnalysisTask, Detection } from '@/types/api'
import TaskSeriesChart from './TaskSeriesChart.vue'

const props = defineProps<{ task: AnalysisTask }>()

const router = useRouter()
const { getEventById } = useCityEvents()

const result = computed(() => props.task.result ?? null)
const meta = computed(() => typeMeta(props.task.type))
const color = computed(() => meta.value?.color ?? '#4fc3f7')
const detected = computed(() => !!result.value?.detected)
const verdictColor = computed(() => (detected.value ? '#ff6b6b' : '#4dd984'))
const confPct = computed(() => pct100(result.value?.confidence))
const metrics = computed(() => describeMetrics(result.value?.metrics))
const detections = computed<Detection[]>(() => result.value?.detections ?? [])

// ---------- 图像 ----------
const annotated = computed(() =>
  (result.value?.artifacts ?? [])
    .filter((a) => a.kind !== 'json' && isImageUrl(a.url))
    .map((a) => ({ name: a.name, url: fileUrl(a.url) }))
)
const originals = computed(() =>
  (props.task.inputs ?? []).filter((i) => isImageUrl(i.url)).map((i) => ({ name: i.name, url: fileUrl(i.url) }))
)
const jsonArtifacts = computed(() => (result.value?.artifacts ?? []).filter((a) => a.kind === 'json' || !isImageUrl(a.url)))
const activeAnn = ref(0)
watch(
  () => props.task.id,
  () => (activeAnn.value = 0)
)
const previewList = computed(() => [...annotated.value.map((a) => a.url), ...originals.value.map((o) => o.url)])
const mainAnnotated = computed(() => annotated.value[Math.min(activeAnn.value, annotated.value.length - 1)])

// 无算法标注图时，在原图上叠加检测框（来自 result.detections.bbox）
const overlayOnOriginal = computed(() => !annotated.value.length && originals.value.length > 0 && detections.value.length > 0)
const natural = ref<{ w: number; h: number } | null>(null)
function onOriginalLoad(ev: Event) {
  const img = ev.target as HTMLImageElement
  natural.value = { w: img.naturalWidth, h: img.naturalHeight }
}
watch(
  () => props.task.id,
  () => (natural.value = null)
)

const hasMedia = computed(() => annotated.value.length > 0 || originals.value.length > 0)

// ---------- 元信息 ----------
const timeCost = computed(() => {
  const m = result.value?.metrics?.elapsed_ms
  if (typeof m === 'number') return fmtDuration(m)
  const a = parseTs(props.task.createdAt)
  const b = parseTs(props.task.finished_at)
  return a && b ? fmtDuration(b.getTime() - a.getTime()) : '—'
})

const eventCards = computed(() =>
  (result.value?.event_ids ?? []).map((id) => ({ id, event: getEventById(id) }))
)

function gotoScene(id: string) {
  void router.push({ path: '/dashboard', query: { eventId: id } })
}
function gotoEvent(id: string) {
  void router.push({ path: '/event-center', query: { id } })
}
</script>

<template>
  <section v-if="result" class="res cp-panel" :style="{ '--c': color, '--v': verdictColor }">
    <!-- 结论横幅 -->
    <header class="verdict">
      <div class="verdict__icon">{{ detected ? '⚠️' : '✅' }}</div>
      <div class="verdict__main">
        <h3>{{ detected ? '检测到异常' : '未发现异常' }}<small>{{ meta?.label }}</small></h3>
        <p>{{ result.summary || (detected ? '算法判定存在异常，请结合现场核查。' : '算法未发现需要关注的异常。') }}</p>
        <div class="verdict__meta">
          <span class="cp-mono">{{ task.id }}</span>
          <span v-if="task.algorithm">{{ task.algorithm.name }} v{{ task.algorithm.version }}</span>
          <span v-if="task.finished_at">完成于 {{ task.finished_at }}</span>
          <span>耗时 {{ timeCost }}</span>
          <span v-if="task.location">位置 {{ task.location.longitude.toFixed(4) }}, {{ task.location.latitude.toFixed(4) }}</span>
        </div>
      </div>
      <div class="ring" :style="{ '--p': confPct }">
        <div class="ring__in">
          <b>{{ confPct }}<small>%</small></b>
          <span>置信度</span>
        </div>
      </div>
    </header>

    <div class="res__body" :class="{ 'res__body--nomedia': !hasMedia }">
      <!-- 影像对比 -->
      <div v-if="hasMedia" class="media" :class="{ 'media--solo': !(annotated.length && originals.length) }">
        <figure v-if="annotated.length" class="media__main">
          <figcaption><span class="tag tag--hot">算法标注</span>{{ mainAnnotated?.name }}</figcaption>
          <el-image
            :src="mainAnnotated?.url"
            :preview-src-list="previewList"
            :initial-index="activeAnn"
            fit="contain"
            preview-teleported
            hide-on-click-modal
            class="media__img"
          >
            <template #error><div class="media__err"><el-icon><PictureIcon /></el-icon>标注图加载失败</div></template>
          </el-image>
          <div v-if="annotated.length > 1" class="media__thumbs">
            <button
              v-for="(a, i) in annotated"
              :key="a.url"
              type="button"
              :class="{ 'is-on': i === activeAnn }"
              @click="activeAnn = i"
            >
              <img :src="a.url" :alt="a.name" loading="lazy" />
            </button>
          </div>
        </figure>

        <div v-if="originals.length" class="media__orig">
          <figure v-for="(o, i) in originals" :key="o.url + i">
            <figcaption>
              <span class="tag">{{ originals.length > 1 ? (i === 0 ? '前时相' : i === 1 ? '后时相' : `原图 ${i + 1}`) : '原始输入' }}</span>
              {{ o.name }}
            </figcaption>
            <div v-if="overlayOnOriginal && i === 0" class="ov">
              <img :src="o.url" :alt="o.name" @load="onOriginalLoad" />
              <svg v-if="natural" class="ov__svg" :viewBox="`0 0 ${natural.w} ${natural.h}`" preserveAspectRatio="none">
                <g v-for="(d, j) in detections" :key="j">
                  <rect :x="d.bbox[0]" :y="d.bbox[1]" :width="d.bbox[2]" :height="d.bbox[3]" fill="none" :stroke="verdictColor" stroke-width="3" vector-effect="non-scaling-stroke" />
                </g>
              </svg>
            </div>
            <el-image
              v-else
              :src="o.url"
              :preview-src-list="previewList"
              :initial-index="annotated.length + i"
              fit="cover"
              preview-teleported
              hide-on-click-modal
              class="media__thumb"
            >
              <template #error><div class="media__err"><el-icon><PictureIcon /></el-icon>原图不可用</div></template>
            </el-image>
          </figure>
          <p v-if="overlayOnOriginal" class="media__note">未返回标注图，已按检测框坐标在原图上叠加标注。</p>
        </div>
      </div>

      <!-- 检测目标 + 指标 -->
      <div class="side">
        <div v-if="detections.length" class="blk">
          <h4 class="blk__t"><el-icon><Tickets /></el-icon>检测目标<em>{{ detections.length }}</em></h4>
          <table class="dt">
            <thead>
              <tr><th>#</th><th>目标</th><th>置信度</th><th>位置 x, y, 宽×高 (px)</th></tr>
            </thead>
            <tbody>
              <tr v-for="(d, i) in detections" :key="i">
                <td class="cp-mono">{{ i + 1 }}</td>
                <td><b>{{ detectionLabel(d.label) }}</b><small v-if="d.area_ratio !== undefined">占 {{ (d.area_ratio * 100).toFixed(2) }}%</small></td>
                <td>
                  <span class="dt__conf"><span class="cp-bar"><i :style="{ width: `${pct100(d.confidence)}%` }"></i></span>{{ pct100(d.confidence) }}%</span>
                </td>
                <td class="cp-mono">{{ d.bbox[0] }}, {{ d.bbox[1] }}, {{ d.bbox[2] }}×{{ d.bbox[3] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="blk blk--empty">
          <h4 class="blk__t"><el-icon><Tickets /></el-icon>检测目标</h4>
          <p>{{ detected ? '该分析类型不输出目标框（时序 / 指标类判定）。' : '未检出目标。' }}</p>
        </div>

        <div v-if="metrics.length" class="blk">
          <h4 class="blk__t"><el-icon><Document /></el-icon>算法指标</h4>
          <div class="metrics">
            <el-tooltip v-for="m in metrics" :key="m.key" :disabled="!m.hint" :content="m.hint" placement="top" popper-class="cp-popper">
              <div class="metric">
                <span class="metric__l">{{ m.label }}</span>
                <span class="metric__v">{{ m.value }}<small>{{ m.unit }}</small></span>
              </div>
            </el-tooltip>
          </div>
        </div>

        <div v-if="jsonArtifacts.length" class="blk">
          <h4 class="blk__t"><el-icon><Download /></el-icon>其他产物</h4>
          <div class="files">
            <a v-for="a in jsonArtifacts" :key="a.url" :href="fileUrl(a.url)" target="_blank" rel="noopener" class="files__a">
              <el-icon><Document /></el-icon>{{ a.name }}
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- 时序图 -->
    <div v-if="result.series?.length" class="chart">
      <h4 class="blk__t">时序分析曲线<em>{{ result.series.length }} 个采样点</em></h4>
      <TaskSeriesChart :series="result.series" :type="task.type" :metrics="result.metrics ?? {}" />
    </div>

    <!-- 关联事件 -->
    <div v-if="eventCards.length" class="events">
      <h4 class="blk__t"><el-icon><Position /></el-icon>由本次分析生成的事件<em>{{ eventCards.length }}</em></h4>
      <div class="events__list">
        <div v-for="c in eventCards" :key="c.id" class="ev" :style="{ '--ec': c.event ? EVENT_TYPE_META[c.event.event_type].color : '#4fc3f7' }">
          <span class="ev__icon">{{ c.event ? EVENT_TYPE_META[c.event.event_type].icon : '📍' }}</span>
          <div class="ev__txt">
            <b>{{ c.event?.name ?? '事件详情加载中' }}</b>
            <span class="ev__sub">
              <span class="cp-mono">{{ c.id }}</span>
              <template v-if="c.event">
                <span class="cp-pill cp-pill--sm" :style="{ '--c': SEVERITY_META[c.event.severity].color }">{{ SEVERITY_META[c.event.severity].label }}</span>
                <span class="cp-pill cp-pill--sm" :style="{ '--c': EVENT_STATUS_COLOR[c.event.status] }">{{ EVENT_STATUS_LABEL[c.event.status] }}</span>
              </template>
            </span>
          </div>
          <el-button size="small" type="primary" plain @click="gotoScene(c.id)">在三维场景中查看</el-button>
          <el-button size="small" @click="gotoEvent(c.id)">事件中心</el-button>
        </div>
      </div>
    </div>
    <p v-else-if="detected" class="noevent">本次分析未关联事件（可能已关闭「自动生成事件」）。</p>
  </section>
  <section v-else class="res cp-panel res--empty">
    <el-empty :image-size="80" description="该任务没有返回分析结果" />
  </section>
</template>

<style scoped>
.res {
  --c: #4fc3f7;
  --v: #4dd984;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.res--empty {
  padding: 24px;
}
.verdict {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 18px 22px;
  background:
    radial-gradient(520px 160px at 0% 0%, color-mix(in srgb, var(--v) 22%, transparent), transparent 70%),
    linear-gradient(90deg, color-mix(in srgb, var(--v) 9%, transparent), transparent 60%);
  border-bottom: 1px solid color-mix(in srgb, var(--v) 35%, transparent);
}
.verdict__icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  font-size: 28px;
  border-radius: 16px;
  background: color-mix(in srgb, var(--v) 16%, rgba(9, 16, 34, 0.85));
  border: 1px solid color-mix(in srgb, var(--v) 60%, transparent);
  box-shadow: 0 0 26px color-mix(in srgb, var(--v) 35%, transparent);
}
.verdict__main {
  flex: 1;
  min-width: 0;
}
.verdict__main h3 {
  margin: 0 0 4px;
  display: flex;
  align-items: baseline;
  gap: 12px;
  font-size: 20px;
  letter-spacing: 2px;
  color: var(--v);
  text-shadow: 0 0 18px color-mix(in srgb, var(--v) 45%, transparent);
}
.verdict__main h3 small {
  font-size: 12px;
  font-weight: 400;
  letter-spacing: 1px;
  color: #8aa3c4;
  text-shadow: none;
}
.verdict__main p {
  margin: 0 0 8px;
  font-size: 13.5px;
  line-height: 1.7;
  color: #cfe0fa;
}
.verdict__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  font-size: 12px;
  color: #7f98b8;
}
.ring {
  --p: 0;
  flex: none;
  display: grid;
  place-items: center;
  width: 86px;
  height: 86px;
  border-radius: 50%;
  background: conic-gradient(var(--v) calc(var(--p) * 1%), rgba(120, 160, 210, 0.16) 0);
  box-shadow: 0 0 22px color-mix(in srgb, var(--v) 25%, transparent);
}
.ring__in {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: #0c1630;
}
.ring__in b {
  font-size: 22px;
  line-height: 1.1;
  color: #fff;
  font-variant-numeric: tabular-nums;
}
.ring__in b small {
  font-size: 11px;
  margin-left: 1px;
  color: #8aa3c4;
}
.ring__in span {
  font-size: 10.5px;
  letter-spacing: 1px;
  color: #6f89aa;
}
.res__body {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 18px;
  padding: 18px 22px;
}
.res__body--nomedia {
  grid-template-columns: 1fr;
}
@media (max-width: 1250px) {
  .res__body {
    grid-template-columns: 1fr;
  }
}
.media {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 12px;
  align-content: start;
}
.media--solo {
  grid-template-columns: 1fr;
}
.media figure {
  margin: 0;
}
.media figcaption {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #8aa3c4;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.tag {
  flex: none;
  padding: 0 7px;
  line-height: 18px;
  font-size: 11px;
  border-radius: 4px;
  color: #a9cdf0;
  background: rgba(79, 195, 247, 0.1);
  border: 1px solid rgba(79, 195, 247, 0.32);
}
.tag--hot {
  color: var(--v);
  background: color-mix(in srgb, var(--v) 12%, transparent);
  border-color: color-mix(in srgb, var(--v) 45%, transparent);
}
.media__img {
  width: 100%;
  height: 340px;
  border-radius: 9px;
  border: 1px solid color-mix(in srgb, var(--c) 40%, transparent);
  background: #050912;
  cursor: zoom-in;
}
.media__thumb {
  width: 100%;
  height: 150px;
  border-radius: 8px;
  border: 1px solid rgba(64, 120, 180, 0.3);
  background: #050912;
}
.media__orig {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.media__err {
  display: flex;
  height: 100%;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12.5px;
  color: #5d748f;
}
.media__thumbs {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.media__thumbs button {
  width: 64px;
  height: 46px;
  padding: 0;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  background: #050912;
  opacity: 0.65;
}
.media__thumbs button.is-on {
  border-color: var(--c);
  opacity: 1;
}
.media__thumbs img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.media__note {
  margin: 0;
  font-size: 12px;
  color: #6f89aa;
}
.ov {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(64, 120, 180, 0.3);
}
.ov img {
  display: block;
  width: 100%;
}
.ov__svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.side {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.blk__t {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #8fb0d3;
}
.blk__t em {
  font-style: normal;
  font-weight: 400;
  letter-spacing: 0.5px;
  padding: 0 7px;
  line-height: 17px;
  border-radius: 9px;
  color: #a9cdf0;
  background: rgba(79, 195, 247, 0.12);
}
.blk--empty p {
  margin: 0;
  font-size: 13px;
  color: #6f89aa;
}
.dt {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}
.dt th {
  padding: 6px 8px;
  text-align: left;
  font-weight: 500;
  font-size: 11.5px;
  letter-spacing: 0.8px;
  color: #6f89aa;
  border-bottom: 1px solid rgba(64, 120, 180, 0.22);
}
.dt td {
  padding: 8px;
  color: #cfe0fa;
  border-bottom: 1px solid rgba(64, 120, 180, 0.12);
}
.dt td small {
  margin-left: 8px;
  color: #6f89aa;
}
.dt__conf {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dt__conf .cp-bar {
  flex: 1;
  min-width: 48px;
  --c: var(--v);
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
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
.files {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.files__a {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: 12.5px;
  border-radius: 6px;
  color: var(--ce-accent, #4fc3f7);
  text-decoration: none;
  border: 1px solid rgba(79, 195, 247, 0.32);
}
.files__a:hover {
  background: rgba(79, 195, 247, 0.1);
}
.chart,
.events {
  padding: 4px 22px 18px;
}
.chart {
  border-top: 1px dashed rgba(64, 120, 180, 0.22);
  padding-top: 16px;
}
.events {
  border-top: 1px dashed rgba(64, 120, 180, 0.22);
  padding-top: 16px;
}
.events__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ev {
  --ec: #4fc3f7;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 9px;
  background: color-mix(in srgb, var(--ec) 7%, rgba(9, 16, 34, 0.6));
  border: 1px solid color-mix(in srgb, var(--ec) 35%, transparent);
}
.ev__icon {
  font-size: 22px;
}
.ev__txt {
  flex: 1;
  min-width: 180px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ev__txt b {
  font-size: 14px;
  color: #eaf2ff;
}
.ev__sub {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #8aa3c4;
}
.noevent {
  margin: 0;
  padding: 0 22px 18px;
  font-size: 12.5px;
  color: #6f89aa;
}
</style>

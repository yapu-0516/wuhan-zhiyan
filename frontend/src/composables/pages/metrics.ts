// 算法指标 → 中文标签 / 单位 / 展示值
// 事件 metrics 与 AI 任务 result.metrics 共用；权威字典见 @/config/metrics，
// 未登记的键按后缀推断单位，仍无法识别则显示原始键名。
import { METRIC_DEFS, METRIC_VALUE_LABEL, type MetricDef } from '@/config/metrics'

export interface MetricView {
  key: string
  label: string
  /** 已格式化的数值文本（不含单位） */
  value: string
  unit: string
  /** 是否为已识别的指标（未识别时 label 即原始 key） */
  known: boolean
  hint?: string
  /** 原始值 */
  raw: number | string
}

const DEFS: Record<string, MetricDef> = {
  // —— 火灾识别
  flame_area_ratio: { label: '火焰面积占比', ratio: true, digits: 2, hint: '火焰像素占整幅画面的比例' },
  smoke_score: { label: '烟雾特征得分', digits: 2, hint: '0~1，越高越接近烟雾特征' },
  flame_pixels: { label: '火焰像素数', unit: 'px', digits: 0 },
  hotspot_count: { label: '火点数量', unit: '处', digits: 0 },
  region_count: { label: '检测区域数', unit: '个', digits: 0 },
  max_region_ratio: { label: '最大区域占比', ratio: true, digits: 2 },
  flame_intensity: { label: '火焰亮度强度', digits: 2 },
  // —— 交通
  avg_speed: { label: '平均车速', unit: 'km/h', digits: 1 },
  mean_speed: { label: '平均车速', unit: 'km/h', digits: 1 },
  min_speed: { label: '最低车速', unit: 'km/h', digits: 1 },
  max_speed: { label: '最高车速', unit: 'km/h', digits: 1 },
  speed: { label: '实时车速', unit: 'km/h', digits: 1 },
  free_flow_speed: { label: '自由流车速', unit: 'km/h', digits: 1 },
  speed_limit: { label: '限速', unit: 'km/h', digits: 0 },
  speed_drop_ratio: { label: '车速降幅', ratio: true, digits: 1 },
  congestion_ratio: { label: '拥堵时段占比', ratio: true, digits: 1 },
  congestion_minutes: { label: '拥堵持续时长', unit: '分钟', digits: 0 },
  congestion_duration_min: { label: '拥堵持续时长', unit: '分钟', digits: 0 },
  tpi: { label: '交通运行指数 TPI', digits: 1, hint: '0~10，越高越拥堵' },
  peak_tpi: { label: '峰值 TPI', digits: 1 },
  avg_flow: { label: '平均流量', unit: '辆/h', digits: 0 },
  peak_flow: { label: '峰值流量', unit: '辆/h', digits: 0 },
  flow: { label: '流量', unit: '辆/h', digits: 0 },
  occupancy: { label: '车道占有率', ratio: true, digits: 1 },
  occupancy_ratio: { label: '车道占有率', ratio: true, digits: 1 },
  vehicle_count: { label: '车辆数', unit: '辆', digits: 0 },
  vehicle_area_ratio: { label: '车辆面积占比', ratio: true, digits: 1 },
  // —— 建筑异常
  change_ratio: { label: '变化区域占比', ratio: true, digits: 2 },
  changed_pixels: { label: '变化像素数', unit: 'px', digits: 0 },
  change_regions: { label: '变化区域数', unit: '处', digits: 0 },
  ssim: { label: '结构相似度 SSIM', digits: 3, hint: '越接近 1 表示前后时相越一致' },
  rate_mm_per_month: { label: '沉降速率', unit: 'mm/月', digits: 2 },
  cumulative_mm: { label: '累计沉降量', unit: 'mm', digits: 1 },
  max_displacement_mm: { label: '最大位移', unit: 'mm', digits: 1 },
  displacement_mm: { label: '位移', unit: 'mm', digits: 1 },
  acceleration: { label: '沉降加速度', unit: 'mm/月²', digits: 2 },
  // —— 内涝积水
  water_area_ratio: { label: '积水面积占比', ratio: true, digits: 2 },
  water_level_cm: { label: '水位', unit: 'cm', digits: 1 },
  max_water_level_cm: { label: '最高水位', unit: 'cm', digits: 1 },
  peak_water_level_cm: { label: '峰值水位', unit: 'cm', digits: 1 },
  rainfall_mm: { label: '降雨量', unit: 'mm', digits: 1 },
  total_rainfall_mm: { label: '累计降雨量', unit: 'mm', digits: 1 },
  rise_rate_cm_per_h: { label: '水位上涨速率', unit: 'cm/h', digits: 1 },
  ponding_area_m2: { label: '积水面积', unit: '㎡', digits: 0 },
  // —— 通用
  elapsed_ms: { label: '算法耗时', unit: 'ms', digits: 0 },
  samples: { label: '样本点数', unit: '个', digits: 0 },
  sample_count: { label: '样本点数', unit: '个', digits: 0 },
  warning_threshold: { label: '预警阈值', digits: 1 },
  alert_threshold: { label: '报警阈值', digits: 1 },
  threshold: { label: '判定阈值', digits: 1 },
  // —— 以算法实际输出的键为准（覆盖上方同名兜底项）
  ...METRIC_DEFS
}

/** 后缀推断：键名以这些后缀结尾时自动带单位 */
const SUFFIX_UNITS: [RegExp, { unit: string; ratio?: boolean; digits?: number }][] = [
  [/_ratio$|_pct$|_percent$/, { unit: '', ratio: true, digits: 1 }],
  [/_per_month$/, { unit: '/月', digits: 2 }],
  [/_mm$/, { unit: 'mm', digits: 1 }],
  [/_cm$/, { unit: 'cm', digits: 1 }],
  [/_ms$/, { unit: 'ms', digits: 0 }],
  [/_kmh$|_km_h$/, { unit: 'km/h', digits: 1 }],
  [/_min$|_minutes$/, { unit: '分钟', digits: 0 }],
  [/_sec$|_seconds$/, { unit: '秒', digits: 0 }],
  [/_m2$/, { unit: '㎡', digits: 0 }],
  [/_m$/, { unit: 'm', digits: 1 }],
  [/_count$/, { unit: '个', digits: 0 }]
]

function fmt(n: number, digits: number): string {
  if (!Number.isFinite(n)) return '—'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: digits })
}

/** 把单个指标转换为展示用结构 */
export function describeMetric(key: string, value: number | string): MetricView {
  const def = DEFS[key]
  const num = typeof value === 'number' ? value : Number(value)
  const isNum = typeof value === 'number' || (value !== '' && Number.isFinite(num))
  if (def) {
    if (!isNum) return { key, label: def.label, value: METRIC_VALUE_LABEL[String(value)] ?? String(value), unit: '', known: true, hint: def.hint, raw: value }
    const shown = def.ratio ? num * 100 : num
    const digits = def.ratio && Math.abs(shown) > 0 && Math.abs(shown) < 1 ? Math.max(def.digits ?? 1, 2) : (def.digits ?? 1)
    return {
      key,
      label: def.label,
      value: fmt(shown, digits),
      unit: def.ratio ? '%' : (def.unit ?? ''),
      known: true,
      hint: def.hint,
      raw: value
    }
  }
  for (const [re, s] of SUFFIX_UNITS) {
    if (re.test(key)) {
      if (!isNum) break
      const shown = s.ratio ? num * 100 : num
      return { key, label: key, value: fmt(shown, s.digits ?? 1), unit: s.ratio ? '%' : s.unit, known: false, raw: value }
    }
  }
  return { key, label: key, value: isNum ? fmt(num, 2) : String(value), unit: '', known: false, raw: value }
}

/** 批量转换；耗时类指标排在最后 */
export function describeMetrics(metrics?: Record<string, number | string> | null): MetricView[] {
  if (!metrics) return []
  const list = Object.entries(metrics)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => describeMetric(k, v))
  return list.sort((a, b) => Number(a.key === 'elapsed_ms') - Number(b.key === 'elapsed_ms'))
}

/** 是否为"阈值"类指标（用于时序图 markLine） */
export function isThresholdKey(key: string): boolean {
  return /threshold|warn(ing)?_level|alert_level|alarm_level/i.test(key)
}

/** 时序图中额外数值列的中文名（t / v 之外的列） */
export function seriesLabel(key: string): string {
  const def = DEFS[key]
  if (def) return def.unit ? `${def.label} (${def.unit})` : def.label
  return key
}

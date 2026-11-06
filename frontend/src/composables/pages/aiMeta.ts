// AI 分析页元信息：分析类型、文件校验、任务状态、步骤映射
import type { AnalysisTask, TaskStatus } from '@/types/api'
import type { EventType } from '@/types/event'

export interface AnalysisTypeMeta {
  key: EventType
  label: string
  icon: string
  color: string
  /** 一句话介绍 */
  blurb: string
  /** 支持的输入形式 */
  inputs: string[]
  /** el-upload accept 属性 */
  accept: string
  /** 上传规则说明 */
  rule: string
  /** 可选择的最大文件数 */
  maxFiles: number
}

const IMG = '.jpg,.jpeg,.png'

const ANALYSIS_TYPES: AnalysisTypeMeta[] = [
  {
    key: 'fire',
    label: '火灾识别',
    icon: '🔥',
    color: '#ff6b6b',
    blurb: '识别无人机 / 监控影像中的明火与烟雾，输出火焰区域与面积占比',
    inputs: ['JPG / PNG 影像'],
    accept: IMG,
    rule: '上传 1~4 张 JPG / PNG 影像',
    maxFiles: 4
  },
  {
    key: 'traffic',
    label: '交通拥堵分析',
    icon: '🚗',
    color: '#f0c050',
    blurb: '基于车速 / 流量时序或路面影像，评估拥堵程度与持续时长',
    inputs: ['CSV 时序 (time,speed[,flow])', '路面影像'],
    accept: `.csv,${IMG}`,
    rule: '上传 1 个 CSV（列 time,speed[,flow]）或 1~4 张路面影像',
    maxFiles: 4
  },
  {
    key: 'building',
    label: '建筑异常检测',
    icon: '🏢',
    color: '#9b8fff',
    blurb: '前后时相影像变化检测，或对沉降监测时序做速率 / 加速度分析',
    inputs: ['前后时相影像对 ×2', '沉降 CSV'],
    accept: `.csv,${IMG}`,
    rule: '上传 2 张前后时相影像（变化检测）或 1 个沉降 CSV',
    maxFiles: 2
  },
  {
    key: 'flood',
    label: '内涝积水监测',
    icon: '🌊',
    color: '#3fa9ff',
    blurb: '分析水位 / 降雨时序，或分割路面影像中的积水区域',
    inputs: ['CSV 时序 (time,water_level_cm[,rainfall_mm])', '积水影像'],
    accept: `.csv,${IMG}`,
    rule: '上传 1 个 CSV（列 time,water_level_cm[,rainfall_mm]）或 1~4 张积水影像',
    maxFiles: 4
  }
]

export function typeMeta(type: string): AnalysisTypeMeta | undefined {
  return ANALYSIS_TYPES.find((t) => t.key === type)
}

const extOf = (name: string) => (name.split('.').pop() ?? '').toLowerCase()
export const isImageFile = (name: string) => ['jpg', 'jpeg', 'png'].includes(extOf(name))
export const isCsvFile = (name: string) => extOf(name) === 'csv'

/** 校验待上传文件是否满足所选分析类型的输入规则；合法返回 null */
export function validateFiles(type: EventType, names: string[]): string | null {
  const meta = typeMeta(type)
  if (!meta) return '未知分析类型'
  if (!names.length) return '请先添加待分析文件'
  const imgs = names.filter(isImageFile).length
  const csvs = names.filter(isCsvFile).length
  if (imgs + csvs !== names.length) return '包含不支持的文件格式，仅支持 JPG / PNG / CSV'
  if (type === 'fire') {
    if (csvs) return '火灾识别仅支持 JPG / PNG 影像'
    return imgs <= 4 ? null : '最多上传 4 张影像'
  }
  if (type === 'building') {
    if (csvs) return csvs === 1 && !imgs ? null : '沉降分析仅支持上传 1 个 CSV，且不能与影像混传'
    return imgs === 2 ? null : '变化检测需要上传 2 张前后时相影像'
  }
  if (csvs) return csvs === 1 && !imgs ? null : '时序分析仅支持上传 1 个 CSV，且不能与影像混传'
  return imgs <= 4 ? null : '最多上传 4 张影像'
}

const TASK_STATUS_META: Record<TaskStatus, { label: string; color: string; pulse?: boolean }> = {
  prototype: { label: '原型', color: '#8aa3c4' },
  pending: { label: '排队中', color: '#f0c050', pulse: true },
  running: { label: '分析中', color: '#4fc3f7', pulse: true },
  done: { label: '已完成', color: '#4dd984' },
  failed: { label: '失败', color: '#ff6b6b' }
}

export function taskStatusMeta(s: string): { label: string; color: string; pulse?: boolean } {
  return TASK_STATUS_META[s as TaskStatus] ?? { label: s, color: '#8aa3c4' }
}

export const STEP_TITLES = ['提交', '预处理', '模型推理', '后处理', '完成']

export function isTerminal(t: Pick<AnalysisTask, 'status'>): boolean {
  return t.status === 'done' || t.status === 'failed' || t.status === 'prototype'
}

/** 由进度映射到 el-steps 的 active 值（全部完成 = 步骤总数） */
export function stepActive(t: Pick<AnalysisTask, 'status' | 'progress'>): number {
  if (t.status === 'done') return STEP_TITLES.length
  const p = t.progress ?? 0
  if (t.status === 'pending' || p < 10) return 0
  if (p < 30) return 1
  if (p < 75) return 2
  return 3
}

/** 检测目标标签中文化 */
const DET_LABELS: Record<string, string> = {
  flame: '火焰',
  fire: '明火',
  smoke: '烟雾',
  vehicle: '车辆',
  car: '车辆',
  congestion: '拥堵区域',
  crack: '裂缝',
  change: '变化区域',
  building_change: '建筑变化',
  water: '积水区域',
  ponding: '积水区域',
  waterlogging: '积水区域',
  anomaly: '异常时段'
}
export function detectionLabel(label: string): string {
  return DET_LABELS[label.toLowerCase()] ?? label
}

/** 输入面板 → 页面的提交载荷 */
export interface SubmitPayload {
  type: EventType
  /** 选择示例数据时的示例编号 */
  sampleId?: string
  /** 上传的本地文件（与 sampleId 二选一） */
  files: File[]
  longitude?: number
  latitude?: number
  createEvent: boolean
}

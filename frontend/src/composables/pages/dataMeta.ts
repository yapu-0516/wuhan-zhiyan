// 数据资产元信息：类型图标 / 颜色，状态颜色
export const DATA_TYPES = ['遥感影像', '无人机影像', '视频流', '三维模型', '传感器数据', '矢量数据'] as const
export const DATA_STATUSES = ['已入库', '处理中', '采集中', '待接入'] as const

export const DATA_TYPE_META: Record<string, { icon: string; color: string }> = {
  遥感影像: { icon: '🛰️', color: '#4fc3f7' },
  无人机影像: { icon: '🚁', color: '#5eead4' },
  视频流: { icon: '📹', color: '#ff8a65' },
  三维模型: { icon: '🏙️', color: '#9b8fff' },
  传感器数据: { icon: '📡', color: '#4dd984' },
  矢量数据: { icon: '🗺️', color: '#f0c050' }
}

export const DATA_STATUS_META: Record<string, { color: string; pulse?: boolean }> = {
  已入库: { color: '#4dd984' },
  处理中: { color: '#f0c050' },
  采集中: { color: '#4fc3f7', pulse: true },
  待接入: { color: '#7f8ea6' }
}

export function dataTypeMeta(type: string): { icon: string; color: string } {
  return DATA_TYPE_META[type] ?? { icon: '📁', color: '#8aa3c4' }
}

export function dataStatusMeta(status: string): { color: string; pulse?: boolean } {
  return DATA_STATUS_META[status] ?? { color: '#8aa3c4' }
}

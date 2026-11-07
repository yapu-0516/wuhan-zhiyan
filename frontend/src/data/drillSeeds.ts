import type { EventType, Severity } from '@/types/event'

export interface DrillMetric {
  label: string
  value: string
}

export interface DrillSeed {
  key: string
  sourceEventId: string
  eventType: EventType
  typeLabel: string
  name: string
  severity: Severity
  severityLabel: string
  district: string
  address: string
  longitude: number
  latitude: number
  confidence: number
  algorithm: string
  description: string
  color: string
  riskRadiusM: number
  affectedBuildings: number
  responseLabel: string
  responseMix: Array<{ type: 'firefighter' | 'rescuer'; count: number }>
  metrics: DrillMetric[]
}

/**
 * 固定的演练种子来自现有演示事件。运行时只复制事件语义和算法指标，
 * 时间、受影响人员和车辆均由当前演练现场重新计算。
 */
export const DRILL_SEEDS: DrillSeed[] = [
  {
    key: 'fire-wanda',
    sourceEventId: 'E0049',
    eventType: 'fire',
    typeLabel: '建筑火情',
    name: '万达商业广场疑似火情',
    severity: 'high',
    severityLabel: 'Ⅱ级 重大',
    district: '江汉区',
    address: '民生路 · 万达商业广场附近',
    longitude: 114.285684,
    latitude: 30.579608,
    confidence: 0.948,
    algorithm: 'FlameNet-Lite',
    description: '无人机巡检发现屋面明火并伴随浓烟，系统自动划定风险半径并检索周边人员与车辆。',
    color: '#e4777b',
    riskRadiusM: 230,
    affectedBuildings: 6,
    responseLabel: '消防与现场疏散',
    responseMix: [
      { type: 'firefighter', count: 14 },
      { type: 'rescuer', count: 18 }
    ],
    metrics: [
      { label: '火焰面积', value: '0.38%' },
      { label: '烟雾评分', value: '1.00' },
      { label: '检出区域', value: '1 处' }
    ]
  },
  {
    key: 'traffic-hongkong',
    sourceEventId: 'E0032',
    eventType: 'traffic',
    typeLabel: '交通拥堵',
    name: '香港路严重拥堵',
    severity: 'high',
    severityLabel: 'Ⅱ级 重大',
    district: '江岸区',
    address: '香港路沿线',
    longitude: 114.285665,
    latitude: 30.598881,
    confidence: 0.92,
    algorithm: 'TrafficPulse',
    description: '连续车流检测识别到持续拥堵，系统向周边车辆推送减速提示并模拟交通管控。',
    color: '#d6b45d',
    riskRadiusM: 190,
    affectedBuildings: 4,
    responseLabel: '交通疏导',
    responseMix: [{ type: 'rescuer', count: 12 }],
    metrics: [
      { label: '当前 TPI', value: '9.1' },
      { label: '当前车速', value: '8.8 km/h' },
      { label: '持续拥堵', value: '62 分钟' }
    ]
  },
  {
    key: 'flood-jiefang',
    sourceEventId: 'E0024',
    eventType: 'flood',
    typeLabel: '道路积水',
    name: '建设大道路面中度积水',
    severity: 'medium',
    severityLabel: 'Ⅲ级 较大',
    district: '江汉区',
    address: '建设大道 · 台北路交汇处',
    longitude: 114.273274,
    latitude: 30.601779,
    confidence: 0.842,
    algorithm: 'AquaSeg',
    description: '航拍识别到连续积水区域，系统模拟低洼路段封闭、车辆避让和周边人员疏散。',
    color: '#71acd2',
    riskRadiusM: 260,
    affectedBuildings: 8,
    responseLabel: '排水与道路管控',
    responseMix: [{ type: 'rescuer', count: 20 }],
    metrics: [
      { label: '积水占比', value: '18.2%' },
      { label: '识别区域', value: '1 处' },
      { label: '处置等级', value: '中度' }
    ]
  },
  {
    key: 'building-crack',
    sourceEventId: 'E0045',
    eventType: 'building',
    typeLabel: '建筑异常',
    name: '中环大厦-A座墙体开裂',
    severity: 'high',
    severityLabel: 'Ⅱ级 重大',
    district: '江岸区',
    address: '云林街 · 中环大厦-A座附近',
    longitude: 114.271493,
    latitude: 30.597827,
    confidence: 0.96,
    algorithm: 'SettleWatch',
    description: '结构监测发现裂缝持续扩展，系统模拟建筑周边警戒、人员转移和结构专家联动。',
    color: '#8eaaa8',
    riskRadiusM: 170,
    affectedBuildings: 3,
    responseLabel: '结构安全处置',
    responseMix: [
      { type: 'firefighter', count: 6 },
      { type: 'rescuer', count: 16 }
    ],
    metrics: [
      { label: '裂缝宽度', value: '3 mm' },
      { label: '扩展趋势', value: '持续' },
      { label: '风险等级', value: 'Ⅱ级' }
    ]
  }
]

// 算法指标字典 —— 与 algorithm/cityeye_algo 各分析器输出的 metrics 键一一对应
// 事件详情（三维浮层 / 事件中心抽屉）与 AI 分析结果页共用，未收录的键原样展示。

export interface MetricDef {
  label: string
  unit?: string
  /** 0~1 比例，展示为百分比 */
  ratio?: boolean
  digits?: number
  hint?: string
}

export const METRIC_DEFS: Record<string, MetricDef> = {
  // —— 通用
  algorithm: { label: '算法' },
  elapsed_ms: { label: '算法耗时', unit: 'ms', digits: 0 },
  image_size: { label: '影像尺寸' },
  samples: { label: '样本点数', unit: '个', digits: 0 },
  step_min: { label: '采样间隔', unit: '分钟', digits: 1 },
  threshold: { label: '自适应阈值', digits: 2 },
  channel: { label: '上报渠道' },
  reporter: { label: '上报人' },

  // —— 火灾 FlameNet-Lite
  flame_area_ratio: { label: '火焰面积占比', ratio: true, digits: 2, hint: '火焰像素占整幅画面的比例' },
  flame_regions: { label: '火焰区域数', unit: '处', digits: 0 },
  smoke_score: { label: '烟雾特征得分', digits: 2, hint: '0~1，越高越接近烟雾特征' },
  candidate_pixel_ratio: { label: '暖色候选像素占比', ratio: true, digits: 2 },
  rejected_candidates: { label: '被否决候选区', unit: '个', digits: 0, hint: '未通过焰心 / 纹理 / 形状校验的暖色区域' },
  best_candidate_score: { label: '最佳候选得分', digits: 2 },

  // —— 交通 TrafficPulse / RoadOcc
  current_speed_kmh: { label: '当前车速', unit: 'km/h', digits: 1 },
  mean_speed_kmh: { label: '平均车速', unit: 'km/h', digits: 1 },
  min_speed_kmh: { label: '最低车速', unit: 'km/h', digits: 1 },
  free_flow_kmh: { label: '自由流车速', unit: 'km/h', digits: 1 },
  current_tpi: { label: '当前 TPI', digits: 1, hint: '交通运行指数 0~10，越高越拥堵' },
  mean_tpi: { label: '平均 TPI', digits: 1 },
  max_tpi: { label: '峰值 TPI', digits: 1 },
  am_peak_tpi: { label: '早高峰 TPI', digits: 1 },
  pm_peak_tpi: { label: '晚高峰 TPI', digits: 1 },
  forecast_tpi: { label: '预测 TPI', digits: 1 },
  equivalent_tpi: { label: '等效 TPI', digits: 1 },
  current_level: { label: '当前路况' },
  level: { label: '拥堵等级' },
  peak_time: { label: '拥堵峰值时刻' },
  am_peak_time: { label: '早高峰时刻' },
  pm_peak_time: { label: '晚高峰时刻' },
  congestion_periods: { label: '拥堵时段数', unit: '段', digits: 0 },
  congested_minutes: { label: '拥堵累计时长', unit: '分钟', digits: 0 },
  slow_minutes: { label: '缓行累计时长', unit: '分钟', digits: 0 },
  ongoing: { label: '拥堵持续中', digits: 0 },
  forecast_minutes: { label: '预测时长', unit: '分钟', digits: 0 },
  mean_flow: { label: '平均流量', unit: '辆/h', digits: 0 },
  max_flow: { label: '峰值流量', unit: '辆/h', digits: 0 },
  vehicles: { label: '识别车辆', unit: '辆', digits: 0 },
  occupancy: { label: '路面占有率', ratio: true, digits: 1 },
  road_area_ratio: { label: '路面面积占比', ratio: true, digits: 1 },

  // —— 建筑 SettleWatch / ChangeScope
  rate_mm_per_month: { label: '近期沉降速率', unit: 'mm/月', digits: 2 },
  overall_rate_mm_per_month: { label: '整体沉降速率', unit: 'mm/月', digits: 2 },
  acceleration: { label: '沉降加速度', unit: 'mm/月²', digits: 2 },
  cumulative_mm: { label: '累计位移', unit: 'mm', digits: 1 },
  anomaly_points: { label: '异常测点', unit: '个', digits: 0 },
  span_days: { label: '监测跨度', unit: '天', digits: 0 },
  risk_level: { label: '风险等级' },
  change_ratio: { label: '变化面积占比', ratio: true, digits: 2 },
  changed_regions: { label: '变化区域数', unit: '处', digits: 0 },
  mean_change: { label: '平均变化强度', digits: 2 },
  dominant_change: { label: '主要变化类型' },
  resized_after: { label: '后时相重采样', digits: 0 },

  // —— 内涝 AquaLevel / AquaSeg
  current_level_cm: { label: '当前水位', unit: 'cm', digits: 1 },
  max_level_cm: { label: '最高水位', unit: 'cm', digits: 1 },
  max_time: { label: '最高水位时刻' },
  max_rise_cm_per_10min: { label: '最大涨速', unit: 'cm/10min', digits: 1 },
  minutes_over_15cm: { label: '超 15cm 时长', unit: '分钟', digits: 0, hint: '15 cm：影响行人与非机动车通行' },
  minutes_over_27cm: { label: '超 27cm 时长', unit: '分钟', digits: 0, hint: '27 cm：危及小型车辆' },
  minutes_over_40cm: { label: '超 40cm 时长', unit: '分钟', digits: 0, hint: '40 cm：严重积水，建议封闭' },
  total_rainfall_mm: { label: '累计降雨量', unit: 'mm', digits: 1 },
  max_rain_intensity_mm_h: { label: '最大雨强', unit: 'mm/h', digits: 1 },
  response_lag_min: { label: '雨洪响应滞后', unit: '分钟', digits: 0 },
  lag_correlation: { label: '雨洪相关系数', digits: 2 },
  forecast_peak_cm: { label: '预测峰值水位', unit: 'cm', digits: 1 },
  forecast_peak_time: { label: '预测峰值时刻' },
  forecast_model: { label: '预测模型' },
  trend: { label: '水位趋势' },
  water_area_ratio: { label: '积水面积占比', ratio: true, digits: 1 },
  water_regions: { label: '积水区域数', unit: '处', digits: 0 }
}

/** 枚举型指标值的中文 */
export const METRIC_VALUE_LABEL: Record<string, string> = {
  smooth: '畅通',
  basic: '基本畅通',
  light: '轻度拥堵',
  moderate: '中度拥堵',
  heavy: '严重拥堵',
  normal: '正常',
  watch: '关注',
  warning: '预警'
}

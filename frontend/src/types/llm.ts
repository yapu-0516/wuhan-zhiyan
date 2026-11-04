// 大模型桥接接口类型（与 llm_module 的 Pydantic 模型一一对应，见 backend/app/routers/llm.py）
import type { EventType } from './event'

/** 自然语言任务解析结果（llm_module.task_parser.ParsedTask） */
export interface ParsedTask {
  event_type: EventType | 'unknown'
  analysis_targets: AnalysisTarget[]
  location: string | null
  event_time: string | null
  extracted_facts: Record<string, string>
  missing_information: string[]
  needs_clarification: boolean
}

export type AnalysisTarget =
  | 'impact_assessment'
  | 'nearby_hospitals'
  | 'road_impact'
  | 'casualty_assessment'
  | 'traffic_impact'
  | 'building_safety'
  | 'drainage_assessment'
  | 'response_advice'
  | 'other'

export const ANALYSIS_TARGET_LABEL: Record<AnalysisTarget, string> = {
  impact_assessment: '影响评估',
  nearby_hospitals: '周边医院',
  road_impact: '道路影响',
  casualty_assessment: '伤亡评估',
  traffic_impact: '交通影响',
  building_safety: '建筑安全',
  drainage_assessment: '排水评估',
  response_advice: '处置建议',
  other: '其他'
}

/** 研判报告单条分析结论（llm_module.report_generator.AnalysisFinding） */
export interface ReportFinding {
  kind: 'fact' | 'inference' | 'unknown'
  statement: string
  basis: string | null
}

export type RiskLevel = 'unknown' | 'low' | 'medium' | 'high' | 'critical'

/** 结构化研判报告（llm_module.report_generator.CityEventReport） */
export interface EventReport {
  report_title: string
  data_classification: string
  event_overview: {
    event_id: string
    event_type: string
    location: string | null
    event_time: string | null
    description: string
    data_type: string
  }
  analysis_targets: string[]
  known_information: string[]
  analysis_results: ReportFinding[]
  risk_assessment: { level: RiskLevel; statement: string; basis: string[] }
  recommendations: string[]
  data_gaps_and_uncertainty: string[]
}

export const RISK_META: Record<RiskLevel, { label: string; color: string }> = {
  unknown: { label: '未知', color: '#8aa3c4' },
  low: { label: '低风险', color: '#4dd984' },
  medium: { label: '中风险', color: '#f0c050' },
  high: { label: '高风险', color: '#ff9040' },
  critical: { label: '严重', color: '#ff5a5a' }
}

/** 城市治理助手的一轮对话（只接受用户和助手两种角色） */
export interface AssistantTurn {
  role: 'user' | 'assistant'
  content: string
}

/** POST /api/llm/chat 响应 */
export interface AssistantReply {
  answer: string
  event_id: string | null
  data_type: string | null
}

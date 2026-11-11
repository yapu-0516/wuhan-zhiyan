export type ScenarioType = 'flood' | 'traffic' | 'fire' | 'building'
export type ScenarioRisk = 'unknown' | 'low' | 'medium' | 'high' | 'critical'
export type ScenarioDataClass = 'real' | 'professional_analysis' | 'simulated' | 'llm_inference' | 'unknown'

export interface ScenarioMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  action?: string
}

export interface ScenarioParameters {
  location_name?: string | null
  longitude?: number | null
  latitude?: number | null
  start_time?: string | null
  duration_min?: number | null
  rainfall_mm_h?: number | null
  congestion_level?: 'light' | 'moderate' | 'severe' | null
  traffic_cause?: string | null
  fire_severity?: 'small' | 'medium' | 'large' | null
  danger_radius_m?: number | null
  settlement_rate_mm_month?: number | null
  affected_building_id?: string | null
  people_count?: number | null
  population_profile?: 'workday' | 'weekend_day' | 'weekend_night' | null
  response_delay_min?: number | null
  closed_exit_count?: number | null
  available_resource_count?: number | null
  resource_types?: string[]
  resource_ids?: string[]
  source_event_id?: string | null
  variation_seed?: number | null
}

export interface ScenarioZone {
  id: string
  risk_level: ScenarioRisk
  longitude: number
  latitude: number
  radius_m: number | null
  polygon: [number, number][] | null
  data_classification: ScenarioDataClass
}

export interface ScenarioPerson {
  id: string
  longitude: number
  latitude: number
  state: 'idle' | 'queued' | 'moving' | 'safe'
}

export interface ScenarioFrame {
  offset_min: number
  risk_level: ScenarioRisk
  zones: ScenarioZone[]
  metrics: Record<string, number | string | null>
  affected_building_ids: string[]
  affected_road_ids: string[]
  people: ScenarioPerson[]
  data_classification: ScenarioDataClass
  limitations: string[]
}

export interface ScenarioRun {
  run_id: string
  version_id: string
  scenario_type: ScenarioType
  variant_label?: string
  status: string
  provider: string
  model_version?: string
  data_classification: ScenarioDataClass
  frames: ScenarioFrame[]
  summary: string
  assumptions: string[]
  limitations: string[]
  generated_at: string
  report?: ScenarioReport
}

export interface ScenarioComparison {
  left_run_id: string
  right_run_id: string
  parameter_changes: Array<{ field: string; before: unknown; after: unknown }>
  risk_changes: Array<{ field: string; before: string; after: string }>
  metric_changes: Record<string, { before: number | null; after: number | null }>
  summary: string
  data_classification: ScenarioDataClass
}

export interface ScenarioSessionView {
  session_id: string
  title: string
  scenario_type: ScenarioType | null
  state: string
  parameters: ScenarioParameters
  messages: ScenarioMessage[]
  current_version_id: string | null
  run_ids: string[]
  latest_run: ScenarioRun | null
  variant_runs: ScenarioRun[]
  last_comparison: ScenarioComparison | null
  assistant_reply?: string
  action?: string
}

export interface ScenarioVariantsResult {
  latest_run: ScenarioRun
  variant_runs: ScenarioRun[]
}

export interface ScenarioTemplate {
  id: string
  name: string
  description: string
  scenario_type: ScenarioType
  parameters: ScenarioParameters
  created_at: string
  updated_at: string
}

export interface ScenarioTemplateCreate {
  name: string
  description: string
  scenario_type: ScenarioType
  parameters: ScenarioParameters
}

export interface ScenarioTemplatePatch {
  name?: string
  description?: string
  scenario_type?: ScenarioType
  parameters?: ScenarioParameters
  operator?: string
}

export interface ScenarioTemplateRevision {
  id: number
  template_id: string
  version_no: number
  name: string
  description: string
  scenario_type: ScenarioType
  parameters: ScenarioParameters
  operator: string
  created_at: string
}

export interface ScenarioReport {
  report_title: string
  data_classification: string
  event_summary: string
  original_scenario: Record<string, unknown>
  extracted_parameters: Record<string, unknown>
  data_and_methods: string[]
  development_process: string[]
  affected_objects: string[]
  risk_assessment: string
  comparison_summary: string
  uncertainties: string[]
  recommendations: string[]
  visualization_summary: string[]
}

export const SCENARIO_LABEL: Record<ScenarioType, string> = {
  flood: '强降水与内涝',
  traffic: '交通拥堵',
  fire: '火灾应急',
  building: '建筑异常'
}

export interface TaskRecord {
  task_id: string
  kind: string
  status: string
  progress: number
  message: string
  metadata?: Record<string, unknown> | null
  result?: Record<string, unknown> | null
  error?: string | null
}

export interface GraphSnapshot {
  graph_id: string
  node_count: number
  edge_count: number
  entity_types: Record<string, number>
  nodes: Array<Record<string, unknown>>
  edges: Array<Record<string, unknown>>
}

export interface ProjectRecord {
  project_id: string
  name: string
  status: string
  simulation_requirement: string
  graph_id?: string | null
  analysis_summary?: string
  ontology?: Record<string, unknown> | null
  graph_snapshot?: GraphSnapshot | null
  latest_task_id?: string | null
  error?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface SimulationRecord {
  simulation_id: string
  project_id: string
  graph_id: string
  status: string
  entity_limit: number
  rounds: number
  active_agents_per_round: number
  temperature: number
  config: Record<string, unknown>
  state: Record<string, unknown>
  profiles_count: number
  current_round: number
  events_count: number
  latest_summary: string
  latest_task_id?: string | null
  error?: string | null
}

export interface FeedPayload {
  simulation_id: string
  state: Record<string, unknown>
  events: Array<Record<string, unknown>>
  round_summaries: Array<Record<string, unknown>>
  analytics: Record<string, unknown>
}

export interface ReportRecord {
  report_id: string
  simulation_id: string
  status: string
  title: string
  summary: string
  sections: Array<{ title: string; content: string }>
  markdown_content: string
  latest_task_id?: string | null
  error?: string | null
}

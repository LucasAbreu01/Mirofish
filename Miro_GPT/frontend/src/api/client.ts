import type { FeedPayload, ProjectRecord, ReportRecord, SimulationRecord, TaskRecord } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5001/api'

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`)
  }
  return payload as T
}

export const api = {
  listProjects: async (): Promise<ProjectRecord[]> => {
    const payload = await requestJson<{ projects: ProjectRecord[] }>('/projects')
    return payload.projects
  },
  createProject: (formData: FormData): Promise<ProjectRecord> =>
    requestJson('/projects', { method: 'POST', body: formData }),
  getProject: (projectId: string): Promise<ProjectRecord> => requestJson(`/projects/${projectId}`),
  requestOntology: (projectId: string): Promise<{ task_id: string }> =>
    requestJson(`/projects/${projectId}/ontology`, { method: 'POST' }),
  requestGraph: (projectId: string): Promise<{ task_id: string }> =>
    requestJson(`/projects/${projectId}/graph`, { method: 'POST' }),
  createSimulation: (payload: Record<string, unknown>): Promise<SimulationRecord> =>
    requestJson('/simulations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  getSimulation: (simulationId: string): Promise<SimulationRecord> =>
    requestJson(`/simulations/${simulationId}`),
  prepareSimulation: (simulationId: string): Promise<SimulationRecord> =>
    requestJson(`/simulations/${simulationId}/prepare`, { method: 'POST' }),
  runSimulation: (simulationId: string): Promise<{ task_id: string; simulation_id: string }> =>
    requestJson(`/simulations/${simulationId}/run`, { method: 'POST' }),
  getFeed: (simulationId: string): Promise<FeedPayload> =>
    requestJson(`/simulations/${simulationId}/feed`),
  createReport: (simulationId: string): Promise<{ report_id: string; task_id: string }> =>
    requestJson('/reports', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulation_id: simulationId }),
    }),
  getReport: (reportId: string): Promise<ReportRecord> => requestJson(`/reports/${reportId}`),
  getTask: (taskId: string): Promise<TaskRecord> => requestJson(`/tasks/${taskId}`),
}

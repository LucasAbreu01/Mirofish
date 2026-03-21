import api from './index'

export async function uploadDocuments(files, scenario, projectName) {
  const formData = new FormData()
  files.forEach(f => formData.append('files', f))
  formData.append('scenario', scenario)
  formData.append('project_name', projectName)
  const { data } = await api.post('/api/graph/upload', formData)
  return data
}

export async function getProject(projectId) {
  const { data } = await api.get(`/api/graph/${projectId}`)
  return data
}

export async function getProjectStatus(projectId) {
  const { data } = await api.get(`/api/graph/${projectId}/status`)
  return data
}

export async function getHistory() {
  const { data } = await api.get('/api/graph/history')
  return data
}

export async function deleteProject(projectId) {
  const { data } = await api.delete(`/api/graph/history/${projectId}`)
  return data
}

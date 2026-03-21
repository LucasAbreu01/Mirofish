import api from './index'

export async function generateReport(simId) {
  const { data } = await api.post(`/api/report/${simId}/generate`)
  return data
}

export async function chatWithReport(simId, question, history = []) {
  const { data } = await api.post(`/api/report/${simId}/chat`, { question, history })
  return data
}

export async function getReport(simId) {
  const { data } = await api.get(`/api/report/${simId}`)
  return data
}

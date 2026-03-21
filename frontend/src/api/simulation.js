import api from './index'

export async function createSimulation(config) {
  const { data } = await api.post('/api/simulation/create', config)
  return data
}

export async function getAgents(simId) {
  const { data } = await api.get(`/api/simulation/${simId}/agents`)
  return data
}

export async function updateAgent(simId, agentName, profile) {
  const { data } = await api.put(`/api/simulation/${simId}/agents/${agentName}`, profile)
  return data
}

export function startSimulationSSE(simId, onEvent) {
  const eventSource = new EventSource(`/api/simulation/${simId}/run`)
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    onEvent(data)
  }
  eventSource.onerror = () => {
    eventSource.close()
  }
  return eventSource
}

export async function getSimulationStatus(simId) {
  const { data } = await api.get(`/api/simulation/${simId}/status`)
  return data
}

export async function getActions(simId) {
  const { data } = await api.get(`/api/simulation/${simId}/actions`)
  return data
}

import { reactive } from 'vue'

const state = reactive({
  projectId: null,
  projectName: '',
  status: '',
  scenario: '',
  graph: null,
  agents: [],
  simulationId: null,
  report: null
})

export function useProject() {
  function setProject(data) {
    const project = data.project || data
    state.projectId = project.project_id || project.id
    state.projectName = project.project_name || project.name || ''
    state.status = project.status || ''
    state.scenario = project.scenario || ''
  }

  function setGraph(graph) {
    state.graph = graph
  }

  function setAgents(agents) {
    state.agents = agents
  }

  function setSimulation(simId) {
    state.simulationId = simId
  }

  function setReport(report) {
    state.report = report
  }

  function reset() {
    state.projectId = null
    state.projectName = ''
    state.status = ''
    state.scenario = ''
    state.graph = null
    state.agents = []
    state.simulationId = null
    state.report = null
  }

  return { state, setProject, setGraph, setAgents, setSimulation, setReport, reset }
}

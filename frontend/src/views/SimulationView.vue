<template>
  <div class="simulation-view">
    <div class="sim-top-bar">
      <StepNav :currentStep="4" :projectId="projectId" :simulationId="simId" />
      <span class="status-badge" :class="statusClass">{{ statusLabel }}</span>
    </div>

    <div class="sim-layout">
      <!-- Left panel: action feed -->
      <div class="panel-left">
        <div class="panel-header">
          <h2>Live Action Feed</h2>
        </div>
        <ActionFeed :actions="actions" />
      </div>

      <!-- Right panel: stats -->
      <div class="panel-right">
        <div class="stat-card">
          <h3>Round Progress</h3>
          <div class="progress-bar-container">
            <div class="progress-bar" :style="{ width: roundProgress + '%' }"></div>
          </div>
          <p class="progress-text">{{ currentRound }} / {{ totalRounds }}</p>
        </div>

        <div class="stat-card">
          <h3>Total Actions</h3>
          <p class="stat-number">{{ actions.length }}</p>
        </div>

        <div class="stat-card">
          <h3>Round Activity</h3>
          <div v-if="roundAgents.length" class="agent-chips">
            <span v-for="name in roundAgents" :key="name" class="agent-chip">
              {{ name }}
            </span>
          </div>
          <p v-else class="muted">Waiting for activity...</p>
        </div>

        <div v-if="projectId" class="stat-card">
          <div class="graph-toggle-header">
            <h3>Live Graph</h3>
            <button class="btn-toggle" @click="toggleGraph">
              {{ showGraph ? 'Hide Graph' : 'Show Live Graph' }}
            </button>
          </div>
          <div v-if="showGraph" class="live-graph-container">
            <GraphPanel v-if="graphData" :graph-data="graphData" />
            <p v-else class="muted">Graph data will appear after the first round completes.</p>
          </div>
        </div>

        <div v-if="error" class="error-card">
          {{ error }}
        </div>

        <button
          v-if="status === 'completed'"
          class="btn-primary"
          @click="viewReport"
        >
          View Report
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { startSimulationSSE, getActions, getSimulationStatus } from '../api/simulation'
import { getProject } from '../api/graph'
import { useProject } from '../store/project'
import StepNav from '../components/StepNav.vue'
import ActionFeed from '../components/ActionFeed.vue'
import GraphPanel from '../components/GraphPanel.vue'

const route = useRoute()
const router = useRouter()
const { state: projectState } = useProject()

const simId = route.params.id
const projectId = ref(projectState.projectId || '')
const actions = ref([])
const currentRound = ref(0)
const totalRounds = ref(0)
const status = ref('connecting')
const error = ref('')
const roundAgents = ref([])
const showGraph = ref(false)
const graphData = ref(null)

let eventSource = null

const statusLabel = computed(() => {
  const labels = {
    connecting: 'Connecting',
    running: 'Running',
    completed: 'Completed',
    error: 'Error'
  }
  return labels[status.value] || status.value
})

const statusClass = computed(() => `status-${status.value}`)

const roundProgress = computed(() => {
  if (!totalRounds.value) return 0
  return Math.round((currentRound.value / totalRounds.value) * 100)
})

function handleEvent(data) {
  const eventType = data.event || data.type

  switch (eventType) {
    case 'round_start':
      currentRound.value = data.round || data.round_number || currentRound.value + 1
      totalRounds.value = data.total_rounds || data.total || totalRounds.value
      roundAgents.value = []
      status.value = 'running'
      break

    case 'action': {
      const action = data.action || data.data || data
      actions.value.push(action)
      if (action.agent_name || data.agent_name) {
        const name = action.agent_name || data.agent_name
        if (!roundAgents.value.includes(name)) {
          roundAgents.value.push(name)
        }
      }
      break
    }

    case 'round_end':
      fetchGraphData()
      break

    case 'simulation_end':
      status.value = 'completed'
      if (eventSource) {
        eventSource.close()
        eventSource = null
      }
      break

    case 'error':
      error.value = data.message || data.error || 'An error occurred'
      status.value = 'error'
      break

    default:
      // Handle unknown event types gracefully
      if (data.action_type) {
        actions.value.push(data)
      }
  }
}

async function fetchGraphData() {
  if (!projectId.value || !showGraph.value) return
  try {
    const data = await getProject(projectId.value)
    const graph = data.graph || (data.project && data.project.graph)
    if (graph) graphData.value = graph
  } catch (_) {
    // silently ignore graph fetch errors
  }
}

onMounted(async () => {
  try {
    // Check existing status first
    const statusData = await getSimulationStatus(simId)
    // Extract projectId from status if available
    if (statusData.project_id && !projectId.value) {
      projectId.value = statusData.project_id
    }
    if (statusData.status === 'completed') {
      status.value = 'completed'
      totalRounds.value = statusData.total_rounds || 0
      currentRound.value = totalRounds.value
      const existingActions = await getActions(simId)
      actions.value = existingActions.actions || existingActions || []
      return
    }

    totalRounds.value = statusData.total_rounds || statusData.num_rounds || 0

    // Start SSE
    eventSource = startSimulationSSE(simId, handleEvent)
    status.value = 'running'
  } catch (err) {
    // If status check fails, try SSE directly
    eventSource = startSimulationSSE(simId, handleEvent)
    status.value = 'running'
  }
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})

function toggleGraph() {
  showGraph.value = !showGraph.value
  if (showGraph.value && !graphData.value) {
    fetchGraphData()
  }
}

function viewReport() {
  router.push(`/report/${simId}`)
}
</script>

<style scoped>
.simulation-view {
  min-height: 100vh;
  background: var(--bg);
}

.sim-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 20px;
}

.sim-top-bar .step-nav {
  flex: 1;
}

.status-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.status-connecting {
  background: rgba(139, 148, 158, 0.15);
  border: 1px solid rgba(139, 148, 158, 0.3);
  color: var(--text-muted);
}

.status-running {
  background: rgba(255, 107, 53, 0.15);
  border: 1px solid rgba(255, 107, 53, 0.4);
  color: var(--accent);
  box-shadow: 0 0 12px rgba(255, 107, 53, 0.2);
  animation: pulse 2s infinite;
}

.status-completed {
  background: rgba(63, 185, 80, 0.15);
  border: 1px solid rgba(63, 185, 80, 0.3);
  color: var(--success);
}

.status-error {
  background: rgba(248, 81, 73, 0.15);
  color: var(--error);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.sim-layout {
  display: flex;
  gap: 0;
  height: calc(100vh - 60px);
}

.panel-left {
  flex: 0 0 65%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.panel-header h2 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.panel-right {
  flex: 0 0 35%;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.stat-card {
  background: rgba(28, 33, 40, 0.4);
  border: 1px solid rgba(48, 54, 61, 0.6);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-card h3 {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.progress-bar-container {
  height: 10px;
  background: rgba(22, 27, 34, 0.8);
  border-radius: 5px;
  overflow: hidden;
  margin-bottom: 12px;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
}

.progress-bar {
  height: 100%;
  background: var(--accent);
  border-radius: 5px;
  transition: width 0.4s ease-out;
  box-shadow: 0 0 10px rgba(255, 107, 53, 0.5);
}

.progress-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  text-align: center;
  font-family: var(--font-mono);
}

.stat-number {
  font-size: 32px;
  font-weight: 800;
  color: var(--accent);
  text-align: center;
  font-family: var(--font-mono);
  letter-spacing: -0.02em;
}

.agent-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.agent-chip {
  background: rgba(28, 33, 40, 0.8);
  border: 1px solid rgba(48, 54, 61, 0.8);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  padding: 4px 10px;
  border-radius: 8px;
}

.muted {
  color: var(--text-muted);
  font-size: 13px;
}

.error-card {
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid var(--error);
  color: var(--error);
  padding: 12px;
  border-radius: 8px;
  font-size: 13px;
}

.btn-primary {
  width: 100%;
  padding: 12px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:hover {
  opacity: 0.9;
}

.graph-toggle-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.graph-toggle-header h3 {
  margin-bottom: 0;
}

.btn-toggle {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text);
  font-size: 11px;
  font-weight: 600;
  font-family: inherit;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.btn-toggle:hover {
  border-color: var(--accent);
}

.live-graph-container {
  height: 300px;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg);
}
</style>

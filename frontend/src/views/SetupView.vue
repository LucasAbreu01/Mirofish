<template>
  <div class="setup-view">
    <StepNav :currentStep="3" :projectId="route.params.id" />

    <div class="setup-container">
      <h1 class="page-title">Simulation Setup</h1>

      <!-- Loading project -->
      <div v-if="loadingProject" class="loading-state">
        <div class="spinner" />
        <p>Loading project...</p>
      </div>

      <!-- Config form (no simulation yet) -->
      <div v-else-if="!agents.length && !generatingAgents" class="config-form">
        <div class="form-group">
          <label>Number of Agents</label>
          <div class="slider-row">
            <input
              type="range"
              v-model.number="config.numAgents"
              min="1"
              max="20"
              step="1"
            />
            <span class="slider-value">{{ config.numAgents }}</span>
          </div>
        </div>

        <div class="form-group">
          <label>Number of Rounds</label>
          <div class="slider-row">
            <input
              type="range"
              v-model.number="config.numRounds"
              min="1"
              max="30"
              step="1"
            />
            <span class="slider-value">{{ config.numRounds }}</span>
          </div>
        </div>

        <div class="form-group">
          <label>Scenario</label>
          <textarea
            v-model="config.scenario"
            rows="4"
            placeholder="Describe the simulation scenario..."
          />
        </div>

        <div class="form-group">
          <label>Agent Roles <span class="optional-tag">(optional)</span></label>
          <textarea
            v-model="config.agentRoles"
            rows="3"
            placeholder="e.g. 2 clinical psychologists, 1 neuropsychologist, 1 psychiatrist, 1 social worker"
          />
          <p class="field-hint">
            Define who should participate. Leave empty to auto-generate from document entities.
          </p>
        </div>

        <button class="btn-primary" @click="generateAgents" :disabled="!config.scenario.trim()">
          Generate Agents
        </button>
      </div>

      <!-- Generating agents loading -->
      <div v-else-if="generatingAgents" class="loading-state">
        <div class="spinner" />
        <p>Generating {{ config.numAgents }} agents...</p>
        <p class="muted">This may take a moment</p>
      </div>

      <!-- Agents grid -->
      <div v-else class="agents-section">
        <h2 class="section-title">Generated Agents ({{ agents.length }})</h2>
        <div class="agents-grid">
          <AgentCard
            v-for="agent in agents"
            :key="agent.name"
            :agent="agent"
            @update="handleAgentUpdate"
          />
        </div>

        <div class="actions-bar">
          <button class="btn-primary" @click="startSimulation">
            Start Simulation
          </button>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createSimulation, getAgents, updateAgent } from '../api/simulation'
import { getProject } from '../api/graph'
import { useProject } from '../store/project'
import StepNav from '../components/StepNav.vue'
import AgentCard from '../components/AgentCard.vue'

const route = useRoute()
const router = useRouter()
const { state: projectState, setSimulation, setAgents: storeAgents } = useProject()

const loadingProject = ref(true)
const generatingAgents = ref(false)
const error = ref('')
const agents = ref([])
const simulationId = ref(null)

const config = ref({
  numAgents: 5,
  numRounds: 10,
  scenario: '',
  agentRoles: ''
})

onMounted(async () => {
  try {
    const projectId = route.params.id
    const data = await getProject(projectId)
    const project = data.project || data

    config.value.scenario = project.scenario || project.description || ''

    // Check if simulation already exists in project state
    if (projectState.simulationId) {
      simulationId.value = projectState.simulationId
      const agentList = await getAgents(projectState.simulationId)
      agents.value = agentList.agents || agentList || []
    }
  } catch (err) {
    error.value = 'Failed to load project: ' + (err.response?.data?.detail || err.message)
  } finally {
    loadingProject.value = false
  }
})

async function generateAgents() {
  generatingAgents.value = true
  error.value = ''

  try {
    const projectId = route.params.id
    const result = await createSimulation({
      project_id: projectId,
      agent_count: config.value.numAgents,
      num_rounds: config.value.numRounds,
      scenario: config.value.scenario,
      agent_roles: config.value.agentRoles
    })

    simulationId.value = result.simulation_id || result.id
    setSimulation(simulationId.value)

    const agentList = await getAgents(simulationId.value)
    agents.value = agentList.agents || agentList || []
    storeAgents(agents.value)
  } catch (err) {
    error.value = 'Failed to generate agents: ' + (err.response?.data?.detail || err.message)
  } finally {
    generatingAgents.value = false
  }
}

async function handleAgentUpdate(updatedAgent) {
  try {
    await updateAgent(simulationId.value, updatedAgent.name, {
      personality: updatedAgent.personality,
      goals: updatedAgent.goals,
      backstory: updatedAgent.backstory
    })
    const idx = agents.value.findIndex(a => a.name === updatedAgent.name)
    if (idx >= 0) {
      agents.value[idx] = { ...agents.value[idx], ...updatedAgent }
    }
  } catch (err) {
    error.value = 'Failed to update agent: ' + (err.response?.data?.detail || err.message)
  }
}

function startSimulation() {
  router.push(`/simulation/${simulationId.value}`)
}
</script>

<style scoped>
.setup-view {
  min-height: 100vh;
  background: var(--bg);
}

.setup-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 24px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--text);
}

.loading-state .muted {
  color: var(--text-muted);
  font-size: 13px;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.config-form {
  max-width: 500px;
  margin: 0 auto;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 8px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider-row input[type="range"] {
  flex: 1;
  accent-color: var(--accent);
  height: 6px;
}

.slider-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--accent);
  min-width: 28px;
  text-align: center;
}

.form-group textarea {
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  color: var(--text);
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}

.form-group textarea:focus {
  outline: none;
  border-color: var(--accent);
}

.form-group textarea::placeholder {
  color: var(--text-muted);
}

.optional-tag {
  font-weight: 400;
  color: var(--text-muted);
  font-size: 12px;
}

.field-hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
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

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.agents-section .section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 16px;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.actions-bar {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}

.actions-bar .btn-primary {
  max-width: 300px;
}

.error-message {
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid var(--error);
  color: var(--error);
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13px;
  margin-top: 16px;
}
</style>

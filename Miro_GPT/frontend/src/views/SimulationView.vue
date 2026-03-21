<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api/client'
import EventFeed from '../components/EventFeed.vue'
import TaskStatusBar from '../components/TaskStatusBar.vue'
import WizardNav from '../components/WizardNav.vue'
import { useWorkspaceStore } from '../stores/workspace'

const route = useRoute()
const router = useRouter()
const store = useWorkspaceStore()
const error = ref('')

const projectId = computed(() => String(route.params.projectId || ''))
const simulationId = computed(() => String(route.params.simulationId || ''))

const form = reactive({
  entity_limit: 25,
  rounds: 12,
  active_agents_per_round: 4,
  temperature: 0.35,
})

await store.loadProject(projectId.value)
if (simulationId.value) {
  await store.loadSimulation(simulationId.value)
  await store.loadFeed(simulationId.value).catch(() => undefined)
}

const activeTask = computed(() => {
  const taskId = store.currentSimulation?.latest_task_id || ''
  return taskId ? store.tasks[taskId] || null : null
})

async function createSimulation() {
  error.value = ''
  try {
    const simulation = await api.createSimulation({
      project_id: projectId.value,
      entity_limit: form.entity_limit,
      rounds: form.rounds,
      active_agents_per_round: form.active_agents_per_round,
      temperature: form.temperature,
    })
    localStorage.setItem(`miro_gpt:lastSimulation:${projectId.value}`, simulation.simulation_id)
    router.replace(`/projects/${projectId.value}/simulation/${simulation.simulation_id}`)
    await store.loadSimulation(simulation.simulation_id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to create simulation.'
  }
}

async function prepareSimulation() {
  if (!store.currentSimulation) return
  error.value = ''
  try {
    store.currentSimulation = await api.prepareSimulation(store.currentSimulation.simulation_id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to prepare simulation.'
  }
}

async function runSimulation() {
  if (!store.currentSimulation) return
  error.value = ''
  try {
    const task = await api.runSimulation(store.currentSimulation.simulation_id)
    const result = await store.trackTask(task.task_id, async () => {
      await store.loadSimulation(store.currentSimulation!.simulation_id)
      await store.loadFeed(store.currentSimulation!.simulation_id).catch(() => undefined)
    })
    if (result.status === 'failed') {
      error.value = result.error || 'Simulation run failed.'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Simulation run failed.'
  }
}

async function createReport() {
  if (!store.currentSimulation) return
  const created = await api.createReport(store.currentSimulation.simulation_id)
  localStorage.setItem(`miro_gpt:lastReport:${projectId.value}`, created.report_id)
  router.push({
    path: `/reports/${created.report_id}`,
    query: {
      projectId: projectId.value,
      simulationId: store.currentSimulation.simulation_id,
      taskId: created.task_id,
    },
  })
}
</script>

<template>
  <section class="stack">
    <WizardNav
      step="simulation"
      :project-id="projectId"
      :simulation-id="store.currentSimulation?.simulation_id"
    />

    <article class="panel">
      <div class="feed-head">
        <div>
          <p class="eyebrow">Step 3</p>
          <h2>Configure and run the social simulation</h2>
        </div>
        <span>{{ store.currentSimulation?.status || 'No simulation yet' }}</span>
      </div>
      <TaskStatusBar :task="activeTask" />
      <p v-if="error" class="error-copy">{{ error }}</p>
      <div v-if="!store.currentSimulation" class="form-grid">
        <div class="split-grid">
          <div class="field">
            <label>Entity limit</label>
            <input v-model.number="form.entity_limit" type="number" min="5" max="40" />
          </div>
          <div class="field">
            <label>Rounds</label>
            <input v-model.number="form.rounds" type="number" min="3" max="24" />
          </div>
          <div class="field">
            <label>Active agents / round</label>
            <input v-model.number="form.active_agents_per_round" type="number" min="2" max="6" />
          </div>
          <div class="field">
            <label>Temperature</label>
            <input v-model.number="form.temperature" type="number" min="0.1" max="1" step="0.05" />
          </div>
        </div>
        <div class="button-row">
          <button class="button-primary" @click="createSimulation">Create simulation</button>
        </div>
      </div>
      <div v-else class="button-row">
        <button class="button-primary" @click="prepareSimulation">Prepare</button>
        <button class="button-secondary" @click="runSimulation">Run</button>
        <button
          class="button-ghost"
          :disabled="store.currentSimulation.status !== 'completed'"
          @click="createReport"
        >
          Generate report
        </button>
      </div>
    </article>

    <div v-if="store.currentSimulation" class="page-grid">
      <article class="panel">
        <h2>Simulation status</h2>
        <div class="metrics-grid">
          <div class="metric">
            <span>Profiles</span>
            <strong>{{ store.currentSimulation.profiles_count }}</strong>
          </div>
          <div class="metric">
            <span>Current round</span>
            <strong>{{ store.currentSimulation.current_round }}</strong>
          </div>
          <div class="metric">
            <span>Events</span>
            <strong>{{ store.currentSimulation.events_count }}</strong>
          </div>
        </div>
        <p class="status-copy">{{ store.currentSimulation.latest_summary || 'No round summary yet.' }}</p>
      </article>

      <article class="panel">
        <h2>Analytics</h2>
        <div class="metrics-grid">
          <div class="metric">
            <span>Rounds completed</span>
            <strong>{{ store.currentFeed?.analytics.rounds_completed || 0 }}</strong>
          </div>
          <div class="metric">
            <span>Dominant sentiment</span>
            <strong>{{ store.currentFeed?.analytics.dominant_sentiment || 'neutral' }}</strong>
          </div>
          <div class="metric">
            <span>Event types</span>
            <strong>{{ Object.keys(store.currentFeed?.analytics.event_types || {}).length }}</strong>
          </div>
        </div>
      </article>
    </div>

    <article v-if="store.currentFeed" class="panel">
      <h2>Simulation feed</h2>
      <EventFeed :rounds="store.currentFeed.round_summaries" :events="store.currentFeed.events" />
    </article>
  </section>
</template>

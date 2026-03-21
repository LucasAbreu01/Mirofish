<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api/client'
import GraphSummaryChart from '../components/GraphSummaryChart.vue'
import TaskStatusBar from '../components/TaskStatusBar.vue'
import WizardNav from '../components/WizardNav.vue'
import { useWorkspaceStore } from '../stores/workspace'

const store = useWorkspaceStore()
const route = useRoute()
const router = useRouter()
const error = ref('')

const projectId = computed(() => String(route.params.projectId || ''))

await store.loadProject(projectId.value)

const activeTask = computed(() => {
  const taskId = store.currentProject?.latest_task_id || ''
  return taskId ? store.tasks[taskId] || null : null
})

async function generateOntology() {
  error.value = ''
  try {
    const task = await api.requestOntology(projectId.value)
    const result = await store.trackTask(task.task_id, async () => {
      await store.loadProject(projectId.value)
    })
    if (result.status === 'failed') {
      error.value = result.error || 'Ontology generation failed.'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Ontology generation failed.'
  }
}

async function buildGraph() {
  error.value = ''
  try {
    const task = await api.requestGraph(projectId.value)
    const result = await store.trackTask(task.task_id, async () => {
      await store.loadProject(projectId.value)
    })
    if (result.status === 'failed') {
      error.value = result.error || 'Graph build failed.'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Graph build failed.'
  }
}

function continueToSimulation() {
  router.push(`/projects/${projectId.value}/simulation`)
}
</script>

<template>
  <section class="stack">
    <WizardNav step="graph" :project-id="projectId" />

    <article class="panel">
      <div class="feed-head">
        <div>
          <p class="eyebrow">{{ store.currentProject?.status }}</p>
          <h2>{{ store.currentProject?.name }}</h2>
        </div>
        <span>{{ store.currentProject?.graph_id || 'No graph yet' }}</span>
      </div>
      <p>{{ store.currentProject?.simulation_requirement || 'No simulation requirement provided.' }}</p>
      <TaskStatusBar :task="activeTask" />
      <p v-if="error" class="error-copy">{{ error }}</p>
      <div class="button-row">
        <button
          class="button-primary"
          :disabled="store.currentProject?.status === 'ontology_pending'"
          @click="generateOntology"
        >
          {{ store.currentProject?.ontology ? 'Regenerate ontology' : 'Generate ontology' }}
        </button>
        <button
          class="button-secondary"
          :disabled="!store.currentProject?.ontology || store.currentProject?.status === 'graph_pending'"
          @click="buildGraph"
        >
          {{ store.currentProject?.graph_snapshot ? 'Rebuild graph' : 'Build graph in Zep' }}
        </button>
        <button
          class="button-ghost"
          :disabled="!store.currentProject?.graph_snapshot"
          @click="continueToSimulation"
        >
          Continue to simulation
        </button>
      </div>
    </article>

    <div class="page-grid">
      <article class="panel">
        <h2>Ontology</h2>
        <p>{{ store.currentProject?.analysis_summary || 'Generate the ontology to inspect entity and edge types.' }}</p>
        <div class="split-grid">
          <div class="metric">
            <span>Entity types</span>
            <strong>{{ ((store.currentProject?.ontology?.entity_types as unknown[]) || []).length }}</strong>
          </div>
          <div class="metric">
            <span>Edge types</span>
            <strong>{{ ((store.currentProject?.ontology?.edge_types as unknown[]) || []).length }}</strong>
          </div>
        </div>
        <div class="stack">
          <div
            v-for="entity in ((store.currentProject?.ontology?.entity_types as Array<Record<string, unknown>>) || [])"
            :key="String(entity.name)"
            class="metric"
          >
            <strong>{{ entity.name }}</strong>
            <p>{{ entity.description }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <h2>Graph snapshot</h2>
        <GraphSummaryChart :snapshot="store.currentProject?.graph_snapshot || null" />
        <div class="metrics-grid">
          <div class="metric">
            <span>Nodes</span>
            <strong>{{ store.currentProject?.graph_snapshot?.node_count || 0 }}</strong>
          </div>
          <div class="metric">
            <span>Edges</span>
            <strong>{{ store.currentProject?.graph_snapshot?.edge_count || 0 }}</strong>
          </div>
          <div class="metric">
            <span>Types</span>
            <strong>{{ Object.keys(store.currentProject?.graph_snapshot?.entity_types || {}).length }}</strong>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

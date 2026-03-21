<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api/client'
import { useWorkspaceStore } from '../stores/workspace'
import WizardNav from '../components/WizardNav.vue'

const router = useRouter()
const store = useWorkspaceStore()
const files = ref<FileList | null>(null)
const error = ref('')
const form = reactive({
  project_name: '',
  simulation_requirement: '',
})

store.loadProjects()

async function submitProject() {
  error.value = ''
  const payload = new FormData()
  payload.append('project_name', form.project_name)
  payload.append('simulation_requirement', form.simulation_requirement)
  Array.from(files.value || []).forEach((file) => payload.append('files[]', file))
  try {
    const project = await api.createProject(payload)
    await store.loadProjects()
    router.push(`/projects/${project.project_id}/graph`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to create project.'
  }
}
</script>

<template>
  <section class="stack">
    <WizardNav step="upload" />

    <div class="page-grid">
      <article class="panel hero-panel">
        <div>
          <p class="eyebrow">Step 1</p>
          <h2 class="display">Upload source material and frame the scenario.</h2>
        </div>
        <div class="stack">
          <p>
            Mini MiroFish reads local documents, derives a compact ontology, builds a Zep graph,
            runs a low-cost social simulation, and writes a structured report.
          </p>
          <div class="inline-list">
            <span class="pill">PDF / TXT / MD</span>
            <span class="pill">SQLite task tracking</span>
            <span class="pill">One LLM call per round</span>
          </div>
        </div>
      </article>

      <article class="panel">
        <h2>Create Project</h2>
        <div class="form-grid">
          <div class="field">
            <label for="project_name">Project name</label>
            <input id="project_name" v-model="form.project_name" placeholder="Semiconductor response mapping" />
          </div>
          <div class="field">
            <label for="simulation_requirement">Simulation requirement</label>
            <textarea
              id="simulation_requirement"
              v-model="form.simulation_requirement"
              placeholder="Describe the scenario, pressure, or question the simulation should explore."
            />
          </div>
          <div class="field">
            <label for="files">Documents</label>
            <input id="files" type="file" multiple accept=".pdf,.txt,.md,.markdown" @change="files = ($event.target as HTMLInputElement).files" />
          </div>
          <div class="button-row">
            <button class="button-primary" @click="submitProject">Create and continue</button>
          </div>
          <p v-if="error" class="error-copy">{{ error }}</p>
        </div>
      </article>
    </div>

    <article class="panel">
      <div class="feed-head">
        <h2>Recent projects</h2>
        <span>{{ store.projects.length }}</span>
      </div>
      <div class="feed-grid">
        <RouterLink
          v-for="project in store.projects"
          :key="project.project_id"
          :to="`/projects/${project.project_id}/graph`"
          class="feed-card"
        >
          <p class="eyebrow">{{ project.status }}</p>
          <h3>{{ project.name }}</h3>
          <p>{{ project.analysis_summary || project.simulation_requirement || 'No summary yet.' }}</p>
        </RouterLink>
      </div>
    </article>
  </section>
</template>

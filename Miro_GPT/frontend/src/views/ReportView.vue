<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import { useRoute } from 'vue-router'

import TaskStatusBar from '../components/TaskStatusBar.vue'
import WizardNav from '../components/WizardNav.vue'
import { useWorkspaceStore } from '../stores/workspace'

const route = useRoute()
const store = useWorkspaceStore()
const error = ref('')

const reportId = String(route.params.reportId || '')
const projectId = computed(() => String(route.query.projectId || ''))
const simulationId = computed(() => String(route.query.simulationId || ''))
const taskId = computed(() => String(route.query.taskId || ''))

await store.loadReport(reportId)

if (taskId.value) {
  const result = await store.trackTask(taskId.value, async () => {
    await store.loadReport(reportId)
  })
  if (result.status === 'failed') {
    error.value = result.error || 'Report generation failed.'
  }
}

const rendered = computed(() => marked.parse(store.currentReport?.markdown_content || ''))
const activeTask = computed(() => (taskId.value ? store.tasks[taskId.value] || null : null))
</script>

<template>
  <section class="stack">
    <WizardNav
      step="report"
      :project-id="projectId"
      :simulation-id="simulationId"
      :report-id="reportId"
    />

    <article class="panel">
      <div class="feed-head">
        <div>
          <p class="eyebrow">Step 4</p>
          <h2>{{ store.currentReport?.title || 'Simulation report' }}</h2>
        </div>
        <span>{{ store.currentReport?.status }}</span>
      </div>
      <TaskStatusBar :task="activeTask" />
      <p>{{ store.currentReport?.summary }}</p>
      <p v-if="error" class="error-copy">{{ error }}</p>
    </article>

    <div class="page-grid">
      <article class="panel report-body">
        <h2>Sections</h2>
        <div
          v-for="section in store.currentReport?.sections || []"
          :key="section.title"
          class="metric"
        >
          <strong>{{ section.title }}</strong>
          <p>{{ section.content }}</p>
        </div>
      </article>

      <article class="panel">
        <h2>Markdown</h2>
        <div class="report-render" v-html="rendered"></div>
      </article>
    </div>
  </section>
</template>

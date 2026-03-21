<template>
  <div class="report-view">
    <StepNav :currentStep="5" />

    <div v-if="loading" class="loading-state">
      <div class="spinner" />
      <p>{{ loadingMessage }}</p>
    </div>

    <div v-else-if="!reportContent && !loading" class="generate-state">
      <div class="generate-card">
        <h2>Simulation Complete</h2>
        <p>Generate an AI-powered analysis report of the simulation results.</p>
        <button class="btn-primary" @click="handleGenerateReport">
          Generate Report
        </button>
      </div>
    </div>

    <div v-else class="report-layout">
      <div class="report-main">
        <div class="report-content markdown-body" v-html="renderedReport"></div>
      </div>
      <div class="report-sidebar">
        <ChatPanel :simulationId="simId" />
      </div>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import { generateReport, getReport } from '../api/report'
import { useProject } from '../store/project'
import StepNav from '../components/StepNav.vue'
import ChatPanel from '../components/ChatPanel.vue'

const route = useRoute()
const { setReport } = useProject()

const simId = route.params.id
const reportContent = ref('')
const loading = ref(true)
const loadingMessage = ref('Checking for existing report...')
const error = ref('')

const renderedReport = computed(() => {
  if (!reportContent.value) return ''
  return marked(reportContent.value)
})

onMounted(async () => {
  try {
    const data = await getReport(simId)
    if (data.report || data.content || data.markdown) {
      reportContent.value = data.report || data.content || data.markdown
      setReport(reportContent.value)
    }
  } catch (err) {
    // No report exists yet, that's fine
  } finally {
    loading.value = false
  }
})

async function handleGenerateReport() {
  loading.value = true
  loadingMessage.value = 'Generating report... This may take a minute.'
  error.value = ''

  try {
    const data = await generateReport(simId)
    reportContent.value = data.report || data.content || data.markdown || ''
    setReport(reportContent.value)
  } catch (err) {
    error.value = 'Failed to generate report: ' + (err.response?.data?.detail || err.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.report-view {
  min-height: 100vh;
  background: var(--bg);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  gap: 16px;
  color: var(--text);
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

.generate-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
}

.generate-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  max-width: 400px;
}

.generate-card h2 {
  font-size: 20px;
  color: var(--text);
  margin-bottom: 12px;
}

.generate-card p {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 24px;
  line-height: 1.5;
}

.btn-primary {
  padding: 12px 32px;
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

.report-layout {
  display: flex;
  height: calc(100vh - 60px);
}

.report-main {
  flex: 0 0 60%;
  overflow-y: auto;
  padding: 32px;
  border-right: 1px solid var(--border);
}

.report-sidebar {
  flex: 0 0 40%;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.error-message {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid var(--error);
  color: var(--error);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 13px;
}

/* Markdown rendered content styles */
.markdown-body :deep(h1) {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  margin: 24px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.markdown-body :deep(h2) {
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
  margin: 20px 0 10px;
}

.markdown-body :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin: 16px 0 8px;
}

.markdown-body :deep(p) {
  font-size: 14px;
  color: var(--text);
  line-height: 1.7;
  margin: 8px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 24px;
  margin: 8px 0;
}

.markdown-body :deep(li) {
  font-size: 14px;
  color: var(--text);
  line-height: 1.6;
  margin: 4px 0;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--accent);
  padding: 8px 16px;
  margin: 12px 0;
  background: var(--bg-secondary);
  border-radius: 0 6px 6px 0;
}

.markdown-body :deep(blockquote p) {
  color: var(--text-muted);
  font-style: italic;
}

.markdown-body :deep(code) {
  background: var(--bg-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: var(--accent);
}

.markdown-body :deep(pre) {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  margin: 12px 0;
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--text);
}

.markdown-body :deep(strong) {
  color: var(--text);
  font-weight: 600;
}

.markdown-body :deep(em) {
  color: var(--text-muted);
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}

.markdown-body :deep(th) {
  background: var(--bg-secondary);
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
  text-align: left;
  padding: 8px 12px;
  border: 1px solid var(--border);
}

.markdown-body :deep(td) {
  font-size: 13px;
  color: var(--text);
  padding: 8px 12px;
  border: 1px solid var(--border);
}

.markdown-body :deep(tr:nth-child(even)) {
  background: var(--bg-secondary);
}

.markdown-body :deep(a) {
  color: var(--accent);
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 20px 0;
}
</style>

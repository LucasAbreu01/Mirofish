<template>
  <div class="home">
    <div class="hero">
      <h1 class="title">MIROFISH</h1>
      <span class="subtitle">Mini</span>
      <p class="tagline">Multi-Agent Simulation Engine</p>
    </div>

    <div class="upload-section">
      <div
        class="dropzone"
        :class="{ 'dropzone--active': isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
        @click="openFilePicker"
      >
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".pdf,.txt,.md"
          hidden
          @change="onFileSelect"
        />
        <div class="dropzone-content">
          <svg class="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 16V4m0 0L8 8m4-4l4 4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
          </svg>
          <p class="dropzone-text">Drop files here or click to browse</p>
          <p class="dropzone-hint">.pdf, .txt, .md accepted</p>
        </div>
      </div>

      <ul v-if="files.length" class="file-list">
        <li v-for="(file, i) in files" :key="i" class="file-item">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatSize(file.size) }}</span>
          <button class="file-remove" @click="removeFile(i)" title="Remove file">&times;</button>
        </li>
      </ul>

      <div class="form-group">
        <label class="label" for="scenario">Simulation Scenario</label>
        <textarea
          id="scenario"
          v-model="scenario"
          class="textarea"
          rows="4"
          placeholder="Describe what you want to simulate..."
        ></textarea>
      </div>

      <div class="form-group">
        <label class="label" for="projectName">Project Name <span class="optional">(optional)</span></label>
        <input
          id="projectName"
          v-model="projectName"
          class="input"
          type="text"
          placeholder="My Simulation"
        />
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <button
        class="btn-start"
        :disabled="loading || (!files.length && !scenario.trim())"
        @click="startEngine"
      >
        <span v-if="loading" class="spinner"></span>
        <span v-else>Start Engine</span>
      </button>

      <p v-if="loading" class="loading-text">Uploading &amp; extracting knowledge graph&hellip;</p>
    </div>

    <div v-if="history.length" class="history-section">
      <div class="history-separator"></div>
      <h2 class="history-heading">Previous Simulations</h2>
      <div class="history-grid">
        <div
          v-for="project in history"
          :key="project.project_id || project.id"
          class="history-card"
          @click="goToProject(project)"
        >
          <button
            class="history-delete"
            title="Delete project"
            @click.stop="removeProject(project)"
          >&times;</button>
          <div class="history-card-name">{{ project.name || project.project_name || 'Untitled' }}</div>
          <p class="history-card-scenario">{{ truncate(project.scenario, 100) }}</p>
          <div class="history-card-meta">
            <span v-if="project.entity_count != null" class="badge badge--accent">{{ project.entity_count }} entities</span>
            <span class="badge badge--muted">{{ (project.simulations || []).length }} sim{{ (project.simulations || []).length === 1 ? '' : 's' }}</span>
          </div>
          <div v-if="(project.simulations || []).length" class="history-sims">
            <div v-for="(sim, si) in project.simulations" :key="si" class="history-sim-row">
              <span
                class="badge"
                :class="sim.status === 'completed' ? 'badge--success' : sim.status === 'failed' ? 'badge--error' : 'badge--muted'"
              >{{ sim.status || 'unknown' }}</span>
              <span class="history-sim-detail">{{ sim.action_count ?? 0 }} actions</span>
              <span v-if="sim.has_report" class="badge badge--accent">report</span>
            </div>
          </div>
          <div class="history-card-date">{{ formatDate(project.created_at) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { uploadDocuments, getHistory, deleteProject } from '../api/graph'
import { useProject } from '../store/project'

const router = useRouter()
const { setProject, setGraph } = useProject()

const fileInput = ref(null)
const files = ref([])
const scenario = ref('')
const projectName = ref('')
const loading = ref(false)
const error = ref('')
const isDragging = ref(false)
const history = ref([])

function openFilePicker() {
  fileInput.value?.click()
}

function addFiles(newFiles) {
  const allowed = ['.pdf', '.txt', '.md']
  for (const file of newFiles) {
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (allowed.includes(ext)) {
      files.value.push(file)
    }
  }
}

function onFileSelect(e) {
  addFiles(Array.from(e.target.files))
  e.target.value = ''
}

function onDrop(e) {
  isDragging.value = false
  addFiles(Array.from(e.dataTransfer.files))
}

function removeFile(index) {
  files.value.splice(index, 1)
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

async function startEngine() {
  error.value = ''
  loading.value = true
  try {
    const data = await uploadDocuments(
      files.value,
      scenario.value,
      projectName.value || 'Untitled Project'
    )
    setProject(data)
    if (data.graph) {
      setGraph(data.graph)
    }
    const id = data.project_id || data.id
    router.push(`/graph/${id}`)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Upload failed. Please try again.'
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  try {
    const data = await getHistory()
    history.value = Array.isArray(data) ? data : data.projects || []
  } catch {
    // silently ignore – history is non-critical
  }
}

function truncate(text, max) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function goToProject(project) {
  const pid = project.project_id || project.id
  const sims = project.simulations || []
  const withReport = sims.filter(s => s.has_report)
  if (withReport.length) {
    const latest = withReport[withReport.length - 1]
    router.push(`/report/${pid}/${latest.simulation_id || latest.id}`)
  } else {
    router.push(`/graph/${pid}`)
  }
}

async function removeProject(project) {
  const pid = project.project_id || project.id
  const name = project.name || project.project_name || 'this project'
  if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return
  try {
    await deleteProject(pid)
    history.value = history.value.filter(p => (p.project_id || p.id) !== pid)
  } catch {
    // ignore
  }
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 24px 80px;
  background: var(--bg);
  color: var(--text);
  font-family: 'JetBrains Mono', monospace;
}

.hero {
  text-align: center;
  margin-bottom: 48px;
}

.title {
  font-size: 3.5rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: var(--text);
  margin: 0;
  line-height: 1.1;
}

.subtitle {
  display: inline-block;
  font-size: 1.4rem;
  font-weight: 400;
  color: var(--accent);
  letter-spacing: 0.3em;
  margin-top: 4px;
}

.tagline {
  margin-top: 16px;
  font-size: 0.95rem;
  color: var(--text-muted);
  letter-spacing: 0.05em;
}

.upload-section {
  width: 100%;
  max-width: 560px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dropzone {
  border: 2px dashed var(--border);
  border-radius: 10px;
  padding: 40px 24px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  background: var(--bg-secondary);
}

.dropzone:hover,
.dropzone--active {
  border-color: var(--accent);
  background: rgba(255, 107, 53, 0.05);
}

.dropzone-icon {
  width: 40px;
  height: 40px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.dropzone--active .dropzone-icon,
.dropzone:hover .dropzone-icon {
  color: var(--accent);
}

.dropzone-text {
  font-size: 0.9rem;
  color: var(--text);
  margin: 0 0 6px;
}

.dropzone-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin: 0;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.8rem;
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
}

.file-size {
  color: var(--text-muted);
  flex-shrink: 0;
}

.file-remove {
  background: none;
  border: none;
  color: var(--error);
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  font-family: inherit;
}

.file-remove:hover {
  opacity: 0.7;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 0.8rem;
  color: var(--text-muted);
  letter-spacing: 0.03em;
}

.optional {
  opacity: 0.6;
}

.textarea,
.input {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 14px;
  color: var(--text);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  resize: vertical;
  transition: border-color 0.2s;
}

.textarea:focus,
.input:focus {
  outline: none;
  border-color: var(--accent);
}

.btn-start {
  padding: 14px 28px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s, opacity 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-start:hover:not(:disabled) {
  background: #e55a28;
  transform: translateY(-1px);
}

.btn-start:active:not(:disabled) {
  transform: translateY(0);
}

.btn-start:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin: 0;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.error {
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid var(--error);
  border-radius: 6px;
  padding: 10px 14px;
  color: var(--error);
  font-size: 0.8rem;
  margin: 0;
}

/* History section */
.history-section {
  width: 100%;
  max-width: 720px;
  margin-top: 48px;
}

.history-separator {
  height: 1px;
  background: var(--border);
  margin-bottom: 24px;
}

.history-heading {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  margin: 0 0 20px;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.history-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.1s;
}

.history-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.history-delete {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  color: var(--error);
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: inherit;
  opacity: 0;
  transition: opacity 0.15s;
}

.history-card:hover .history-delete {
  opacity: 1;
}

.history-delete:hover {
  background: rgba(248, 81, 73, 0.15);
}

.history-card-name {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text);
  margin-bottom: 6px;
  padding-right: 24px;
}

.history-card-scenario {
  font-size: 0.78rem;
  color: var(--text-muted);
  margin: 0 0 10px;
  line-height: 1.45;
}

.history-card-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.badge {
  display: inline-block;
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.badge--accent {
  background: rgba(255, 107, 53, 0.15);
  color: var(--accent);
}

.badge--muted {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-muted);
}

.badge--success {
  background: rgba(63, 185, 80, 0.15);
  color: var(--success);
}

.badge--error {
  background: rgba(248, 81, 73, 0.15);
  color: var(--error);
}

.history-sims {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.history-sim-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
}

.history-sim-detail {
  color: var(--text-muted);
}

.history-card-date {
  font-size: 0.7rem;
  color: var(--text-muted);
  opacity: 0.7;
  margin-top: 4px;
}
</style>

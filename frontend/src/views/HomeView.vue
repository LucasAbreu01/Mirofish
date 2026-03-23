<template>
  <div class="home">
    <!-- Top navbar -->
    <header class="navbar">
      <div class="navbar-brand">Curica Mirror</div>
      <nav class="navbar-tabs">
        <span class="navbar-tab navbar-tab--active">Simulations</span>
      </nav>
    </header>

    <!-- Main content -->
    <div class="main-layout">
      <!-- Left panel: create -->
      <div class="panel-create">
        <div class="welcome-section">
          <h1 class="welcome-title">Curica Mirror</h1>
          <p class="welcome-sub">Multi-Agent Simulation Engine</p>
        </div>

        <!-- File upload -->
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
          <svg class="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 16V4m0 0L8 8m4-4l4 4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
          </svg>
          <span class="dropzone-text">Drop files or click to browse</span>
          <span class="dropzone-hint">.pdf, .txt, .md</span>
        </div>

        <ul v-if="files.length" class="file-list">
          <li v-for="(file, i) in files" :key="i" class="file-item">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatSize(file.size) }}</span>
            <button class="file-remove" @click="removeFile(i)">&times;</button>
          </li>
        </ul>

        <!-- Scenario input (chat-style) -->
        <div class="scenario-input-wrapper">
          <textarea
            v-model="scenario"
            class="scenario-input"
            rows="3"
            placeholder="Enter Simulation Scenario"
            @keydown.ctrl.enter="startEngine"
          ></textarea>
          <button
            class="btn-send"
            :disabled="loading || (!files.length && !scenario.trim())"
            @click="startEngine"
            title="Start simulation"
          >
            <svg v-if="!loading" viewBox="0 0 24 24" fill="currentColor" class="send-icon">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
            <span v-else class="spinner"></span>
          </button>
        </div>

        <div class="form-row">
          <input
            v-model="projectName"
            class="input-project-name"
            type="text"
            placeholder="Project Name (optional)"
          />
        </div>

        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="loading" class="loading-text">Uploading & extracting knowledge graph...</p>

        <!-- Action buttons -->
        <div class="action-buttons">
          <button class="btn-action btn-action--primary" @click="focusScenario">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-action-icon"><circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/></svg>
            New Sim
          </button>
          <button class="btn-action" @click="scrollToHistory">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-action-icon"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            History
          </button>
        </div>
      </div>

      <!-- Right panel: activity feed -->
      <div class="panel-feed" ref="feedPanel">
        <h2 class="feed-title">Recent Activity Feed</h2>
        <div v-if="!history.length" class="feed-empty">
          <p>No simulations yet.</p>
          <p>Create your first one!</p>
        </div>
        <div v-else class="feed-list">
          <div
            v-for="project in history"
            :key="project.project_id || project.id"
            class="feed-card"
            @click="goToProject(project)"
          >
            <div class="feed-card-header">
              <span class="feed-card-name">{{ project.name || 'Untitled' }}</span>
              <button
                class="feed-card-delete"
                title="Delete"
                @click.stop="removeProject(project)"
              >&times;</button>
            </div>
            <p class="feed-card-scenario">{{ truncate(project.scenario, 80) }}</p>
            <div class="feed-card-meta">
              <span class="meta-item">
                <span class="meta-count">{{ project.entity_count || 0 }}</span> entities
              </span>
              <span class="meta-separator"></span>
              <span class="meta-item">
                <span class="meta-count">{{ (project.simulations || []).length }}</span> sim{{ (project.simulations || []).length === 1 ? '' : 's' }}
              </span>
            </div>
            <div v-if="(project.simulations || []).length" class="feed-card-sims">
              <div v-for="(sim, si) in project.simulations" :key="si" class="feed-sim-row">
                <span class="feed-sim-bar" :class="sim.status === 'completed' ? 'bar--success' : 'bar--muted'"></span>
                <span class="feed-sim-status" :class="sim.status === 'completed' ? 'text--success' : ''">{{ sim.status }}</span>
                <span class="feed-sim-actions">{{ sim.action_count ?? 0 }} actions</span>
                <span v-if="sim.has_report" class="feed-sim-report">report</span>
              </div>
            </div>
            <div class="feed-card-date">{{ formatDate(project.created_at) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
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
const feedPanel = ref(null)

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

function focusScenario() {
  document.querySelector('.scenario-input')?.focus()
}

function scrollToHistory() {
  feedPanel.value?.scrollIntoView({ behavior: 'smooth' })
}

async function startEngine() {
  if (loading.value || (!files.value.length && !scenario.value.trim())) return
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
    // silently ignore
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
  const withActions = sims.filter(s => s.action_count > 0)
  if (withReport.length) {
    const latest = withReport[withReport.length - 1]
    router.push(`/report/${latest.simulation_id || latest.id}`)
  } else if (withActions.length) {
    const latest = withActions[withActions.length - 1]
    router.push(`/simulation/${latest.simulation_id || latest.id}`)
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
  background: var(--bg);
  color: var(--text);
  display: flex;
  flex-direction: column;
}

/* Navbar */
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 28px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
}

.navbar-brand {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.03em;
}

.navbar-tabs {
  display: flex;
  gap: 24px;
}

.navbar-tab {
  font-size: 0.8rem;
  color: var(--text-muted);
  cursor: pointer;
  padding-bottom: 2px;
  transition: color 0.2s;
}

.navbar-tab--active {
  color: var(--text);
  border-bottom: 2px solid var(--accent);
}

/* Main layout */
.main-layout {
  display: flex;
  flex: 1;
  gap: 0;
  overflow: hidden;
}

.panel-create {
  flex: 0 0 55%;
  padding: 60px 48px 40px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel-feed {
  flex: 0 0 45%;
  padding: 48px 28px 40px;
  overflow-y: auto;
  border-left: 1px solid var(--border);
  background: rgba(22, 27, 34, 0.5);
}

/* Welcome */
.welcome-section {
  margin-bottom: 8px;
}

.welcome-title {
  font-size: 2.4rem;
  font-weight: 800;
  color: var(--text);
  margin: 0;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.welcome-sub {
  font-size: 0.95rem;
  color: var(--text-muted);
  margin: 8px 0 0;
}

/* Dropzone */
.dropzone {
  border: 1.5px dashed rgba(48, 54, 61, 0.8);
  border-radius: 12px;
  padding: 24px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: all 0.25s ease;
  background: rgba(22, 27, 34, 0.4);
}

.dropzone:hover,
.dropzone--active {
  border-color: var(--accent);
  background: rgba(255, 107, 53, 0.05);
  box-shadow: 0 0 0 1px rgba(255, 107, 53, 0.1) inset;
}

.dropzone-icon {
  width: 28px;
  height: 28px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.dropzone--active .dropzone-icon,
.dropzone:hover .dropzone-icon {
  color: var(--accent);
}

.dropzone-text {
  font-size: 0.82rem;
  color: var(--text);
}

.dropzone-hint {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-left: auto;
}

/* File list */
.file-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.75rem;
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
  font-size: 1rem;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  font-family: inherit;
}

/* Scenario input */
.scenario-input-wrapper {
  position: relative;
  background: rgba(22, 27, 34, 0.6);
  border: 1px solid var(--border);
  border-radius: 12px;
  transition: all 0.25s ease;
}

.scenario-input-wrapper:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent), 0 4px 12px rgba(255, 107, 53, 0.08);
}

.scenario-input {
  width: 100%;
  background: transparent;
  border: none;
  padding: 16px 50px 16px 16px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  resize: none;
  outline: none;
  line-height: 1.5;
}

.scenario-input::placeholder {
  color: var(--text-muted);
}

.btn-send {
  position: absolute;
  bottom: 10px;
  right: 10px;
  width: 36px;
  height: 36px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.2s, transform 0.1s;
}

.btn-send:hover:not(:disabled) {
  opacity: 0.85;
  transform: scale(1.05);
}

.btn-send:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.send-icon {
  width: 18px;
  height: 18px;
}

/* Project name */
.form-row {
  display: flex;
  gap: 8px;
}

.input-project-name {
  flex: 1;
  background: rgba(22, 27, 34, 0.6);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  transition: all 0.2s;
}

.input-project-name:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

/* Action buttons */
.action-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-action {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(28, 33, 40, 0.5);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-action:hover {
  border-color: var(--text-muted);
  color: var(--text);
}

.btn-action--primary {
  background: rgba(255, 107, 53, 0.12);
  border-color: var(--accent);
  color: var(--accent);
}

.btn-action--primary:hover {
  background: rgba(255, 107, 53, 0.2);
  color: var(--accent);
}

.btn-action-icon {
  width: 16px;
  height: 16px;
}

/* Error / loading */
.error {
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid var(--error);
  border-radius: 6px;
  padding: 10px 14px;
  color: var(--error);
  font-size: 0.8rem;
  margin: 0;
}

.loading-text {
  text-align: center;
  font-size: 0.78rem;
  color: var(--text-muted);
  margin: 0;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Activity Feed */
.feed-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 20px;
  letter-spacing: 0.02em;
}

.feed-empty {
  text-align: center;
  padding: 40px 0;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feed-card {
  background: rgba(28, 33, 40, 0.4);
  border: 1px solid rgba(48, 54, 61, 0.6);
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.feed-card:hover {
  border-color: rgba(255, 107, 53, 0.6);
  background: rgba(28, 33, 40, 0.8);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.feed-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 6px;
}

.feed-card-name {
  font-weight: 700;
  font-size: 0.88rem;
  color: var(--text);
}

.feed-card-delete {
  background: none;
  border: none;
  color: var(--error);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
  opacity: 0;
  transition: opacity 0.15s;
  font-family: inherit;
}

.feed-card:hover .feed-card-delete {
  opacity: 1;
}

.feed-card-delete:hover {
  background: rgba(248, 81, 73, 0.15);
  border-radius: 4px;
}

.feed-card-scenario {
  font-size: 0.73rem;
  color: var(--text-muted);
  margin: 0 0 10px;
  line-height: 1.4;
}

.feed-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 0.72rem;
  color: var(--text-muted);
}

.meta-count {
  color: var(--accent);
  font-weight: 700;
}

.meta-separator {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--border);
}

.feed-card-sims {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.feed-sim-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.7rem;
}

.feed-sim-bar {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.bar--success {
  background: var(--success);
  box-shadow: 0 0 4px var(--success);
}

.bar--muted {
  background: var(--border);
}

.feed-sim-status {
  color: var(--text-muted);
}

.text--success {
  color: var(--success);
}

.feed-sim-actions {
  color: var(--text-muted);
}

.feed-sim-report {
  background: rgba(255, 107, 53, 0.15);
  color: var(--accent);
  font-size: 0.65rem;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 600;
}

.feed-card-date {
  font-size: 0.68rem;
  color: var(--text-muted);
  opacity: 0.6;
}
</style>

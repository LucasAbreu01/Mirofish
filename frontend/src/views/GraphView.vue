<template>
  <div class="graph-view">
    <StepNav :currentStep="2" :projectId="route.params.id" />
    <header class="topbar">
      <div class="topbar-left">
        <h1 class="project-name">{{ projectState.projectName || 'Knowledge Graph' }}</h1>
      </div>
      <div class="topbar-center">
        <span class="badge">
          <span class="badge-count">{{ nodeCount }}</span> entities
        </span>
        <span class="badge">
          <span class="badge-count">{{ edgeCount }}</span> relationships
        </span>
      </div>
      <div class="topbar-right">
        <button class="btn-continue" @click="goToSetup">Continue to Setup</button>
      </div>
    </header>

    <div class="content">
      <div class="panel-graph">
        <GraphPanel
          v-if="graphData"
          :graph-data="graphData"
          @node-click="onNodeClick"
        />
        <div v-else class="loading-graph">
          <span class="spinner"></span>
          <p>Loading graph data&hellip;</p>
        </div>
      </div>

      <aside class="panel-detail">
        <div v-if="selectedNode" class="detail-card">
          <h2 class="detail-name">{{ selectedNode.name || selectedNode.entity_name || selectedNode.id }}</h2>
          <span class="detail-type" :style="{ color: typeColor }">{{ selectedNode.entity_type || 'Unknown' }}</span>

          <div v-if="selectedNode.description" class="detail-section">
            <h3 class="detail-heading">Description</h3>
            <p class="detail-text">{{ selectedNode.description }}</p>
          </div>

          <div v-if="selectedNode.attributes && Object.keys(selectedNode.attributes).length" class="detail-section">
            <h3 class="detail-heading">Attributes</h3>
            <ul class="attr-list">
              <li v-for="(value, key) in selectedNode.attributes" :key="key" class="attr-item">
                <span class="attr-key">{{ key }}</span>
                <span class="attr-value">{{ value }}</span>
              </li>
            </ul>
          </div>
        </div>

        <div v-else class="detail-empty">
          <p>Click a node to see details</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProject } from '../api/graph'
import { useProject } from '../store/project'
import GraphPanel from '../components/GraphPanel.vue'
import StepNav from '../components/StepNav.vue'

const route = useRoute()
const router = useRouter()
const { state: projectState, setProject, setGraph } = useProject()

const graphData = ref(null)
const selectedNode = ref(null)
const error = ref('')

const TYPE_COLORS = {
  Person: '#ff6b35',
  Organization: '#3fb950',
  Location: '#58a6ff',
  Event: '#d2a8ff',
  Concept: '#f0883e'
}

const nodeCount = computed(() => graphData.value?.nodes?.length || 0)
const edgeCount = computed(() => graphData.value?.edges?.length || 0)
const typeColor = computed(() => {
  if (!selectedNode.value) return '#8b949e'
  const t = selectedNode.value.entity_type
  if (!t) return '#8b949e'
  const normalized = t.charAt(0).toUpperCase() + t.slice(1).toLowerCase()
  return TYPE_COLORS[normalized] || '#8b949e'
})

function onNodeClick(node) {
  selectedNode.value = node
}

function goToSetup() {
  router.push(`/setup/${route.params.id}`)
}

onMounted(async () => {
  const id = route.params.id

  try {
    const data = await getProject(id)
    const project = data.project || data
    setProject(project)
    const graph = data.graph || project.graph
    if (graph) {
      setGraph(graph)
      graphData.value = graph
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load project'
  }
})
</script>

<style scoped>
.graph-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--text);
  font-family: 'JetBrains Mono', monospace;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.topbar-left,
.topbar-right {
  flex: 1;
}

.topbar-right {
  display: flex;
  justify-content: flex-end;
}

.topbar-center {
  display: flex;
  gap: 12px;
}

.project-name {
  font-size: 0.95rem;
  font-weight: 600;
  margin: 0;
  color: var(--text);
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 4px 12px;
}

.badge-count {
  color: var(--text);
  font-weight: 600;
}

.btn-continue {
  padding: 8px 18px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
}

.btn-continue:hover {
  background: #e55a28;
  transform: translateY(-1px);
}

.content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.panel-graph {
  flex: 0 0 60%;
  position: relative;
  border-right: 1px solid var(--border);
}

.panel-detail {
  flex: 0 0 40%;
  overflow-y: auto;
  padding: 24px;
}

.loading-graph {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.detail-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.detail-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 24px;
}

.detail-name {
  font-size: 1.2rem;
  font-weight: 700;
  margin: 0 0 6px;
  color: var(--text);
}

.detail-type {
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.detail-section {
  margin-top: 20px;
}

.detail-heading {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 8px;
}

.detail-text {
  font-size: 0.85rem;
  color: var(--text);
  line-height: 1.6;
  margin: 0;
}

.attr-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.attr-item {
  display: flex;
  gap: 10px;
  font-size: 0.8rem;
  padding: 6px 10px;
  background: var(--bg-secondary);
  border-radius: 4px;
}

.attr-key {
  color: var(--text-muted);
  flex-shrink: 0;
  min-width: 100px;
}

.attr-value {
  color: var(--text);
  word-break: break-word;
}
</style>

<template>
  <div class="action-feed" ref="feedContainer">
    <div v-if="actions.length === 0" class="empty-feed">
      <p>Waiting for simulation actions...</p>
    </div>
    <div
      v-for="(action, index) in actions"
      :key="index"
      class="action-item"
    >
      <div class="action-header">
        <span class="round-badge">R{{ action.round }}</span>
        <span class="agent-name" :style="{ color: agentColor(action.agent_name) }">
          {{ action.agent_name }}
        </span>
        <span class="action-type" :class="actionTypeClass(action.action_type)">
          {{ action.action_type }}
        </span>
      </div>
      <div v-if="action.action_type === 'REPLY' && action.target" class="reply-ref">
        Replying to: <span class="reply-target">{{ action.target }}</span>
      </div>
      <p class="action-content">{{ action.content }}</p>
      <p v-if="action.reasoning" class="action-reasoning">{{ action.reasoning }}</p>
      <div v-if="action.memories_used && action.memories_used.length" class="memories-section">
        <button class="memories-toggle" @click="toggleMemories(index)">
          {{ expandedMemories[index] ? 'Hide' : 'Show' }} memories recalled ({{ action.memories_used.length }})
        </button>
        <ul v-if="expandedMemories[index]" class="memories-list">
          <li v-for="(mem, mi) in action.memories_used" :key="mi" class="memory-item">
            {{ mem }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, nextTick } from 'vue'

const props = defineProps({
  actions: {
    type: Array,
    default: () => []
  }
})

const feedContainer = ref(null)
const expandedMemories = reactive({})

function toggleMemories(index) {
  expandedMemories[index] = !expandedMemories[index]
}

watch(
  () => props.actions.length,
  async () => {
    await nextTick()
    if (feedContainer.value) {
      feedContainer.value.scrollTop = feedContainer.value.scrollHeight
    }
  }
)

const nameColors = {}
const palette = ['#58a6ff', '#3fb950', '#d2a8ff', '#f0883e', '#f85149', '#79c0ff', '#7ee787', '#e3b341', '#ffa198', '#a5d6ff']
let colorIndex = 0

function agentColor(name) {
  if (!name) return '#8b949e'
  if (!nameColors[name]) {
    nameColors[name] = palette[colorIndex % palette.length]
    colorIndex++
  }
  return nameColors[name]
}

function actionTypeClass(type) {
  const t = (type || '').toUpperCase()
  return {
    'type-post': t === 'POST',
    'type-reply': t === 'REPLY',
    'type-react': t === 'REACT',
    'type-opinion': t === 'OPINION',
    'type-nothing': t === 'NOTHING'
  }
}
</script>

<style scoped>
.action-feed {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-feed::-webkit-scrollbar {
  width: 6px;
}

.action-feed::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

.action-feed::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 3px;
}

.empty-feed {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  font-size: 14px;
}

.action-item {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  transition: border-color 0.2s;
}

.action-item:hover {
  border-color: #484f58;
}

.action-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.round-badge {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}

.agent-name {
  font-size: 13px;
  font-weight: 600;
}

.action-type {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-left: auto;
}

.type-post {
  background: rgba(88, 166, 255, 0.15);
  color: #58a6ff;
}

.type-reply {
  background: rgba(63, 185, 80, 0.15);
  color: #3fb950;
}

.type-react {
  background: rgba(255, 107, 53, 0.15);
  color: #ff6b35;
}

.type-opinion {
  background: rgba(210, 168, 255, 0.15);
  color: #d2a8ff;
}

.type-nothing {
  background: rgba(139, 148, 158, 0.15);
  color: #8b949e;
}

.reply-ref {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
  padding-left: 10px;
  border-left: 2px solid var(--border);
}

.reply-target {
  color: var(--text);
  font-style: italic;
}

.action-content {
  font-size: 13px;
  color: var(--text);
  line-height: 1.5;
}

.action-reasoning {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
  font-style: italic;
  line-height: 1.4;
}

.memories-section {
  margin-top: 8px;
  border-top: 1px solid var(--border);
  padding-top: 6px;
}

.memories-toggle {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  padding: 2px 0;
  transition: color 0.2s;
}

.memories-toggle:hover {
  color: var(--accent);
}

.memories-list {
  list-style: none;
  padding: 0;
  margin: 6px 0 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.memory-item {
  font-size: 11px;
  color: var(--text-muted);
  font-style: italic;
  line-height: 1.4;
  padding: 4px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  border-left: 2px solid var(--accent);
}
</style>

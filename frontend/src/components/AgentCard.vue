<template>
  <div class="agent-card" :class="{ editing: isEditing }">
    <div class="card-header">
      <div class="avatar" :style="{ background: avatarColor }">
        {{ agent.name?.charAt(0)?.toUpperCase() || '?' }}
      </div>
      <div class="header-info">
        <h3 class="agent-name">{{ agent.name }}</h3>
        <span class="agent-profession">{{ agent.profession || 'Unknown' }}</span>
      </div>
      <span class="type-badge" :style="{ background: avatarColor + '22', color: avatarColor }">
        {{ agent.entity_type || 'agent' }}
      </span>
    </div>

    <div v-if="!isEditing" class="card-body">
      <div class="field">
        <span class="field-label">Personality</span>
        <p class="field-text" :class="{ expanded: personalityExpanded }" @click="personalityExpanded = !personalityExpanded">
          {{ agent.personality }}
        </p>
      </div>
      <div v-if="agent.goals" class="field">
        <span class="field-label">Goals</span>
        <p class="field-text-small">{{ agent.goals }}</p>
      </div>
      <div class="card-meta">
        <span v-if="agent.age" class="meta-item">Age: {{ agent.age }}</span>
        <span v-if="agent.communication_style" class="meta-item">Style: {{ agent.communication_style }}</span>
      </div>
      <button class="btn-edit" @click="startEdit">Edit</button>
    </div>

    <div v-else class="card-body edit-mode">
      <div class="edit-field">
        <label>Personality</label>
        <textarea v-model="editData.personality" rows="3" />
      </div>
      <div class="edit-field">
        <label>Goals</label>
        <textarea v-model="editData.goals" rows="2" />
      </div>
      <div class="edit-field">
        <label>Backstory</label>
        <textarea v-model="editData.backstory" rows="3" />
      </div>
      <div class="edit-actions">
        <button class="btn-save" @click="saveEdit">Save</button>
        <button class="btn-cancel" @click="cancelEdit">Cancel</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  agent: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update'])

const isEditing = ref(false)
const personalityExpanded = ref(false)
const editData = ref({})

const typeColors = {
  human: '#3fb950',
  person: '#3fb950',
  bot: '#58a6ff',
  influencer: '#d2a8ff',
  troll: '#f85149',
  moderator: '#f0883e',
  organization: '#f0883e',
  company: '#f0883e',
  government: '#f0883e',
  agent: '#58a6ff',
  default: '#8b949e'
}

const avatarColor = computed(() => {
  const t = (props.agent.entity_type || '').toLowerCase()
  return typeColors[t] || typeColors.default
})

function startEdit() {
  editData.value = {
    personality: props.agent.personality || '',
    goals: props.agent.goals || '',
    backstory: props.agent.backstory || ''
  }
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
}

function saveEdit() {
  emit('update', { ...props.agent, ...editData.value })
  isEditing.value = false
}
</script>

<style scoped>
.agent-card {
  background: rgba(28, 33, 40, 0.4);
  border: 1px solid rgba(48, 54, 61, 0.6);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.25s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.agent-card:hover {
  border-color: rgba(255, 107, 53, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

.agent-card.editing {
  border-color: var(--accent);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.header-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--font-sans);
}

.agent-profession {
  font-size: 12px;
  color: var(--text-muted);
}

.type-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
  border: 1px solid currentColor;
  background: transparent !important;
}

.field {
  margin-bottom: 10px;
}

.field-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 4px;
}

.field-text {
  font-size: 13px;
  color: var(--text);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}

.field-text.expanded {
  -webkit-line-clamp: unset;
}

.field-text-small {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}

.card-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
}

.meta-item {
  font-size: 11px;
  color: var(--text-muted);
}

.btn-edit {
  width: 100%;
  padding: 6px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  transition: all 0.2s;
}

.btn-edit:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.edit-mode .edit-field {
  margin-bottom: 10px;
}

.edit-mode label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 4px;
}

.edit-mode textarea {
  width: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  padding: 8px;
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
}

.edit-mode textarea:focus {
  outline: none;
  border-color: var(--accent);
}

.edit-actions {
  display: flex;
  gap: 8px;
}

.btn-save,
.btn-cancel {
  flex: 1;
  padding: 6px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  font-weight: 600;
}

.btn-save {
  background: var(--accent);
  color: #fff;
}

.btn-save:hover {
  opacity: 0.9;
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
}

.btn-cancel:hover {
  border-color: var(--text-muted);
}
</style>

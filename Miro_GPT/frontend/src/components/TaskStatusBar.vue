<script setup lang="ts">
import type { TaskRecord } from '../types'

defineProps<{
  task?: TaskRecord | null
}>()
</script>

<template>
  <section v-if="task" class="task-panel">
    <div class="task-row">
      <div>
        <p class="task-kind">{{ task.kind }}</p>
        <strong>{{ task.message }}</strong>
      </div>
      <span class="task-state" :class="task.status">{{ task.status }}</span>
    </div>
    <div class="task-track">
      <div class="task-fill" :style="{ width: `${task.progress}%` }"></div>
    </div>
    <p v-if="task.error" class="task-error">{{ task.error }}</p>
  </section>
</template>

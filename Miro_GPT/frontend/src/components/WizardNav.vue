<script setup lang="ts">
const props = defineProps<{
  step: 'upload' | 'graph' | 'simulation' | 'report'
  projectId?: string
  simulationId?: string
  reportId?: string
}>()

const items: Array<{ key: string; label: string; to: string; disabled: boolean }> = [
  { key: 'upload', label: '1 Upload', to: '/', disabled: false },
  {
    key: 'graph',
    label: '2 Graph',
    to: props.projectId ? `/projects/${props.projectId}/graph` : '/',
    disabled: !props.projectId,
  },
  {
    key: 'simulation',
    label: '3 Simulation',
    to: props.projectId
      ? `/projects/${props.projectId}/simulation/${props.simulationId ?? ''}`
      : '/',
    disabled: !props.projectId,
  },
  {
    key: 'report',
    label: '4 Report',
    to: props.reportId ? `/reports/${props.reportId}` : '/',
    disabled: !props.reportId,
  },
] as const
</script>

<template>
  <nav class="wizard-nav">
    <RouterLink
      v-for="item in items"
      :key="item.key"
      :to="item.to"
      class="wizard-link"
      :class="{ active: item.key === step, disabled: item.disabled }"
    >
      <span>{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>

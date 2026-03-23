<template>
  <nav class="step-nav">
    <button class="btn-home" @click="router.push('/')" title="New Simulation">
      <svg viewBox="0 0 16 16" fill="currentColor" class="home-icon">
        <path d="M8.354 1.146a.5.5 0 00-.708 0l-6.5 6.5A.5.5 0 001.5 8.5h1v6a.5.5 0 00.5.5h3a.5.5 0 00.5-.5V11h2v3.5a.5.5 0 00.5.5h3a.5.5 0 00.5-.5v-6h1a.5.5 0 00.354-.854l-6.5-6.5z"/>
      </svg>
      <span>+ New</span>
    </button>

    <div class="steps-center">
      <div
        v-for="(step, i) in steps"
        :key="i"
        class="step"
        :class="{
          'step--completed': i + 1 < currentStep,
          'step--active': i + 1 === currentStep,
          'step--future': i + 1 > currentStep,
          'step--clickable': isClickable(i + 1)
        }"
        @click="handleClick(i + 1)"
      >
        <span class="step-dot">
          <svg v-if="i + 1 < currentStep" class="step-check" viewBox="0 0 16 16" fill="currentColor">
            <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
          </svg>
          <span v-else class="step-number">{{ i + 1 }}</span>
        </span>
        <span class="step-label">{{ step }}</span>
        <span v-if="i < steps.length - 1" class="step-connector"></span>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const props = defineProps({
  currentStep: {
    type: Number,
    default: 1,
    validator: v => v >= 1 && v <= 5
  },
  projectId: {
    type: String,
    default: ''
  },
  simulationId: {
    type: String,
    default: ''
  }
})

const steps = ['Upload', 'Graph', 'Setup', 'Simulate', 'Report']

function isClickable(stepNum) {
  return stepNum < props.currentStep
}

function handleClick(stepNum) {
  if (!isClickable(stepNum)) return

  const routes = {
    1: '/',
    2: props.projectId ? `/graph/${props.projectId}` : null,
    3: props.projectId ? `/setup/${props.projectId}` : null,
    4: props.simulationId ? `/simulation/${props.simulationId}` : null,
    5: props.simulationId ? `/report/${props.simulationId}` : null
  }

  const target = routes[stepNum]
  if (target) router.push(target)
}
</script>

<style scoped>
.step-nav {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  font-family: 'JetBrains Mono', monospace;
  gap: 0;
}

.btn-home {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-muted);
  font-family: inherit;
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  margin-right: auto;
  white-space: nowrap;
}

.btn-home:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(255, 107, 53, 0.08);
}

.home-icon {
  width: 14px;
  height: 14px;
}

.steps-center {
  display: flex;
  align-items: center;
  margin: 0 auto;
}

.step {
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
}

.step-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  font-weight: 700;
  flex-shrink: 0;
  transition: background 0.2s, border-color 0.2s;
}

.step--completed .step-dot {
  background: var(--success);
  color: #fff;
}

.step--active .step-dot {
  background: var(--accent);
  color: #fff;
}

.step--future .step-dot {
  background: transparent;
  border: 2px solid var(--border);
  color: var(--text-muted);
}

.step-check {
  width: 12px;
  height: 12px;
}

.step-label {
  font-size: 0.7rem;
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.step--completed .step-label {
  color: var(--success);
}

.step--active .step-label {
  color: var(--accent);
  font-weight: 600;
}

.step--future .step-label {
  color: var(--text-muted);
}

.step-connector {
  display: block;
  width: 32px;
  height: 1px;
  margin: 0 8px;
  flex-shrink: 0;
}

.step--completed .step-connector {
  background: var(--success);
}

.step--active .step-connector {
  background: var(--border);
}

.step--future .step-connector {
  background: var(--border);
}

.step--clickable {
  cursor: pointer;
}

.step--clickable:hover .step-dot {
  filter: brightness(1.3);
  transform: scale(1.1);
}

.step--clickable:hover .step-label {
  text-decoration: underline;
}
</style>

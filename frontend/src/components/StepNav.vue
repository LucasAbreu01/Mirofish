<template>
  <nav class="step-nav">
    <div
      v-for="(step, i) in steps"
      :key="i"
      class="step"
      :class="{
        'step--completed': i + 1 < currentStep,
        'step--active': i + 1 === currentStep,
        'step--future': i + 1 > currentStep
      }"
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
  </nav>
</template>

<script setup>
defineProps({
  currentStep: {
    type: Number,
    default: 1,
    validator: v => v >= 1 && v <= 5
  }
})

const steps = ['Upload', 'Graph', 'Setup', 'Simulate', 'Report']
</script>

<style scoped>
.step-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  font-family: 'JetBrains Mono', monospace;
  gap: 0;
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
</style>

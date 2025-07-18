<template>
  <div class="tax-progress-container">
    <div class="progress-header">
      <span class="progress-text">
        Step {{ currentStep }} of {{ totalSteps }}: {{ currentStepLabel }}
      </span>
      <span class="progress-percentage">{{ Math.round(progressPercentage) }}%</span>
    </div>

    <div
      :style="{
        width: '100%',
        height: '8px',
        backgroundColor: '#e0e0e0',
        borderRadius: '4px',
        overflow: 'hidden',
        position: 'relative',
        marginBottom: '0.5rem'
      }"
    >
      <div
        :style="{
          width: progressPercentage + '%',
          height: '100%',
          background: 'linear-gradient(90deg, #4caf50, #45a049)',
          transition: 'width 0.3s ease-in-out',
          borderRadius: '4px',
          position: 'absolute',
          top: '0',
          left: '0'
        }"
      ></div>
    </div>

    <div class="progress-status">
      <Markdown v-if="currentStep === 1" :markdownContent="statusText" />
      <span class="status-text" v-else>{{ statusText }}</span>
    </div>
  </div>
</template>


<script setup>
import { ref, computed, watch } from 'vue'
import Markdown from './Markdown.vue'
const props = defineProps({
  status: {
    type: String,
    default: 'idle' // idle, processing, complete, error
  },
  currentStep: {
    type: Number,
    default: 0
  },
  totalSteps: {
    type: Number,
    default: 5
  },
  statusText: {
    type: String,
    default: 'Ready to process'
  }
})

// Steps representing tax file processing
const stepLabels = [
  'Uploading file',
  'Processing data',
  'Analyzing content',
  'Generating report',
  'Finalizing results'
]

// Calculate progress % for the bar
const progressPercentage = computed(() => {
  if (props.status === 'complete') return 100
  if (props.status === 'error') return 0
  return Math.min((props.currentStep / props.totalSteps) * 100, 100)
})

// Label for the current step
const currentStepLabel = computed(() => {
  if (props.status === 'complete') return 'Complete'
  if (props.status === 'error') return 'Error'
  if (props.currentStep === 0) return 'Initializing...'
  return stepLabels[props.currentStep - 1] || 'Processing...'
})
</script>

<style scoped>
.tax-progress-container {
  padding: 1rem;
  background: rgba(45, 45, 53, 0.1);
  backdrop-filter: blur(2px);
  border-radius: 8px;
  margin: 0.5rem 0;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  color: var(--text-color, #333);
}

.progress-text {
  font-weight: 500;
}

.progress-percentage {
  font-weight: 600;
  color: #4caf50;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #45a049);
  transition: width 0.3s ease-in-out;
  border-radius: 4px;
}

.progress-status {
  font-size: 0.8rem;
  color: var(--text-color, #666);
  opacity: 0.8;
}

.status-text {
  font-style: italic;
}
</style>

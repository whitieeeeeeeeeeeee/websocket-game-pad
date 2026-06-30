<template>
  <span class="ws-badge" :class="statusClass" role="status" :aria-label="ariaLabel">
    <span class="dot"></span>
    {{ displayLabel }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  status: 'connected' | 'connecting' | 'disconnected' | 'recording' | 'playing' | 'idle'
  label?: string
}

const props = withDefaults(defineProps<Props>(), {
  label: ''
})

const statusClass = computed(() => {
  switch (props.status) {
    case 'connected': return 'connected'
    case 'connecting': return 'connecting'
    case 'disconnected': return 'disconnected'
    case 'recording': return 'recording'
    case 'playing': return 'playing'
    case 'idle': return 'disconnected'
    default: return 'disconnected'
  }
})

const displayLabel = computed(() => {
  if (props.label) return props.label
  switch (props.status) {
    case 'connected': return '已连接'
    case 'connecting': return '连接中'
    case 'disconnected': return '未连接'
    case 'recording': return '录制中'
    case 'playing': return '回放中'
    case 'idle': return '空闲'
    default: return ''
  }
})

const ariaLabel = computed(() => `状态: ${displayLabel.value}`)
</script>

<style scoped>
/* recording 状态：橙色 */
.ws-badge.recording {
  background: var(--state-recording-subtle);
  border-color: var(--state-recording-border);
  color: var(--state-recording-text);
}
.ws-badge.recording .dot {
  background: var(--state-recording);
  animation: pulse-dot 1.2s ease-in-out infinite;
}

/* playing 状态：紫色 */
.ws-badge.playing {
  background: var(--state-playback-subtle);
  border-color: var(--state-playback-border);
  color: var(--state-playback-text);
}
.ws-badge.playing .dot {
  background: var(--state-playback);
  animation: pulse-dot 1.2s ease-in-out infinite;
}
</style>

<template>
  <div class="card" style="flex:1; display:flex; flex-direction:column;">
    <div class="panel-title">
      <h3>数据发送</h3>
    </div>
    <div class="tab-bar" style="margin-bottom:8px;">
      <button
        class="pill"
        :class="{ active: format === 'text' }"
        @click="changeFormat('text')"
      >文本</button>
      <button
        class="pill"
        :class="{ active: format === 'hex' }"
        @click="changeFormat('hex')"
      >HEX</button>
    </div>
    <div class="sender-toolbar">
      <select
        v-model="encoding"
        style="height:28px; padding:0 8px; font-size:11px; border-radius:calc(var(--space-4) * 3);"
        aria-label="编码选择"
        :disabled="disabled"
      >
        <option value="UTF-8">UTF-8</option>
        <option value="GBK">GBK</option>
        <option value="ASCII">ASCII</option>
      </select>
    </div>
    <div v-if="mode === 'server'" class="sender-target-bar" style="display:flex; gap:8px; align-items:center; margin-bottom:8px; flex-wrap:wrap;">
      <div class="tab-bar" style="margin:0;">
        <button class="pill" :class="{ active: sendTarget === 'broadcast' }" @click="sendTarget = 'broadcast'">广播所有</button>
        <button class="pill" :class="{ active: sendTarget === 'directional' }" @click="sendTarget = 'directional'">定向发送</button>
      </div>
      <select
        v-if="sendTarget === 'directional'"
        v-model="selectedClientId"
        style="height:28px; padding:0 8px; font-size:11px; border-radius:calc(var(--space-4) * 3);"
        aria-label="选择客户端"
        :disabled="disabled"
      >
        <option value="" disabled>选择客户端</option>
        <option v-for="client in serverClients" :key="client.client_id" :value="client.client_id">
          {{ client.client_id }} ({{ client.ip }}:{{ client.port }})
        </option>
      </select>
    </div>
    <textarea
      v-if="format === 'text'"
      v-model="dataInput"
      class="sender-textarea"
      placeholder="输入要发送的数据..."
      aria-label="发送数据"
      :disabled="disabled"
      @keydown.ctrl.enter="handleSend"
    ></textarea>
    <input
      v-else
      v-model="dataInput"
      type="text"
      class="sender-textarea hex-input"
      placeholder="输入十六进制数据，如: FF 01 AB"
      aria-label="发送数据"
      :disabled="disabled"
      @keydown.ctrl.enter="handleSend"
    />
    <div class="sender-counter">{{ charCount }} 字符 / {{ byteCount }} 字节</div>
    <div class="sender-footer">
      <button
        class="btn primary"
        @click="handleSend"
        :disabled="disabled || !canSend"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        发送
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  mode?: 'client' | 'server'
  disabled?: boolean
  serverClients?: Array<{ client_id: string; ip: string; port: number }>
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'client',
  disabled: false,
  serverClients: () => []
})

const emit = defineEmits<{
  (e: 'send', data: { data: string; format: string; encoding: string; clientId: string | null }): void
}>()

const format = ref<'text' | 'hex'>('text')
const encoding = ref<string>('UTF-8')
const dataInput = ref('')
const sendTarget = ref<'broadcast' | 'directional'>('broadcast')
const selectedClientId = ref<string>('')

const charCount = computed(() => dataInput.value.length)

const byteCount = computed(() => {
  if (format.value === 'hex') {
    const clean = dataInput.value.replace(/\s/g, '')
    return Math.floor(clean.length / 2)
  }
  return new TextEncoder().encode(dataInput.value).length
})

const canSend = computed(() => dataInput.value.trim().length > 0)

function changeFormat(newFormat: 'text' | 'hex') {
  if (format.value !== newFormat) {
    format.value = newFormat
    dataInput.value = ''
  }
}

function handleSend() {
  if (props.disabled || !canSend.value) return
  const clientId = (props.mode === 'server' && sendTarget.value === 'directional')
    ? selectedClientId.value
    : null
  emit('send', {
    data: dataInput.value,
    format: format.value,
    encoding: encoding.value,
    clientId
  })
  dataInput.value = ''
}
</script>

<style scoped>
.hex-input {
  min-height: auto;
  height: 32px;
  resize: none;
}
</style>

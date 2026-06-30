<template>
  <div class="card">
    <div class="panel-title">
      <h3>手柄状态</h3>
    </div>

    <!-- Gamepad Visualizer -->
    <div class="gamepad-wrap">
      <ControllerVisualizer />
    </div>

    <!-- Axis Data Grid -->
    <div class="axis-grid">
      <div class="axis-cell">
        <span class="axis-label">LX</span>
        <span class="axis-value">{{ axes.LX.toFixed(2) }}</span>
      </div>
      <div class="axis-cell">
        <span class="axis-label">LY</span>
        <span class="axis-value">{{ axes.LY.toFixed(2) }}</span>
      </div>
      <div class="axis-cell">
        <span class="axis-label">RX</span>
        <span class="axis-value">{{ axes.RX.toFixed(2) }}</span>
      </div>
      <div class="axis-cell">
        <span class="axis-label">RY</span>
        <span class="axis-value">{{ axes.RY.toFixed(2) }}</span>
      </div>
    </div>

    <!-- Send Mode -->
    <div class="send-mode-row" role="group" aria-label="发送模式">
      <span class="send-mode-label">发送模式</span>
      <div class="tab-bar" style="margin:0;">
        <button
          class="pill"
          :class="{ active: controllerSendMode === 'continuous' }"
          :aria-pressed="controllerSendMode === 'continuous'"
          @click="handleSendModeChange('continuous')"
        >持续发送</button>
        <button
          class="pill"
          :class="{ active: controllerSendMode === 'onchange' }"
          :aria-pressed="controllerSendMode === 'onchange'"
          @click="handleSendModeChange('onchange')"
        >改变发送</button>
      </div>
    </div>

    <!-- Frequency Slider -->
    <div class="slider-row">
      <label for="freq-slider">频率 Hz</label>
      <input
        id="freq-slider"
        type="range"
        min="10"
        max="60"
        step="1"
        aria-label="控制器数据发送频率"
        v-model="controllerFrequency"
        @change="handleFrequencyChange"
      />
      <span class="slider-value">{{ controllerFrequency }}</span>
    </div>

    <!-- Toggle -->
    <div class="toggle-row">
      <label for="mapping-toggle">按键映射发送</label>
      <button
        id="mapping-toggle"
        class="toggle"
        :class="buttonMappingSendEnabled ? 'on' : 'off'"
        :aria-pressed="buttonMappingSendEnabled"
        aria-label="按键映射发送开关"
        @click="buttonMappingSendEnabled = !buttonMappingSendEnabled"
      >
        <span></span>
      </button>
    </div>

    <!-- Manual Reconnect -->
    <button
      class="btn secondary"
      style="margin-top: 12px; width: 100%;"
      :disabled="reconnecting"
      @click="handleReconnect"
    >
      {{ reconnecting ? '重连中...' : '手动重连' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useAppStore } from '@/stores/app'
import { api } from '@/api/client'
import type { SendMode } from '@/types'
import ControllerVisualizer from '@/components/ControllerVisualizer.vue'

const appStore = useAppStore()
const { controllerFrequency, controllerSendMode, buttonMappingSendEnabled } = storeToRefs(appStore)

const axes = computed(() => appStore.controllerState.axes)
const reconnecting = ref(false)
const userSelectedMode = ref(false)

async function handleFrequencyChange(event: Event) {
  const target = event.target as HTMLInputElement
  const value = parseInt(target.value, 10)
  if (isNaN(value) || value < 10 || value > 60) return
  try {
    await api.setControllerFrequency(value)
  } catch (e) {
    console.error('[wifi-spi] Failed to set controller frequency:', e)
  }
}

async function handleSendModeChange(mode: SendMode) {
  if (controllerSendMode.value === mode) return
  controllerSendMode.value = mode
  userSelectedMode.value = true
  try {
    await api.setControllerSendMode(mode)
  } catch (e) {
    console.error('[wifi-spi] Failed to set send mode:', e)
  }
}

async function handleReconnect() {
  reconnecting.value = true
  try {
    await appStore.refreshControllerStatus()
  } catch (e) {
    console.error('[wifi-spi] Reconnect failed:', e)
  } finally {
    reconnecting.value = false
  }
}

onMounted(async () => {
  try {
    const res = await api.getControllerFrequency()
    if (res && typeof res.frequency === 'number') {
      const freq = Math.round(res.frequency)
      if (freq >= 10 && freq <= 60) {
        controllerFrequency.value = freq
      }
    }
    const mode = await api.getControllerSendMode()
    if (mode === 'continuous' || mode === 'onchange') {
      // 始终以后端为准（后端已持久化到 config.json）
      // 除非用户在本次会话中已手动切换过模式
      if (!userSelectedMode.value) {
        controllerSendMode.value = mode
      }
    }
  } catch (e) {
    console.warn('[wifi-spi] Failed to fetch controller frequency:', e)
  }
})
</script>

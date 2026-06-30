<template>
  <div class="card recording-panel">
    <div class="tab-bar">
      <button
        class="pill"
        :class="{ active: activeTab === 'control' }"
        @click="activeTab = 'control'"
        role="tab"
      >录制控制</button>
      <button
        class="pill"
        :class="{ active: activeTab === 'list' }"
        @click="activeTab = 'list'"
        role="tab"
      >录制列表</button>
    </div>

    <!-- Recording Control Tab -->
    <div class="tab-content" :class="{ active: activeTab === 'control' }" data-tab="rec-ctrl">
      <div class="rec-btn-row">
        <button
          class="btn primary"
          @click="handleStartRecording"
          :disabled="recordingState.status !== 'idle' || recLoading"
        >
          <Circle :size="12" />
          开始录制
        </button>
        <button
          class="btn secondary"
          @click="handlePauseRecording"
          :disabled="recordingState.status !== 'recording' || recLoading"
        >
          <Pause :size="12" />
          暂停
        </button>
        <button
          class="btn secondary"
          @click="handleResumeRecording"
          :disabled="recordingState.status !== 'paused' || recLoading"
        >
          <Play :size="12" />
          继续
        </button>
        <button
          class="btn danger"
          @click="handleStopRecording"
          :disabled="recordingState.status === 'idle' || recLoading"
        >
          <Square :size="12" />
          停止
        </button>
      </div>
      <div class="rec-input-row">
        <input
          v-model="recName"
          type="text"
          placeholder="录制名称"
          aria-label="录制名称"
        />
      </div>
      <div class="rec-timer">{{ formatTime(displayDuration) }}</div>
      <div class="rec-frames">帧数: {{ recordingState.current_frames }}</div>

      <!-- Playback Section -->
      <div class="playback-section">
        <div class="playback-progress" :class="{ playing: playbackState.status === 'playing' }">
          <span class="bar" :style="{ width: playbackProgress + '%' }"></span>
          <input
            type="range"
            min="0"
            max="100"
            step="0.1"
            :value="playbackProgress"
            @change="handleSeek"
            :disabled="playbackState.status === 'idle'"
            aria-label="回放进度"
            class="playback-seek-input"
          />
        </div>
        <div class="playback-controls">
          <button
            class="btn secondary icon-only playback-btn"
            :class="{ active: playbackState.status === 'playing' }"
            @click="handlePlayButton"
            :disabled="playbackState.status === 'playing' || playLoading || !selectedRecordingId"
            aria-label="播放"
          >
            <Play :size="14" />
          </button>
          <button
            class="btn secondary icon-only playback-btn"
            :class="{ active: playbackState.status === 'paused' }"
            @click="handlePausePlayback"
            :disabled="playbackState.status !== 'playing' || playLoading"
            aria-label="暂停回放"
          >
            <Pause :size="14" />
          </button>
          <button
            class="btn secondary icon-only playback-btn"
            :class="{ active: playbackState.status === 'idle' }"
            @click="handleStopPlayback"
            :disabled="playbackState.status === 'idle' || playLoading"
            aria-label="停止回放"
          >
            <Square :size="14" />
          </button>
          <div class="speed-pills">
            <button
              v-for="speed in [0.5, 1, 2]"
              :key="speed"
              class="speed-pill"
              :class="{ active: playbackSpeed === speed }"
              @click="handleSpeedChange(speed)"
            >{{ speed }}x</button>
          </div>
          <div class="custom-speed" style="display:flex; align-items:center; gap:4px; margin-left:8px;">
            <input
              v-model="customSpeedInput"
              type="number"
              min="0.1"
              max="10"
              step="0.1"
              style="width:60px; height:24px; padding:0 4px; font-size:11px; border:1px solid var(--color-border); border-radius:4px; background:var(--color-surface); color:var(--color-text);"
              aria-label="自定义倍速"
              @keydown.enter="handleCustomSpeed"
            />
            <button
              class="btn secondary playback-btn"
              :class="{ active: ![0.5, 1, 2].includes(playbackSpeed) }"
              style="height:24px; padding:0 6px; font-size:11px;"
              @click="handleCustomSpeed"
            >自定义</button>
          </div>
        </div>
      </div>

      <div class="toggle-row" style="margin-top:12px;">
        <label>禁止真手柄</label>
        <button
          class="toggle"
          :class="blockRealController ? 'on' : 'off'"
          @click="handleToggleBlockRealController"
          aria-label="禁止真手柄开关"
        >
          <span></span>
        </button>
      </div>
    </div>

    <!-- Recording List Tab -->
    <div class="tab-content" :class="{ active: activeTab === 'list' }" data-tab="rec-list">
      <div style="margin-bottom:8px;">
        <button
          class="btn secondary"
          @click="handleImport"
          :disabled="importLoading"
        >
          <Import :size="12" />
          导入
        </button>
      </div>
      <div v-if="recordings.length === 0" class="empty-state">暂无录制记录</div>
      <div v-else class="rec-list panel-scroll">
        <div
          v-for="rec in recordings"
          :key="rec.id"
          class="rec-list-item"
        >
          <div class="rec-list-info">
            <div class="rec-list-name">{{ rec.name }}</div>
            <div class="rec-list-meta">{{ formatTime(rec.duration) }} · {{ rec.frame_count }} 帧</div>
          </div>
          <div class="rec-list-actions">
            <button
              class="btn ghost icon-only"
              @click="handlePlay(rec.id)"
              aria-label="播放"
            >
              <Play :size="12" />
            </button>
            <button
              class="btn ghost icon-only"
              @click="handleRename(rec)"
              aria-label="重命名"
            >
              <Pencil :size="12" />
            </button>
            <button
              class="btn ghost icon-only"
              @click="handleExport(rec)"
              aria-label="导出"
            >
              <Download :size="12" />
            </button>
            <button
              class="btn ghost icon-only"
              style="color: var(--color-danger-600);"
              @click="handleDelete(rec)"
              aria-label="删除"
            >
              <Trash2 :size="12" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <input
      ref="fileInputRef"
      type="file"
      accept=".json"
      style="display:none"
      @change="handleFileSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { api, isNetworkConnectionError } from '@/api/client'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Circle, Pause, Play, Square, Import, Pencil, Download, Trash2 } from 'lucide-vue-next'
import type { RecordingInfo } from '@/types'

const appStore = useAppStore()

const recordingState = computed(() => appStore.recordingState)
const playbackState = computed(() => appStore.playbackState)
const recordings = computed(() => appStore.recordings)

const activeTab = ref<'control' | 'list'>('control')
const recLoading = ref(false)
const playLoading = ref(false)
const importLoading = ref(false)
const selectedRecordingId = ref<string>('')
const playbackSpeed = ref(1)
const recName = ref<string>('')
const fileInputRef = ref<HTMLInputElement | null>(null)
const blockRealController = ref(true)

let localTimer: ReturnType<typeof setInterval> | null = null
let localDuration = 0
let lastBackendDuration = 0
let lastTimerUpdateTime = 0

const displayDuration = computed(() => {
  if (recordingState.value.status === 'recording') {
    return Math.max(recordingState.value.current_duration, localDuration)
  }
  return recordingState.value.current_duration
})

const playbackProgress = computed(() => playbackState.value.progress * 100)

function startLocalTimer() {
  stopLocalTimer()
  lastBackendDuration = recordingState.value.current_duration
  localDuration = lastBackendDuration
  lastTimerUpdateTime = Date.now()
  localTimer = setInterval(() => {
    const now = Date.now()
    const delta = (now - lastTimerUpdateTime) / 1000
    lastTimerUpdateTime = now
    localDuration += delta
  }, 100)
}

function stopLocalTimer() {
  if (localTimer) {
    clearInterval(localTimer)
    localTimer = null
  }
}

function resetLocalTimer() {
  stopLocalTimer()
  localDuration = 0
  lastBackendDuration = 0
  lastTimerUpdateTime = 0
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`
}

async function handleStartRecording() {
  recLoading.value = true
  try {
    const res = await api.startRecording(recName.value || undefined)
    if (res.success) {
      ElMessage.success('开始录制')
      recName.value = ''
    } else {
      ElMessage.error(res.message || '开始录制失败')
    }
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('录制失败，无法连接到后端服务')
    else ElMessage.error('录制失败，请稍后重试')
  } finally {
    recLoading.value = false
  }
}

async function handlePauseRecording() {
  recLoading.value = true
  try {
    const res = await api.pauseRecording()
    if (res.success) ElMessage.success('已暂停')
    else ElMessage.error(res.message || '暂停失败')
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('暂停失败，无法连接到后端服务')
    else ElMessage.error('暂停失败，请稍后重试')
  } finally {
    recLoading.value = false
  }
}

async function handleResumeRecording() {
  recLoading.value = true
  try {
    const res = await api.resumeRecording()
    if (res.success) ElMessage.success('继续录制')
    else ElMessage.error(res.message || '继续失败')
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('继续失败，无法连接到后端服务')
    else ElMessage.error('继续失败，请稍后重试')
  } finally {
    recLoading.value = false
  }
}

async function handleStopRecording() {
  recLoading.value = true
  try {
    const res = await api.stopRecording()
    if (res.success) {
      ElMessage.success('录制已保存')
      appStore.loadRecordings()
    } else {
      ElMessage.error(res.message || '停止失败')
    }
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('停止失败，无法连接到后端服务')
    else ElMessage.error('停止失败，请稍后重试')
  } finally {
    recLoading.value = false
  }
}

async function handlePlayButton() {
  if (playbackState.value.status === 'paused') {
    await handleResumePlayback()
  } else if (playbackState.value.status === 'idle') {
    await handleStartPlayback()
  }
}

async function handleStartPlayback() {
  if (!selectedRecordingId.value) return
  playLoading.value = true
  try {
    await api.setPlaybackMode(true, blockRealController.value)
    const res = await api.startPlayback(selectedRecordingId.value, playbackSpeed.value)
    if (res.success) ElMessage.success('开始回放')
    else ElMessage.error(res.message || '开始回放失败')
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('回放失败，无法连接到后端服务')
    else ElMessage.error('回放失败，请稍后重试')
  } finally {
    playLoading.value = false
  }
}

async function handleResumePlayback() {
  playLoading.value = true
  try {
    const res = await api.resumePlayback()
    if (res.success) ElMessage.success('继续回放')
    else ElMessage.error(res.message || '继续失败')
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('继续失败，无法连接到后端服务')
    else ElMessage.error('继续失败，请稍后重试')
  } finally {
    playLoading.value = false
  }
}

async function handlePausePlayback() {
  playLoading.value = true
  try {
    const res = await api.pausePlayback()
    if (res.success) ElMessage.success('已暂停回放')
    else ElMessage.error(res.message || '暂停失败')
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('暂停失败，无法连接到后端服务')
    else ElMessage.error('暂停失败，请稍后重试')
  } finally {
    playLoading.value = false
  }
}

async function handleStopPlayback() {
  playLoading.value = true
  try {
    const res = await api.stopPlayback()
    await api.setPlaybackMode(false, false)
    if (res.success) ElMessage.success('已停止回放')
    else ElMessage.error(res.message || '停止失败')
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('停止失败，无法连接到后端服务')
    else ElMessage.error('停止失败，请稍后重试')
  } finally {
    playLoading.value = false
  }
}

async function handleSpeedChange(speed: number) {
  playbackSpeed.value = speed
  if (playbackState.value.status === 'idle') return  // idle 时仅本地预设不调 API
  try {
    await api.setPlaybackSpeed(speed)
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('设置速度失败，无法连接到后端服务')
    else ElMessage.error('设置速度失败，请稍后重试')
  }
}

const customSpeedInput = ref<string>('1')

async function handleCustomSpeed() {
  const speed = parseFloat(customSpeedInput.value)
  if (isNaN(speed) || speed < 0.1 || speed > 10) {
    ElMessage.error('倍速必须在 0.1 ~ 10 之间')
    return
  }
  playbackSpeed.value = speed
  if (playbackState.value.status === 'idle') return
  try {
    await api.setPlaybackSpeed(speed)
    ElMessage.success(`倍速已设为 ${speed}x`)
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('设置速度失败，无法连接到后端服务')
    else ElMessage.error('设置速度失败，请稍后重试')
  }
}

async function handleSeek(event: Event) {
  const target = event.target as HTMLInputElement
  const value = parseFloat(target.value)
  if (isNaN(value)) return
  try {
    await api.seekPlayback(value / 100)
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('进度跳转失败，无法连接到后端服务')
    else ElMessage.error('进度跳转失败，请稍后重试')
  }
}

async function handleToggleBlockRealController() {
  blockRealController.value = !blockRealController.value
  if (playbackState.value.status !== 'idle') {
    try {
      await api.setPlaybackMode(true, blockRealController.value)
    } catch (e: any) {
      if (isNetworkConnectionError(e)) ElMessage.error('设置失败，无法连接到后端服务')
      else ElMessage.error('设置失败，请稍后重试')
    }
  }
}

async function handlePlay(id: string) {
  selectedRecordingId.value = id
  activeTab.value = 'control'
  if (playbackState.value.status === 'idle') {
    await handleStartPlayback()
  }
}

async function handleRename(rec: RecordingInfo) {
  try {
    const { value } = await ElMessageBox.prompt('输入新名称', '重命名', {
      inputValue: rec.name,
      inputValidator: (val) => val?.trim().length > 0 || '名称不能为空'
    })
    const res = await api.renameRecording(rec.id, value.trim())
    if (res.success) {
      ElMessage.success('重命名成功')
      appStore.loadRecordings()
    } else {
      ElMessage.error(res.message || '重命名失败')
    }
  } catch {
    // cancelled
  }
}

async function handleDelete(rec: RecordingInfo) {
  try {
    await ElMessageBox.confirm(`确定删除 "${rec.name}" 吗？`, '删除确认', { type: 'warning' })
    const res = await api.deleteRecording(rec.id)
    if (res.success) {
      ElMessage.success('删除成功')
      appStore.loadRecordings()
      if (selectedRecordingId.value === rec.id) selectedRecordingId.value = ''
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch {
    // cancelled
  }
}

async function handleExport(rec: RecordingInfo) {
  try {
    const jsonData = await api.exportRecording(rec.id)
    if (jsonData) {
      const blob = new Blob([jsonData], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${rec.name}.json`
      a.click()
      URL.revokeObjectURL(url)
      ElMessage.success('导出成功')
    } else {
      ElMessage.error('导出内容为空')
    }
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('导出失败，无法连接到后端服务')
    else ElMessage.error('导出失败，请稍后重试')
  }
}

function handleImport() {
  fileInputRef.value?.click()
}

async function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  importLoading.value = true
  try {
    const text = await file.text()
    const res = await api.importRecording(text)
    if (res.success) {
      ElMessage.success('导入成功')
      appStore.loadRecordings()
    } else {
      ElMessage.error(res.message || '导入失败')
    }
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('导入失败，无法连接到后端服务')
    else ElMessage.error('导入失败，请稍后重试')
  } finally {
    importLoading.value = false
    input.value = ''
  }
}

watch(() => playbackState.value.recording_id, (id) => {
  if (id && !selectedRecordingId.value) selectedRecordingId.value = id
})

watch(() => playbackState.value.speed, (newSpeed) => {
  if (newSpeed !== playbackSpeed.value) playbackSpeed.value = newSpeed
})

watch(() => recordingState.value.status, (newStatus) => {
  if (newStatus === 'recording') startLocalTimer()
  else if (newStatus === 'paused') stopLocalTimer()
  else if (newStatus === 'idle') resetLocalTimer()
}, { immediate: true })

watch(() => recordingState.value.current_duration, (newDuration) => {
  if (newDuration > localDuration) {
    localDuration = newDuration
    lastBackendDuration = newDuration
  }
})

onUnmounted(() => {
  stopLocalTimer()
})
</script>

<style scoped>
.recording-panel {
  display: flex;
  flex-direction: column;
}

.rec-list.panel-scroll {
  max-height: 360px;
  overflow-y: auto;
}

.playback-progress {
  position: relative;
}

.playback-seek-input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  opacity: 0;
  cursor: pointer;
  -webkit-appearance: none;
  appearance: none;
}

.playback-seek-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.playback-seek-input::-moz-range-thumb {
  width: 100%;
  height: 100%;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.playback-seek-input:disabled {
  cursor: default;
}
</style>

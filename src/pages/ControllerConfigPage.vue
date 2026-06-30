<template>
  <main class="config-main">
    <!-- Header Card -->
    <div class="header-card">
      <div class="header-left">
        <router-link to="/" class="back-btn" aria-label="返回仪表盘">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
        </router-link>
        <h2 class="header-title">手柄映射配置</h2>
      </div>
      <div class="header-actions">
        <input
          type="file"
          ref="fileInput"
          class="hidden-file"
          accept=".json"
          @change="handleImport"
          aria-label="导入配置文件"
        />
        <button class="action-btn" @click="refreshControllerStatus" aria-label="刷新手柄状态">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          <span>刷新手柄状态</span>
        </button>
        <button class="action-btn primary" @click="reconnectController" aria-label="手动重连">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
          <span>手动重连</span>
        </button>
        <button class="action-btn" @click="triggerImport" aria-label="导入配置">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span>导入配置</span>
        </button>
        <button class="action-btn" @click="exportConfig" aria-label="导出配置">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          <span>导出配置</span>
        </button>
        <button class="action-btn danger" @click="resetConfig" aria-label="重置默认">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="1 4 1 10 7 10" />
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
          </svg>
          <span>重置默认</span>
        </button>
      </div>
    </div>

    <!-- Two Column Grid -->
    <div class="config-grid">
      <!-- Left Column -->
      <div class="left-col">
        <!-- Controller Visualizer Card -->
        <div class="card">
          <div class="visualizer-wrapper">
            <ControllerVisualizer />
          </div>
        </div>

        <!-- Real-time Input Status Card -->
        <div class="card">
          <h3 class="card-title">实时输入状态</h3>

          <!-- Axis Data Row 1: LX / LY / RX -->
          <div class="axis-grid">
            <div v-for="key in axisKeysRow1" :key="key" class="axis-cell">
              <div class="axis-label">{{ key }}</div>
              <div class="axis-bar">
                <div class="axis-bar-center"></div>
                <div
                  class="axis-bar-dot"
                  :style="{ left: `${((state.axes[key] + 1) / 2) * 100}%` }"
                ></div>
              </div>
              <div class="axis-value">{{ state.axes[key].toFixed(2) }}</div>
            </div>
          </div>

          <!-- Axis Data Row 2: RY / LT / RT -->
          <div class="axis-grid">
            <div class="axis-cell">
              <div class="axis-label">RY</div>
              <div class="axis-bar">
                <div class="axis-bar-center"></div>
                <div
                  class="axis-bar-dot"
                  :style="{ left: `${((state.axes.RY + 1) / 2) * 100}%` }"
                ></div>
              </div>
              <div class="axis-value">{{ state.axes.RY.toFixed(2) }}</div>
            </div>
            <div v-for="key in triggerKeys" :key="key" class="axis-cell">
              <div class="axis-label">{{ key }}</div>
              <div class="trigger-bar">
                <div
                  class="trigger-bar-fill"
                  :style="{ width: `${state.triggers[key] * 100}%` }"
                ></div>
              </div>
              <div class="axis-value">{{ state.triggers[key].toFixed(2) }}</div>
            </div>
          </div>

          <!-- Separator -->
          <div class="separator"></div>

          <!-- Button Status Grid -->
          <div class="btn-status-grid">
            <div
              v-for="btn in buttonKeys"
              :key="btn.key"
              class="btn-status-row"
            >
              <div
                class="btn-dot"
                :class="{ 'dot-active': isPressed(btn.key) }"
              ></div>
              <span class="btn-name">{{ btn.label }}</span>
              <span class="btn-value">{{ mapping[btn.key]?.value || '--' }}</span>
            </div>
          </div>
        </div>

        <!-- Protocol Info Banner -->
        <div class="protocol-info" style="margin-top: 12px; padding: 12px; background: var(--color-bg-subtle, #f4f4f5); border: 1px solid var(--color-border, #e4e4e7); border-radius: 6px; font-size: 12px;">
          <div style="font-weight: 600; margin-bottom: 8px; color: var(--color-text, #18181b);">通讯协议说明</div>
          <div style="color: var(--color-text-secondary, #71717a); line-height: 1.6;">
            <div style="margin-bottom: 4px;">手柄状态以 JSON 格式发送：<code style="background: var(--color-bg-inset, #e4e4e7); padding: 1px 4px; border-radius: 3px;">{"btns": {...}, "axes": {...}, "trigs": {...}}</code></div>
            <div style="margin-bottom: 4px;">• <strong>btns</strong>：按键状态，布尔值 <code>true</code>/<code>false</code>（A/B/X/Y/LB/RB/LS/RS/Back/Start/DpadUp/DpadDown/DpadLeft/DpadRight）</div>
            <div style="margin-bottom: 4px;">• <strong>axes</strong>：摇杆轴值，范围 <code>-1.0 ~ 1.0</code>（LX/LY/RX/RY）</div>
            <div style="margin-bottom: 4px;">• <strong>trigs</strong>：扳机值，范围 <code>0.0 ~ 1.0</code>（LT/RT）</div>
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--color-border, #e4e4e7); color: var(--color-text-secondary, #71717a);">
              注意：LT/RT 扳机和摇杆轴（axes）为线性输入，不支持自定义按键映射。仅按键（btns）支持自定义映射值。
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column -->
      <div class="right-col">
        <!-- Button Mapping Configuration Card -->
        <div class="card">
          <!-- Title row -->
          <div class="mapping-header">
            <h3 class="card-title">按键功能映射</h3>
            <span class="auto-save-badge">
              <span class="auto-save-dot"></span>
              自动保存
            </span>
          </div>

          <!-- Info alert box -->
          <div class="info-banner">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="info-icon" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <span>配置每个按键按下时通过 web 发送的数据。支持文本或 HEX 格式。</span>
          </div>

          <!-- Mapping List -->
          <div class="mapping-list">
            <template v-for="btn in buttonKeys" :key="btn.key">
              <div
                class="mapping-row"
                :class="{ 'mapping-row-active': isPressed(btn.key), 'mapping-row-selected': selectedMappingKey === btn.key }"
                tabindex="0"
                role="button"
                @click="selectedMappingKey = btn.key"
                @keydown.enter="selectedMappingKey = btn.key"
                @keydown.space.prevent="selectedMappingKey = btn.key"
              >
                <span class="mapping-name">{{ btn.label }}</span>
                <span
                  class="status-badge"
                  :class="{ 'badge-pressed': isPressed(btn.key) }"
                >
                  {{ isPressed(btn.key) ? '已按下' : '未按下' }}
                </span>
                <select
                  v-model="mapping[btn.key].type"
                  class="mapping-select"
                  aria-label="指令类型"
                >
                  <option value="text">文本</option>
                  <option value="hex">HEX</option>
                </select>
                <input
                  v-model="mapping[btn.key].value"
                  type="text"
                  class="mapping-input"
                  placeholder="输入发送数据"
                  aria-label="发送指令"
                />
                <button
                  class="test-send-btn"
                  @click="testSend(btn.key)"
                  aria-label="测试发送"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M3.714 3.048a.498.498 0 0 0-.681.627l2.843 7.626a2 2 0 0 1 0 1.398l-2.843 7.626a.498.498 0 0 0 .681.627l18-8.5a.5.5 0 0 0 0-.904z" />
                    <path d="M6 12h16" />
                  </svg>
                  <span>测试发送</span>
                </button>
              </div>
              <div class="mapping-example">
                <span>示例: {{ btn.example }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { api, isNetworkConnectionError } from '@/api/client'
import ControllerVisualizer from '@/components/ControllerVisualizer.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const appStore = useAppStore()
const state = computed(() => appStore.controllerState)
const mapping = appStore.buttonMapping
const selectedMappingKey = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

// Ensure LT/RT keys exist in buttonMapping (they're not in store defaultMapping)
if (!mapping.LT) mapping.LT = { type: 'text', value: '' }
if (!mapping.RT) mapping.RT = { type: 'text', value: '' }

const axisKeysRow1 = ['LX', 'LY', 'RX'] as const
const triggerKeys = ['LT', 'RT'] as const

const buttonKeys = [
  { key: 'A', label: 'A', example: 'FORWARD' },
  { key: 'B', label: 'B', example: 'BACKWARD' },
  { key: 'X', label: 'X', example: 'LEFT' },
  { key: 'Y', label: 'Y', example: 'RIGHT' },
  { key: 'LB', label: 'LB', example: 'BOOST' },
  { key: 'RB', label: 'RB', example: 'BRAKE' },
  { key: 'LS', label: 'LS', example: 'LS_BTN' },
  { key: 'RS', label: 'RS', example: 'RS_BTN' },
  { key: 'Back', label: 'Back', example: 'STOP' },
  { key: 'Start', label: 'Start', example: 'START' },
  { key: 'DpadUp', label: 'DPadUp', example: 'UP' },
  { key: 'DpadDown', label: 'DPadDown', example: 'DOWN' },
  { key: 'DpadLeft', label: 'DPadLeft', example: 'TURN_LEFT' },
  { key: 'DpadRight', label: 'DPadRight', example: 'TURN_RIGHT' }
]

function isPressed(key: string): boolean {
  if (key === 'LT') return state.value.triggers.LT > 0.1
  if (key === 'RT') return state.value.triggers.RT > 0.1
  return state.value.buttons[key] || false
}

async function refreshControllerStatus() {
  try {
    await api.detectController()
    await appStore.refreshControllerStatus()
    ElMessage.success('手柄状态已刷新')
  } catch (e: any) {
    if (isNetworkConnectionError(e)) {
      ElMessage.error('刷新失败，无法连接到后端服务')
    } else {
      ElMessage.error('刷新手柄状态失败')
    }
  }
}

async function reconnectController() {
  try {
    await api.detectController()
    await appStore.refreshControllerStatus()
    if (appStore.controllerState.connected) {
      ElMessage.success('手柄重连成功')
    } else {
      ElMessage.warning('未检测到手柄，请确保手柄已连接到电脑')
    }
  } catch (e: any) {
    if (isNetworkConnectionError(e)) {
      ElMessage.error('重连失败，无法连接到后端服务')
    } else {
      ElMessage.error('手柄重连失败')
    }
  }
}

function triggerImport() {
  fileInput.value?.click()
}

function handleImport(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string
        const parsed = JSON.parse(content)
        if (typeof parsed === 'object') {
          Object.assign(mapping, parsed)
          ElMessage.success('配置导入成功')
        } else {
          ElMessage.error('无效的配置文件格式')
        }
      } catch (err) {
        ElMessage.error('解析配置文件失败')
      }
      if (fileInput.value) fileInput.value.value = ''
    }
    reader.readAsText(file)
  }
}

function exportConfig() {
  const dataStr = JSON.stringify(mapping, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `controller-config-${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('配置导出已开始')
}

function resetConfig() {
  ElMessageBox.confirm(
    '确定要重置所有按键映射为默认值吗？此操作不可恢复。',
    '重置确认',
    {
      confirmButtonText: '确定重置',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(() => {
      appStore.resetMapping()
      // Re-ensure LT/RT after reset (store defaultMapping doesn't include them)
      if (!mapping.LT) mapping.LT = { type: 'text', value: '' }
      if (!mapping.RT) mapping.RT = { type: 'text', value: '' }
      ElMessage.success('已重置为默认配置')
    })
    .catch(() => {})
}

async function testSend(key: string) {
  const config = mapping[key]
  if (!config || !config.value) {
    ElMessage.warning('请先输入发送数据')
    return
  }
  try {
    const res = await api.sendData({
      data: config.value,
      format: config.type,
      encoding: 'utf-8'
    })
    if (res.success) {
      ElMessage.success(`已发送: ${config.value}`)
    } else {
      ElMessage.error('发送失败')
    }
  } catch (e: any) {
    if (isNetworkConnectionError(e)) {
      ElMessage.error('发送失败，无法连接到后端服务')
    } else {
      ElMessage.error('发送失败')
    }
  }
}
</script>

<style scoped>
/* Page wrapper */
.config-main {
  padding: 20px;
  min-height: 100vh;
  background: var(--color-surface-muted);
  font-family: var(--font-sans);
  box-sizing: border-box;
}

.hidden-file {
  display: none;
}

/* Header Card */
.header-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 16px;
  background: var(--accent-blue-subtle);
  border: 1px solid var(--accent-blue-border);
  border-radius: 12px;
  margin-bottom: 20px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.back-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--accent-blue);
  cursor: pointer;
  transition: background 180ms ease, border-color 180ms ease;
  text-decoration: none;
}
.back-btn:hover {
  background: var(--muted);
  border-color: var(--color-border);
}
.header-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--color-text);
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* Action buttons */
.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: background 180ms ease, border-color 180ms ease;
}
.action-btn:hover {
  opacity: 0.9;
}
.action-btn.primary {
  border-color: var(--accent-blue);
  background: var(--accent-blue);
  color: var(--accent-blue-foreground);
}
.action-btn.danger {
  border-color: transparent;
  background: transparent;
  color: var(--color-danger-600);
}
.action-btn.danger:hover {
  background: var(--muted);
}

/* Two Column Grid */
.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}
.left-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.right-col {
  display: flex;
  flex-direction: column;
}

/* Card base */
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px;
  transition: border-color 180ms ease;
}
.card-title {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

/* Visualizer */
.visualizer-wrapper {
  position: relative;
  width: 100%;
  max-width: 320px;
  aspect-ratio: 441 / 383;
  margin: 0 auto;
}

/* Axis Data Grid */
.axis-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}
.axis-cell {
  text-align: center;
}
.axis-label {
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  color: var(--color-text-muted);
  letter-spacing: 0.1em;
  margin-bottom: 6px;
}
.axis-bar {
  position: relative;
  width: 100%;
  height: 6px;
  background: var(--color-border);
  border-radius: 999px;
  overflow: hidden;
}
.axis-bar-center {
  position: absolute;
  top: 0;
  left: 50%;
  width: 2px;
  height: 100%;
  background: var(--color-text-muted);
  transform: translateX(-50%);
}
.axis-bar-dot {
  position: absolute;
  top: 50%;
  width: 8px;
  height: 8px;
  background: var(--accent-blue);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  transition: left 100ms ease;
}
.axis-value {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-blue);
  margin-top: 4px;
}

/* Trigger bar */
.trigger-bar {
  position: relative;
  width: 100%;
  height: 6px;
  background: var(--color-border);
  border-radius: 999px;
  overflow: hidden;
}
.trigger-bar-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--accent-blue);
  border-radius: 999px;
  transition: width 100ms ease;
}

/* Separator */
.separator {
  border-top: 1px solid var(--color-border);
  margin: 12px 0;
}

/* Button Status Grid */
.btn-status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 16px;
}
.btn-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}
.btn-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #a1a1aa;
  flex-shrink: 0;
  transition: background 180ms ease;
}
.btn-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--color-text);
  flex: 1;
}
.btn-value {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 80px;
}

/* Mapping header */
.mapping-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.mapping-header .card-title {
  margin: 0;
}
.auto-save-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--success-subtle);
  border: 1px solid var(--success-border);
  font-size: 11px;
  font-weight: 500;
  color: var(--success-text);
  white-space: nowrap;
}
.auto-save-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--success);
}

/* Info banner */
.info-banner {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  background: var(--accent-blue-subtle);
  border: 1px solid var(--accent-blue-border);
  border-radius: 8px;
  margin-bottom: 16px;
}
.info-icon {
  color: var(--accent-blue);
  flex-shrink: 0;
  margin-top: 1px;
}
.info-banner span {
  font-size: 12px;
  color: var(--color-text);
  line-height: 1.5;
}

/* Mapping List */
.mapping-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Mapping Row */
.mapping-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  transition: background 180ms ease, border-color 180ms ease;
}
.mapping-row-active {
  background: var(--success-subtle) !important;
  border-color: var(--success-border) !important;
}
.mapping-name {
  width: 80px;
  flex-shrink: 0;
  font-weight: 600;
  font-size: 13px;
  color: var(--color-text);
}

/* Status badge */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--muted);
  border: 1px solid var(--color-border);
  font-size: 11px;
  font-weight: 500;
  color: var(--color-text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}
.badge-pressed {
  background: var(--success-subtle) !important;
  border-color: var(--success-border) !important;
  color: var(--success-text) !important;
}

/* Mapping select */
.mapping-select {
  width: 100px;
  flex-shrink: 0;
  height: 32px;
  padding: 0 8px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 13px;
  font-family: var(--font-sans);
  cursor: pointer;
  appearance: auto;
  transition: border-color 180ms ease, box-shadow 180ms ease;
}

/* Mapping input */
.mapping-input {
  flex: 1;
  min-width: 0;
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 13px;
  font-family: var(--font-mono);
  outline: none;
  transition: border-color 180ms ease, box-shadow 180ms ease;
}

/* Focus styles */
.mapping-input:focus,
.mapping-select:focus {
  border-color: var(--ring);
  box-shadow: 0 0 0 3px var(--brand-subtle);
}

/* Test send button */
.test-send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 180ms ease, color 180ms ease;
  flex-shrink: 0;
}
.test-send-btn:hover {
  background: var(--muted);
  color: var(--color-text);
}

/* Mapping example */
.mapping-example {
  padding: 0 12px;
}
.mapping-example span {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* Active dot pulse */
@keyframes pulse-green {
  0%, 100% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.4); }
  50% { box-shadow: 0 0 0 4px rgba(22, 163, 74, 0); }
}
.dot-active {
  background: var(--success) !important;
  animation: pulse-green 1.5s ease infinite;
}

/* Button hover */
button:hover {
  opacity: 0.9;
}

/* Responsive */
@media (max-width: 1023px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .header-card {
    flex-direction: column;
    align-items: flex-start;
  }
  .header-actions {
    width: 100%;
  }
  .mapping-row {
    flex-wrap: wrap;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
</style>

<template>
  <div class="card" style="flex:1; display:flex; flex-direction:column; min-height:0;">
    <div class="tab-bar">
      <button class="pill" :class="{ active: activeTab === 'comm' }" @click="activeTab = 'comm'">通信日志</button>
      <button class="pill" :class="{ active: activeTab === 'system' }" @click="activeTab = 'system'">系统日志</button>
    </div>
    <!-- Communication Log Tab -->
    <div class="tab-content" :class="{ active: activeTab === 'comm' }" data-tab="log-comm" style="flex:1; min-height:0;">
      <div class="log-toolbar" style="margin-bottom:8px;">
        <div class="log-filter">
          <input type="checkbox" id="filter-send" v-model="filterSend" />
          <label for="filter-send">过滤发送 ↑</label>
        </div>
        <div class="log-filter">
          <input type="checkbox" id="filter-recv" v-model="filterRecv" />
          <label for="filter-recv">过滤接收 ↓</label>
        </div>
        <div class="log-filter">
          <input type="checkbox" id="filter-auto" v-model="filterAuto" />
          <label for="filter-auto">过滤自动发送 ●</label>
        </div>
        <div class="log-filter">
          <input type="checkbox" id="filter-raw" v-model="showRawJson" />
          <label for="filter-raw">原始JSON</label>
        </div>
      </div>
      <div ref="commLogRef" class="log-list">
        <div v-for="log in filteredCommLogs" :key="log.id" class="log-entry">
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span v-if="log.auto" class="log-auto-dot"></span>
          <span class="log-arrow" :class="log.direction === 'send' ? 'send' : 'recv'">{{ log.direction === 'send' ? '↑' : '↓' }}</span>
          <span class="log-content">{{ showRawJson ? log.data : parseControllerData(log.data) }}</span>
        </div>
        <div v-if="filteredCommLogs.length === 0" class="empty-state">暂无通信日志</div>
      </div>
    </div>
    <!-- System Log Tab -->
    <div class="tab-content" :class="{ active: activeTab === 'system' }" data-tab="log-sys" style="flex:1; min-height:0;">
      <div class="log-toolbar" style="margin-bottom:8px;">
        <div class="sender-toolbar">
          <button class="speed-pill" :class="{ active: enabledLevels.has('INFO') }" @click="toggleLevel('INFO')">INFO</button>
          <button class="speed-pill" :class="{ active: enabledLevels.has('WARN') }" @click="toggleLevel('WARN')">WARN</button>
          <button class="speed-pill" :class="{ active: enabledLevels.has('ERROR') }" @click="toggleLevel('ERROR')">ERROR</button>
          <div style="margin-left:auto;">
            <button class="btn ghost" style="color: var(--color-danger-600);" @click="handleClear">清除</button>
          </div>
        </div>
      </div>
      <div ref="sysLogRef" class="log-list">
        <div v-for="log in filteredSysLogs" :key="log.id" class="syslog-entry">
          <span class="syslog-time">{{ formatSysTime(log.timestamp) }}</span>
          <span class="syslog-level" :class="levelClass(log.level)">{{ levelLabel(log.level) }}</span>
          <span class="syslog-msg">{{ log.message }}</span>
        </div>
        <div v-if="filteredSysLogs.length === 0" class="empty-state">暂无系统日志</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const activeTab = ref<'comm' | 'system'>('comm')
const filterSend = ref(true)
const filterRecv = ref(true)
const filterAuto = ref(true)
const showRawJson = ref(false)
const enabledLevels = ref<Set<string>>(new Set(['INFO', 'WARN', 'ERROR']))

const commLogRef = ref<HTMLElement | null>(null)
const sysLogRef = ref<HTMLElement | null>(null)

const filteredCommLogs = computed(() => {
  return appStore.logs.filter(log => {
    if (log.direction === 'send' && !filterSend.value) return false
    if (log.direction === 'receive' && !filterRecv.value) return false
    if (log.auto && !filterAuto.value) return false
    return true
  })
})

const filteredSysLogs = computed(() => {
  return appStore.systemLogs.filter(log => {
    return enabledLevels.value.has(levelKey(log.level))
  })
})

function levelKey(level: string): string {
  if (level === 'WARNING') return 'WARN'
  if (level === 'DEBUG') return 'INFO'
  return level
}

function levelClass(level: string): string {
  if (level === 'WARNING') return 'warn'
  if (level === 'ERROR') return 'error'
  return 'info'
}

function levelLabel(level: string): string {
  if (level === 'WARNING') return 'WARN'
  return level
}

function toggleLevel(key: string) {
  const next = new Set(enabledLevels.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  enabledLevels.value = next
}

function formatTime(ts: string): string {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ss = String(d.getSeconds()).padStart(2, '0')
    const ms = String(d.getMilliseconds()).padStart(3, '0')
    return `${hh}:${mm}:${ss}.${ms}`
  } catch {
    return ts
  }
}

function formatSysTime(ts: string): string {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ss = String(d.getSeconds()).padStart(2, '0')
    return `${hh}:${mm}:${ss}`
  } catch {
    return ts
  }
}

function parseControllerData(data: string): string {
  try {
    const obj = JSON.parse(data)

    // 非控制器数据（没有 btns/axes/trigs 字段）按原始字符串显示
    if (!obj.btns && !obj.axes && !obj.trigs) {
      return data
    }

    let result = ''

    if (obj.btns) {
      const btnsStr = Object.entries(obj.btns)
        .map(([k, v]) => `${k}:${v === true || v === 1 ? 1 : 0}`)
        .join(' ')
      result += `[按键] ${btnsStr}`
    }

    if (obj.axes) {
      const axesStr = Object.entries(obj.axes)
        .map(([k, v]) => `${k}:${Number(v).toFixed(2)}`)
        .join(' ')
      if (result) result += ' '
      result += `[摇杆] ${axesStr}`
    }

    if (obj.trigs) {
      const trigsStr = Object.entries(obj.trigs)
        .map(([k, v]) => `${k}:${Number(v).toFixed(2)}`)
        .join(' ')
      if (result) result += ' '
      result += `[扳机] ${trigsStr}`
    }

    return result
  } catch {
    return data
  }
}

function handleClear() {
  appStore.clearSystemLogs()
}

function scrollToBottom() {
  nextTick(() => {
    if (activeTab.value === 'comm' && commLogRef.value) {
      commLogRef.value.scrollTop = commLogRef.value.scrollHeight
    } else if (activeTab.value === 'system' && sysLogRef.value) {
      sysLogRef.value.scrollTop = sysLogRef.value.scrollHeight
    }
  })
}

watch(() => appStore.logs.length, () => {
  if (activeTab.value === 'comm') scrollToBottom()
})

watch(() => appStore.systemLogs.length, () => {
  if (activeTab.value === 'system') scrollToBottom()
})

watch(activeTab, () => {
  scrollToBottom()
})

onMounted(() => {
  scrollToBottom()
})
</script>

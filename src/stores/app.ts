import { defineStore } from 'pinia'
import { ref, reactive, watch, computed } from 'vue'
import { api, WS_BASE } from '@/api/client'
import type {
  NetworkConfig,
  ControllerState,
  ButtonMapping,
  SystemLog,
  CommLogEntry,
  WebSocketMessage,
  ServerStatus,
  ServerClient,
  ServerConfig,
  NetworkMode,
  RecordingInfo,
  RecordingState,
  PlaybackState,
  RecordingStateData,
  SendMode
} from '@/types'

export const useAppStore = defineStore('app', () => {
  const networkMode = ref<NetworkMode>('client')
  const isNetworkConnected = ref(false)
  const networkConfig = reactive<NetworkConfig>({
    ip: '192.168.4.1',
    port: 8080,
    protocol: 'UDP'
  })

  const serverStatus = ref<ServerStatus>({
    status: 'stopped',
    port: null,
    client_count: 0
  })
  const serverIsRunning = computed(() => serverStatus.value.status === 'running')
  const serverClients = ref<ServerClient[]>([])
  const serverConfig = reactive<ServerConfig>({
    port: 8080,
    max_clients: 8,
    heartbeat_timeout: 600
  })

  const controllerState = ref<ControllerState>({
    connected: false,
    buttons: {
      A: false, B: false, X: false, Y: false,
      LB: false, RB: false,
      Back: false, Start: false,
      LS: false, RS: false,
      DpadUp: false, DpadDown: false, DpadLeft: false, DpadRight: false
    },
    axes: {
      LX: 0.0, LY: 0.0,
      RX: 0.0, RY: 0.0
    },
    triggers: {
      LT: 0.0, RT: 0.0
    },
    timestamp: ''
  })

  const defaultMapping: Record<string, ButtonMapping> = {
    A: { type: 'text', value: '' },
    B: { type: 'text', value: '' },
    X: { type: 'text', value: '' },
    Y: { type: 'text', value: '' },
    LB: { type: 'text', value: '' },
    RB: { type: 'text', value: '' },
    Back: { type: 'text', value: '' },
    Start: { type: 'text', value: '' },
    LS: { type: 'text', value: '' },
    RS: { type: 'text', value: '' },
    DpadUp: { type: 'text', value: '' },
    DpadDown: { type: 'text', value: '' },
    DpadLeft: { type: 'text', value: '' },
    DpadRight: { type: 'text', value: '' },
  }

  const buttonMapping = reactive<Record<string, ButtonMapping>>(
    JSON.parse(JSON.stringify(defaultMapping))
  )

  const savedMapping = localStorage.getItem('buttonMapping')
  if (savedMapping) {
    try {
      const parsed = JSON.parse(savedMapping)
      Object.assign(buttonMapping, parsed)
    } catch (e) {
      console.error('[wifi-spi] Failed to load saved mapping:', e)
    }
  }

  const savedNetwork = localStorage.getItem('networkConfig')
  if (savedNetwork) {
    try {
      const parsed = JSON.parse(savedNetwork)
      Object.assign(networkConfig, parsed)
    } catch (e) {
      console.error('[wifi-spi] Failed to load saved network config:', e)
    }
  }

  const savedMode = localStorage.getItem('networkMode')
  if (savedMode === 'client' || savedMode === 'server') {
    networkMode.value = savedMode
  }

  const savedServerConfig = localStorage.getItem('serverConfig')
  if (savedServerConfig) {
    try {
      const parsed = JSON.parse(savedServerConfig)
      Object.assign(serverConfig, parsed)
    } catch (e) {
      console.error('[wifi-spi] Failed to load saved server config:', e)
    }
  }

  watch(buttonMapping, (newVal) => {
    localStorage.setItem('buttonMapping', JSON.stringify(newVal))
  }, { deep: true })

  watch(networkConfig, (newVal) => {
    localStorage.setItem('networkConfig', JSON.stringify(newVal))
  }, { deep: true })

  watch(networkMode, (newVal) => {
    localStorage.setItem('networkMode', newVal)
  })

  watch(serverConfig, (newVal) => {
    localStorage.setItem('serverConfig', JSON.stringify(newVal))
  }, { deep: true })

  function resetMapping() {
    Object.assign(buttonMapping, JSON.parse(JSON.stringify(defaultMapping)))
  }

  const buttonMappingSendEnabled = ref(true)

  const logs = ref<CommLogEntry[]>([])
  const maxLogs = 1000

  // 日志缓冲队列（后台标签页性能优化）
  const logBuffer: CommLogEntry[] = []

  function addLog(entry: CommLogEntry) {
    logBuffer.push(entry)
  }

  let flushTimer: ReturnType<typeof setInterval> | null = null

  function startLogFlushTimer() {
    if (flushTimer) return
    flushTimer = setInterval(() => {
      if (logBuffer.length === 0) return
      // 如果页面不可见，不刷新（只缓冲）
      if (document.hidden) return

      // 合并缓冲日志
      const newLogs = logBuffer.splice(0)
      logs.value.push(...newLogs)

      // 限制最大条目数
      if (logs.value.length > maxLogs) {
        logs.value.splice(0, logs.value.length - maxLogs)
      }
    }, 100)
  }

  // 页面恢复可见时立即刷新
  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && logBuffer.length > 0) {
        const newLogs = logBuffer.splice(0)
        logs.value.push(...newLogs)
        if (logs.value.length > maxLogs) {
          logs.value.splice(0, logs.value.length - maxLogs)
        }
      }
    })
  }

  startLogFlushTimer()

  const systemLogs = ref<SystemLog[]>([])
  const maxSystemLogs = 500

  const wsConnected = ref(false)
  const wsReconnecting = ref(false)
  const backendVersion = ref<string>('')
  const backendName = ref<string>('')

  const recordingState = reactive<RecordingState>({
    status: 'idle',
    current_duration: 0,
    current_frames: 0
  })

  const playbackState = reactive<PlaybackState>({
    status: 'idle',
    recording_id: null,
    current_time: 0,
    total_duration: 0,
    progress: 0,
    speed: 1
  })

  const recordings = ref<RecordingInfo[]>([])
  const selectedRecordingId = ref<string | null>(null)
  const controllerFrequency = ref<number>(20)
  const controllerSendMode = ref<SendMode>('onchange')

  const savedControllerFrequency = localStorage.getItem('controllerFrequency')
  if (savedControllerFrequency) {
    try {
      const parsed = parseFloat(savedControllerFrequency)
      if (!isNaN(parsed) && parsed >= 10 && parsed <= 60) {
        controllerFrequency.value = parsed
      }
    } catch (e) {
      console.error('[wifi-spi] Failed to load saved controller frequency:', e)
    }
  }

  watch(controllerFrequency, (newVal) => {
    localStorage.setItem('controllerFrequency', String(newVal))
  })

  const savedSendMode = localStorage.getItem('controller_send_mode') as SendMode | null
  if (savedSendMode === 'continuous' || savedSendMode === 'onchange') {
    controllerSendMode.value = savedSendMode
  }

  watch(controllerSendMode, (val) => {
    localStorage.setItem('controller_send_mode', val)
  })

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  const INITIAL_RECONNECT_DELAY = 3000
  const MAX_RECONNECT_DELAY = 30000
  let currentReconnectDelay = INITIAL_RECONNECT_DELAY

  const CONTROLLER_TIMEOUT_MS = 3000
  let lastControllerStateTime = 0
  let controllerTimeoutTimer: ReturnType<typeof setTimeout> | null = null

  function clearReconnectTimer() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function clearControllerTimeoutTimer() {
    if (controllerTimeoutTimer) {
      clearTimeout(controllerTimeoutTimer)
      controllerTimeoutTimer = null
    }
  }

  function startControllerTimeoutTimer() {
    clearControllerTimeoutTimer()
    controllerTimeoutTimer = setTimeout(() => {
      if (!controllerState.value.connected) {
        return  // 不再继续检测
      }
      const now = Date.now()
      if (now - lastControllerStateTime > CONTROLLER_TIMEOUT_MS) {
        controllerState.value.connected = false
      } else {
        // 未超时，重新设置定时器继续检测
        startControllerTimeoutTimer()
      }
    }, 1000)
  }

  async function fetchVersion() {
    try {
      const versionInfo = await api.getVersion()
      backendVersion.value = versionInfo.version
      backendName.value = versionInfo.name
      console.log(`[wifi-spi] Backend version: ${versionInfo.name} v${versionInfo.version}`)
    } catch (e) {
      console.warn('[wifi-spi] Failed to fetch backend version:', e)
    }
  }

  async function fetchControllerStatus() {
    try {
      const status = await api.getControllerStatus()
      handleControllerState(status)
      console.log(`[wifi-spi] Controller status fetched: connected=${status.connected}`)
    } catch (e) {
      console.warn('[wifi-spi] Failed to fetch controller status:', e)
    }
  }

  async function refreshControllerStatus() {
    try {
      await api.detectController()
      const status = await api.getControllerStatus()
      handleControllerState(status)
      console.log('[wifi-spi] Controller status refreshed: connected=', status.connected)
    } catch (e) {
      console.warn('[wifi-spi] Failed to refresh controller status:', e)
      throw e
    }
  }

  function handleWebSocketOpen() {
    console.log('[wifi-spi] WebSocket connected')
    wsConnected.value = true
    wsReconnecting.value = false
    currentReconnectDelay = INITIAL_RECONNECT_DELAY
    clearReconnectTimer()
    fetchVersion()
    fetchControllerStatus()
    loadRecordings()
  }

  function handleWebSocketMessage(event: MessageEvent) {
    try {
      const msg = JSON.parse(event.data) as WebSocketMessage

      switch (msg.type) {
        case 'controller_state':
          handleControllerState(msg.data as ControllerState)
          break
        case 'network_data':
          handleNetworkData(msg.data as CommLogEntry)
          break
        case 'system_log':
          handleSystemLog(msg.data as SystemLog)
          break
        case 'system_log_history':
          handleSystemLogHistory(msg.data as SystemLog[])
          break
        case 'server_status':
          handleServerStatus(msg.data as ServerStatus)
          break
        case 'server_clients':
          handleServerClients(msg.data as ServerClient[])
          break
        case 'server_data':
          handleServerData(msg.data as CommLogEntry)
          break
        case 'recording_state':
          handleRecordingState(msg.data as RecordingStateData)
          break
      }
    } catch (e) {
      console.error('[wifi-spi] WS message parse error:', e)
    }
  }

  function handleControllerState(newState: ControllerState) {
    lastControllerStateTime = Date.now()

    if (isNetworkConnected.value || serverIsRunning.value) {
      const oldButtons = controllerState.value.buttons
      const newButtons = newState.buttons

      for (const key in newButtons) {
        if (newButtons[key] !== oldButtons[key]) {
          handleButtonChange(key, newButtons[key])
        }
      }
    }

    controllerState.value = newState

    if (newState.connected) {
      startControllerTimeoutTimer()
    }
  }

  function handleNetworkData(logEntry: CommLogEntry) {
    logEntry.id = Date.now() + Math.random()
    addLog(logEntry)
  }

  function handleSystemLog(logEntry: SystemLog) {
    const entry: SystemLog = {
      ...logEntry,
      id: Date.now() + Math.random()
    }
    systemLogs.value.push(entry)
    if (systemLogs.value.length > maxSystemLogs) {
      systemLogs.value.shift()
    }
  }

  function handleSystemLogHistory(history: SystemLog[]) {
    const entries: SystemLog[] = history.map((log, index) => ({
      ...log,
      id: Date.now() + Math.random() + index
    }))
    systemLogs.value = [...systemLogs.value, ...entries]
    if (systemLogs.value.length > maxSystemLogs) {
      systemLogs.value = systemLogs.value.slice(-maxSystemLogs)
    }
  }

  function handleServerStatus(status: ServerStatus) {
    serverStatus.value = status
  }

  function handleServerClients(clients: ServerClient[]) {
    serverClients.value = clients
  }

  function handleServerData(logEntry: CommLogEntry) {
    logEntry.id = Date.now() + Math.random()
    addLog(logEntry)
  }

  function handleRecordingState(data: RecordingStateData) {
    const recState = data.recording?.state || 'idle'
    recordingState.status = recState === 'recording' ? 'recording' : recState === 'paused' ? 'paused' : 'idle'
    recordingState.current_duration = data.recording?.current_time || 0
    recordingState.current_frames = data.recording?.frame_count || 0

    const playState = data.playback?.state || 'idle'
    playbackState.status = playState === 'playing' ? 'playing' : playState === 'playback_paused' ? 'paused' : 'idle'
    playbackState.recording_id = data.playback?.recording_id || null
    playbackState.current_time = data.playback?.current_time || 0
    playbackState.total_duration = data.playback?.total_duration || 0
    playbackState.progress = data.playback?.progress || 0
    playbackState.speed = data.playback?.speed || 1
  }

  async function loadRecordings() {
    try {
      const list = await api.getRecordingList()
      recordings.value = list
    } catch (e) {
      console.error('[wifi-spi] Failed to load recordings:', e)
    }
  }

  function handleWebSocketClose() {
    console.log(`[wifi-spi] WebSocket disconnected, retrying in ${currentReconnectDelay / 1000}s...`)
    wsConnected.value = false
    wsReconnecting.value = true
    clearControllerTimeoutTimer()
    scheduleReconnect()
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  function handleWebSocketError(err: Event) {
    console.warn('[wifi-spi] WebSocket connection error (backend may not be running)')
  }

  function scheduleReconnect() {
    clearReconnectTimer()
    wsReconnecting.value = true
    reconnectTimer = setTimeout(() => {
      connectWebSocket()
      currentReconnectDelay = Math.min(currentReconnectDelay * 2, MAX_RECONNECT_DELAY)
    }, currentReconnectDelay)
  }

  function connectWebSocket() {
    clearReconnectTimer()

    try {
      ws = new WebSocket(WS_BASE)

      ws.onopen = handleWebSocketOpen
      ws.onmessage = handleWebSocketMessage
      ws.onclose = handleWebSocketClose
      ws.onerror = handleWebSocketError
    } catch (e) {
      console.error('[wifi-spi] WebSocket init error:', e)
      scheduleReconnect()
    }
  }

  connectWebSocket()
  fetchVersion()
  fetchControllerStatus()

  async function handleButtonChange(buttonKey: string, isPressed: boolean) {
    // 按键映射文本发送已移除，通信只发送 JSON 控制器状态
    // 保留函数签名以兼容 handleControllerState 调用
    return
  }

  function clearSystemLogs() {
    systemLogs.value = []
  }

  return {
    networkMode,
    isNetworkConnected,
    networkConfig,
    serverStatus,
    serverIsRunning,
    serverClients,
    serverConfig,
    controllerState,
    buttonMapping,
    buttonMappingSendEnabled,
    logs,
    systemLogs,
    wsConnected,
    wsReconnecting,
    backendVersion,
    backendName,
    recordingState,
    playbackState,
    recordings,
    selectedRecordingId,
    controllerFrequency,
    controllerSendMode,
    resetMapping,
    clearSystemLogs,
    fetchVersion,
    loadRecordings,
    refreshControllerStatus,
    addLog
  }
})

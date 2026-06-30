import axios from 'axios'
import type {
  NetworkStatus,
  ConnectRequest,
  ConnectResponse,
  SendRequest,
  SendResponse,
  ShutdownResponse,
  VersionInfo,
  ServerStatus,
  ServerClient,
  ServerConfig,
  ServerInfo,
  ServerSendRequest,
  RecordingInfo,
  ControllerState,
  SendMode
} from '@/types'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const WS_BASE = import.meta.env.VITE_WS_BASE || 'ws://localhost:8000/ws'

function isNetworkConnectionError(error: any): boolean {
  return error.code === 'ERR_NETWORK' ||
    error.message === 'Network Error' ||
    error.code === 'ECONNREFUSED'
}

const httpClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (isNetworkConnectionError(error)) {
      console.warn('[wifi-spi] Backend unreachable —', error.message)
    } else if (error.response) {
      console.error('[wifi-spi] API Error:', error.message)
    } else {
      console.error('[wifi-spi] API Error:', error.message)
    }
    return Promise.reject(error)
  }
)

export const api = {
  async getVersion(): Promise<VersionInfo> {
    const res = await httpClient.get('/api/version')
    return res.data
  },

  async getInstanceInfo(): Promise<any> {
    const res = await httpClient.get('/api/instance/info')
    return res.data
  },

  async getControllerStatus(): Promise<ControllerState> {
    const res = await httpClient.get('/api/controller/status')
    return res.data
  },

  async getControllerFrequency(): Promise<{ frequency: number }> {
    const res = await httpClient.get('/api/controller/frequency')
    return res.data
  },

  async setControllerFrequency(frequency: number): Promise<any> {
    const res = await httpClient.post('/api/controller/frequency', { frequency })
    return res.data
  },

  async getControllerSendMode(): Promise<SendMode> {
    const res = await httpClient.get('/api/controller/send-mode')
    return res.data.mode || 'onchange'
  },

  async setControllerSendMode(mode: SendMode): Promise<void> {
    await httpClient.post('/api/controller/send-mode', { mode })
  },

  async detectController(): Promise<any> {
    const res = await httpClient.post('/api/controller/detect')
    return res.data
  },

  async getNetworkStatus(): Promise<NetworkStatus> {
    const res = await httpClient.post('/api/network/status')
    return res.data
  },

  async connect(req: ConnectRequest): Promise<ConnectResponse> {
    const res = await httpClient.post('/api/network/connect', req)
    return res.data
  },

  async disconnect(): Promise<ConnectResponse> {
    const res = await httpClient.post('/api/network/disconnect')
    return res.data
  },

  async stopReconnect(): Promise<any> {
    const res = await httpClient.post('/api/network/stop-reconnect')
    return res.data
  },

  async sendData(req: SendRequest): Promise<SendResponse> {
    const res = await httpClient.post('/api/network/send', req)
    return res.data
  },

  async shutdown(): Promise<ShutdownResponse> {
    const res = await httpClient.post('/api/shutdown')
    return res.data
  },

  async startServer(config: ServerConfig): Promise<any> {
    const res = await httpClient.post('/api/server/start', config)
    return res.data
  },

  async stopServer(): Promise<any> {
    const res = await httpClient.post('/api/server/stop')
    return res.data
  },

  async getServerStatus(): Promise<ServerStatus> {
    const res = await httpClient.post('/api/server/status')
    return res.data
  },

  async getServerClients(): Promise<ServerClient[]> {
    const res = await httpClient.post('/api/server/clients')
    return res.data.clients || []
  },

  async getServerInfo(): Promise<ServerInfo> {
    const res = await httpClient.post('/api/server/info')
    return res.data
  },

  async sendServerData(data: ServerSendRequest): Promise<SendResponse> {
    const res = await httpClient.post('/api/server/send', data)
    return res.data
  },

  async startRecording(name?: string): Promise<any> {
    const res = await httpClient.post('/api/recording/start', { name })
    return res.data
  },

  async pauseRecording(): Promise<any> {
    const res = await httpClient.post('/api/recording/pause')
    return res.data
  },

  async resumeRecording(): Promise<any> {
    const res = await httpClient.post('/api/recording/resume')
    return res.data
  },

  async stopRecording(): Promise<any> {
    const res = await httpClient.post('/api/recording/stop')
    return res.data
  },

  async getRecordingList(): Promise<RecordingInfo[]> {
    const res = await httpClient.post('/api/recording/list')
    return res.data.recordings || []
  },

  async getRecording(id: string): Promise<any> {
    const res = await httpClient.post('/api/recording/get', { recording_id: id })
    return res.data
  },

  async renameRecording(id: string, name: string): Promise<any> {
    const res = await httpClient.post('/api/recording/rename', { recording_id: id, new_name: name })
    return res.data
  },

  async deleteRecording(id: string): Promise<any> {
    const res = await httpClient.post('/api/recording/delete', { recording_id: id })
    return res.data
  },

  async exportRecording(id: string): Promise<string> {
    const res = await httpClient.post('/api/recording/export', { recording_id: id })
    return res.data.json_data || ''
  },

  async importRecording(jsonData: string): Promise<any> {
    const res = await httpClient.post('/api/recording/import', { json_data: jsonData })
    return res.data
  },

  async startPlayback(id: string, speed?: number): Promise<any> {
    const res = await httpClient.post('/api/playback/start', { recording_id: id, speed })
    return res.data
  },

  async pausePlayback(): Promise<any> {
    const res = await httpClient.post('/api/playback/pause')
    return res.data
  },

  async resumePlayback(): Promise<any> {
    const res = await httpClient.post('/api/playback/resume')
    return res.data
  },

  async stopPlayback(): Promise<any> {
    const res = await httpClient.post('/api/playback/stop')
    return res.data
  },

  async setPlaybackMode(enabled: boolean, blockRealController: boolean): Promise<any> {
    const res = await httpClient.post('/api/playback/mode', {
      enabled,
      block_real_controller: blockRealController
    })
    return res.data
  },

  async seekPlayback(progress: number): Promise<any> {
    const res = await httpClient.post('/api/playback/seek', { progress })
    return res.data
  },

  async setPlaybackSpeed(speed: number): Promise<any> {
    const res = await httpClient.post('/api/playback/speed', { speed })
    return res.data
  }
}

export { API_BASE, WS_BASE, httpClient, isNetworkConnectionError }

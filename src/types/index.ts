export interface NetworkConfig {
  ip: string
  port: number
  protocol: 'UDP' | 'TCP'
}

export interface NetworkStatus {
  connected: boolean
  ip: string | null
  port: number | null
  protocol: string | null
}

export interface ControllerState {
  connected: boolean
  buttons: Record<string, boolean>
  axes: Record<string, number>
  triggers: Record<string, number>
  timestamp: string
}

export interface ButtonMapping {
  type: 'text' | 'hex'
  value: string
}

export interface SystemLog {
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'
  module: string
  message: string
  timestamp: string
  id?: number
}

export interface CommLogEntry {
  direction: 'send' | 'receive'
  timestamp: string
  data: string
  text?: string
  format: string
  encoding?: string
  id?: number
  auto?: boolean
}

export interface ConnectRequest {
  ip: string
  port: number
  protocol: string
}

export interface SendRequest {
  data: string
  format: string
  encoding?: string
}

export interface SendResponse {
  success: boolean
  bytes_sent?: number
  message?: string
}

export interface ConnectResponse {
  status: boolean
  message: string
  ip?: string
  port?: number
  protocol?: string
}

export interface ShutdownResponse {
  status: boolean
  message: string
}

export interface VersionInfo {
  version: string
  name: string
}

export interface ServerStatus {
  status: 'stopped' | 'running' | 'error'
  port: number | null
  client_count: number
}

export interface ServerClient {
  client_id: string
  ip: string
  port: number
  connected_at: string
  last_active: string
}

export interface ServerConfig {
  port: number
  max_clients: number
  heartbeat_timeout: number
}

export type SendMode = 'continuous' | 'onchange'

export interface ServerInfo {
  ips: string[]
  port: number | null
  status: string
  client_count: number
}

export interface ServerSendRequest {
  data: string
  format: string
  encoding?: string
  client_id?: string | null
}

export type NetworkMode = 'client' | 'server'

export type WebSocketMessageType =
  | 'controller_state'
  | 'network_data'
  | 'system_log'
  | 'system_log_history'
  | 'server_status'
  | 'server_clients'
  | 'server_data'
  | 'recording_state'

export interface WebSocketMessage {
  type: WebSocketMessageType
  data: unknown
}

export interface RecordingInfo {
  id: string
  name: string
  created_at: string
  duration: number
  frame_count: number
}

export interface RecordingState {
  status: 'idle' | 'recording' | 'paused'
  current_duration: number
  current_frames: number
}

export interface PlaybackState {
  status: 'idle' | 'playing' | 'paused'
  recording_id: string | null
  current_time: number
  total_duration: number
  progress: number
  speed: number
}

export interface RecordingStateData {
  state: string
  recording: {
    state: string
    name: string
    frame_count: number
    current_time: number
  }
  playback: {
    state: string
    recording_id: string | null
    recording_name: string | null
    progress: number
    current_time: number
    total_duration: number
    frame_index: number
    frame_count: number
    speed: number
  }
}

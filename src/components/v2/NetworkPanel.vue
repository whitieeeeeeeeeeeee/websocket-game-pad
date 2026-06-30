<template>
  <div class="card">
    <div class="tab-bar">
      <button
        class="pill"
        :class="{ active: activeTab === 'client' }"
        @click="handleTabChange('client')"
        role="tab"
      >客户端</button>
      <button
        class="pill"
        :class="{ active: activeTab === 'server' }"
        @click="handleTabChange('server')"
        role="tab"
      >服务端</button>
    </div>
    <!-- Client Mode -->
    <div class="tab-content" :class="{ active: activeTab === 'client' }" data-tab="net-client">
      <div class="form-row">
        <div class="form-group">
          <label>IP地址</label>
          <input
            v-model="networkConfig.ip"
            type="text"
            placeholder="192.168.1.100"
            aria-label="IP地址"
            :disabled="isNetworkConnected"
          />
        </div>
        <div class="form-group">
          <label>端口</label>
          <input
            v-model.number="networkConfig.port"
            type="text"
            placeholder="8080"
            aria-label="端口"
            style="width:80px;flex:none;"
            :disabled="isNetworkConnected"
          />
        </div>
      </div>
      <div class="sender-toolbar" style="margin-bottom:12px;">
        <button
          class="pill"
          :class="{ active: networkConfig.protocol === 'UDP' }"
          @click="networkConfig.protocol = 'UDP'"
          :disabled="isNetworkConnected"
        >UDP</button>
        <button
          class="pill"
          :class="{ active: networkConfig.protocol === 'TCP' }"
          @click="networkConfig.protocol = 'TCP'"
          :disabled="isNetworkConnected"
        >TCP</button>
        <div style="margin-left:auto; display:flex; gap:6px;">
          <button
            class="btn primary"
            @click="toggleConnection"
            :disabled="isNetworkConnected || connecting"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22v-5"/><path d="M9 8V2"/><path d="M15 8V2"/><path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/></svg>
            连接
          </button>
          <button
            class="btn secondary"
            @click="toggleConnection"
            :disabled="!isNetworkConnected || connecting"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22v-5"/><path d="M9 8V2"/><path d="M15 8V2"/><path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/><line x1="2" y1="2" x2="22" y2="22"/></svg>
            断开
          </button>
        </div>
      </div>
      <div v-if="wsReconnecting" class="sender-toolbar" style="margin-bottom:12px;">
        <span class="ws-badge connecting">
          <span class="dot"></span>
          重连中
        </span>
        <div style="margin-left:auto;">
          <button class="btn secondary" @click="stopReconnect">停止重试</button>
        </div>
      </div>
      <div style="font-size:11px; color:var(--color-text-muted); font-family:var(--font-mono);">
        状态: {{ isNetworkConnected ? '已连接' : '未连接' }}
      </div>
    </div>
    <!-- Server Mode -->
    <div class="tab-content" :class="{ active: activeTab === 'server' }" data-tab="net-server">
      <div class="form-row">
        <div class="form-group">
          <label>监听端口</label>
          <input
            v-model.number="serverConfig.port"
            type="text"
            placeholder="8080"
            aria-label="监听端口"
            style="width:120px;"
            :disabled="serverIsRunning"
          />
        </div>
        <div class="form-group">
          <label>最大客户端</label>
          <input
            v-model.number="serverConfig.max_clients"
            type="text"
            placeholder="8"
            aria-label="最大客户端"
            style="width:80px;flex:none;"
            :disabled="serverIsRunning"
          />
        </div>
        <div class="form-group">
          <label>心跳超时(秒)</label>
          <input
            v-model.number="serverConfig.heartbeat_timeout"
            type="number"
            placeholder="600"
            aria-label="心跳超时秒数"
            style="width:100px;flex:none;"
            :disabled="serverIsRunning"
          />
        </div>
        <div style="display:flex; gap:6px; align-self:flex-end;">
          <button
            class="btn primary"
            @click="toggleServer"
            :disabled="serverIsRunning || serverLoading"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/></svg>
            启动
          </button>
          <button
            class="btn secondary"
            @click="toggleServer"
            :disabled="!serverIsRunning || serverLoading"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 2h13a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H4"/><path d="m4 9 2-2"/><path d="M9 9h.01"/><path d="M11.5 6.5h.01"/><path d="m2 2 20 20"/><path d="M5 18H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h3"/><path d="M9 18h6"/><path d="M9 22V14"/><path d="M13 22v-4"/></svg>
            停止
          </button>
        </div>
      </div>
      <div style="margin-top:8px;">
        <div v-if="serverClients.length === 0" class="empty-state">暂无连接客户端</div>
        <table v-else class="clients-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>地址</th>
              <th>连接时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="client in serverClients" :key="client.client_id">
              <td class="mono">{{ client.client_id }}</td>
              <td class="mono">{{ client.ip }}:{{ client.port }}</td>
              <td class="mono">{{ formatTime(client.connected_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="serverInfo && serverInfo.ips.length > 0" style="margin-top:8px; padding:8px; background:var(--color-bg-subtle,#f4f4f5); border-radius:4px; font-size:11px;">
        <div style="font-weight:600; margin-bottom:4px;">服务端信息</div>
        <div style="font-family:var(--font-mono); color:var(--color-text-secondary,#71717a);">
          <div>本机 IP: {{ serverInfo.ips.join(', ') }}</div>
          <div>监听端口: {{ serverInfo.port }}</div>
          <div>客户端连接地址: {{ serverInfo.ips[0] }}:{{ serverInfo.port }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import { api, isNetworkConnectionError } from '@/api/client'
import type { ServerInfo } from '@/types'

const appStore = useAppStore()

const networkConfig = appStore.networkConfig
const serverConfig = appStore.serverConfig

const activeTab = ref(appStore.networkMode)
const connecting = ref(false)
const serverLoading = ref(false)
const serverInfo = ref<ServerInfo | null>(null)

const isNetworkConnected = computed(() => appStore.isNetworkConnected)
const serverClients = computed(() => appStore.serverClients)
const serverIsRunning = computed(() => appStore.serverIsRunning)
const wsReconnecting = computed(() => appStore.wsReconnecting)

function handleTabChange(tab: 'client' | 'server') {
  activeTab.value = tab
  appStore.networkMode = tab
}

function formatTime(isoString: string) {
  try {
    const date = new Date(isoString)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return isoString
  }
}

async function fetchServerInfo() {
  try {
    serverInfo.value = await api.getServerInfo()
  } catch (e) {
    console.warn('Failed to fetch server info:', e)
  }
}

onMounted(async () => {
  try {
    const status = await api.getNetworkStatus()
    appStore.isNetworkConnected = status.connected
    if (status.connected && status.ip && status.port && status.protocol) {
      networkConfig.ip = status.ip
      networkConfig.port = status.port
      networkConfig.protocol = status.protocol as 'UDP' | 'TCP'
    }
  } catch {
    // backend may not be running
  }

  try {
    const srvStatus = await api.getServerStatus()
    appStore.serverStatus = srvStatus
    if (srvStatus.status === 'running') {
      const clients = await api.getServerClients()
      appStore.serverClients = clients
      fetchServerInfo()
    }
  } catch {
    // backend may not be running
  }
})

async function toggleConnection() {
  connecting.value = true
  try {
    if (isNetworkConnected.value) {
      await api.disconnect()
      appStore.isNetworkConnected = false
      ElMessage.success('已断开连接')
    } else {
      const res = await api.connect({
        ip: networkConfig.ip,
        port: networkConfig.port,
        protocol: networkConfig.protocol
      })
      if (res.status) {
        appStore.isNetworkConnected = true
        ElMessage.success('连接成功')
      } else {
        ElMessage.error(res.message || '连接失败，请检查网络配置')
      }
    }
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('连接失败，无法连接到后端服务')
    else ElMessage.error('连接失败，请稍后重试')
  } finally {
    connecting.value = false
  }
}

async function stopReconnect() {
  try {
    await api.stopReconnect()
    ElMessage.success('已停止重连')
  } catch (e: any) {
    console.warn('Stop reconnect API error:', e)
  }
}

async function toggleServer() {
  serverLoading.value = true
  try {
    if (serverIsRunning.value) {
      await api.stopServer()
      appStore.serverStatus = { status: 'stopped', port: null, client_count: 0 }
      appStore.serverClients = []
      serverInfo.value = null
      ElMessage.success('服务已停止')
    } else {
      await api.startServer({
        port: serverConfig.port,
        max_clients: serverConfig.max_clients,
        heartbeat_timeout: serverConfig.heartbeat_timeout
      })
      appStore.serverStatus = { status: 'running', port: serverConfig.port, client_count: 0 }
      ElMessage.success('服务启动成功')
      fetchServerInfo()
    }
  } catch (e: any) {
    if (isNetworkConnectionError(e)) ElMessage.error('操作失败，无法连接到后端服务')
    else ElMessage.error('操作失败，请稍后重试')
  } finally {
    serverLoading.value = false
  }
}
</script>

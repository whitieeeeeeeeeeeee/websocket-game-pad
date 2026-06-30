<template>
  <div class="dashboard-root">
    <div class="status-bar">
      <span class="status-bar-title">WiFi-SPI 控制器</span>
      <div class="status-bar-right">
        <a href="#" class="author-link" aria-label="Powered By whitiee" title="Powered By whitiee">
          <span>Powered By whitiee</span>
          <Github :size="14" />
        </a>
        <router-link to="/config" class="btn ghost" aria-label="手柄配置">
          <ArrowRight :size="14" />
          手柄配置
        </router-link>
        <StatusBadge :status="wsStatus" />
        <button
          class="btn ghost"
          style="color: var(--color-danger-600);"
          @click="handleShutdown"
          :disabled="shuttingDown"
          aria-label="关闭服务"
        >
          <Power :size="14" />
        </button>
      </div>
    </div>

    <div class="dashboard-grid">
      <!-- ═══ Left Column ═══ -->
      <div class="col-left">
        <ControllerPanel />
        <RecordingPanel />
      </div>

      <!-- ═══ Center Column ═══ -->
      <div class="col-center">
        <NetworkPanel />
        <DataSender :mode="appStore.networkMode" :server-clients="appStore.serverClients" @send="handleSendData" />
      </div>

      <!-- ═══ Right Column ═══ -->
      <div class="col-right panel-scroll">
        <LogPanel />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, Power, Github } from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import { api } from '@/api/client'
import StatusBadge from '@/components/v2/StatusBadge.vue'
import ControllerPanel from '@/components/v2/ControllerPanel.vue'
import RecordingPanel from '@/components/v2/RecordingPanel.vue'
import NetworkPanel from '@/components/v2/NetworkPanel.vue'
import DataSender from '@/components/v2/DataSender.vue'
import LogPanel from '@/components/v2/LogPanel.vue'

const appStore = useAppStore()

const wsStatus = computed<'connected' | 'connecting' | 'disconnected'>(() => {
  if (appStore.wsConnected) return 'connected'
  if (appStore.wsReconnecting) return 'connecting'
  return 'disconnected'
})

const shuttingDown = ref(false)

async function handleShutdown() {
  try {
    await ElMessageBox.confirm(
      '确定要关闭后端服务吗？关闭后需要手动重启才能继续使用。',
      '退出确认',
      {
        confirmButtonText: '确定退出',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    shuttingDown.value = true
    await api.shutdown()
    ElMessage.success('服务正在关闭...')
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error('关闭服务失败，请重试')
    }
    shuttingDown.value = false
  }
}

async function handleSendData(payload: { data: string; format: string; encoding: string; clientId?: string | null }) {
  try {
    let res
    if (payload.clientId === undefined) {
      // 客户端模式 - 使用客户端发送 API
      res = await api.sendData({
        data: payload.data,
        format: payload.format,
        encoding: payload.encoding
      })
    } else {
      // 服务器模式 - 使用服务器发送 API（client_id 为 null 时广播，为字符串时定向发送）
      res = await api.sendServerData({
        data: payload.data,
        format: payload.format,
        encoding: payload.encoding,
        client_id: payload.clientId
      })
    }
    // 无论成功与否都记录通信日志
    appStore.addLog({
      direction: 'send',
      timestamp: new Date().toISOString(),
      data: payload.data,
      text: payload.data,
      format: payload.format,
      encoding: payload.encoding,
      auto: false,
    })
    if (res.success) {
      ElMessage.success(`已发送 ${payload.data.length} 字符`)
    } else {
      ElMessage.error(res.message || '发送失败')
    }
  } catch (e: any) {
    // 网络错误也记录日志
    appStore.addLog({
      direction: 'send',
      timestamp: new Date().toISOString(),
      data: payload.data,
      text: payload.data,
      format: payload.format,
      encoding: payload.encoding,
      auto: false,
    })
    ElMessage.error('发送失败：' + (e.message || '未知错误'))
  }
}

onMounted(async () => {
  // 实例检测弹窗
  try {
    const info = await api.getInstanceInfo()
    if (info.killed_old_instance) {
      ElMessageBox.alert(
        '检测到旧的后端服务，已自动杀死并重启。',
        '实例已重启',
        { confirmButtonText: '确定', type: 'success' }
      )
    } else if (info.kill_failed) {
      ElMessageBox.alert(
        `检测到旧的后端服务但无法自动杀死。\n\n请手动在终端执行以下命令杀死旧的后端服务：\n\n${info.manual_kill_cmd}`,
        '需要手动操作',
        { confirmButtonText: '确定', type: 'warning' }
      )
    }
  } catch (e) {
    // 实例检测失败不阻塞
  }
})
</script>

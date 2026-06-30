<template>
  <div class="app-root">
    <Transition name="fade">
      <div
        v-if="serviceShutdown"
        class="shutdown-overlay"
      >
        <div class="shutdown-overlay-content">
          <svg class="shutdown-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M18.36 6.64a9 9 0 1 1-12.73 0"/>
            <line x1="12" y1="2" x2="12" y2="12"/>
          </svg>
          <div class="shutdown-title">服务已关闭</div>
          <div class="shutdown-subtitle">后端服务已停止运行，您可以关闭此页面</div>
        </div>
      </div>
    </Transition>

    <router-view v-slot="{ Component }">
      <transition name="page-fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const serviceShutdown = ref(false)

defineExpose({ serviceShutdown })
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
  'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}

.shutdown-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  backdrop-filter: blur(4px);
}

.shutdown-overlay-content {
  text-align: center;
  color: #ffffff;
  padding: 32px;
  border-radius: var(--radius-md, 0.75rem);
  background: rgba(24, 24, 27, 0.85);
  border: 1px solid rgba(63, 63, 70, 0.8);
  backdrop-filter: blur(8px);
}

.shutdown-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 16px;
  color: var(--destructive, #dc2626);
}

.shutdown-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
}

.shutdown-subtitle {
  font-size: 13px;
  color: rgba(161, 161, 170, 0.9);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: all 0.25s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(0.5rem);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-0.25rem);
}
</style>

<template>
  <div class="gamepad-wrap">
    <svg class="gamepad-svg" viewBox="0 0 441 383" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="手柄可视化">
      <g id="Controller">
        <!-- Left grip (real controller shape) -->
        <path d="M220.5 294.5C220.5 294.5 195 294.5 150 294.5C105 294.5 81.5 378.5 49.5 378.5C17.5 378.5 4 363.9 4 317.5C4 271.1 43.5 165.5 55 137.5C66.5 109.5 95.5 92 128 92C154 92 200.5 92 220.5 92" class="gp-body"/>
        <!-- Right grip -->
        <path d="M220 294.5C220 294.5 245.5 294.5 290.5 294.5C335.5 294.5 359 378.5 391 378.5C423 378.5 436.5 363.9 436.5 317.5C436.5 271.1 397 165.5 385.5 137.5C374 109.5 345 92 312.5 92C286.5 92 240 92 220 92" class="gp-body"/>
        <!-- LT trigger -->
        <path d="m152.5,52.97c0,4.62 -3.36,8.36 -7.5,8.36l-13,0c-4.14,0 -7.5,-3.74 -7.5,-8.36l0,-22.86c0,-8.62 6.27,-15.61 14,-15.61c7.73,0 14,6.99 14,15.61l0,22.86z" class="gp-trigger" data-gp="lt" :style="{ fill: triggers.LT > 0 ? '#AED581' : '#3f3f46', fillOpacity: 0.3 + triggers.LT * 0.7, stroke: triggers.LT > 0 ? '#AED581' : '#52525b', filter: triggers.LT > 0.05 ? `drop-shadow(0 0 ${triggers.LT * 8}px #AED581)` : 'none' }"/>
        <!-- RT trigger -->
        <path d="m316.83,53.44c0,4.64 -3.44,8.39 -7.68,8.39l-13.31,0c-4.24,0 -7.68,-3.76 -7.68,-8.39l0,-22.94c0,-8.65 6.42,-15.67 14.33,-15.67c7.92,0 14.33,7.01 14.33,15.67l0,22.94z" class="gp-trigger" data-gp="rt" :style="{ fill: triggers.RT > 0 ? '#AED581' : '#3f3f46', fillOpacity: 0.3 + triggers.RT * 0.7, stroke: triggers.RT > 0 ? '#AED581' : '#52525b', filter: triggers.RT > 0.05 ? `drop-shadow(0 0 ${triggers.RT * 8}px #AED581)` : 'none' }"/>
        <!-- LB shoulder -->
        <rect x="116.83" y="66.83" width="43.33" height="17" rx="6.5" class="gp-shoulder" data-gp="lb" :class="{ pressed: buttons.LB }"/>
        <text x="138.5" y="79" class="gp-label">LB</text>
        <!-- RB shoulder -->
        <rect x="281.33" y="67" width="42.67" height="17" rx="6.5" class="gp-shoulder" data-gp="rb" :class="{ pressed: buttons.RB }"/>
        <text x="302.5" y="79" class="gp-label">RB</text>
        <!-- Left stick base -->
        <circle cx="113" cy="160" r="37.5" class="gp-stick-base" data-gp="lstick" :class="{ pressed: buttons.LS }"/>
        <circle :cx="113 + axes.LX * 10" :cy="160 - axes.LY * 10" r="28" class="gp-stick-thumb"/>
        <circle cx="113" cy="160" r="22" class="gp-stick-ring"/>
        <!-- Right stick base -->
        <circle cx="278" cy="238" r="37.5" class="gp-stick-base" data-gp="rstick" :class="{ pressed: buttons.RS }"/>
        <circle :cx="278 + axes.RX * 10" :cy="238 - axes.RY * 10" r="28" class="gp-stick-thumb"/>
        <circle cx="278" cy="238" r="22" class="gp-stick-ring"/>
        <!-- D-pad center -->
        <circle cx="166" cy="238" r="37.5" class="gp-dpad-center"/>
        <!-- D-pad up -->
        <rect x="159" y="211" width="14" height="20" class="gp-dpad-dir" data-gp="dup" :class="{ pressed: buttons.DpadUp }"/>
        <!-- D-pad down -->
        <rect x="159" y="244" width="14" height="20" class="gp-dpad-dir" data-gp="ddown" :class="{ pressed: buttons.DpadDown }"/>
        <!-- D-pad left -->
        <rect x="142" y="228" width="14" height="20" transform="rotate(-90 149 238)" class="gp-dpad-dir" data-gp="dleft" :class="{ pressed: buttons.DpadLeft }"/>
        <!-- D-pad right -->
        <rect x="176" y="228" width="14" height="20" transform="rotate(-90 183 238)" class="gp-dpad-dir" data-gp="dright" :class="{ pressed: buttons.DpadRight }"/>
        <!-- D-pad center dot -->
        <rect x="159" y="228" width="14" height="19" class="gp-dpad-center"/>
        <!-- ABXY buttons (diamond layout) -->
        <circle cx="329" cy="140" r="13" class="gp-abxy gp-abxy-y" data-gp="y" :class="{ pressed: buttons.Y }"/>
        <text x="329" y="140" class="gp-abxy-text">Y</text>
        <circle cx="310" cy="162" r="13" class="gp-abxy gp-abxy-x" data-gp="x" :class="{ pressed: buttons.X }"/>
        <text x="310" y="162" class="gp-abxy-text">X</text>
        <circle cx="348" cy="161" r="13" class="gp-abxy gp-abxy-b" data-gp="b" :class="{ pressed: buttons.B }"/>
        <text x="348" y="161" class="gp-abxy-text">B</text>
        <circle cx="330" cy="181" r="13" class="gp-abxy gp-abxy-a" data-gp="a" :class="{ pressed: buttons.A }"/>
        <text x="330" y="181" class="gp-abxy-text">A</text>
        <!-- Select button -->
        <circle cx="188" cy="162" r="10" class="gp-meta-btn" data-gp="select" :class="{ pressed: buttons.Back }"/>
        <rect x="184" y="159" width="8" height="6" rx="1" class="gp-meta-icon"/>
        <!-- Start button -->
        <circle cx="253" cy="162" r="10" class="gp-meta-btn" data-gp="start" :class="{ pressed: buttons.Start }"/>
        <g class="gp-meta-icon">
          <line x1="248" y1="158" x2="258" y2="158"/>
          <line x1="248" y1="162" x2="258" y2="162"/>
          <line x1="248" y1="166" x2="258" y2="166"/>
        </g>
        <!-- Guide button -->
        <rect x="211.5" y="153" width="18" height="18" rx="9" class="gp-guide-outer" data-gp="guide"/>
        <g class="gp-guide-icon">
          <path d="M220.5 158 V164 M218 160.5 L220.5 158 L223 160.5 M218 166 H223" stroke-linecap="round" stroke-linejoin="round"/>
        </g>
      </g>
    </svg>
    <!-- 断开 overlay -->
    <div v-if="!state.connected" class="gamepad-overlay">未连接</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const state = computed(() => appStore.controllerState)
const buttons = computed(() => state.value.buttons)
const axes = computed(() => state.value.axes)
const triggers = computed(() => state.value.triggers)
</script>

<style scoped></style>

import { createRouter, createWebHashHistory } from 'vue-router'
import ControllerConfigPage from '@/pages/ControllerConfigPage.vue'
import DashboardV2 from '@/pages/DashboardV2.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: DashboardV2,
  },
  {
    path: '/config',
    name: 'config',
    component: ControllerConfigPage,
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router


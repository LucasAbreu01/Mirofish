import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/HomeView.vue')
  },
  {
    path: '/graph/:id',
    name: 'Graph',
    component: () => import('../views/GraphView.vue')
  },
  {
    path: '/setup/:id',
    name: 'Setup',
    component: () => import('../views/SetupView.vue')
  },
  {
    path: '/simulation/:id',
    name: 'Simulation',
    component: () => import('../views/SimulationView.vue')
  },
  {
    path: '/report/:id',
    name: 'Report',
    component: () => import('../views/ReportView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

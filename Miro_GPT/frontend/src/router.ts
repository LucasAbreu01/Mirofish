import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'upload',
      component: () => import('./views/UploadView.vue'),
    },
    {
      path: '/projects/:projectId/graph',
      name: 'graph',
      component: () => import('./views/GraphView.vue'),
      props: true,
    },
    {
      path: '/projects/:projectId/simulation/:simulationId?',
      name: 'simulation',
      component: () => import('./views/SimulationView.vue'),
      props: true,
    },
    {
      path: '/reports/:reportId',
      name: 'report',
      component: () => import('./views/ReportView.vue'),
      props: true,
    },
  ],
})

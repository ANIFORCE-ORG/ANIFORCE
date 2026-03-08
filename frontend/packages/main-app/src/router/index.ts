import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/pages/Home.vue'),
    },
    {
      path: '/market-analysis',
      name: 'market-analysis',
      component: () => import('@/pages/MarketAnalysis.vue'),
    },
    {
      path: '/material',
      name: 'material',
      component: () => import('@/pages/Material.vue'),
    },
    {
      path: '/campaign',
      name: 'campaign',
      component: () => import('@/pages/Campaign.vue'),
    },
    {
      path: '/monitor',
      name: 'monitor',
      component: () => import('@/pages/Monitor.vue'),
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/pages/Dashboard.vue'),
    },
    {
      path: '/projects',
      name: 'projects',
      component: () => import('@/pages/Projects.vue'),
    },
    {
      path: '/projects/:id',
      name: 'project-detail',
      component: () => import('@/pages/ProjectDetail.vue'),
    },
    {
      path: '/campaigns/:id',
      name: 'campaign-detail',
      component: () => import('@/pages/CampaignDetail.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/Login.vue'),
    },
  ],
})

export default router

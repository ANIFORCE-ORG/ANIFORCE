import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/dashboard',
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
      path: '/campaigns/create',
      name: 'create-campaign',
      component: () => import('@/pages/CreateCampaign.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/Login.vue'),
    },
    // AI生成素材路由
    {
      path: '/material/ai-generate/new',
      name: 'ai-generate-new',
      component: () => import('@/pages/AIGenerateNew.vue'),
    },
    {
      path: '/material/ai-generate/remix',
      name: 'ai-generate-remix',
      component: () => import('@/pages/AIGenerateRemix.vue'),
    },
    {
      path: '/material/ai-generate/hot',
      name: 'ai-generate-hot',
      component: () => import('@/pages/AIGenerateHot.vue'),
    },
    {
      path: '/material/ai-generate/mix',
      name: 'ai-generate-mix',
      component: () => import('@/pages/AIGenerateMix.vue'),
    },
  ],
})

export default router

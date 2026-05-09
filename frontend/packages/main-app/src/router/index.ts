import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0 }
  },
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
      path: '/platform-accounts',
      name: 'platform-accounts',
      component: () => import('@/pages/MediaOps.vue'),
    },
    {
      path: '/platform-accounts/manage',
      name: 'platform-accounts-manage',
      component: () => import('@/pages/PlatformAccounts.vue'),
    },
    {
      path: '/media-ops',
      name: 'media-ops',
      redirect: '/platform-accounts',
    },
    {
      path: '/platform-connections',
      name: 'platform-connections',
      component: () => import('@/pages/PlatformConnections.vue'),
    },
    {
      path: '/platform-accounts/callback',
      name: 'platform-accounts-callback',
      component: () => import('@/pages/PlatformAccountsCallback.vue'),
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/pages/Dashboard.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/pages/Settings.vue'),
    },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('@/pages/Reports.vue'),
    },
    {
      path: '/monitor',
      name: 'monitor',
      redirect: '/reports',
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

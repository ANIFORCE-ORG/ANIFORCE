import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'marketing-home',
      component: () => import('@/pages/MarketingHome.vue'),
    },
    {
      path: '/contact',
      name: 'contact',
      component: () => import('@/pages/Contact.vue'),
    },
    {
      path: '/home',
      name: 'home',
      component: () => import('@/pages/Home.vue'),
    },
    {
      path: '/market-analysis',
      name: 'market-analysis',
      component: () => import('@/pages/MarketAnalysis.vue'),
    },
    {
      path: '/campaign',
      name: 'campaign',
      redirect: '/projects',
    },
    {
      path: '/material',
      name: 'material',
      component: () => import('@/pages/creatives/Material.vue'),
    },
    {
      path: '/monitor',
      name: 'monitor',
      component: () => import('@/pages/Monitor.vue'),
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      redirect: '/monitor',
    },
    {
      path: '/projects',
      name: 'projects',
      component: () => import('@/pages/projects/Projects.vue'),
    },
    {
      path: '/projects/:id',
      name: 'project-detail',
      component: () => import('@/pages/projects/ProjectDetail.vue'),
    },
    {
      path: '/campaigns/:id',
      name: 'campaign-detail',
      component: () => import('@/pages/campaigns/CampaignDetail.vue'),
    },
    {
      path: '/campaigns/create',
      name: 'create-campaign',
      component: () => import('@/pages/campaigns/CreateCampaign.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/starting/Login.vue'),
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/pages/starting/Register.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/pages/settings/Settings.vue'),
    },
    {
      path: '/organization-settings',
      name: 'organization-settings',
      redirect: '/account-config',
    },
    {
      path: '/account-config',
      name: 'account-config',
      component: () => import('@/pages/settings/AccountConfig.vue'),
    },
    {
      path: '/ai-usage-config',
      name: 'ai-usage-config',
      component: () => import('@/pages/settings/AIUsageConfig.vue'),
    },
    {
      path: '/platform-connections',
      name: 'platform-connections',
      component: () => import('@/pages/settings/PlatformConnections.vue'),
    },
  ],
})

// 导航守卫 - 统一处理路由保护和重定向
router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  
  // 需要登录的页面列表
  const requiresAuth = ['/home', '/dashboard', '/projects', '/campaign', '/material', '/monitor', '/settings', '/organization-settings', '/account-config', '/ai-usage-config', '/platform-connections']
  
  // 未登录用户访问需要登录的页面,重定向到登录页
  if (requiresAuth.includes(to.path) && !auth.isLoggedIn) {
    next('/login')
    return
  }
  
  // 已登录用户访问登录页,重定向到/home
  if (to.path === '/login' && auth.isLoggedIn) {
    next('/home')
    return
  }
  
  next()
})

export default router

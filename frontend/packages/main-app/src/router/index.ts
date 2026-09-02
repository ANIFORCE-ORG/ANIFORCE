import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'get-start-formal',
      component: () => import('@/pages/starting/GetStartFormal.vue'),
    },
    {
      path: '/getstart',
      name: 'get-start',
      component: () => import('@/pages/starting/GetStart.vue'),
    },
    {
      path: '/home',
      name: 'home',
      component: () => import('@/pages/Home.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/market-analysis',
      name: 'market-analysis',
      component: () => import('@/pages/MarketAnalysis.vue'),
    },
    {
      path: '/material',
      name: 'material',
      component: () => import('@/pages/creatives/Material.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/monitor',
      name: 'monitor',
      component: () => import('@/pages/Monitor.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/pages/Dashboard.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/projects',
      name: 'projects',
      component: () => import('@/pages/projects/Projects.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/projects/:id',
      name: 'project-detail',
      component: () => import('@/pages/projects/ProjectDetail.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/campaigns/:id',
      name: 'campaign-detail',
      component: () => import('@/pages/campaigns/CampaignDetail.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/campaigns/:campaignId/ad-units/create',
      name: 'create-ad-unit',
      component: () => import('@/pages/campaigns/CreateAdUnit.vue'),
      meta: { workspaceShell: true },
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
      meta: { workspaceShell: true },
    },
    {
      path: '/account-config',
      name: 'account-config',
      component: () => import('@/pages/settings/AccountConfig.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/ai-usage-config',
      name: 'ai-usage-config',
      component: () => import('@/pages/settings/AIUsageConfig.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/platform-connections',
      name: 'platform-connections',
      component: () => import('@/pages/settings/PlatformConnections.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/system-admin',
      name: 'system-admin',
      component: () => import('@/pages/system/SystemAdmin.vue'),
      meta: { workspaceShell: true },
    },
    {
      path: '/privacy',
      name: 'privacy-policy',
      component: () => import('@/pages/legal/PrivacyPolicy.vue'),
    },
    {
      path: '/terms',
      name: 'terms-of-service',
      component: () => import('@/pages/legal/TermsOfService.vue'),
    },
    {
      path: '/contact',
      name: 'contact',
      component: () => import('@/pages/legal/Contact.vue'),
    },
  ],
})

// 导航守卫 - 统一处理路由保护和重定向
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  // 本地 Demo 模式直接进入业务页面，不经过登录页。
  // 仅在 VITE_DEMO_MODE=true 时生效，生产环境仍使用正常认证流程。
  if (import.meta.env.VITE_DEMO_MODE === 'true' && !auth.isLoggedIn && !auth.hasExplicitDemoLogout) {
    auth.fakeLogin()
  }

  // Workspace routes, including dynamic detail routes, require authentication.
  const requiresAuth = to.meta.workspaceShell === true

  // 已登录用户访问GetStart页面,重定向到/home
  if (to.path === '/' && auth.isLoggedIn) {
    next('/home')
    return
  }

  // 未登录用户访问需要登录的页面,重定向到登录页
  if (requiresAuth && !auth.isLoggedIn) {
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

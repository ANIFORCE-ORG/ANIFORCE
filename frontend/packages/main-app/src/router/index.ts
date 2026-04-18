import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'get-start',
      component: () => import('@/pages/GetStart.vue'),
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
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/pages/Settings.vue'),
    },
  ],
})

// 导航守卫 - 统一处理路由保护和重定向
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  
  // 需要登录的页面列表
  const requiresAuth = ['/home', '/dashboard', '/projects', '/campaign', '/material', '/monitor', '/settings']
  
  // 已登录用户访问GetStart页面,重定向到/home
  if (to.path === '/' && auth.isLoggedIn) {
    next('/home')
    return
  }
  
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

export interface NavItem {
  id: string
  icon: string
  label: string
  path: string
}

export const navItems: NavItem[] = [
  { id: 'new-task', icon: 'add_circle', label: '新任务', path: '/home' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/projects' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'query_stats', label: '数据复盘', path: '/monitor' },
  { id: 'settings', icon: 'settings', label: '账户设置', path: '/settings' }
]

export interface NavItem {
  id: string
  icon: string
  label: string
  path: string
}

export const navItems: NavItem[] = [
  { id: 'new-task', icon: 'add_circle', label: '新任务', path: '/home' },
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/monitor' },
  { id: 'reports', icon: 'query_stats', label: '数据复盘', path: '/monitor' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告计划', path: '/projects' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'settings', icon: 'settings', label: '账户设置', path: '/settings' }
]

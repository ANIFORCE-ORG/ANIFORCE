export interface NavItem {
  id: string
  icon: string
  label: string
  path: string
}

export const navItems: NavItem[] = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/monitor' },
  { id: 'settings', icon: 'settings', label: '账户设置', path: '/settings' }
]

/**
 * 工具名称映射：将后台技术名称转换为用户友好的中文描述
 */

export const TOOL_NAME_MAP: Record<string, string> = {
  // 项目管理
  get_project_detail: '查询项目详情',
  list_projects: '查询项目列表',
  create_project: '创建项目',
  update_project: '更新项目',
  delete_project: '删除项目',

  // 广告计划管理
  get_campaign_detail: '查询广告计划详情',
  list_campaigns: '查询广告计划列表',
  create_campaign: '创建广告计划',
  update_campaign: '更新广告计划',
  update_campaign_status: '更新广告计划状态',
  delete_campaign: '删除广告计划',
  get_campaign_materials: '查询计划关联素材',

  // 素材管理
  get_material_detail: '查询素材详情',
  list_materials: '查询素材列表',
  create_material: '创建素材',
  update_material: '更新素材',
  delete_material: '删除素材',
  get_material_image: '查询素材图片',
  list_available_images: '查询本地图片',

  // 关联操作
  add_material_to_campaign: '关联素材到计划',
  remove_material_from_campaign: '从计划移除素材',
  add_material_to_project: '关联素材到项目',
  remove_material_from_project: '从项目移除素材',

  // Workspace
  request_workspace_projection: '投影到右侧面板',
}

/**
 * 获取用户友好的工具名称
 * @param toolName 技术名称（如 get_project_detail）
 * @returns 用户友好名称（如 查询项目详情）
 */
export function getFriendlyToolName(toolName: string): string {
  return TOOL_NAME_MAP[toolName] || toolName
}

/**
 * 工具分类图标
 */
export const TOOL_ICON_MAP: Record<string, string> = {
  get_project_detail: '📋',
  list_projects: '📂',
  create_project: '✨',
  update_project: '✏️',
  delete_project: '🗑️',

  get_campaign_detail: '📊',
  list_campaigns: '📈',
  create_campaign: '🚀',
  update_campaign: '✏️',
  update_campaign_status: '⚡',
  delete_campaign: '🗑️',

  get_material_detail: '🖼️',
  list_materials: '🎨',
  create_material: '➕',
  update_material: '✏️',
  delete_material: '🗑️',
  get_material_image: '🖼️',
  list_available_images: '📁',

  add_material_to_campaign: '🔗',
  remove_material_from_campaign: '🔓',
  add_material_to_project: '🔗',
  remove_material_from_project: '🔓',

  request_workspace_projection: '👉',
}

/**
 * 获取工具图标
 */
export function getToolIcon(toolName: string): string {
  return TOOL_ICON_MAP[toolName] || '🔧'
}

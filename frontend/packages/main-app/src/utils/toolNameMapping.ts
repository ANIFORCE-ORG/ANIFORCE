/**
 * Frontend-only presentation registry for Agent tool activity.
 * Runtime tool names remain unchanged; this module controls what users see.
 */

export type ToolPresentationState = 'running' | 'completed' | 'error'
export type ToolPresentationCategory = 'read' | 'write' | 'link' | 'work'

interface ToolPresentationDefinition {
  visibility?: 'user' | 'hidden'
  category: ToolPresentationCategory
  icon: string
  running: string
  completed: string
  error: string
  summary?: (result: unknown) => string
}

export interface ToolPresentation {
  visible: boolean
  category: ToolPresentationCategory
  icon: string
  title: string
  summary: string
}

export interface HiddenToolActivity {
  icon: string
  label: string
}

function collectionSummary(keys: string[], noun: string) {
  return (result: unknown): string => {
    const count = collectionCount(result, keys, noun)
    return count === null ? '' : `找到 ${count} 个${noun}`
  }
}

type MetaSummaryKind = 'overview' | 'account' | 'campaign' | 'trend'

function metaDashboardSummary(kind: MetaSummaryKind) {
  return (result: unknown): string => {
    const overview = findDashboardOverview(result)
    if (!overview) return ''

    const accounts = Array.isArray(overview.accounts) ? overview.accounts : []
    const campaigns = Array.isArray(overview.campaigns) ? overview.campaigns : []
    const adsets = Array.isArray(overview.adsets) ? overview.adsets : []
    const trend = Array.isArray(overview.trend) ? overview.trend : []
    const window = isRecord(overview.window) ? overview.window : {}

    if (kind === 'account') {
      const account = accounts.length === 1 && isRecord(accounts[0]) ? accounts[0] : null
      const name = account && String(account.account_name || account.account_id || '').trim()
      return name ? `${name} · ${trend.length || 0} 天` : `${trend.length || 0} 天数据`
    }
    if (kind === 'campaign') return `${campaigns.length} 个 Campaign · ${adsets.length} 个 AdSet`
    if (kind === 'trend') {
      const since = compactDate(window.since)
      const until = compactDate(window.until)
      return since && until ? `${trend.length} 天 · ${since} 至 ${until}` : `${trend.length} 天数据`
    }

    const quality = isRecord(overview.data_quality) ? overview.data_quality : {}
    const covered = Number(quality.accounts_with_rows)
    const expected = Number(quality.accounts_expected)
    if (Number.isFinite(covered) && Number.isFinite(expected)) return `${covered} / ${expected} 个账号有数据`
    return `${accounts.length} 个广告账号`
  }
}

const TOOL_PRESENTATION_REGISTRY: Record<string, ToolPresentationDefinition> = {
  // Project management
  get_project_detail: tool('read', 'description', '读取项目详情'),
  list_projects: tool('read', 'folder_open', '查询项目列表', collectionSummary(['projects', 'items', 'list'], '项目')),
  create_project: tool('write', 'create_new_folder', '创建项目'),
  update_project: tool('write', 'edit_note', '更新项目'),
  delete_project: tool('write', 'delete', '删除项目'),

  // Campaign management
  get_campaign_detail: tool('read', 'description', '读取广告计划详情'),
  list_campaigns: tool('read', 'campaign', '查询广告计划', collectionSummary(['campaigns', 'items', 'list'], '广告计划')),
  create_campaign: tool('write', 'add_circle', '创建广告计划'),
  update_campaign: tool('write', 'edit_note', '更新广告计划'),
  update_campaign_status: tool('write', 'published_with_changes', '调整广告计划状态'),
  delete_campaign: tool('write', 'delete', '删除广告计划'),
  get_campaign_materials: tool('read', 'perm_media', '查询关联素材', collectionSummary(['materials', 'items', 'list'], '素材')),

  // Material management
  get_material_detail: tool('read', 'description', '读取素材详情'),
  list_materials: tool('read', 'video_library', '查询创意素材', collectionSummary(['materials', 'items', 'list'], '素材')),
  create_material: tool('write', 'add_photo_alternate', '创建素材'),
  update_material: tool('write', 'edit_note', '更新素材'),
  delete_material: tool('write', 'delete', '删除素材'),
  get_material_image: tool('read', 'image', '读取素材图片'),
  list_available_images: tool('read', 'photo_library', '读取可用素材', collectionSummary(['files', 'images', 'items', 'list'], '素材')),

  // Meta performance
  list_meta_ad_accounts_with_spend: tool(
    'read',
    'monitoring',
    '汇总 Meta 投放数据',
    metaDashboardSummary('overview'),
  ),
  get_meta_account_performance: tool(
    'read',
    'account_balance',
    '读取广告账号表现',
    metaDashboardSummary('account'),
  ),
  get_meta_campaign_performance: tool(
    'read',
    'campaign',
    '比较 Campaign 与 AdSet',
    metaDashboardSummary('campaign'),
  ),
  get_meta_performance_trend: tool(
    'read',
    'show_chart',
    '生成投放趋势',
    metaDashboardSummary('trend'),
  ),

  // Relationships
  add_material_to_campaign: tool('link', 'link', '关联素材与广告计划'),
  remove_material_from_campaign: tool('link', 'link_off', '移除广告计划素材'),
  add_material_to_project: tool('link', 'link', '关联素材与项目'),
  remove_material_from_project: tool('link', 'link_off', '移除项目素材'),

  // Internal orchestration
  request_workspace_projection: hiddenTool(),
}

function tool(
  category: ToolPresentationCategory,
  icon: string,
  action: string,
  summary?: (result: unknown) => string,
): ToolPresentationDefinition {
  return {
    category,
    icon,
    running: `正在${action}`,
    completed: `已${action}`,
    error: `${action.replace(/^(查询|读取)/, '$1')}失败`,
    summary,
  }
}

function hiddenTool(): ToolPresentationDefinition {
  return {
    visibility: 'hidden',
    category: 'work',
    icon: 'progress_activity',
    running: '',
    completed: '',
    error: '',
  }
}

const fallbackCopy: Record<ToolPresentationState, string> = {
  running: '正在处理任务',
  completed: '已完成一项处理',
  error: '任务处理失败',
}

export function hasToolPresentationDefinition(toolName: string): boolean {
  return Boolean(TOOL_PRESENTATION_REGISTRY[normalizeToolName(toolName)])
}

export function getToolPresentation(
  toolName: string,
  state: ToolPresentationState,
  result?: unknown,
): ToolPresentation {
  const normalizedName = normalizeToolName(toolName)
  const definition = TOOL_PRESENTATION_REGISTRY[normalizedName]

  // Skill selection belongs to the task state UI, not the tool activity stream.
  if (isSkillTool(normalizedName)) {
    return { visible: false, category: 'work', icon: 'progress_activity', title: '', summary: '' }
  }

  if (!definition) {
    return {
      visible: true,
      category: 'work',
      icon: 'progress_activity',
      title: fallbackCopy[state],
      summary: '',
    }
  }

  const visible = definition.visibility !== 'hidden'
  return {
    visible,
    category: definition.category,
    icon: definition.icon,
    title: definition[state],
    summary: visible && state === 'completed' && definition.summary ? definition.summary(result) : '',
  }
}

export function getHiddenToolActivity(
  toolName: string,
  state: ToolPresentationState,
): HiddenToolActivity | null {
  const normalizedName = normalizeToolName(toolName)
  if (normalizedName === 'request_workspace_projection') {
    return {
      icon: 'dashboard_customize',
      label: state === 'running' ? '正在更新工作台' : '正在整理工作台内容',
    }
  }
  if (isSkillTool(normalizedName)) {
    return { icon: 'account_tree', label: '正在准备处理流程' }
  }
  if (!getToolPresentation(normalizedName, state).visible) {
    return { icon: 'progress_activity', label: '正在处理任务' }
  }
  return null
}

function normalizeToolName(toolName: string): string {
  return String(toolName || '').trim().toLowerCase()
}

function isSkillTool(toolName: string): boolean {
  return toolName.includes('skill')
}

function collectionCount(result: unknown, keys: string[], noun: string): number | null {
  const parsed = parseJsonLike(result)
  if (Array.isArray(parsed)) return parsed.length
  if (parsed && typeof parsed === 'object') {
    const record = parsed as Record<string, unknown>
    for (const key of keys) {
      if (Array.isArray(record[key])) return record[key].length
    }
    for (const key of ['data', 'result', 'output', 'content']) {
      if (record[key] !== undefined) {
        const nested = collectionCount(record[key], keys, noun)
        if (nested !== null) return nested
      }
    }
  }
  if (typeof parsed === 'string') {
    const escapedNoun = noun.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const match = new RegExp(`(?:找到|共)\\s*(\\d+)\\s*个?${escapedNoun}`).exec(parsed)
    return match ? Number(match[1]) : null
  }
  return null
}

function findDashboardOverview(result: unknown): Record<string, unknown> | null {
  const parsed = parseJsonLike(result)
  if (!isRecord(parsed)) return null
  if (isRecord(parsed.window) && isRecord(parsed.kpis)) return parsed
  for (const key of ['data', 'result', 'output', 'content']) {
    if (parsed[key] === undefined) continue
    const nested = findDashboardOverview(parsed[key])
    if (nested) return nested
  }
  return null
}

function compactDate(value: unknown): string {
  const text = String(value || '')
  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text.slice(5) : ''
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function parseJsonLike(result: unknown): unknown {
  if (typeof result !== 'string') return result
  const trimmed = result.trim()
  if (!trimmed || !['{', '['].includes(trimmed[0])) return result
  try {
    return JSON.parse(trimmed)
  } catch {
    return result
  }
}

// Compatibility exports for callers outside MessageView.
export const TOOL_NAME_MAP: Record<string, string> = Object.fromEntries(
  Object.entries(TOOL_PRESENTATION_REGISTRY)
    .filter(([, definition]) => definition.visibility !== 'hidden')
    .map(([name, definition]) => [name, definition.completed]),
)

export function getFriendlyToolName(toolName: string): string {
  return TOOL_NAME_MAP[toolName] || fallbackCopy.completed
}

export const TOOL_ICON_MAP: Record<string, string> = Object.fromEntries(
  Object.entries(TOOL_PRESENTATION_REGISTRY).map(([name, definition]) => [name, definition.icon]),
)

export function getToolIcon(toolName: string): string {
  return TOOL_ICON_MAP[toolName] || 'progress_activity'
}

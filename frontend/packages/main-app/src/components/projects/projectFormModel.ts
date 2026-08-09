/**
 * 项目表单模型 - 页面表单和 Workspace 审核表单共用，不新造字段
 */

export interface ProjectFormModel {
  name: string
  product: string
  countries: string      // 对应 API 的 target_market
  status: string
  start: string          // 对应 API 的 start_date
  end: string            // 对应 API 的 end_date
  total_budget: number
  description: string
}

export interface CreateProjectPayload {
  name: string
  product?: string
  target_market?: string
  status?: string
  start_date?: string
  end_date?: string
  total_budget?: number
  description?: string
  [key: string]: unknown
}

export function getDefaultStartDate(): string {
  return new Date().toISOString().slice(0, 16)
}

export function getDefaultEndDate(): string {
  const now = new Date()
  const sevenDaysLater = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
  return sevenDaysLater.toISOString().slice(0, 16)
}

export function emptyProjectForm(): ProjectFormModel {
  return {
    name: '',
    product: '',
    countries: '',
    status: 'active',
    start: getDefaultStartDate(),
    end: getDefaultEndDate(),
    total_budget: 0,
    description: '',
  }
}

/** API payload -> 表单模型（用于 Workspace 审核表单初始化） */
export function fromCreateProjectArgs(args: Record<string, unknown>): ProjectFormModel {
  const formatDateForInput = (dateString: string | undefined | null): string => {
    if (!dateString) return getDefaultStartDate()
    try {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return getDefaultStartDate()
      return date.toISOString().slice(0, 16)
    } catch {
      return getDefaultStartDate()
    }
  }
  return {
    name: String(args.name || ''),
    product: String(args.product || ''),
    countries: String(args.target_market || args.countries || ''),
    status: String(args.status || 'active'),
    start: formatDateForInput(args.start_date as string | undefined),
    end: formatDateForInput(args.end_date as string | undefined),
    total_budget: Number(args.total_budget || 0),
    description: String(args.description || ''),
  }
}

/** 表单模型 -> API payload（用于 approve 时提交最终参数） */
export function toCreateProjectPayload(form: ProjectFormModel): CreateProjectPayload {
  return {
    name: form.name,
    product: form.product,
    target_market: form.countries,
    status: form.status,
    start_date: form.start,
    end_date: form.end,
    total_budget: form.total_budget,
    description: form.description,
  }
}

export const projectCountryOptions = [
  { code: 'US', name: 'United States' },
  { code: 'CA', name: 'Canada' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'AU', name: 'Australia' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  { code: 'JP', name: 'Japan' },
  { code: 'KR', name: 'South Korea' },
  { code: 'TW', name: 'Taiwan' },
  { code: 'HK', name: 'Hong Kong' },
  { code: 'SG', name: 'Singapore' },
  { code: 'CN', name: 'China' },
  { code: 'BR', name: 'Brazil' },
  { code: 'IN', name: 'India' },
  { code: 'TH', name: 'Thailand' },
  { code: 'VN', name: 'Vietnam' },
  { code: 'ID', name: 'Indonesia' },
  { code: 'MY', name: 'Malaysia' },
  { code: 'PH', name: 'Philippines' },
]

export const projectStatusOptions = [
  { value: 'active', label: '进行中' },
  { value: 'paused', label: '已暂停' },
  { value: 'completed', label: '已完成' },
  { value: 'draft', label: '草稿' },
]

/** 对比原始参数和编辑后参数，返回 diff */
export function diffProjectArgs(
  original: Record<string, unknown>,
  edited: CreateProjectPayload,
): Array<{ field: string; before: unknown; after: unknown }> {
  const fields: Array<{ key: string; label: string }> = [
    { key: 'name', label: 'name' },
    { key: 'product', label: 'product' },
    { key: 'target_market', label: 'target_market' },
    { key: 'status', label: 'status' },
    { key: 'start_date', label: 'start_date' },
    { key: 'end_date', label: 'end_date' },
    { key: 'total_budget', label: 'total_budget' },
    { key: 'description', label: 'description' },
  ]
  const diff: Array<{ field: string; before: unknown; after: unknown }> = []
  for (const field of fields) {
    const before = original[field.key]
    const after = (edited as Record<string, unknown>)[field.key]
    if (String(before ?? '') !== String(after ?? '')) {
      diff.push({ field: field.label, before, after })
    }
  }
  return diff
}

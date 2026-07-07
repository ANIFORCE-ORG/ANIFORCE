/**
 * Workspace 投影 Store
 *
 * 职责：管理 Agent run 对业务页面的投影、可编辑审批草稿、用户交互记录。
 * 不重新实现业务组件，只做投影容器和事件桥。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Project } from '@/api/projects'
import type {
  ProjectFormModel,
  CreateProjectPayload,
} from '@/components/projects/projectFormModel'
  import {
  fromCreateProjectArgs,
  toCreateProjectPayload,
  diffProjectArgs,
  emptyProjectForm,
} from '@/components/projects/projectFormModel'

// ==================== 类型定义 ====================

export interface WorkspaceProjection {
  id: string
  sessionId: string
  runId?: string
  surface: WorkspaceSurface
  sourceToolName?: string
  sourceToolCallId?: string
  mode: WorkspaceProjectionMode
  payload: Record<string, unknown>
  approval?: {
    runId: string
    checkpointId: string
    decisionStatus: 'pending' | 'approved' | 'rejected'
  }
  updatedAt: number
}

export type WorkspaceSurface =
  | 'project.list'
  | 'project.detail'
  | 'project.create'
  | 'project.delete'
  | 'campaign.list'
  | 'campaign.create'
  | 'campaign.status'
  | 'material.list'

export type WorkspaceProjectionMode =
  | 'loading'
  | 'readonly'
  | 'editable'
  | 'review'
  | 'executing'
  | 'completed'
  | 'stale'
  | 'failed'

export interface WorkspaceApprovalDraft {
  id: string               // = checkpointId
  runId: string
  checkpointId: string
  toolName: string
  surface: WorkspaceSurface
  originalArguments: Record<string, unknown>
  editedArguments: Record<string, unknown>   // API payload 格式
  formModel?: ProjectFormModel               // 表单格式（project.create 专用）
  dirtyFields: string[]
  status: 'pending' | 'approved' | 'rejected' | 'executing' | 'completed'
  updatedAt: number
}

export interface WorkspaceInteractionEvent {
  id: string
  sessionId: string
  runId?: string
  type:
    | 'entity.selected'
    | 'entity.unselected'
    | 'draft.field_changed'
    | 'approval.confirmed'
    | 'approval.rejected'
  surface: string
  field?: string
  before?: unknown
  after?: unknown
  createdAt: number
}

export interface SelectedEntity {
  type: 'project' | 'campaign' | 'material'
  id: string
  name?: string
}

// ==================== Store ====================

export const useWorkspaceStore = defineStore('workspace', () => {
  const projectionsBySession = ref<Map<string, WorkspaceProjection[]>>(new Map())
  const approvalDrafts = ref<Map<string, WorkspaceApprovalDraft>>(new Map())  // key = checkpointId
  const selectedEntitiesBySession = ref<Map<string, SelectedEntity[]>>(new Map())
  const interactionsBySession = ref<Map<string, WorkspaceInteractionEvent[]>>(new Map())

  // ==================== Projection 操作 ====================

  function getProjections(sessionId: string): WorkspaceProjection[] {
    return projectionsBySession.value.get(sessionId) || []
  }

  function getActiveProjection(sessionId: string): WorkspaceProjection | null {
    const list = getProjections(sessionId)
    return list.length ? list[list.length - 1] : null
  }

  function upsertProjection(sessionId: string, projection: WorkspaceProjection): void {
    const current = projectionsBySession.value.get(sessionId) || []
    const index = current.findIndex(p => p.id === projection.id)
    if (index >= 0) {
      current[index] = { ...current[index], ...projection, updatedAt: Date.now() }
    } else {
      current.push(projection)
    }
    // 只保留最近 8 个投影
    const trimmed = current.slice(-8)
    projectionsBySession.value.set(sessionId, [...trimmed])
  }

  function setProjectionLoading(
    sessionId: string,
    runId: string,
    surface: WorkspaceSurface,
    toolName: string,
    toolCallId: string,
  ): void {
    upsertProjection(sessionId, {
      id: `proj_${toolCallId}`,
      sessionId,
      runId,
      surface,
      sourceToolName: toolName,
      sourceToolCallId: toolCallId,
      mode: 'loading',
      payload: {},
      updatedAt: Date.now(),
    })
  }

  function setProjectionReady(
    sessionId: string,
    toolCallId: string,
    payload: Record<string, unknown>,
    mode: WorkspaceProjectionMode = 'readonly',
  ): void {
    const current = projectionsBySession.value.get(sessionId) || []
    const index = current.findIndex(p => p.sourceToolCallId === toolCallId)
    if (index >= 0) {
      current[index] = { ...current[index], payload, mode, updatedAt: Date.now() }
      projectionsBySession.value.set(sessionId, [...current])
    }
  }

  function markProjectionStale(sessionId: string, surface: WorkspaceSurface): void {
    const current = projectionsBySession.value.get(sessionId) || []
    const updated = current.map(p =>
      p.surface === surface ? { ...p, mode: 'stale' as const, updatedAt: Date.now() } : p,
    )
    projectionsBySession.value.set(sessionId, [...updated])
  }

  // ==================== Approval Draft 操作 ====================

  function createApprovalDraft(
    checkpointId: string,
    runId: string,
    toolName: string,
    surface: WorkspaceSurface,
    originalArguments: Record<string, unknown>,
  ): WorkspaceApprovalDraft {
    let formModel: ProjectFormModel | undefined
    let editedArguments: Record<string, unknown> = { ...originalArguments }

    if (toolName === 'create_project') {
      formModel = fromCreateProjectArgs(originalArguments)
      editedArguments = toCreateProjectPayload(formModel)
    }

    const draft: WorkspaceApprovalDraft = {
      id: checkpointId,
      runId,
      checkpointId,
      toolName,
      surface,
      originalArguments: { ...originalArguments },
      editedArguments,
      formModel,
      dirtyFields: [],
      status: 'pending',
      updatedAt: Date.now(),
    }
    approvalDrafts.value.set(checkpointId, draft)
    return draft
  }

  function getApprovalDraft(checkpointId: string): WorkspaceApprovalDraft | undefined {
    return approvalDrafts.value.get(checkpointId)
  }

  function updateApprovalDraftForm(checkpointId: string, formModel: ProjectFormModel): void {
    const draft = approvalDrafts.value.get(checkpointId)
    if (!draft) return
    draft.formModel = { ...formModel }
    draft.editedArguments = toCreateProjectPayload(formModel) as Record<string, unknown>
    draft.dirtyFields = diffProjectArgs(draft.originalArguments, draft.editedArguments as CreateProjectPayload).map(d => d.field)
    draft.updatedAt = Date.now()
    approvalDrafts.value.set(checkpointId, { ...draft })
  }

  function setApprovalDraftStatus(
    checkpointId: string,
    status: WorkspaceApprovalDraft['status'],
  ): void {
    const draft = approvalDrafts.value.get(checkpointId)
    if (!draft) return
    draft.status = status
    draft.updatedAt = Date.now()
    approvalDrafts.value.set(checkpointId, { ...draft })
  }

  function getApprovalDiff(checkpointId: string): Array<{ field: string; before: unknown; after: unknown }> {
    const draft = approvalDrafts.value.get(checkpointId)
    if (!draft) return []
    if (draft.toolName === 'create_project') {
      return diffProjectArgs(draft.originalArguments, draft.editedArguments as unknown as CreateProjectPayload)
    }
    return []
  }

  // ==================== Selected Entities ====================

  function selectEntity(sessionId: string, entity: SelectedEntity): void {
    const current = selectedEntitiesBySession.value.get(sessionId) || []
    const filtered = current.filter(e => !(e.type === entity.type && e.id === entity.id))
    filtered.push(entity)
    selectedEntitiesBySession.value.set(sessionId, filtered.slice(-5))
    recordInteraction(sessionId, {
      type: 'entity.selected',
      surface: entity.type,
      field: entity.id,
      after: entity.name,
    })
  }

  function unselectEntity(sessionId: string, entity: SelectedEntity): void {
    const current = selectedEntitiesBySession.value.get(sessionId) || []
    const filtered = current.filter(e => !(e.type === entity.type && e.id === entity.id))
    selectedEntitiesBySession.value.set(sessionId, filtered)
    recordInteraction(sessionId, {
      type: 'entity.unselected',
      surface: entity.type,
      field: entity.id,
      before: entity.name,
    })
  }

  function getSelectedEntities(sessionId: string): SelectedEntity[] {
    return selectedEntitiesBySession.value.get(sessionId) || []
  }

  // ==================== Interactions ====================

  function recordInteraction(
    sessionId: string,
    event: Omit<WorkspaceInteractionEvent, 'id' | 'sessionId' | 'createdAt'>,
  ): void {
    const current = interactionsBySession.value.get(sessionId) || []
    current.push({
      ...event,
      id: `interaction_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      sessionId,
      createdAt: Date.now(),
    })
    interactionsBySession.value.set(sessionId, current.slice(-50))
  }

  function getRecentInteractions(sessionId: string, limit = 10): WorkspaceInteractionEvent[] {
    const current = interactionsBySession.value.get(sessionId) || []
    return current.slice(-limit)
  }

  // ==================== Context Snapshot ====================

  function getDraftSummaries(sessionId: string): Array<Record<string, unknown>> {
    const summaries: Array<Record<string, unknown>> = []
    for (const draft of approvalDrafts.value.values()) {
      if (draft.status !== 'pending') continue
      summaries.push({
        checkpointId: draft.checkpointId,
        surface: draft.surface,
        toolName: draft.toolName,
        dirtyFields: draft.dirtyFields,
        editedArguments: draft.editedArguments,
        diffSummary: draft.toolName === 'create_project'
          ? getApprovalDiff(draft.checkpointId).map(d => `${d.field}: ${d.before} → ${d.after}`).join(', ')
          : '',
      })
      // 添加类型索引以满足 Record<string, unknown>
    }
    return summaries
  }

  function getPendingApprovalSummaries(sessionId: string): Array<Record<string, unknown>> {
    const summaries: Array<Record<string, unknown>> = []
    for (const draft of approvalDrafts.value.values()) {
      if (draft.status !== 'pending') continue
      summaries.push({
        runId: draft.runId,
        checkpointId: draft.checkpointId,
        toolName: draft.toolName,
        surface: draft.surface,
      })
    }
    return summaries
  }

  function clearSession(sessionId: string): void {
    projectionsBySession.value.delete(sessionId)
    selectedEntitiesBySession.value.delete(sessionId)
    interactionsBySession.value.delete(sessionId)
  }

  return {
    projectionsBySession,
    approvalDrafts,
    selectedEntitiesBySession,
    interactionsBySession,
    // projection
    getProjections,
    getActiveProjection,
    upsertProjection,
    setProjectionLoading,
    setProjectionReady,
    markProjectionStale,
    // approval draft
    createApprovalDraft,
    getApprovalDraft,
    updateApprovalDraftForm,
    setApprovalDraftStatus,
    getApprovalDiff,
    // selected entities
    selectEntity,
    unselectEntity,
    getSelectedEntities,
    // interactions
    recordInteraction,
    getRecentInteractions,
    // context snapshot
    getDraftSummaries,
    getPendingApprovalSummaries,
    clearSession,
  }
})

// ==================== 工具投影注册表 ====================

export interface ToolProjectionConfig {
  surface: WorkspaceSurface
  mode: WorkspaceProjectionMode
  requiresApproval: boolean
  resultToPayload?: (result: unknown) => Record<string, unknown>
}

export const toolProjectionRegistry: Record<string, ToolProjectionConfig> = {
  list_projects: {
    surface: 'project.list',
    mode: 'readonly',
    requiresApproval: false,
    resultToPayload: parseProjectsResult,
  },
  get_project_detail: {
    surface: 'project.detail',
    mode: 'readonly',
    requiresApproval: false,
    resultToPayload: result => ({ project: firstRecord(result, ['project', 'data']) }),
  },
  list_campaigns: {
    surface: 'campaign.list',
    mode: 'readonly',
    requiresApproval: false,
    resultToPayload: result => parseCollectionResult(result, 'campaigns'),
  },
  get_campaign_detail: {
    surface: 'campaign.list',
    mode: 'readonly',
    requiresApproval: false,
    resultToPayload: result => ({ campaigns: compactRecords([firstRecord(result, ['campaign', 'data'])]) }),
  },
  list_materials: {
    surface: 'material.list',
    mode: 'readonly',
    requiresApproval: false,
    resultToPayload: result => parseCollectionResult(result, 'materials'),
  },
  get_material_detail: {
    surface: 'material.list',
    mode: 'readonly',
    requiresApproval: false,
    resultToPayload: result => ({ materials: compactRecords([firstRecord(result, ['material', 'data'])]) }),
  },
  create_project: {
    surface: 'project.create',
    mode: 'review',
    requiresApproval: true,
  },
  delete_project: {
    surface: 'project.delete',
    mode: 'review',
    requiresApproval: true,
  },
}

function parseProjectsResult(result: unknown): Record<string, unknown> {
  // 复用 useHomeAgentSession 已有的 extractProjects 逻辑
  if (!result) return { projects: [] }
  const parsed = parseJsonLikeResult(result)
  if (parsed !== result) return parseProjectsResult(parsed)
  if (typeof result === 'object') {
    const record = result as Record<string, unknown>
    const candidates = [record.projects, record.items, record.list]
    for (const candidate of candidates) {
      if (Array.isArray(candidate)) {
        return { projects: candidate.filter(isRecord) }
      }
    }
    if (typeof record.text === 'string') return parseProjectsResult(record.text)
  }
  if (typeof result !== 'string') return { projects: [] }
  const projects: Record<string, unknown>[] = []
  const chunks = result.split(/\n(?=\d+\.\s+\*\*)/g)
  for (const chunk of chunks) {
    const nameMatch = /\d+\.\s+\*\*(.*?)\*\*/.exec(chunk)
    const idMatch = /ID:\s*([^\n]+)/.exec(chunk)
    if (!nameMatch || !idMatch) continue
    const budgetMatch = /预算:\s*[¥￥]?([\d,\.]+)/.exec(chunk)
    const statusMatch = /状态:\s*([^\n]+)/.exec(chunk)
    const descriptionMatch = /描述:\s*([^\n]+)/.exec(chunk)
    projects.push({
      id: idMatch[1].trim(),
      name: nameMatch[1].trim(),
      total_budget: budgetMatch ? Number(budgetMatch[1].replace(/,/g, '')) : 0,
      spent: 0,
      status: statusMatch ? statusMatch[1].trim() : undefined,
      description: descriptionMatch ? descriptionMatch[1].trim() : undefined,
      game_type: '',
      target_market: '',
      tags: [],
    })
  }
  return { projects: projects.length ? projects : [] }
}

function parseCollectionResult(result: unknown, key: string): Record<string, unknown> {
  if (!result) return { [key]: [] }
  const parsed = parseJsonLikeResult(result)
  if (parsed !== result) return parseCollectionResult(parsed, key)
  if (Array.isArray(result)) return { [key]: result.filter(isRecord) }
  if (typeof result === 'object') {
    const record = result as Record<string, unknown>
    const candidates = [record[key], record.items, record.list, record.data]
    for (const candidate of candidates) {
      if (Array.isArray(candidate)) return { [key]: candidate.filter(isRecord) }
    }
    if (isBusinessRecord(record)) return { [key]: [record] }
    if (typeof record.text === 'string') return parseCollectionResult(record.text, key)
  }
  return { [key]: [] }
}

function firstRecord(result: unknown, keys: string[]): Record<string, unknown> | null {
  if (!result) return null
  const parsed = parseJsonLikeResult(result)
  if (parsed !== result) return firstRecord(parsed, keys)
  if (isRecord(result)) {
    for (const key of keys) {
      const value = result[key]
      if (isRecord(value)) return value
    }
    if (isBusinessRecord(result)) return result
  }
  return null
}

function parseJsonLikeResult(result: unknown): unknown {
  if (typeof result !== 'string') return result
  const trimmed = result.trim()
  if (!trimmed || !['{', '['].includes(trimmed[0])) return result
  try {
    return JSON.parse(trimmed)
  } catch {
    return result
  }
}

function compactRecords(records: Array<Record<string, unknown> | null>): Record<string, unknown>[] {
  return records.filter((item): item is Record<string, unknown> => Boolean(item))
}

function isBusinessRecord(value: Record<string, unknown>): boolean {
  return typeof value.id === 'string' || typeof value.name === 'string'
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

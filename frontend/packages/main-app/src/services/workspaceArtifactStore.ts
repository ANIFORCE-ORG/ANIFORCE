import type { AgentSessionSnapshot } from '@/api/agent'
import type { WorkspaceSurface } from '@/store/workspace'

interface WorkspaceHydrationTarget {
  clearSession(sessionId: string): void
  upsertProjection(sessionId: string, projection: any): void
  createApprovalDraft(
    sessionId: string,
    checkpointId: string,
    runId: string,
    toolName: string,
    surface: WorkspaceSurface,
    originalArguments: Record<string, unknown>,
  ): unknown
  setApprovalDraftStatus(
    checkpointId: string,
    status: 'pending' | 'approved' | 'rejected' | 'executing' | 'completed',
  ): void
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

export function hydrateWorkspaceSnapshot(
  workspace: WorkspaceHydrationTarget,
  sessionId: string,
  snapshot: AgentSessionSnapshot,
): void {
  workspace.clearSession(sessionId)
  let hasDashboardArtifact = false
  for (const artifact of snapshot.artifacts) {
    const payload = record(artifact.payload)
    const surface = String(artifact.surface || payload.surface || '') as WorkspaceSurface
    if (!surface) continue
    if (surface === 'dashboard') hasDashboardArtifact = true
    workspace.upsertProjection(sessionId, {
      id: String(artifact.artifact_id),
      sessionId,
      runId: String(artifact.run_id || ''),
      sourceToolCallId: artifact.source_tool_call_id ? String(artifact.source_tool_call_id) : undefined,
      surface,
      mode: artifact.status === 'failed' ? 'failed' : 'readonly',
      payload,
      updatedAt: Date.parse(String(artifact.updated_at || '')) || Date.now(),
    })
  }

  // Older runs persisted Meta results as tool calls before dashboard artifacts existed.
  // Rebuild the latest dashboard projection so navigation and refresh do not lose it.
  if (!hasDashboardArtifact) {
    const metaToolNames = new Set([
      'list_meta_ad_accounts_with_spend',
      'get_meta_account_performance',
      'get_meta_campaign_performance',
      'get_meta_performance_trend',
    ])
    const toolCall = [...snapshot.tool_calls]
      .reverse()
      .find(item => metaToolNames.has(String(item.tool_name || '')) && String(item.status || '') === 'completed')
    if (toolCall) {
      const result = parsePersistedToolResult(toolCall.result_json ?? toolCall.result)
      const overview = findDashboardOverview(result)
      if (overview) {
        workspace.upsertProjection(sessionId, {
          id: `proj_restored_${String(toolCall.tool_call_id || toolCall.run_id || Date.now())}`,
          sessionId,
          runId: String(toolCall.run_id || ''),
          sourceToolName: String(toolCall.tool_name),
          sourceToolCallId: toolCall.tool_call_id ? String(toolCall.tool_call_id) : undefined,
          surface: 'dashboard',
          mode: 'readonly',
          payload: { overview },
          updatedAt: Date.parse(String(toolCall.completed_at || '')) || Date.now(),
        })
      }
    }
  }
  const approval = snapshot.pending_approval || snapshot.approvals[snapshot.approvals.length - 1]
  if (!approval) return

  const checkpointId = String(approval.checkpoint_ref || approval.approval_id || '')
  const runId = String(approval.run_id || '')
  const toolName = String(approval.tool_name || '')
  const args = record(approval.edited_arguments || approval.original_arguments)
  const status = approvalDraftStatus(String(approval.status || ''), String(approval.decision || ''))
  workspace.createApprovalDraft(sessionId, checkpointId, runId, toolName, 'approval.review', args)
  workspace.setApprovalDraftStatus(checkpointId, status)
  workspace.upsertProjection(sessionId, {
    id: `proj_approval_${checkpointId}`,
    sessionId,
    runId,
    surface: 'approval.review',
    sourceToolName: toolName,
    mode: status === 'pending' ? 'review' : status === 'rejected' ? 'failed' : status === 'completed' ? 'completed' : 'executing',
    payload: { originalArguments: record(approval.original_arguments), editedArguments: record(approval.edited_arguments) },
    approval: {
      runId,
      checkpointId,
      decisionStatus: status === 'rejected' ? 'rejected' : status === 'pending' ? 'pending' : 'approved',
    },
    updatedAt: Date.parse(String(approval.resolved_at || approval.created_at || '')) || Date.now(),
  })
}

function parsePersistedToolResult(value: unknown): unknown {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return value
    try {
      return parsePersistedToolResult(JSON.parse(trimmed))
    } catch {
      return value
    }
  }
  if (Array.isArray(value)) return value.map(parsePersistedToolResult)
  if (!value || typeof value !== 'object') return value
  const object = value as Record<string, unknown>
  for (const key of ['text', 'output', 'content', 'result']) {
    if (object[key] !== undefined) return parsePersistedToolResult(object[key])
  }
  return value
}

function findDashboardOverview(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const object = value as Record<string, unknown>
  if (object.window && object.kpis) return object
  for (const key of ['data', 'output', 'content', 'result']) {
    const nested = findDashboardOverview(object[key])
    if (nested) return nested
  }
  return null
}

function approvalDraftStatus(
  status: string,
  decision: string,
): 'pending' | 'rejected' | 'executing' | 'completed' {
  if (status === 'rejected' || decision === 'reject') return 'rejected'
  if (status === 'resolved' || status === 'completed') return 'completed'
  if (status === 'resuming') return 'executing'
  return 'pending'
}

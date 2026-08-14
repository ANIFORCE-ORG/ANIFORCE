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
  for (const artifact of snapshot.artifacts) {
    const payload = record(artifact.payload)
    const surface = String(artifact.surface || payload.surface || '') as WorkspaceSurface
    if (!surface) continue
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

function approvalDraftStatus(
  status: string,
  decision: string,
): 'pending' | 'rejected' | 'executing' | 'completed' {
  if (status === 'rejected' || decision === 'reject') return 'rejected'
  if (status === 'resolved' || status === 'completed') return 'completed'
  if (status === 'resuming') return 'executing'
  return 'pending'
}

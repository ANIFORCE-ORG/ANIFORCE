import type { AgentSessionSnapshot } from '@/api/agent'
import type { WorkspaceSurface } from '@/store/workspace'

interface WorkspaceHydrationTarget {
  clearSession(sessionId: string): void
  upsertProjection(sessionId: string, projection: any): void
  createApprovalDraft(
    checkpointId: string,
    runId: string,
    toolName: string,
    surface: WorkspaceSurface,
    originalArguments: Record<string, unknown>,
  ): unknown
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
  const approval = snapshot.pending_approval
  if (approval) {
    workspace.createApprovalDraft(
      String(approval.checkpoint_ref || ''),
      String(approval.run_id || ''),
      String(approval.tool_name || ''),
      'approval.review',
      record(approval.edited_arguments || approval.original_arguments),
    )
  }
}

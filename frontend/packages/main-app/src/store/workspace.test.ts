import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useWorkspaceStore } from './workspace'

describe('workspace approval session isolation', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('exposes pending approval context only to its owning session', () => {
    const store = useWorkspaceStore()

    store.createApprovalDraft('session-a', 'checkpoint-a', 'run-a', 'create_project', 'approval.review', { name: 'Project A' })

    expect(store.getDraftSummaries('session-a')).toHaveLength(1)
    expect(store.getPendingApprovalSummaries('session-a')).toHaveLength(1)
    expect(store.getDraftSummaries('session-b')).toEqual([])
    expect(store.getPendingApprovalSummaries('session-b')).toEqual([])
  })

  it('removes approval drafts when their owning session is cleared', () => {
    const store = useWorkspaceStore()

    store.createApprovalDraft('session-a', 'checkpoint-a', 'run-a', 'create_project', 'approval.review', { name: 'Project A' })
    store.createApprovalDraft('session-b', 'checkpoint-b', 'run-b', 'create_project', 'approval.review', { name: 'Project B' })

    store.clearSession('session-a')

    expect(store.getApprovalDraft('checkpoint-a')).toBeUndefined()
    expect(store.getPendingApprovalSummaries('session-b')).toHaveLength(1)
  })
})

import type { AgentSessionTaskState } from '@/api/agent'

export interface AgentTaskPresentation {
  id: string
  session_id: string
  title: string
  task_type: string
  status: string
  phase: string
  summary: string
  task_definition: {
    label: string
    phases: Array<{ key: string; label: string }>
  }
}

const skillLabels: Record<string, string> = {
  campaign_diagnosis: '广告计划诊断',
  project_review: '项目效果复盘',
  safe_business_mutation: '业务变更执行',
}

export function buildAgentTaskPresentation(
  taskState: AgentSessionTaskState | null | undefined,
  pendingApproval: unknown,
  sessionId: string,
): AgentTaskPresentation | null {
  const active = taskState?.active_skill
  if (!active) return null
  const status = active.status === 'collecting_inputs'
    ? 'waiting_user_input'
    : active.status === 'executing'
      ? (pendingApproval ? 'waiting_approval' : 'applying')
      : active.status === 'cancelled'
        ? 'canceled'
        : active.status === 'failed'
          ? 'failed'
          : active.status === 'completed'
            ? 'completed'
            : 'running'
  const phase = active.status === 'collecting_inputs'
    ? 'scope'
    : active.status === 'executing'
      ? (pendingApproval ? 'approval' : 'apply')
      : active.status === 'completed'
        ? 'verify'
        : active.status === 'failed' || active.status === 'cancelled'
          ? 'apply'
          : 'evidence'
  const missing = active.missing_slots || []
  const summary = active.pending_question
    || (missing.length ? `还需要补充：${missing.join('、')}` : '')
    || (active.status === 'executing' ? '业务操作已进入确认或执行阶段。' : '')
    || (active.status === 'completed' ? '任务已执行完成，并已记录验证状态。' : '')
    || taskState?.last_conclusion
    || '正在根据当前业务上下文推进任务。'
  const title = skillLabels[active.name] || active.name
  return {
    id: `${active.name}:${active.version}`,
    session_id: sessionId,
    title,
    task_type: active.name,
    status,
    phase,
    summary,
    task_definition: {
      label: `${title} · v${active.version}`,
      phases: [
        { key: 'scope', label: '确认目标与对象' },
        { key: 'evidence', label: '查询业务证据' },
        { key: 'analysis', label: '形成判断' },
        { key: 'approval', label: '等待业务确认' },
        { key: 'apply', label: '执行变更' },
        { key: 'verify', label: '验证实际结果' },
      ],
    },
  }
}

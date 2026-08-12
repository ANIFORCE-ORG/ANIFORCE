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

export type TaskPresentationStatus = 'created' | 'running' | 'waiting_user_input' | 'waiting_approval' | 'applying' | 'completed' | 'failed' | 'canceled'

export const taskStatusPresentation: Record<TaskPresentationStatus, { label: string; icon: string }> = {
  created: { label: '已创建', icon: 'radio_button_unchecked' },
  running: { label: '进行中', icon: 'progress_activity' },
  waiting_user_input: { label: '等待补充', icon: 'edit_note' },
  waiting_approval: { label: '等待确认', icon: 'approval_delegation' },
  applying: { label: '执行中', icon: 'bolt' },
  completed: { label: '已完成', icon: 'check_circle' },
  failed: { label: '失败', icon: 'error' },
  canceled: { label: '已取消', icon: 'do_not_disturb_on' },
}

export function normalizeTaskPanelStatus(status: string): TaskPresentationStatus {
  if (status in taskStatusPresentation) return status as TaskPresentationStatus
  return 'running'
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
  const summary = (active.status === 'completed' ? '任务已执行完成，并已记录验证状态。' : '')
    || (active.status === 'cancelled' ? '任务已取消，未继续执行后续操作。' : '')
    || active.pending_question
    || (missing.length ? `还需要补充：${missing.join('、')}` : '')
    || (active.status === 'executing' ? '业务操作已进入确认或执行阶段。' : '')
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

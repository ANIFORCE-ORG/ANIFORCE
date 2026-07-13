import { describe, expect, it } from 'vitest'
import { buildAgentTaskPresentation } from './taskPresentation'


describe('business task presentation', () => {
  it('shows a persisted clarification as waiting for user input', () => {
    const task = buildAgentTaskPresentation({
      active_skill: {
        name: 'campaign_diagnosis',
        version: '1.0',
        status: 'collecting_inputs',
        slots: { time_range_hours: 168 },
        missing_slots: ['campaign_id'],
        pending_question: '请选择要诊断的广告计划。',
      },
    }, null, 'session_1')

    expect(task?.title).toBe('广告计划诊断')
    expect(task?.status).toBe('waiting_user_input')
    expect(task?.phase).toBe('scope')
    expect(task?.summary).toBe('请选择要诊断的广告计划。')
  })

  it('distinguishes approval from applying and verification', () => {
    const executing = {
      active_skill: {
        name: 'safe_business_mutation',
        version: '1.0',
        status: 'executing' as const,
      },
    }
    expect(buildAgentTaskPresentation(executing, { id: 'approval_1' }, 's1')?.status).toBe('waiting_approval')
    expect(buildAgentTaskPresentation(executing, null, 's1')?.status).toBe('applying')

    const completed = buildAgentTaskPresentation({
      active_skill: {
        name: 'safe_business_mutation',
        version: '1.0',
        status: 'completed',
        missing_slots: ['operation'],
        pending_question: '旧问题',
      },
    }, null, 's1')
    expect(completed?.status).toBe('completed')
    expect(completed?.phase).toBe('verify')
    expect(completed?.summary).toContain('已执行完成')
    expect(completed?.task_definition.phases.at(-1)?.label).toBe('验证实际结果')
  })

  it('returns no task when the backend has no structured task state', () => {
    expect(buildAgentTaskPresentation({}, null, 's1')).toBeNull()
  })
})

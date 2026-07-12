import { describe, expect, it } from 'vitest'
import { parseAgentSdkEvent } from './parser'


describe('parseAgentSdkEvent', () => {
  it('classifies text and reasoning deltas', () => {
    expect(parseAgentSdkEvent({
      type: 'raw_response_event',
      data: { type: 'response.output_text.delta', delta: 'hello' },
    } as any)).toEqual({ kind: 'text', delta: 'hello' })
    expect(parseAgentSdkEvent({
      type: 'raw_response_event',
      data: { type: 'response.reasoning_summary_text.delta', delta: 'thinking' },
    } as any)).toEqual({ kind: 'reasoning', delta: 'thinking' })
  })

  it('normalizes SDK tool call arguments', () => {
    expect(parseAgentSdkEvent({
      type: 'run_item_stream_event',
      name: 'tool_called',
      item: { raw_item: { call_id: 'call_1', name: 'list_projects', arguments: '{"limit":5}' } },
    } as any)).toEqual({
      kind: 'tool_called',
      id: 'call_1',
      name: 'list_projects',
      arguments: { limit: 5 },
    })
  })

  it('preserves the tool call id on output', () => {
    expect(parseAgentSdkEvent({
      type: 'run_item_stream_event',
      name: 'tool_output',
      item: { call_id: 'call_1', output: { projects: [] } },
    } as any)).toEqual({ kind: 'tool_output', id: 'call_1', output: { projects: [] } })
  })

  it('ignores unrelated SDK events', () => {
    expect(parseAgentSdkEvent({ type: 'agent_updated_stream_event' } as any)).toEqual({ kind: 'ignored' })
  })
})

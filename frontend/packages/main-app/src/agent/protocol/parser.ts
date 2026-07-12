import type { AgentSdkStreamEvent } from '@/api/agent'
import type { ParsedAgentEvent } from './events'

function record(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined
}

export function parseAgentSdkEvent(event: AgentSdkStreamEvent): ParsedAgentEvent {
  if (event.type === 'raw_response_event') {
    const data = record(event.data)
    const type = String(data?.type || '')
    const delta = typeof data?.delta === 'string' ? data.delta : ''
    if (type === 'response.output_text.delta' && delta) return { kind: 'text', delta }
    if ((type === 'response.reasoning_text.delta' || type === 'response.reasoning_summary_text.delta') && delta) {
      return { kind: 'reasoning', delta }
    }
    return { kind: 'ignored' }
  }
  if (event.type !== 'run_item_stream_event') return { kind: 'ignored' }
  const item = record(event.item)
  const raw = record(item?.raw_item)
  if (event.name === 'tool_called') {
    const name = String(item?.tool_name || raw?.name || item?.name || 'tool')
    const id = String(item?.call_id || raw?.call_id || raw?.id || `${name}_${Date.now()}`)
    let args: unknown = raw?.arguments || item?.arguments || {}
    if (typeof args === 'string') {
      try { args = args.trim() ? JSON.parse(args) : {} } catch { args = { raw: args } }
    }
    return { kind: 'tool_called', id, name, arguments: record(args) }
  }
  if (event.name === 'tool_output') {
    const id = String(item?.call_id || raw?.call_id || raw?.id || '')
    const output = item && 'output' in item ? item.output : raw && 'output' in raw ? raw.output : raw?.content
    return { kind: 'tool_output', id, output }
  }
  return { kind: 'ignored' }
}

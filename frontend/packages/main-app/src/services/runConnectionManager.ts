import { streamAgentRunEvents, type AgentStreamEvent } from '@/api/agent'

const TERMINAL_EVENTS = new Set(['runtime.completed', 'runtime.error', 'runtime.aborted', 'runtime.requires_action', 'error'])

export interface RunConnectionResult {
  lastSequence: number
  terminalEvent?: AgentStreamEvent
}

export async function connectPersistedRun(
  runId: string,
  afterSequence: number,
  signal?: AbortSignal,
  onEvent?: (event: AgentStreamEvent) => void | Promise<void>,
): Promise<RunConnectionResult> {
  let lastSequence = Math.max(0, afterSequence)
  let terminalEvent: AgentStreamEvent | undefined
  for await (const event of streamAgentRunEvents(runId, lastSequence, signal)) {
    const sequence = Number(event.data.sequence || 0)
    if (sequence && sequence <= lastSequence) continue
    if (sequence) lastSequence = sequence
    await onEvent?.(event)
    if (TERMINAL_EVENTS.has(event.event)) terminalEvent = event
  }
  return { lastSequence, terminalEvent }
}

export interface AgentTextDelta {
  kind: 'text' | 'reasoning'
  delta: string
}

export interface AgentToolCalled {
  kind: 'tool_called'
  id: string
  name: string
  arguments?: Record<string, unknown>
}

export interface AgentToolOutput {
  kind: 'tool_output'
  id: string
  output: unknown
}

export type ParsedAgentEvent = AgentTextDelta | AgentToolCalled | AgentToolOutput | { kind: 'ignored' }

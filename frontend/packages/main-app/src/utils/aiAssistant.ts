import { runAI, type AIRunResponse, type AIScenario } from '@/api/ai'

export interface AssistantMessage {
  role: string
  author: string
  time: string
  content: string
}

export function createUserMessage(content: string): AssistantMessage {
  return {
    role: 'user',
    author: '我',
    time: '刚刚',
    content,
  }
}

export function createAssistantMessage(content: string): AssistantMessage {
  return {
    role: 'assistant',
    author: 'ANIFORCE助手',
    time: '刚刚',
    content,
  }
}

export function formatAIResponse(response: AIRunResponse): string {
  const output = response.output || {}
  const lines: string[] = []

  if (output.summary) lines.push(output.summary)
  if (Array.isArray(output.findings) && output.findings.length > 0) {
    lines.push('发现：')
    output.findings.forEach((item: any) => {
      lines.push(`- ${item.title || item.summary || JSON.stringify(item)}`)
    })
  }
  if (Array.isArray(output.recommendations) && output.recommendations.length > 0) {
    lines.push('建议：')
    output.recommendations.forEach((item: any) => {
      lines.push(`- ${item.summary || item.action_type || JSON.stringify(item)}`)
    })
  }
  if (Array.isArray(output.candidates) && output.candidates.length > 0) {
    lines.push('候选：')
    output.candidates.slice(0, 3).forEach((item: any, index: number) => {
      lines.push(`${index + 1}. ${item.title || '候选'}：${item.description || ''}`)
    })
  }
  if (lines.length === 0) lines.push(JSON.stringify(output, null, 2))

  lines.push('')
  lines.push(`Token: ${response.usage.total_tokens} · ${response.usage.provider}/${response.usage.model}`)
  return lines.join('\n')
}

export async function sendAIChatMessage(params: {
  scenario: AIScenario
  message: string
  projectId?: string
  campaignId?: string
  materialId?: string
  context?: Record<string, any>
}): Promise<AssistantMessage> {
  const response = await runAI({
    scenario: params.scenario,
    project_id: params.projectId,
    campaign_id: params.campaignId,
    material_id: params.materialId,
    messages: [{ role: 'user', content: params.message }],
    context: params.context || {},
  })
  return createAssistantMessage(formatAIResponse(response))
}


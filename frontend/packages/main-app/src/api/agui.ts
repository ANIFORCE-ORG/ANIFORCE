/**
 * AG-UI 协议 SSE 客户端
 * 封装 /api/v1/copilotkit 端点，返回标准 SSE 事件流
 */

export interface AgUiMessage {
  role: 'user' | 'assistant' | 'activity' | 'tool'
  content: string | Array<{ type: string; text?: string; [key: string]: unknown }>
  id?: string
  messageId?: string
  toolCallId?: string
  activityType?: string
  [key: string]: unknown
}

export interface AgUiRequest {
  threadId: string
  messages: AgUiMessage[]
  state?: Record<string, unknown>
  forwardedProps?: Record<string, unknown>
}

export interface AgUiSseEvent {
  event: string
  data: Record<string, unknown>
}

/**
 * 调用 AG-UI 协议的 SSE 端点
 * @param request AG-UI 请求（threadId, messages, state）
 * @returns 异步迭代器，逐个返回 SSE 事件
 */
export async function* streamAgUiMessages(request: AgUiRequest): AsyncGenerator<AgUiSseEvent, void, undefined> {
  console.log('[AG-UI SSE] 准备调用 /api/v1/copilotkit', request)
  const token = localStorage.getItem('animagus_token')
  if (!token) throw new Error('未登录，无法调用 Agent')

  const response = await fetch('/api/v1/copilotkit', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`AG-UI 请求失败 (${response.status}): ${text}`)
  }

  if (!response.body) {
    throw new Error('AG-UI 响应没有 body stream')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      let currentEvent = 'message'
      let currentData = ''

      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEvent = line.substring(6).trim()
        } else if (line.startsWith('data:')) {
          currentData = line.substring(5).trim()
        } else if (line === '' && currentData) {
          // 事件结束，解析并 yield
          try {
            const data = JSON.parse(currentData)
            yield { event: currentEvent, data }
          } catch (err) {
            console.warn('[AG-UI] 无法解析 SSE data:', currentData, err)
          }
          currentEvent = 'message'
          currentData = ''
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

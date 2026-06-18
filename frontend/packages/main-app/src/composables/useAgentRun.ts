/**
 * useAgentRun — 前端直连 ANIFORCE Agent 服务的核心 composable
 *
 * 职责：
 * 1. 会话管理（创建/列表/切换/改名/归档） → /api/agent/sessions
 * 2. 发起 Agent 执行 → POST /api/agent/runs（SSE 业务事件流）
 * 3. 解析 SSE 事件（TaskCreated/Progress/OutputDelta/OutputProduced/Completed）
 * 4. HITL 确认交互 → POST /api/agent/hitl/{id}/respond
 * 5. 累计 stat chips（input/output tokens、cost、tok/s）
 *
 * 替代旧 useAgUiAgent + useHomeAgentSession（两个旧协议废掉）
 */

import { ref, computed, reactive } from 'vue'

/* ------------------------------------------------------------------ *
 * 配置
 * ------------------------------------------------------------------ */
const API_BASE = 'http://localhost:8020/api/agent'

/* ------------------------------------------------------------------ *
 * 类型
 * ------------------------------------------------------------------ */
export interface Session {
  session_id: string
  user_id: string
  title: string
  status: string            // active / archived
  last_task_id: string | null
  last_active_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface AgentMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  /** 折叠的 trace 信息 */
  trace?: { steps: number; approvals: number; tools: number; detail?: TraceStep[] }
  /** HITL 徽标 */
  hitl?: { title: string; detail: string; approved: boolean }
  /** 该消息所属 task_id */
  taskId?: string
}

export interface TraceStep {
  id: string
  label: string
  kind: 'hitl' | 'backend' | 'server'
  tool: string
}

export interface RunStats {
  inputTokens: number
  outputTokens: number
  cost: number
  tokPerSec: number
  turns: number
}

export interface HitlRequest {
  id: string
  title: string
  detail: string
  action: string
  sessionId: string
}

/* ------------------------------------------------------------------ *
 * SSE 事件类型（对齐 BusinessEventAdapter）
 * ------------------------------------------------------------------ */
type SseEvent =
  | 'TaskCreated'
  | 'TaskStatusChanged'
  | 'TaskProgressUpdated'
  | 'TaskOutputDelta'
  | 'TaskOutputProduced'
  | 'TaskCompleted'

/* ------------------------------------------------------------------ *
 * composable 返回值
 * ------------------------------------------------------------------ */
export function useAgentRun() {
  // ---- 会话 ----
  const sessions = ref<Session[]>([])
  const activeSessionId = ref<string | null>(null)
  const activeSession = computed(() => sessions.value.find(s => s.session_id === activeSessionId.value))

  // ---- 消息流 ----
  const messages = ref<AgentMessage[]>([])

  // ---- 运行状态 ----
  const running = ref(false)
  const phaseLabel = ref<string>('')          // 当前 phase 文案
  const stats = reactive<RunStats>({ inputTokens: 0, outputTokens: 0, cost: 0, tokPerSec: 0, turns: 0 })

  // ---- HITL ----
  const hitlQueue = ref<HitlRequest[]>([])

  // ---- 错误 ----
  const error = ref<string | null>(null)

  // ---- 折叠 trace 状态 ----
  const expandedTraces = ref<Set<string>>(new Set())
  function toggleTrace(msgId: string) {
    if (expandedTraces.value.has(msgId)) expandedTraces.value.delete(msgId)
    else expandedTraces.value.add(msgId)
  }

  /* ------------------------------------------------------------------ *
   * JWT 获取（复用 auth store）
   * ------------------------------------------------------------------ */
  function getAuthHeaders(): Record<string, string> {
    // 从 localStorage 读 token（和 auth store 同源）
    const token = localStorage.getItem('animagus_token')
    return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
  }

  /* ------------------------------------------------------------------ *
   * 会话 CRUD
   * ------------------------------------------------------------------ */
  async function fetchSessions() {
    try {
      const res = await fetch(`${API_BASE}/sessions?status=active`, { headers: getAuthHeaders() })
      if (!res.ok) throw new Error(`fetchSessions: ${res.status}`)
      const data = await res.json()
      sessions.value = data.sessions || []
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function createSession(title?: string) {
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(title ? { title } : undefined),
      })
      if (!res.ok) throw new Error(`createSession: ${res.status}`)
      const session: Session = await res.json()
      sessions.value.unshift(session)
      activeSessionId.value = session.session_id
      messages.value = []
      resetStats()
      return session
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  async function renameSession(sessionId: string, title: string) {
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ title }),
      })
      if (!res.ok) throw new Error(`renameSession: ${res.status}`)
      const updated: Session = await res.json()
      const idx = sessions.value.findIndex(s => s.session_id === sessionId)
      if (idx >= 0) sessions.value[idx] = updated
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function archiveSession(sessionId: string) {
    try {
      await fetch(`${API_BASE}/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      })
      sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
      if (activeSessionId.value === sessionId) {
        activeSessionId.value = sessions.value[0]?.session_id || null
        messages.value = []
      }
    } catch (e: any) {
      error.value = e.message
    }
  }

  function selectSession(sessionId: string) {
    activeSessionId.value = sessionId
    // 切换会话时清空消息（后续可从 /sessions/{id}/tasks 加载历史）
    messages.value = []
    resetStats()
  }

  /* ------------------------------------------------------------------ *
   * 发起 Agent 执行（SSE 流）—— 修复版：闭包状态
   * ------------------------------------------------------------------ */
  async function send(prompt: string, _images?: Array<{ type: 'image'; data: string; mimeType: string }>) {
    // 立即显示 loading 状态（完全同步，不 await）
    running.value = true
    error.value = null
    phaseLabel.value = 'Thinking…'

    // 先确保 session 存在（createSession 会清空 messages）
    if (!activeSessionId.value) {
      await createSession()
    }
    if (!activeSessionId.value) {
      running.value = false
      return
    }

    // 再 push 用户消息（避免被 createSession 清空）
    messages.value.push({
      id: `user_${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
    })

    // 流式累积状态（闭包变量，handleSseEvent 直接修改）
    let currentTaskId: string | null = null
    const traceSteps: TraceStep[] = []
    let hitlTitle = ''
    let hitlDetail = ''
    let assistantText = ''
    const assistantMsgId = `asst_${Date.now()}`
    let charCount = 0
    const startTime = Date.now()

    const t0 = performance.now()
    console.log(`[T+0ms] send() called`)

    try {
      const res = await fetch(`${API_BASE}/runs`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          prompt,
          session_id: activeSessionId.value,
          task_type: 'conversation',
          title: prompt.slice(0, 50),
        }),
      })

      console.log(`[T+${Math.round(performance.now() - t0)}ms] fetch headers received, status=${res.status}`)

      if (!res.ok) {
        const errText = await res.text()
        throw new Error(`Agent run failed: ${res.status} ${errText}`)
      }

      // SSE 流处理
      const reader = res.body?.getReader()
      if (!reader) throw new Error('No SSE stream')

      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent: string | null = null
      let firstChunkSeen = false
      let firstDeltaSeen = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        if (!firstChunkSeen) {
          firstChunkSeen = true
          console.log(`[T+${Math.round(performance.now() - t0)}ms] first SSE chunk arrived (${value?.byteLength} bytes)`)
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ') && currentEvent) {
            const payload = JSON.parse(line.slice(6))
            if (currentEvent === 'TaskOutputDelta' && !firstDeltaSeen) {
              firstDeltaSeen = true
              console.log(`[T+${Math.round(performance.now() - t0)}ms] first TaskOutputDelta received: "${payload.delta}"`)
            }
            handleSseEvent(currentEvent as SseEvent, payload)
            if (currentEvent === 'TaskCreated') currentTaskId = payload.taskId
            if (currentEvent === 'TaskCompleted') {
              console.log(`[T+${Math.round(performance.now() - t0)}ms] TaskCompleted`)
              running.value = false
              phaseLabel.value = ''
            }
            currentEvent = null
          }
        }
      }
    } catch (e: any) {
      error.value = e.message
      running.value = false
      phaseLabel.value = ''
    }

    // 内部 SSE 事件处理（闭包访问外层状态）
    function handleSseEvent(event: SseEvent, payload: any) {
      // 诊断日志：记录每个事件到达时间
      console.log(`[SSE] ${event}`, payload.delta || payload.phase || payload.status || '')

      const telemetry = payload.telemetry || {}

      // 更新 stats
      if (telemetry.inputTokens) stats.inputTokens += telemetry.inputTokens
      if (telemetry.outputTokens) stats.outputTokens += telemetry.outputTokens
      if (telemetry.costUsd) stats.cost += telemetry.costUsd
      if (telemetry.charPerSecond) stats.tokPerSec = telemetry.charPerSecond

      switch (event) {
        case 'TaskCreated':
          // 无动作——task_id 已在外层保存
          break

        case 'TaskStatusChanged':
          if (payload.status === 'running') {
            phaseLabel.value = 'Running…'
          } else if (payload.status === 'completed') {
            phaseLabel.value = ''
          } else if (payload.status === 'error') {
            phaseLabel.value = 'Error'
            error.value = payload.error || 'Unknown error'
          }
          break

        case 'TaskProgressUpdated':
          const phase = payload.phase || ''
          if (phase === 'thinking') phaseLabel.value = 'Thinking…'
          else if (phase === 'running_tools') {
            const toolNames = payload.tools?.map((t: any) => t.name) || []
            phaseLabel.value = toolNames.length
              ? `Running ${toolNames[0]}${toolNames.length > 1 ? ` +${toolNames.length - 1}` : ''}…`
              : 'Running tool…'
          } else if (phase === 'waiting_model') phaseLabel.value = 'Waiting for model…'

          // trace step 累积
          if (payload.toolUse) {
            const kind = payload.toolUse.name?.includes('confirm_action') || payload.toolUse.name?.includes('hitl')
              ? 'hitl' : 'backend'
            traceSteps.push({
              id: payload.toolUse.id || `step_${traceSteps.length}`,
              label: payload.toolUse.name || 'unknown',
              kind,
              tool: payload.toolUse.name || '',
            })
          }
          if (payload.hitlRequest) {
            hitlTitle = payload.hitlRequest.title || ''
            hitlDetail = payload.hitlRequest.detail || ''
            hitlQueue.value.push({
              id: payload.hitlRequest.id,
              title: hitlTitle,
              detail: hitlDetail,
              action: payload.hitlRequest.action || '',
              sessionId: activeSessionId.value || '',
            })
          }
          break

        case 'TaskOutputDelta':
          // 文本增量
          assistantText += payload.delta || ''
          charCount += (payload.delta?.length || 0)

          // 计算 tok/s（基于 char/s 近似）
          const elapsed = (Date.now() - startTime) / 1000
          if (elapsed > 0.5) stats.tokPerSec = Math.round(charCount / elapsed)

          // 更新或追加 assistant 消息
          const existingMsg = messages.value.find(m => m.id === assistantMsgId)
          if (existingMsg) {
            existingMsg.content = assistantText
          } else {
            messages.value.push({
              id: assistantMsgId,
              role: 'assistant',
              content: assistantText,
              timestamp: new Date().toISOString(),
              taskId: currentTaskId || undefined,
              trace: traceSteps.length > 0 ? {
                steps: traceSteps.length,
                approvals: traceSteps.filter(s => s.kind === 'hitl').length,
                tools: traceSteps.filter(s => s.kind === 'backend').length,
                detail: traceSteps,
              } : undefined,
              hitl: hitlTitle ? { title: hitlTitle, detail: hitlDetail, approved: false } : undefined,
            })
          }
          break

        case 'TaskOutputProduced':
          // 最终文本（完整版）
          const finalText = payload.text || assistantText
          const finalMsg = messages.value.find(m => m.id === assistantMsgId)
          if (finalMsg) {
            finalMsg.content = finalText
          } else {
            messages.value.push({
              id: assistantMsgId,
              role: 'assistant',
              content: finalText,
              timestamp: new Date().toISOString(),
              taskId: currentTaskId || undefined,
              trace: traceSteps.length > 0 ? {
                steps: traceSteps.length,
                approvals: traceSteps.filter(s => s.kind === 'hitl').length,
                tools: traceSteps.filter(s => s.kind === 'backend').length,
                detail: traceSteps,
              } : undefined,
              hitl: hitlTitle ? { title: hitlTitle, detail: hitlDetail, approved: false } : undefined,
            })
          }
          break

        case 'TaskCompleted':
          running.value = false
          phaseLabel.value = ''
          // 最终统计
          const summary = payload.summary || {}
          if (summary.cost) stats.cost = summary.cost
          if (summary.numTurns) stats.turns += summary.numTurns
          break
      }
    }
  }

  /* ------------------------------------------------------------------ *
   * HITL 响应
   * ------------------------------------------------------------------ */
  async function respondHitl(hitlId: string, approved: boolean, reason?: string) {
    try {
      const res = await fetch(`${API_BASE}/hitl/${hitlId}/respond`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ approved, reason }),
      })
      if (!res.ok) throw new Error(`HITL respond: ${res.status}`)

      // 从队列移除
      hitlQueue.value = hitlQueue.value.filter(h => h.id !== hitlId)

      // 标记消息里的 HITL 为已批准
      const msg = messages.value.find(m => m.hitl && !m.hitl.approved)
      if (msg && msg.hitl) msg.hitl.approved = true
    } catch (e: any) {
      error.value = e.message
    }
  }

  /* ------------------------------------------------------------------ *
   * 辅助
   * ------------------------------------------------------------------ */
  function resetStats() {
    stats.inputTokens = 0
    stats.outputTokens = 0
    stats.cost = 0
    stats.tokPerSec = 0
    stats.turns = 0
  }

  function fmtTokens(n: number): string {
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
    return String(n)
  }

  /* ------------------------------------------------------------------ *
   * 极简 markdown 渲染（和原型版一致，后续可升级）
   * ------------------------------------------------------------------ */
  function renderMarkdown(src: string): string {
    const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    const lines = esc(src).split('\n')
    let html = ''
    for (const line of lines) {
      if (line.startsWith('## ')) { html += `<h3 class="text-[13px] font-bold mt-[4px] mb-[2px]">${line.slice(3)}</h3>`; continue }
      let l = line
        .replace(/`([^`]+)`/g, '<code class="rounded bg-slate-100 px-[4px] font-mono text-[11px]">$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold">$1</strong>')
      if (l.startsWith('> ')) { html += `<p class="text-[10px] italic text-slate-400">${l.slice(2)}</p>`; continue }
      if (l.trim() === '') { html += '<div class="h-[4px]"></div>'; continue }
      html += `<p>${l}</p>`
    }
    return html
  }

  return {
    // 会话
    sessions,
    activeSessionId,
    activeSession,
    fetchSessions,
    createSession,
    renameSession,
    archiveSession,
    selectSession,

    // 消息
    messages,

    // 运行
    running,
    phaseLabel,
    stats,
    error,
    send,
    fmtTokens,
    renderMarkdown,

    // HITL
    hitlQueue,
    respondHitl,

    // trace
    expandedTraces,
    toggleTrace,

    // reset
    resetStats,
  }
}

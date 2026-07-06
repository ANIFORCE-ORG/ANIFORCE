/**
 * Agent UI 类型定义
 *
 * 流式模型事件使用 Agents SDK 原生 event type；这里保留 UI 组件需要的数据类型。
 */

// ============================================================================
// Agent stream event types
// ============================================================================

export enum AGUIEventType {
  STATE_SNAPSHOT = 'STATE_SNAPSHOT',
  RUNTIME_STARTED = 'runtime.started',
  RUNTIME_COMPLETED = 'runtime.completed',
  RUNTIME_ERROR = 'runtime.error',
  RUNTIME_ABORTED = 'runtime.aborted',
}

// ============================================================================
// 数据模型
// ============================================================================

/**
 * Todo 状态
 */
export enum TodoStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  SKIPPED = 'skipped',
}

/**
 * Todo 项
 */
export interface TodoItem {
  id: string
  title: string
  description?: string
  status: TodoStatus
  result?: string
  error?: string
  dependencies?: string[]
}

/**
 * 执行计划
 */
export interface ExecutionPlan {
  plan_id: string
  task_id: string
  todos: TodoItem[]
  current_todo_index?: number
}

/**
 * 工具调用
 */
export interface ToolCall {
  tool_name: string
  tool_args?: Record<string, any>
  tool_result?: any
  started_at?: string
  completed_at?: string
}

/**
 * HITL 确认请求
 */
export interface HITLConfirmationRequest {
  request_id: string
  operation: string
  description: string
  risk_level: 'low' | 'medium' | 'high'
  details?: Record<string, any>
}

/**
 * HITL 确认响应
 */
export interface HITLConfirmationResponse {
  request_id: string
  confirmed: boolean
  user_feedback?: string
}

/**
 * 共享状态
 */
export interface SharedState {
  current_project_id?: string
  current_campaign_id?: string
  user_preferences?: Record<string, any>
  [key: string]: any
}

// ============================================================================
// 消息类型
// ============================================================================

/**
 * 消息类型
 */
export type MessageType = 'text' | 'plan' | 'tool_call' | 'hitl' | 'error'

/**
 * 消息元数据
 */
export interface MessageMetadata {
  plan?: ExecutionPlan
  tool?: ToolCall
  hitl?: HITLConfirmationRequest
  error?: {
    code: string
    message: string
  }
}

/**
 * 增强的消息接口
 */
export interface EnhancedMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  author: string
  time: string
  content: string
  type: MessageType
  metadata?: MessageMetadata
  isStreaming?: boolean
}

// ============================================================================
// AG-UI 事件
// ============================================================================

/**
 * AG-UI 事件
 */
export interface AGUIEvent {
  event: string
  data: {
    event_type?: string
    subtype?: string
    payload?: Record<string, any>
    [key: string]: any
  }
}

/**
 * 事件处理器
 */
export type AGUIEventHandler = (event: AGUIEvent) => void | Promise<void>


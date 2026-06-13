/**
 * AG-UI 协议类型定义
 * 
 * 定义前端与 Agent Runtime 之间的事件协议
 */

// ============================================================================
// AG-UI 事件类型
// ============================================================================

export enum AGUIEventType {
  // 文本消息事件
  TEXT_MESSAGE_START = 'TEXT_MESSAGE_START',
  TEXT_MESSAGE_CONTENT = 'TEXT_MESSAGE_CONTENT',
  TEXT_MESSAGE_END = 'TEXT_MESSAGE_END',
  
  // 工具调用事件
  TOOL_CALL_START = 'TOOL_CALL_START',
  TOOL_CALL_ARGS = 'TOOL_CALL_ARGS',
  TOOL_CALL_END = 'TOOL_CALL_END',
  
  // 共享状态事件
  STATE_SNAPSHOT = 'STATE_SNAPSHOT',
  
  // 自定义事件（Plan/Todo/HITL）
  CUSTOM = 'CUSTOM',
  
  // 运行时事件
  RUNTIME_STARTED = 'runtime.started',
  RUNTIME_COMPLETED = 'runtime.completed',
  RUNTIME_ERROR = 'runtime.error',
  RUNTIME_ABORTED = 'runtime.aborted',
  
  // 兼容旧事件
  MESSAGE_DELTA = 'message_delta',
  MESSAGE_UPDATED = 'message.updated',
  MESSAGE_COMPLETED = 'message_completed',
  MESSAGE_COMPLETED_ALT = 'message.completed',
}

// ============================================================================
// 自定义事件子类型
// ============================================================================

export enum CustomEventSubtype {
  // Plan 事件
  PLAN_CREATED = 'plan.created',
  PLAN_UPDATED = 'plan.updated',
  
  // Todo 事件
  TODO_STARTED = 'todo.started',
  TODO_COMPLETED = 'todo.completed',
  TODO_FAILED = 'todo.failed',
  TODO_SKIPPED = 'todo.skipped',
  
  // HITL 事件
  HITL_CONFIRMATION_REQUEST = 'hitl.confirmation_request',
  HITL_CONFIRMATION_RESPONSE = 'hitl.confirmation_response',
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

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 判断是否为文本消息事件
 */
export function isTextMessageEvent(eventType: string): boolean {
  return [
    AGUIEventType.TEXT_MESSAGE_CONTENT,
    AGUIEventType.MESSAGE_DELTA,
    AGUIEventType.MESSAGE_UPDATED,
  ].includes(eventType as AGUIEventType)
}

/**
 * 判断是否为消息完成事件
 */
export function isMessageCompletedEvent(eventType: string): boolean {
  return [
    AGUIEventType.TEXT_MESSAGE_END,
    AGUIEventType.MESSAGE_COMPLETED,
    AGUIEventType.MESSAGE_COMPLETED_ALT,
  ].includes(eventType as AGUIEventType)
}

/**
 * 判断是否为工具调用事件
 */
export function isToolCallEvent(eventType: string): boolean {
  return [
    AGUIEventType.TOOL_CALL_START,
    AGUIEventType.TOOL_CALL_ARGS,
    AGUIEventType.TOOL_CALL_END,
  ].includes(eventType as AGUIEventType)
}

/**
 * 判断是否为自定义事件
 */
export function isCustomEvent(eventType: string): boolean {
  return eventType === AGUIEventType.CUSTOM
}

/**
 * 获取自定义事件子类型
 */
export function getCustomEventSubtype(event: AGUIEvent): string | undefined {
  return event.data.subtype || event.data.payload?.subtype
}

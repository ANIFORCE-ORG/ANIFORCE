# ANIFORCE AG-UI 集成完整开发手册

**基于 OpenAI Agents SDK + MCP + Skills 的完整方案**

---

## 🎯 核心决策

### 技术选型
- ✅ **Backend Agent**: OpenAI Agents SDK（保持不变）
- ✅ **MCP**: 原生支持，10 个工具已实现
- ✅ **Skills**: 原生支持，放在 `backend/runtime/skills/`
- ✅ **协议层**: 自己实现 AG-UI 协议（不依赖 LangGraph）
- ✅ **Frontend**: CopilotKit React SDK（只用 UI 层）

### 为什么不用 LangGraph？
1. **LangGraph 没有原生 MCP 支持**（需要 `langchain-mcp-adapters`）
2. **LangGraph 没有 Skills 概念**（需要改造为 nodes/tools）
3. **OpenAI SDK 的 MCP + Skills 是行业标准**（保持不变）
4. **我们只需要 AG-UI 协议**（自己实现 100 行代码即可）

---

## 📐 完整架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                            │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Vue 3 Application (保持不变)                            │  │
│  │  ├── ChatPanel.vue (旧版 SSE 接口)                       │  │
│  │  └── NEW: AGUIChatPanel.tsx (新版 AG-UI)                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↕                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CopilotKit React SDK (可选渐进式集成)                  │  │
│  │  - useCopilotReadable (Shared State)                     │  │
│  │  - useCopilotAction (Frontend Actions)                   │  │
│  │  - CopilotSidebar (UI 组件)                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             ↕
                    AG-UI Protocol (SSE)
                             ↕
┌─────────────────────────────────────────────────────────────────┐
│                     Runtime Layer (FastAPI)                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  NEW: AG-UI Protocol Adapter (100 行)                    │  │
│  │  ├── 事件转换: OpenAI SDK Events → AG-UI Events         │  │
│  │  ├── 状态管理: Shared State                              │  │
│  │  └── HITL: Human-in-the-Loop                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↕                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Existing: AgentRuntime (保持不变)                       │  │
│  │  ├── OpenAISDKAdapter                                     │  │
│  │  ├── AgentTaskRepository                                  │  │
│  │  └── Event Streaming                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             ↕
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Layer (OpenAI SDK)                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  SandboxAgent (保持不变)                                 │  │
│  │  ├── Skills (backend/runtime/skills/)                    │  │
│  │  │   ├── project-management/                             │  │
│  │  │   ├── campaign-optimization/                          │  │
│  │  │   └── data-reporting/                                 │  │
│  │  │                                                         │  │
│  │  ├── MCP Tools (10 个已实现)                             │  │
│  │  │   - list_projects, create_project, ...               │  │
│  │  │   - list_campaigns, create_campaign, ...             │  │
│  │  │                                                         │  │
│  │  └── System Prompt (增强 AG-UI 支持)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 核心实现

### Phase 1: AG-UI 协议适配器（Backend）

#### 1.1 创建 AG-UI 事件转换器

```python
# backend/app/agent_platform/adapters/agui_protocol.py

from typing import Dict, Any, AsyncIterator
from ..models import AgentTaskEvent, EventType

class AGUIProtocolAdapter:
    """
    OpenAI Agents SDK Events → AG-UI Protocol Events
    
    AG-UI 协议核心事件：
    - TEXT_MESSAGE_START
    - TEXT_MESSAGE_CONTENT
    - TEXT_MESSAGE_END
    - TOOL_CALL_START
    - TOOL_CALL_ARGS
    - TOOL_CALL_END
    - STATE_SNAPSHOT
    - CUSTOM
    """
    
    @staticmethod
    def convert_event(sdk_event: AgentTaskEvent) -> Dict[str, Any]:
        """
        将 OpenAI SDK 事件转换为 AG-UI 协议事件
        
        OpenAI SDK Events:
        - runtime.started
        - message.started
        - message.delta
        - message.completed
        - tool_call.started
        - tool_call.completed
        - runtime.completed
        
        AG-UI Events:
        - TEXT_MESSAGE_START
        - TEXT_MESSAGE_CONTENT (streaming)
        - TEXT_MESSAGE_END
        - TOOL_CALL_START
        - TOOL_CALL_ARGS
        - TOOL_CALL_END
        """
        event_type = sdk_event.event_type
        payload = sdk_event.payload
        
        # Message events
        if event_type == EventType.MESSAGE_STARTED:
            return {
                "type": "TEXT_MESSAGE_START",
                "role": "assistant",
                "message_id": sdk_event.event_id,
            }
        
        elif event_type == EventType.MESSAGE_DELTA:
            return {
                "type": "TEXT_MESSAGE_CONTENT",
                "message_id": sdk_event.event_id,
                "delta": payload.get("delta", ""),
            }
        
        elif event_type == EventType.MESSAGE_COMPLETED:
            return {
                "type": "TEXT_MESSAGE_END",
                "message_id": sdk_event.event_id,
            }
        
        # Tool call events
        elif event_type == EventType.TOOL_CALL_STARTED:
            return {
                "type": "TOOL_CALL_START",
                "tool_call_id": sdk_event.event_id,
                "tool_call_name": payload.get("tool_name", ""),
                "parent_message_id": sdk_event.event_id,
            }
        
        elif event_type == EventType.TOOL_CALL_COMPLETED:
            return {
                "type": "TOOL_CALL_END",
                "tool_call_id": sdk_event.event_id,
            }
        
        # Runtime events (custom)
        elif event_type in [EventType.RUNTIME_STARTED, EventType.RUNTIME_COMPLETED]:
            return {
                "type": "CUSTOM",
                "name": event_type.value,
                "value": payload,
            }
        
        # Default: pass through as custom event
        return {
            "type": "CUSTOM",
            "name": event_type.value,
            "value": payload,
        }

#### 1.2 创建 Shared State 管理器

```python
# backend/app/agent_platform/adapters/agui_state.py

from typing import Dict, Any, Optional

class AGUISharedState:
    """
    AG-UI 共享状态管理
    
    前端和 Agent 可以双向读写的状态
    """
    
    def __init__(self):
        self.state: Dict[str, Any] = {
            "current_project": None,
            "current_campaign": None,
            "user_preferences": {},
            "pending_confirmations": [],
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取状态"""
        return self.state.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置状态"""
        self.state[key] = value
    
    def update(self, updates: Dict[str, Any]):
        """批量更新状态"""
        self.state.update(updates)
    
    def to_snapshot(self) -> Dict[str, Any]:
        """转换为 AG-UI STATE_SNAPSHOT 事件"""
        return {
            "type": "STATE_SNAPSHOT",
            "snapshot": self.state.copy(),
        }
```

#### 1.3 创建 Human-in-the-Loop 管理器

```python
# backend/app/agent_platform/adapters/agui_hitl.py

import asyncio
from typing import Dict, Any, Optional
from loguru import logger

class HITLManager:
    """Human-in-the-Loop 管理器"""
    
    def __init__(self):
        self.pending_confirmations: Dict[str, asyncio.Future] = {}
    
    async def request_confirmation(
        self,
        operation_id: str,
        operation: str,
        details: Dict[str, Any],
        risk_level: str = "medium"
    ) -> bool:
        """
        请求用户确认
        
        Args:
            operation_id: 操作唯一 ID
            operation: 操作名称
            details: 操作详情
            risk_level: 风险等级 (low/medium/high)
        
        Returns:
            bool: 用户是否批准
        """
        # 创建 Future 等待用户响应
        future = asyncio.get_event_loop().create_future()
        self.pending_confirmations[operation_id] = future
        
        logger.info(f"[HITL] Requesting confirmation: {operation_id} | {operation}")
        
        # 等待用户响应（超时 5 分钟）
        try:
            approved = await asyncio.wait_for(future, timeout=300)
            return approved
        except asyncio.TimeoutError:
            logger.warning(f"[HITL] Confirmation timeout: {operation_id}")
            return False
        finally:
            self.pending_confirmations.pop(operation_id, None)
    
    def respond_confirmation(self, operation_id: str, approved: bool):
        """
        响应用户确认
        
        由前端调用，设置 Future 结果
        """
        future = self.pending_confirmations.get(operation_id)
        if future and not future.done():
            future.set_result(approved)
            logger.info(f"[HITL] Confirmation received: {operation_id} | approved={approved}")
    
    def generate_confirmation_event(
        self,
        operation_id: str,
        operation: str,
        details: Dict[str, Any],
        risk_level: str
    ) -> Dict[str, Any]:
        """生成 AG-UI 确认请求事件"""
        risk_emoji = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨"
        }
        
        message = f"""
{risk_emoji.get(risk_level, '❓')} **需要您的确认**

**操作**: {operation}
**详情**: {details}
**风险等级**: {risk_level}

是否继续执行？
        """.strip()
        
        return {
            "type": "CUSTOM",
            "name": "HITL_CONFIRMATION_REQUEST",
            "value": {
                "operation_id": operation_id,
                "operation": operation,
                "details": details,
                "risk_level": risk_level,
                "message": message,
            }
        }
```

---

### Phase 2: AG-UI API 端点（Backend）

#### 2.1 创建 AG-UI 路由

```python
# backend/app/api/v1/agent/agui_routes.py

import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from loguru import logger

from ....api.deps import get_current_user
from ....services.agent_task_service import AgentTaskService
from ....agent_platform.adapters.agui_protocol import AGUIProtocolAdapter
from ....agent_platform.adapters.agui_state import AGUISharedState
from ....agent_platform.adapters.agui_hitl import HITLManager

router = APIRouter(prefix="/agent/agui", tags=["Agent AG-UI"])

# 全局实例（TODO: 改为依赖注入）
_agui_adapter = AGUIProtocolAdapter()
_shared_state_manager: Dict[str, AGUISharedState] = {}  # user_id -> state
_hitl_manager = HITLManager()


@router.post("/stream")
async def agui_stream(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    AG-UI 协议端点
    
    接收前端请求，返回 AG-UI 协议事件流（SSE）
    """
    # 解析请求体
    body = await request.json()
    
    # 提取参数
    message = body.get("message", "")
    session_id = body.get("session_id")
    state_updates = body.get("state", {})
    
    if not message:
        async def error_gen():
            yield 'data: {"type": "ERROR", "message": "Message is required"}\n\n'
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    # 获取或创建 Shared State
    user_id = user["id"]
    if user_id not in _shared_state_manager:
        _shared_state_manager[user_id] = AGUISharedState()
    shared_state = _shared_state_manager[user_id]
    
    # 更新 Shared State
    if state_updates:
        shared_state.update(state_updates)
    
    # 获取 Auth Token
    auth_header = request.headers.get("authorization", "")
    auth_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    
    # 创建 Service
    from ....agent_platform.repositories.sqlite import SQLiteAgentTaskRepository
    from ....agent_platform.adapters.openai_adapter import OpenAISDKAdapter
    from ....agent_platform.runtime import AgentRuntime
    from ....config.settings import get_settings
    
    settings = get_settings()
    repo = SQLiteAgentTaskRepository(db_path=getattr(settings, "AGENT_TASK_DB", "runtime/agent/tasks.db"))
    adapter = OpenAISDKAdapter(
        model=getattr(settings, "OPENAI_AGENTS_MODEL", "gpt-4o-mini"),
        api_key=settings.OPENAI_API_KEY,
    )
    runtime = AgentRuntime(adapter=adapter, repo=repo)
    service = AgentTaskService(repo, runtime)
    
    # SSE 事件生成器
    async def event_generator():
        try:
            # 如果没有 session_id，创建新 session
            if not session_id:
                task = await service.create_task(
                    user_id=user_id,
                    task_type="conversation",
                    title="AG-UI Chat",
                )
                task_id = task.task_id
                
                # 推送 session 创建事件
                yield f'data: {json.dumps({"type": "SESSION_CREATED", "session_id": task_id})}\n\n'
            else:
                task_id = session_id
            
            # 推送状态快照
            state_snapshot = shared_state.to_snapshot()
            yield f'data: {json.dumps(state_snapshot)}\n\n'
            
            # 运行 Agent 任务
            async for sdk_event in service.run_task(
                user_id=user_id,
                task_id=task_id,
                user_input=message,
                context={"auth_token": auth_token, "shared_state": shared_state.state},
            ):
                # 转换为 AG-UI 事件
                agui_event = _agui_adapter.convert_event(sdk_event)
                
                # 推送事件
                yield f'data: {json.dumps(agui_event)}\n\n'
        
        except Exception as e:
            logger.exception(f"AG-UI stream error: {e}")
            error_event = {
                "type": "ERROR",
                "message": str(e),
            }
            yield f'data: {json.dumps(error_event)}\n\n'
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/hitl/{operation_id}/respond")
async def hitl_respond(
    operation_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    响应 Human-in-the-Loop 确认请求
    """
    body = await request.json()
    approved = body.get("approved", False)
    
    _hitl_manager.respond_confirmation(operation_id, approved)
    
    return {"status": "ok", "operation_id": operation_id, "approved": approved}
```


---

### Phase 3: Skills 创建（Backend）

#### 3.1 创建 Skills 目录结构

```bash
mkdir -p backend/runtime/skills/project-management
mkdir -p backend/runtime/skills/campaign-optimization
mkdir -p backend/runtime/skills/data-reporting
mkdir -p backend/runtime/skills/hitl-operations
```

#### 3.2 项目管理 Skill

```markdown
# backend/runtime/skills/project-management/SKILL.md

---
name: project-management
description: 项目管理：创建、查询、更新、删除、预算分析
---

# 项目管理 Skill

## 目标
帮助用户管理广告投放项目的全生命周期

## 输入
- 用户自然语言需求
- 项目 ID（可选，用于更新/查询）

## 输出
- 结构化项目信息
- 操作确认消息
- 预算分析报告（如需要）

## 工作流

### 1. 创建项目
1. 提取项目信息：名称、预算、描述、游戏类型
2. 调用 MCP Tool: `create_project`
3. 确认创建成功，返回项目 ID

### 2. 查询项目
1. 调用 MCP Tool: `list_projects` 或 `get_project_detail`
2. 格式化展示项目信息
3. 如用户需要分析，生成预算使用报告

### 3. 更新项目
1. 获取当前项目状态：`get_project_detail`
2. 确认要修改的字段
3. 调用 MCP Tool: `update_project`
4. 确认更新成功

### 4. 删除项目（需要 HITL）
1. 获取项目详情
2. 请求用户确认（高风险操作）
3. 等待用户批准
4. 执行删除

## 硬约束
- 预算必须 > 0
- 项目名称不能为空
- 删除操作必须经用户确认
```

#### 3.3 HITL 操作 Skill

```markdown
# backend/runtime/skills/hitl-operations/SKILL.md

---
name: hitl-operations
description: 需要用户确认的危险操作工作流
---

# Human-in-the-Loop 操作 Skill

## 目标
处理需要用户确认的危险操作，确保安全性

## 工作流

### 1. 删除项目
1. 调用 `get_project_detail` 获取项目详情
2. 使用 HITL Manager 请求用户确认
3. 展示确认对话框（包含项目信息、风险提示）
4. 等待用户响应
5. 如批准，调用 `delete_project`
6. 返回操作结果

### 2. 批量操作
1. 列出受影响的对象
2. 展示操作预览
3. 请求用户确认
4. 批量执行
5. 返回执行报告

## 确认消息格式

```
⚠️ **需要您的确认**

**操作**: 删除项目
**详情**: 
- 项目名称: XXX
- 项目 ID: XXX
- 包含广告计划: N 个
- 总预算: ¥XXX

**风险等级**: high

此操作不可逆，是否继续执行？

[取消] [确认]
```

## 硬约束
- 所有删除操作必须经用户确认
- 批量操作必须展示预览
- 用户可以在任何步骤取消
- 超时 5 分钟自动拒绝
```

---

### Phase 4: System Prompt 增强（Backend）

#### 4.1 增强 System Prompt 支持 AG-UI

```python
# backend/app/agent_platform/prompts.py

AGUI_SYSTEM_PROMPT = """
你是 ANIFORCE AI 助手，使用 AG-UI 协议与用户交互。

## 核心能力

### 1. Shared State（共享状态）
- 你可以访问当前的共享状态（current_project, current_campaign, user_preferences）
- 当用户切换项目或广告计划时，状态会自动更新
- 你可以根据当前状态提供上下文相关的建议

### 2. Human-in-the-Loop（人机协作）
- 执行危险操作前（删除项目、批量修改）必须请求用户确认
- 使用 `hitl-operations` Skill 处理需要确认的操作
- 确认对话框会显示操作详情和风险等级

### 3. Skills（领域知识）
- 使用 `project-management` Skill 处理项目相关操作
- 使用 `campaign-optimization` Skill 处理广告计划相关操作
- 使用 `data-reporting` Skill 生成数据分析报告
- 使用 `hitl-operations` Skill 处理需要确认的危险操作

## 工具调用原则

- 简单查询：直接使用 MCP Tools
- 复杂工作流：优先使用 Skills
- 危险操作：必须使用 `hitl-operations` Skill
- 独立工具：批量并行调用
- 回答简洁：2-3 句话，不过度解释

## 可用 MCP Tools

{mcp_tools_list}

## 工作流程

1. 理解用户需求
2. 判断是否需要 Skill
3. 如需要确认，使用 HITL
4. 执行操作
5. 返回结果
"""


def build_system_prompt(mcp_tools: list) -> str:
    """构建完整的 System Prompt"""
    tools_list = "\n".join([
        f"- {tool.get('name', 'unknown')}: {tool.get('description', '')}"
        for tool in mcp_tools
    ])
    
    return AGUI_SYSTEM_PROMPT.format(mcp_tools_list=tools_list)
```

#### 4.2 更新 Runtime 使用增强的 Prompt

```python
# backend/app/agent_platform/runtime.py (修改 _get_system_prompt 方法)

from .prompts import build_system_prompt

def _get_system_prompt(self, task_type: str) -> str:
    """根据任务类型返回 system prompt"""
    # TODO: 从 MCP 获取工具列表
    mcp_tools = []  # 这里应该从 MCP Server 获取
    
    return build_system_prompt(mcp_tools)
```

---

### Phase 5: Frontend 集成（渐进式）

#### 方案 A: 保持现有 Vue 组件（最小改动）

**优势**: 不需要引入 React，改动最小
**实现**: 直接调用 AG-UI 端点，手动处理事件

```typescript
// frontend/packages/main-app/src/services/aguiService.ts

export interface AGUIMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface AGUIStreamEvent {
  type: string
  [key: string]: any
}

export class AGUIService {
  private baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:18003'
  
  async *streamChat(
    message: string,
    sessionId?: string,
    state?: Record<string, any>
  ): AsyncGenerator<AGUIStreamEvent> {
    const token = localStorage.getItem('auth_token')
    
    const response = await fetch(`${this.baseURL}/api/v1/agent/agui/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        state,
      }),
    })
    
    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const eventData = JSON.parse(line.slice(6))
          yield eventData
        }
      }
    }
  }
  
  async respondHITL(operationId: string, approved: boolean) {
    const token = localStorage.getItem('auth_token')
    
    await fetch(`${this.baseURL}/api/v1/agent/agui/hitl/${operationId}/respond`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ approved }),
    })
  }
}

export const aguiService = new AGUIService()
```


```vue
<!-- frontend/packages/main-app/src/components/agent/AGUIChatWindow.vue -->

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { aguiService, AGUIStreamEvent } from '@/services/aguiService'
import { ElMessageBox } from 'element-plus'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const messages = ref<Message[]>([])
const inputMessage = ref('')
const isStreaming = ref(false)
const currentSessionId = ref<string>()
const sharedState = ref<Record<string, any>>({})

// 处理 AG-UI 事件
const handleAGUIEvent = async (event: AGUIStreamEvent) => {
  console.log('[AG-UI Event]', event)
  
  switch (event.type) {
    case 'SESSION_CREATED':
      currentSessionId.value = event.session_id
      break
    
    case 'TEXT_MESSAGE_START':
      // 开始新的 AI 消息
      messages.value.push({
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      })
      break
    
    case 'TEXT_MESSAGE_CONTENT':
      // 追加内容
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.content += event.delta
      }
      break
    
    case 'TEXT_MESSAGE_END':
      // 消息完成
      break
    
    case 'TOOL_CALL_START':
      console.log('[Tool Call]', event.tool_call_name)
      break
    
    case 'STATE_SNAPSHOT':
      // 更新共享状态
      sharedState.value = event.snapshot
      break
    
    case 'CUSTOM':
      if (event.name === 'HITL_CONFIRMATION_REQUEST') {
        // 显示确认对话框
        await showHITLConfirmation(event.value)
      }
      break
  }
  
  nextTick(() => scrollToBottom())
}

// 显示 HITL 确认对话框
const showHITLConfirmation = async (data: any) => {
  try {
    await ElMessageBox.confirm(
      data.message,
      '需要您的确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: data.risk_level === 'high' ? 'error' : 'warning',
      }
    )
    
    // 用户批准
    await aguiService.respondHITL(data.operation_id, true)
  } catch {
    // 用户取消
    await aguiService.respondHITL(data.operation_id, false)
  }
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || isStreaming.value) return
  
  const userMsg = inputMessage.value.trim()
  inputMessage.value = ''
  
  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: userMsg,
    timestamp: new Date(),
  })
  
  isStreaming.value = true
  
  try {
    // 流式调用 AG-UI
    for await (const event of aguiService.streamChat(
      userMsg,
      currentSessionId.value,
      sharedState.value
    )) {
      await handleAGUIEvent(event)
    }
  } catch (error) {
    console.error('[AG-UI Error]', error)
  } finally {
    isStreaming.value = false
  }
}

const scrollToBottom = () => {
  // 滚动逻辑
}
</script>

<template>
  <div class="agui-chat-window">
    <div class="messages-container">
      <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
        <div class="content">{{ msg.content }}</div>
      </div>
    </div>
    
    <div class="input-area">
      <input
        v-model="inputMessage"
        @keyup.enter="sendMessage"
        placeholder="输入消息..."
        :disabled="isStreaming"
      />
      <button @click="sendMessage" :disabled="isStreaming">
        发送
      </button>
    </div>
  </div>
</template>

<style scoped>
/* 样式 */
</style>
```

---

#### 方案 B: 集成 CopilotKit（推荐长期方案）

**优势**: 官方 UI 组件、Shared State、更好的开发体验
**实现**: 引入 React + CopilotKit SDK

```bash
# 安装依赖
cd frontend/packages/main-app
npm install @copilotkit/react-core @copilotkit/react-ui react react-dom
```

```tsx
// frontend/packages/main-app/src/components/agent/CopilotPanel.tsx

import React from 'react'
import { CopilotKit } from '@copilotkit/react-core'
import { CopilotSidebar } from '@copilotkit/react-ui'
import '@copilotkit/react-ui/styles.css'

export const CopilotPanel: React.FC = () => {
  const token = localStorage.getItem('auth_token')
  
  return (
    <CopilotKit
      runtimeUrl="http://localhost:18003/api/v1/agent/agui/stream"
      headers={{
        Authorization: `Bearer ${token}`
      }}
    >
      <CopilotSidebar>
        <div>
          {/* 你的应用内容 */}
        </div>
      </CopilotSidebar>
    </CopilotKit>
  )
}
```

---

### Phase 6: 集成到现有路由（Backend）

```python
# backend/app/api/v1/router.py

from .agent import agui_routes

# 注册 AG-UI 路由
api_router.include_router(agui_routes.router)
```

---

## 📊 完整工作流示例

### 场景：用户删除项目（带 HITL）

#### 1. 用户输入
```
用户: "帮我删除测试项目"
```

#### 2. Frontend 发送请求
```typescript
for await (const event of aguiService.streamChat("帮我删除测试项目")) {
  // 处理事件
}
```

#### 3. Backend 处理

**Step 1**: Agent 加载 `hitl-operations` Skill

**Step 2**: Agent 调用 MCP Tool 查询项目
```python
project = await mcp_tool("get_project_detail", {"name": "测试项目"})
```

**Step 3**: Agent 生成 HITL 请求
```python
confirmation_event = {
    "type": "CUSTOM",
    "name": "HITL_CONFIRMATION_REQUEST",
    "value": {
        "operation_id": "delete_proj_123",
        "operation": "删除项目",
        "details": {
            "project_name": "测试项目",
            "project_id": "proj_123",
            "campaigns_count": 5,
            "total_budget": 50000,
        },
        "risk_level": "high",
        "message": "⚠️ 确认删除项目 '测试项目'？..."
    }
}
```

**Step 4**: Runtime 推送事件到 Frontend

#### 4. Frontend 显示确认框

```vue
ElMessageBox.confirm(
  "⚠️ 确认删除项目 '测试项目'？\n\n详情：\n- 项目 ID: proj_123\n- 包含 5 个广告计划\n- 总预算: ¥50,000\n\n此操作不可逆！",
  "需要您的确认",
  { type: 'error' }
)
```

#### 5. 用户点击确认

Frontend 调用：
```typescript
await aguiService.respondHITL("delete_proj_123", true)
```

#### 6. Backend 执行删除

```python
# HITL Manager 收到响应
approved = await hitl_manager.request_confirmation(...)

if approved:
    result = await mcp_tool("delete_project", {"project_id": "proj_123"})
    return "✅ 已删除项目 '测试项目'"
else:
    return "❌ 已取消删除操作"
```

#### 7. Frontend 显示结果

```
AI: ✅ 已删除项目 '测试项目'
```

---

## ✅ 实施检查清单

### Backend
- [ ] 创建 `agui_protocol.py` - AG-UI 事件转换器
- [ ] 创建 `agui_state.py` - Shared State 管理
- [ ] 创建 `agui_hitl.py` - Human-in-the-Loop 管理
- [ ] 创建 `agui_routes.py` - AG-UI API 端点
- [ ] 创建 `prompts.py` - 增强 System Prompt
- [ ] 创建 4 个 Skills（`backend/runtime/skills/`）
- [ ] 集成路由到 `router.py`
- [ ] 测试 AG-UI 事件流

### Frontend（方案 A - 最小改动）
- [ ] 创建 `aguiService.ts` - AG-UI 客户端
- [ ] 创建 `AGUIChatWindow.vue` - AG-UI 聊天组件
- [ ] 处理 AG-UI 事件（TEXT_MESSAGE, TOOL_CALL, STATE_SNAPSHOT）
- [ ] 实现 HITL 确认对话框
- [ ] 测试完整流程

### Frontend（方案 B - CopilotKit）
- [ ] 安装 CopilotKit 依赖
- [ ] 创建 `CopilotPanel.tsx` - React 组件
- [ ] 在 Vue 应用中嵌入 React 组件（可选）
- [ ] 配置 `useCopilotReadable` - Shared State
- [ ] 配置 `useCopilotAction` - Frontend Actions

### 测试
- [ ] 测试基本对话（TEXT_MESSAGE 事件）
- [ ] 测试工具调用（TOOL_CALL 事件）
- [ ] 测试 Shared State 同步（STATE_SNAPSHOT）
- [ ] 测试 HITL 确认流程
- [ ] 测试 Skills 加载和执行

---

## 🔑 核心设计决策

1. **保持 OpenAI Agents SDK**：MCP + Skills 原生支持
2. **自己实现 AG-UI 协议**：100 行代码，不依赖 LangGraph
3. **渐进式前端集成**：先用方案 A（Vue），后续可升级到方案 B（CopilotKit）
4. **Skills 为领域知识**：封装复杂工作流
5. **HITL 为安全保障**：危险操作必须确认
6. **Shared State 为协作基础**：前后端状态同步

---

## 📚 参考资源

- **AG-UI 协议**: https://github.com/ag-ui-protocol/ag-ui
- **OpenAI Agents SDK**: https://github.com/openai/openai-agents-python
- **CopilotKit 文档**: https://docs.copilotkit.ai
- **MCP 协议**: https://spec.modelcontextprotocol.io

---

## 🎯 预期收益

1. **符合行业标准**：AG-UI 协议
2. **保留现有能力**：MCP、Skills、认证、权限完全不变
3. **更强交互体验**：Shared State、Generative UI、HITL
4. **代码量可控**：核心适配器只需 100 行
5. **渐进式升级**：可以先用 Vue，后续升级 React


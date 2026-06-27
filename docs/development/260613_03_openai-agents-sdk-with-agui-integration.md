# OpenAI Agents SDK + AG-UI 协议集成开发手册

## 🎯 核心理念

将 **OpenAI Agents SDK**（后端 Agent）与 **AG-UI 协议**（前后端通信）和 **CopilotKit**（前端 UI）完美结合，构建符合行业标准的 Agentic 应用。

---

## 📐 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Web (React) │  │ Mobile (RN)  │  │ Slack / Teams│         │
│  │              │  │              │  │              │         │
│  │ CopilotKit   │  │ CopilotKit   │  │ CopilotKit   │         │
│  │   SDK        │  │   SDK        │  │   Bot SDK    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                    AG-UI Protocol (SSE)
                             │
┌─────────────────────────────┼────────────────────────────────────┐
│                     Runtime Layer                                 │
│                             │                                     │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │         FastAPI + CopilotKit Python SDK                   │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │ CopilotKitMiddleware                                │ │   │
│  │  │  - AG-UI 事件转换                                    │ │   │
│  │  │  - 状态同步                                          │ │   │
│  │  │  - HITL 管理                                         │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────┬───────────────────────────────┘   │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────┐
│                       Agent Layer                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          OpenAI Agents SDK (SandboxAgent)                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │ Skills       │  │ MCP Tools    │  │ System       │   │  │
│  │  │ (Workflows)  │  │ (Data Ops)   │  │ Prompt       │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🔧 技术栈选型

### Frontend
- **Web**: React + `@copilotkit/react-core` + `@copilotkit/react-ui`
- **Mobile**: React Native + `@copilotkit/react-native`
- **协议**: AG-UI Protocol (SSE)

### Runtime (中间层)
- **框架**: FastAPI
- **SDK**: `copilotkit` (Python SDK)
- **职责**: AG-UI 协议实现 + 事件转换 + 状态管理

### Agent Backend
- **框架**: OpenAI Agents SDK
- **Agent 类型**: `SandboxAgent`
- **能力**: Skills + MCP Tools + Sandbox

---

## 🏗️ 实施方案

### Phase 1: Runtime 层集成 CopilotKit

#### 1.1 安装依赖

```bash
cd backend
UV_CACHE_DIR=./uv_cache uv pip install copilotkit
UV_CACHE_DIR=./uv_cache uv pip install ag-ui-langgraph
```

#### 1.2 创建 AG-UI Agent 适配器

**目标**: 将 OpenAI Agents SDK 的 `SandboxAgent` 适配为 AG-UI 兼容的 Agent

```python
# backend/app/agent_platform/adapters/agui_adapter.py

from typing import AsyncGenerator, Dict, Any
from agents import Agent, Runner
from agents.run import RunConfig
from agents.sandbox import SandboxRunConfig
from agents.sandbox.sandboxes import UnixLocalSandboxClient
from copilotkit import LangGraphAGUIAgent
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict


class AGUIState(TypedDict):
    """AG-UI 状态"""
    messages: list
    ag_ui: Dict[str, Any]  # AG-UI 协议字段


def create_openai_agent_to_langgraph_wrapper(
    openai_agent: Agent,
    run_config: RunConfig
) -> CompiledStateGraph:
    """
    将 OpenAI Agents SDK 的 Agent 包装为 LangGraph 图
    """
    
    async def agent_node(state: AGUIState) -> AGUIState:
        """执行 OpenAI Agent"""
        messages = state.get("messages", [])
        user_input = messages[-1]["content"] if messages else ""
        
        # 运行 OpenAI Agent
        result = await Runner.run(
            openai_agent,
            input=user_input,
            run_config=run_config
        )
        
        # 收集结果
        final_message = ""
        async for event in result.stream_events():
            if event.type == "message.delta":
                final_message += event.content
        
        # 更新状态
        new_messages = messages + [{"role": "assistant", "content": final_message}]
        
        return {
            "messages": new_messages,
            "ag_ui": state.get("ag_ui", {})
        }
    
    # 构建 LangGraph
    graph = StateGraph(AGUIState)
    graph.add_node("agent", agent_node)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)
    
    return graph.compile()


class OpenAIAgentAGUIAdapter:
    """OpenAI Agents SDK → AG-UI 适配器"""
    
    def __init__(
        self,
        openai_agent: Agent,
        name: str = "aniforce_assistant",
        description: str = "ANIFORCE AI Assistant"
    ):
        self.openai_agent = openai_agent
        self.name = name
        self.description = description
        
        # 创建 Sandbox 运行配置
        self.run_config = RunConfig(
            sandbox=SandboxRunConfig(
                client=UnixLocalSandboxClient()
            )
        )
        
        # 包装为 LangGraph
        self.langgraph = create_openai_agent_to_langgraph_wrapper(
            openai_agent=self.openai_agent,
            run_config=self.run_config
        )
        
        # 创建 AG-UI Agent
        self.agui_agent = LangGraphAGUIAgent(
            name=self.name,
            graph=self.langgraph,
            description=self.description
        )
    
    async def run(self, input: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """运行 Agent 并返回 AG-UI 事件流"""
        async for event in self.agui_agent.run(input):
            yield event
```

#### 1.3 集成 CopilotKit Middleware

```python
# backend/app/api/v1/agent/agui_routes.py

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from copilotkit import CopilotKitSDK, LangGraphAGUIAgent
from app.agent_platform.adapters.agui_adapter import OpenAIAgentAGUIAdapter
from app.agent_platform.runtime import create_aniforce_agent
from app.core.context import get_current_user

router = APIRouter()


@router.post("/agui/stream")
async def agui_stream(request: Request):
    """AG-UI 协议端点"""
    
    # 获取用户上下文
    user = get_current_user()
    
    # 创建 OpenAI Agent
    openai_agent = await create_aniforce_agent(user_id=user.user_id)
    
    # 适配为 AG-UI Agent
    adapter = OpenAIAgentAGUIAdapter(
        openai_agent=openai_agent,
        name="aniforce_assistant",
        description="ANIFORCE AI Assistant powered by OpenAI Agents SDK"
    )
    
    # 初始化 CopilotKit SDK
    sdk = CopilotKitSDK(
        agents=[adapter.agui_agent]
    )
    
    # 处理请求
    body = await request.json()
    
    # 返回 SSE 流
    async def event_stream():
        async for event in adapter.run(body):
            yield f"data: {event}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

---

### Phase 2: Agent 层改造

#### 2.1 增强 System Prompt 支持 AG-UI

```python
# backend/app/agent_platform/prompts.py

AGUI_SYSTEM_PROMPT = """
你是 ANIFORCE 助手，使用 AG-UI 协议与用户交互。

## 核心能力

### 1. Shared State（共享状态）
- 你可以读取和修改与前端共享的状态
- 使用 `emit_intermediate_state` 更新状态
- 状态会实时同步到前端

### 2. Generative UI（动态生成 UI）
- 简单查询：直接文本回答
- 数据展示：返回结构化数据，前端自动渲染
- 复杂交互：使用预定义组件

### 3. Human-in-the-Loop（人机协作）
- 关键操作前必须请求用户确认
- 使用 `emit_tool_call` 显示操作意图
- 等待用户批准后再执行

## 工具调用规则

- 独立工具批量并行调用
- 简单查询不调用工具
- 回答简洁（2-3 句话）

## 可用 Skills

{skills_index}

## 可用 MCP Tools

{mcp_tools_list}
"""
```

#### 2.2 实现状态同步

```python
# backend/app/agent_platform/state.py

from typing import Dict, Any
from copilotkit import StateStreamingMiddleware, StateItem


class ANIFORCESharedState:
    """ANIFORCE 前后端共享状态"""
    
    def __init__(self):
        self.state: Dict[str, Any] = {
            "current_project": None,
            "current_campaign": None,
            "user_preferences": {},
            "pending_operations": []
        }
    
    def to_state_items(self) -> list[StateItem]:
        """转换为 AG-UI StateItem"""
        return [
            StateItem(
                key="current_project",
                value=self.state["current_project"],
                description="当前选中的项目"
            ),
            StateItem(
                key="current_campaign",
                value=self.state["current_campaign"],
                description="当前选中的广告计划"
            ),
            StateItem(
                key="user_preferences",
                value=self.state["user_preferences"],
                description="用户偏好设置"
            )
        ]
    
    def update(self, key: str, value: Any):
        """更新状态"""
        self.state[key] = value
        # 触发 AG-UI 状态同步事件
        # emit_custom_event("copilotkit_manually_emit_state", self.to_state_items())
```

#### 2.3 实现 Human-in-the-Loop

```python
# backend/app/agent_platform/hitl.py

from typing import Dict, Any, Callable
from copilotkit import CustomEvent


class HITLManager:
    """Human-in-the-Loop 管理器"""
    
    async def request_approval(
        self,
        operation: str,
        details: Dict[str, Any],
        risk_level: str = "medium"
    ) -> bool:
        """
        请求用户批准
        
        Args:
            operation: 操作名称（如 "delete_project"）
            details: 操作详情（如 {"project_id": "xxx", "project_name": "测试项目"}）
            risk_level: 风险等级（low/medium/high）
        
        Returns:
            bool: 用户是否批准
        """
        
        # 构造确认消息
        message = self._build_confirmation_message(operation, details, risk_level)
        
        # 发送 AG-UI 事件
        # emit_custom_event("copilotkit_manually_emit_message", {
        #     "message_id": f"approval_{operation}",
        #     "message": message
        # })
        
        # 等待用户响应（通过 AG-UI 协议）
        # response = await wait_for_user_response()
        
        # return response.get("approved", False)
        pass
    
    def _build_confirmation_message(
        self,
        operation: str,
        details: Dict[str, Any],
        risk_level: str
    ) -> str:
        """构造确认消息"""
        
        risk_emoji = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨"
        }
        
        return f"""
{risk_emoji.get(risk_level, "❓")} **需要您的确认**

**操作**: {operation}
**详情**: {details}
**风险等级**: {risk_level}

是否继续执行？
        """.strip()
```

---

### Phase 3: Frontend 集成

#### 3.1 安装 CopilotKit SDK

```bash
cd frontend/packages/main-app
npm install @copilotkit/react-core @copilotkit/react-ui
```

#### 3.2 配置 CopilotKit Provider

```typescript
// frontend/packages/main-app/src/App.tsx

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

function App() {
  return (
    <CopilotKit
      runtimeUrl="http://localhost:18003/api/v1/agent/agui/stream"
      headers={{
        Authorization: `Bearer ${getAuthToken()}`
      }}
    >
      <CopilotSidebar>
        {/* 你的应用主体 */}
        <YourMainApp />
      </CopilotSidebar>
    </CopilotKit>
  );
}
```

#### 3.3 使用 Shared State

```typescript
// frontend/packages/main-app/src/components/ProjectSelector.tsx

import { useCopilotReadable, useCopilotAction } from "@copilotkit/react-core";

function ProjectSelector() {
  const [currentProject, setCurrentProject] = useState(null);
  
  // 让 Agent 可以读取当前项目
  useCopilotReadable({
    description: "当前选中的项目",
    value: currentProject
  });
  
  // 让 Agent 可以切换项目
  useCopilotAction({
    name: "switch_project",
    description: "切换到指定项目",
    parameters: [
      {
        name: "project_id",
        type: "string",
        description: "项目 ID"
      }
    ],
    handler: async ({ project_id }) => {
      // 切换项目
      const project = await fetchProject(project_id);
      setCurrentProject(project);
      return `已切换到项目: ${project.name}`;
    }
  });
  
  return <div>{/* 项目选择器 UI */}</div>;
}
```

#### 3.4 使用 Generative UI

```typescript
// frontend/packages/main-app/src/components/CampaignDashboard.tsx

import { useCopilotAction } from "@copilotkit/react-core";

function CampaignDashboard() {
  
  // 定义可生成的 UI 组件
  useCopilotAction({
    name: "show_campaign_analytics",
    description: "展示广告计划分析图表",
    parameters: [
      {
        name: "campaign_id",
        type: "string"
      }
    ],
    handler: async ({ campaign_id }) => {
      const data = await fetchCampaignAnalytics(campaign_id);
      
      // 返回结构化数据，CopilotKit 会自动渲染
      return {
        type: "chart",
        data: data,
        config: {
          type: "line",
          xAxis: "date",
          yAxis: "impressions"
        }
      };
    },
    // 自定义渲染组件
    render: ({ result }) => (
      <AnalyticsChart data={result.data} config={result.config} />
    )
  });
  
  return <div>{/* Dashboard UI */}</div>;
}
```

---

### Phase 4: Skills 集成

#### 4.1 Skills 目录结构

```
backend/runtime/skills/
├── project-management/
│   ├── SKILL.md
│   └── scripts/
│       └── validate_budget.py
├── campaign-optimization/
│   ├── SKILL.md
│   └── templates/
│       └── campaign_template.json
├── data-reporting/
│   ├── SKILL.md
│   └── scripts/
│       └── generate_report.py
└── hitl-operations/
    └── SKILL.md
```

#### 4.2 HITL Skill 示例

```markdown
---
name: hitl-operations
description: 需要用户确认的危险操作工作流
---

# Human-in-the-Loop 操作 Skill

## 目标
处理需要用户确认的危险操作，确保安全性

## 工作流

### 1. 删除项目
1. 获取项目详情：`get_project_detail`
2. 构造确认消息并请求用户批准
3. 等待用户响应
4. 如批准，调用 `delete_project`
5. 返回操作结果

### 2. 批量更新广告计划
1. 列出受影响的广告计划
2. 展示修改内容预览
3. 请求用户确认
4. 批量执行更新
5. 返回执行报告

## 硬约束
- 所有删除操作必须经用户确认
- 批量操作必须展示预览
- 用户可以在任何步骤取消
```

#### 4.3 在 Agent 中加载 Skills

```python
# backend/app/agent_platform/runtime.py

from pathlib import Path
from agents.sandbox import SandboxAgent, Manifest
from agents.sandbox.capabilities import Capabilities, Skills, LocalDirLazySkillSource
from agents.sandbox.entries import LocalDir

SKILLS_DIR = Path("backend/runtime/skills")

async def create_aniforce_agent(user_id: str) -> SandboxAgent:
    """创建 ANIFORCE Agent（带 Skills）"""
    
    # 创建 MCP Server
    mcp_server = create_mcp_server(user_id)
    
    # 创建 Agent
    agent = SandboxAgent(
        name="ANIFORCE Assistant",
        instructions=AGUI_SYSTEM_PROMPT,
        mcp_servers=[mcp_server],
        capabilities=Capabilities.default() + [
            Skills(
                lazy_from=LocalDirLazySkillSource(
                    source=LocalDir(src=SKILLS_DIR)
                )
            )
        ]
    )
    
    return agent
```

---

## 🔄 完整工作流示例

### 场景：用户要求删除项目

#### 1. 用户输入
```
用户: 帮我删除"测试项目"
```

#### 2. Agent 处理
```python
# Agent 加载 hitl-operations Skill
skill = load_skill("hitl-operations")

# 查询项目
project = await call_mcp_tool("get_project_detail", {"name": "测试项目"})

# 请求用户确认（通过 AG-UI 事件）
emit_custom_event("copilotkit_manually_emit_message", {
    "message_id": "confirm_delete",
    "message": f"⚠️ 确认删除项目 '{project.name}'？此操作不可逆。"
})

# 等待用户响应...
```

#### 3. Frontend 渲染
CopilotKit 自动渲染确认对话框：
```
⚠️ 确认删除项目 '测试项目'？此操作不可逆。

详情：
- 项目 ID: proj_123
- 包含 5 个广告计划
- 总预算: ¥50,000

[取消] [确认删除]
```

#### 4. 用户确认后
```python
# Agent 收到确认响应
response = await wait_for_user_response()

if response.get("approved"):
    # 执行删除
    result = await call_mcp_tool("delete_project", {"project_id": project.id})
    
    # 返回结果
    return f"✅ 已删除项目 '{project.name}'"
else:
    return "❌ 已取消删除操作"
```

---

## 📊 状态同步示例

### Agent 更新状态
```python
# Agent 切换到新项目
new_project = await call_mcp_tool("get_project_detail", {"id": "proj_456"})

# 更新共享状态
emit_custom_event("copilotkit_manually_emit_state", {
    "current_project": {
        "id": new_project.id,
        "name": new_project.name,
        "budget": new_project.budget
    }
})
```

### Frontend 自动同步
```typescript
// Frontend 自动接收状态更新
const { state } = useCopilotContext();

useEffect(() => {
  // state.current_project 已自动更新
  console.log("当前项目:", state.current_project);
}, [state.current_project]);
```

---

## 🎨 Generative UI 示例

### Agent 生成图表
```python
# Agent 分析数据后生成可视化
analytics_data = await call_mcp_tool("get_campaign_analytics", {
    "campaign_id": "camp_789"
})

# 返回结构化数据（A2UI 模式）
emit_custom_event("copilotkit_manually_emit_tool_call", {
    "id": "chart_001",
    "name": "show_chart",
    "args": {
        "type": "line",
        "data": analytics_data,
        "config": {
            "title": "广告曝光趋势",
            "xAxis": "date",
            "yAxis": "impressions"
        }
    }
})
```

### Frontend 自动渲染
CopilotKit 根据 `show_chart` 工具定义，自动渲染图表组件。

---

## 🚀 部署配置

### Backend (.env)
```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Skills
SKILLS_DIR=backend/runtime/skills

# MCP
MCP_SERVER_URL=http://127.0.0.1:18003/api/v1/mcp

# AG-UI
AGUI_ENDPOINT=/api/v1/agent/agui/stream
```

### Frontend (.env)
```bash
VITE_AGUI_ENDPOINT=http://localhost:18003/api/v1/agent/agui/stream
VITE_AUTH_TOKEN=<从登录获取>
```

---

## 📝 核心文件清单

```
backend/
├── app/agent_platform/
│   ├── adapters/
│   │   ├── agui_adapter.py       # OpenAI Agent → AG-UI 适配器
│   │   └── openai_adapter.py     # 原有适配器（保留）
│   ├── state.py                   # 共享状态管理
│   ├── hitl.py                    # Human-in-the-Loop
│   └── prompts.py                 # AG-UI 增强 Prompt
│
├── app/api/v1/agent/
│   ├── agui_routes.py            # AG-UI 协议端点
│   └── routes.py                 # 原有端点（保留）
│
└── runtime/skills/               # Skills 目录
    ├── project-management/
    ├── campaign-optimization/
    ├── data-reporting/
    └── hitl-operations/

frontend/packages/main-app/src/
├── App.tsx                       # CopilotKit Provider
├── components/
│   ├── ProjectSelector.tsx       # 使用 Shared State
│   ├── CampaignDashboard.tsx     # 使用 Generative UI
│   └── ChatPanel.vue             # 原有组件（可选保留）
└── services/
    └── copilotkit.ts             # CopilotKit 配置
```

---

## ✅ 集成检查清单

### Backend
- [ ] 安装 `copilotkit` 和 `ag-ui-langgraph`
- [ ] 创建 `AGUIAdapter` 适配器
- [ ] 实现 AG-UI 协议端点
- [ ] 集成 `StateStreamingMiddleware`
- [ ] 实现 `HITLManager`
- [ ] 更新 System Prompt 支持 AG-UI

### Frontend
- [ ] 安装 `@copilotkit/react-core` 和 `@copilotkit/react-ui`
- [ ] 配置 `CopilotKit` Provider
- [ ] 实现 `useCopilotReadable` (Shared State)
- [ ] 实现 `useCopilotAction` (Tools)
- [ ] 定义 Generative UI 组件

### Skills
- [ ] 创建 `backend/runtime/skills/` 目录
- [ ] 编写核心 Skills (至少 3 个)
- [ ] 集成 Skills 到 SandboxAgent

### 测试
- [ ] 测试 AG-UI 事件流
- [ ] 测试 Shared State 同步
- [ ] 测试 Human-in-the-Loop 流程
- [ ] 测试 Generative UI 渲染
- [ ] 测试跨平台兼容性（Web + Mobile）

---

## 🔑 核心设计决策

1. **OpenAI Agents SDK 为核心**：保留现有 Agent 架构
2. **CopilotKit 为中间层**：负责 AG-UI 协议转换
3. **LangGraph 为桥梁**：将 OpenAI Agent 包装为 LangGraph 图
4. **Skills 保持独立**：不依赖特定框架
5. **MCP Tools 不变**：继续使用现有 MCP 集成
6. **前端渐进式升级**：可以先保留旧 Chat UI，逐步迁移

---

## 🎯 预期收益

1. **符合行业标准**：使用 AG-UI 协议，与主流生态兼容
2. **更强的交互能力**：Shared State + Generative UI + HITL
3. **跨平台部署**：同一 Agent 运行在 Web、Mobile、Slack
4. **更好的开发体验**：CopilotKit SDK 提供完整工具链
5. **更高的安全性**：HITL 确保关键操作需用户确认

---

## 📚 参考资源

- **AG-UI 协议**: https://github.com/ag-ui-protocol/ag-ui
- **CopilotKit 文档**: https://docs.copilotkit.ai
- **OpenAI Agents SDK**: https://github.com/openai/openai-agents-python
- **LangGraph**: https://langchain-ai.github.io/langgraph

# Session State Manager 开发手册

**日期**：2026-06-19  
**版本**：v2.0（重写版）  
**性质**：开发交付物 + E2E 验证一体

---

## 总览

本手册指导实现 **Session State Manager**，这是 ANIFORCE Agent 架构的核心抽象层。

### 核心理解

ANIFORCE 的 Agent 不是聊天机器人，而是驾驶舱里的自动驾驶员。用户和 Agent 协作完成长程业务任务，这个过程是结构化的：

- 按 **Act（幕）** 组织：每一幕对应一个完整业务动作
- 按 **Panel（投影面板）** 展示：五个维度投影业务状态
- 按 **HITL** 审批：关键操作需人工确认
- 按 **side_effect 事件** 同步：Agent 执行后发语义事件，前端响应投影

### Session State Manager 的职责

**不是**：
- ❌ 简单的 frontend → backend → agent-service 三层转发
- ❌ backend 只做 JWT 校验 + SSE 透传
- ❌ 存一个 session JSON 对象

**而是**：
- ✅ **业务上下文抽象层**：从分散的 DB 数据抽象出"当前任务上下文"
- ✅ **状态持久化**：不受 LLM 上下文限制，可无限增长
- ✅ **变更追踪**：记录所有业务变更，支持回滚
- ✅ **执行编排**：维护当前 phase、已完成 acts、待办 HITL
- ✅ **上下文注入**：把业务语义摘要注入到 Agent prompt
- ✅ **事件发射**：Agent 工具调用后发出语义事件（act.completed, budget.adjusted）

### 四层状态存储

| 层 | 名称 | 存储位置 | 特点 | 职责 |
|----|------|----------|------|------|
| Layer 0 | 权威业务数据 | backend DB | 已落库的事实，不可随意修改 | projects, campaigns, materials, performance |
| Layer 1 | Session State | backend（新增） | 不受 LLM 上下文限制，支持回滚 | 业务上下文摘要、变更历史、执行进度、对话摘要 |
| Layer 2 | LLM 对话缓存 | agent-service SQLiteSession | 有上下文窗口上限，需 compaction | 用户消息、Agent 回复、工具调用历史 |
| Layer 3 | 前端临时状态 | frontend | 刷新后可能丢失 | 当前 tab、选中实体、表单草稿 |

### 架构拓扑

```text
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (3010)                                                 │
│                                                                 │
│ Workspace 投影数据来源：                                         │
│   - 权威数据：backend API 返回的最新实体状态 (Layer 0)          │
│   - Agent 事件：side_effect 事件触发对应 Panel 刷新              │
│   - 本地草稿：frontend form state (Layer 3)                     │
│                                                                 │
│ 不需要在前端存完整业务状态，前端是投影，不是事实源               │
│ 打开任何 session，重新拉 Layer 0 + Layer 1 就能重建视图         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ POST /api/v1/agent/runs
                       │ { prompt, session_id, context_snapshot }
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Backend (8010) - Session State Manager                         │
│                                                                 │
│ 职责：                                                          │
│   ① 校验：JWT → current_user                                   │
│   ② 上下文管理：                                                │
│      - 接收 frontend context_snapshot (Layer 3)                │
│      - 从 DB 抽取业务上下文 (Layer 0)                           │
│      - 维护 Session State (Layer 1)：                           │
│        · execution progress (当前 phase、已完成 acts)            │
│        · changelog (变更历史，支持回滚)                          │
│        · conversation_summary (对话摘要，compaction 结果)        │
│        · ui_snapshot (前端状态快照)                              │
│   ③ 上下文注入：构建业务语义摘要，传给 agent-service             │
│   ④ SSE 透传：不缓冲，直接回 frontend                           │
│   ⑤ 状态更新：Agent 工具调用后更新 Layer 0 + Layer 1            │
│   ⑥ 事件发射：发 side_effect 语义事件给前端                     │
│                                                                 │
│ 这不是简单 proxy，这是业务上下文的抽象层和状态管理者             │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ POST /api/agent/runs
                       │ { prompt, session_id, jwt, business_context }
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Agent Service (8020)                                            │
│                                                                 │
│ 每轮执行上下文构建：                                             │
│   system_prompt (能力描述)                                      │
│   + business_context (从 Layer 1，backend 传入)                │
│   + 近 N 轮对话历史 (从 Layer 2，SQLiteSession)                 │
│   + 用户消息                                                    │
│                                                                 │
│ SQLiteSession 只存对话历史，不存业务状态                         │
│ 超出上限时 compaction：把旧对话压缩成摘要存回 Layer 1             │
│                                                                 │
│ 工具调用：MCP → backend REST → backend 更新 DB + Session State  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Block 清单

| Block | 交付物 | 验证脚本 | 状态 |
|-------|--------|----------|------|
| 1 | Session State Model + Repository | `backend/tests/e2e/block1_session_state.py` | 待开发 |
| 2 | Business Context Abstraction | `backend/tests/e2e/block2_context_abstraction.py` | 待开发 |
| 3 | Backend Agent Gateway + Context Injection | `backend/tests/e2e/block3_agent_gateway.py` | 待开发 |
| 4 | context_snapshot 定义与传输 | `backend/tests/e2e/block4_context_snapshot.py` | 待开发 |
| 5 | Side Effect 语义事件系统 | `backend/tests/e2e/block5_side_effects.py` | 待开发 |
| 6 | LLM Context Compaction | `backend/tests/e2e/block6_compaction.py` | 待开发 |
| 7 | Frontend 完整集成 | `backend/tests/e2e/block7_frontend_integration.py` | 待开发 |

---

## Block 1: Session State Model + Repository

### 目标

实现 Layer 1（Session State）的数据模型和存储层。Session State 是业务上下文的持久化抽象，不受 LLM 上下文限制。

### 核心设计

**Session State 不是简单的 JSON 存储，而是有结构的业务上下文抽象**：

```python
class BusinessContext:
    """当前 session 关联的业务实体（从 Layer 0 抽取）"""
    project_id: Optional[str]
    campaign_ids: list[str]
    material_ids: list[str]
    
    # 实体状态快照（不是完整数据，是摘要）
    active_entities: dict[str, Any]  # {project: {id, name, budget, status}, campaigns: [...]}

class ExecutionState:
    """Agent 执行进度（编排状态）"""
    current_phase: Optional[str]      # "project_creation" | "campaign_creation" | "budget_adjustment"
    completed_phases: list[str]        # 已完成阶段
    pending_hitl: list[dict]           # 待确认操作：[{operation_id, type, detail}]

class ChangelogEntry:
    """变更记录（支持回滚）"""
    entity_type: str                   # "campaign" | "project" | "material"
    entity_id: str
    field: str                         # "budget" | "status" | "name"
    old_value: Any
    new_value: Any
    timestamp: datetime
    rollbackable: bool                 # 是否可回滚
    act_id: Optional[str]              # 关联的 Act ID（语义标记）

class SessionState:
    """Session State（Layer 1）完整结构"""
    session_id: str
    user_id: str
    
    # 业务上下文
    context: BusinessContext
    
    # 执行状态
    execution: ExecutionState
    
    # 变更历史
    changelog: list[ChangelogEntry]
    
    # 对话摘要（compaction 结果）
    conversation_summary: Optional[str]
    
    # 前端状态快照
    ui_snapshot: Optional[dict]
    
    created_at: datetime
    updated_at: datetime
```

### 数据库设计

**表：session_states**

```sql
CREATE TABLE IF NOT EXISTS session_states (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    
    -- 业务上下文（JSON）
    context_json TEXT NOT NULL DEFAULT '{}',
    
    -- 执行状态（JSON）
    execution_json TEXT NOT NULL DEFAULT '{}',
    
    -- 变更历史（JSON array）
    changelog_json TEXT NOT NULL DEFAULT '[]',
    
    -- 对话摘要（compaction 结果）
    conversation_summary TEXT,
    
    -- 前端状态快照（JSON）
    ui_snapshot_json TEXT,
    
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_session_states_user_id ON session_states(user_id);
CREATE INDEX IF NOT EXISTS idx_session_states_updated_at ON session_states(updated_at);
```

### 新增文件

```
backend/app/models/session_state.py          ← SessionState pydantic 模型
backend/app/repositories/session_state_repo.py ← Repository CRUD
backend/tests/e2e/block1_session_state.py    ← 测试脚本
```

### SessionState Model 实现要点

```python
# backend/app/models/session_state.py

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class BusinessContext(BaseModel):
    """业务上下文：当前 session 关联的实体"""
    project_id: Optional[str] = None
    campaign_ids: list[str] = Field(default_factory=list)
    material_ids: list[str] = Field(default_factory=list)
    active_entities: dict[str, Any] = Field(default_factory=dict)


class ExecutionState(BaseModel):
    """执行状态：Agent 编排进度"""
    current_phase: Optional[str] = None
    completed_phases: list[str] = Field(default_factory=list)
    pending_hitl: list[dict] = Field(default_factory=list)


class ChangelogEntry(BaseModel):
    """变更记录"""
    entity_type: str
    entity_id: str
    field: str
    old_value: Any
    new_value: Any
    timestamp: str
    rollbackable: bool = True
    act_id: Optional[str] = None


class SessionState(BaseModel):
    """Session State（Layer 1）"""
    session_id: str
    user_id: str
    context: BusinessContext = Field(default_factory=BusinessContext)
    execution: ExecutionState = Field(default_factory=ExecutionState)
    changelog: list[ChangelogEntry] = Field(default_factory=list)
    conversation_summary: Optional[str] = None
    ui_snapshot: Optional[dict] = None
    created_at: str
    updated_at: str
```

### Repository 实现要点

```python
# backend/app/repositories/session_state_repo.py

import json
import sqlite3
from datetime import datetime
from typing import Optional
from app.models.session_state import SessionState


class SessionStateRepository:
    """Session State Repository（Layer 1 存储）"""
    
    def __init__(self, db_path: str = "backend/data/sqlite/animagus.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化表"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_states (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                context_json TEXT NOT NULL DEFAULT '{}',
                execution_json TEXT NOT NULL DEFAULT '{}',
                changelog_json TEXT NOT NULL DEFAULT '[]',
                conversation_summary TEXT,
                ui_snapshot_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session_states_user_id ON session_states(user_id)")
        conn.commit()
        conn.close()
    
    def create(self, state: SessionState) -> SessionState:
        """创建 session state"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO session_states 
            (session_id, user_id, context_json, execution_json, changelog_json, 
             conversation_summary, ui_snapshot_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            state.session_id,
            state.user_id,
            json.dumps(state.context.model_dump()),
            json.dumps(state.execution.model_dump()),
            json.dumps([e.model_dump() for e in state.changelog]),
            state.conversation_summary,
            json.dumps(state.ui_snapshot) if state.ui_snapshot else None,
            state.created_at,
            state.updated_at,
        ))
        conn.commit()
        conn.close()
        return state
    
    def get(self, session_id: str, user_id: str) -> Optional[SessionState]:
        """查询 session state（多租户隔离）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM session_states WHERE session_id = ? AND user_id = ?",
            (session_id, user_id)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_state(row)
    
    def update(self, state: SessionState) -> SessionState:
        """更新 session state"""
        state.updated_at = datetime.utcnow().isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE session_states
            SET context_json = ?, execution_json = ?, changelog_json = ?,
                conversation_summary = ?, ui_snapshot_json = ?, updated_at = ?
            WHERE session_id = ? AND user_id = ?
        """, (
            json.dumps(state.context.model_dump()),
            json.dumps(state.execution.model_dump()),
            json.dumps([e.model_dump() for e in state.changelog]),
            state.conversation_summary,
            json.dumps(state.ui_snapshot) if state.ui_snapshot else None,
            state.updated_at,
            state.session_id,
            state.user_id,
        ))
        conn.commit()
        conn.close()
        return state
    
    def _row_to_state(self, row: sqlite3.Row) -> SessionState:
        """数据库行转 SessionState"""
        from app.models.session_state import BusinessContext, ExecutionState, ChangelogEntry
        return SessionState(
            session_id=row["session_id"],
            user_id=row["user_id"],
            context=BusinessContext(**json.loads(row["context_json"])),
            execution=ExecutionState(**json.loads(row["execution_json"])),
            changelog=[ChangelogEntry(**e) for e in json.loads(row["changelog_json"])],
            conversation_summary=row["conversation_summary"],
            ui_snapshot=json.loads(row["ui_snapshot_json"]) if row["ui_snapshot_json"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
```

### 验证点

**测试脚本要验证**：

1. 创建 session state 成功
2. 按 session_id + user_id 查询成功
3. 更新 context.project_id 后查询正确
4. 追加 changelog 条目正确
5. 跨用户查询返回 None（多租户隔离）
6. 更新 conversation_summary 正确
7. 更新 ui_snapshot 正确
8. execution.current_phase 更新正确
9. execution.completed_phases 追加正确
10. execution.pending_hitl 更新正确

### 执行

```bash
# 运行测试
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block1_session_state.py

# 预期输出
✓ 1/10 创建 session state
✓ 2/10 查询 session state
✓ 3/10 更新 project_id
✓ 4/10 追加 changelog
✓ 5/10 跨用户隔离
✓ 6/10 更新 conversation_summary
✓ 7/10 更新 ui_snapshot
✓ 8/10 更新 current_phase
✓ 9/10 追加 completed_phases
✓ 10/10 更新 pending_hitl

Block 1: Session State Model + Repository ✓ 10/10
```

---

## Block 2: Business Context Abstraction

### 目标

实现业务上下文抽象逻辑：从分散的 DB 数据（Layer 0）抽取当前任务的业务语义摘要，存入 Session State（Layer 1）。

这是 Session State Manager 的核心能力：**不是简单存数据，而是抽象业务语义**。

### 核心理解

Agent 需要的不是原始数据，而是业务语义：

**错误示例**（数据堆砌）：
```
当前有 2 个 campaign：
- f2ea0073-b563-416d-bff7-55afa4c3cfb7, 计划 A, Meta, 5000, RUNNING
- 302e4871-ebdc-4870-9289-c74972787c46, 计划 B, Google, 3000, RUNNING
```

**正确示例**（业务语义）：
```
当前工作现场：
- 你在协助 PM 优化一个 RPG 项目的投放预算
- 项目"LongTaskDemo"总预算 ¥50,000，已消耗 ¥7,770
- 有 2 个投放计划：
  · 计划 A（Meta，预算 ¥5,000，已花 ¥4,860）- ROI 1.85，效率偏低
  · 计划 B（Google，预算 ¥3,000，已花 ¥2,910）- ROI 3.42，效率优秀
- 当前阶段：预算调整（刚完成投放数据分析）
- PM 当前在"预算"面板，可能要调整分配
```

### Business Context Abstractor 设计

```python
class BusinessContextAbstractor:
    """业务上下文抽象器：从 Layer 0 抽取业务语义"""
    
    def __init__(self, project_repo, campaign_repo, material_repo):
        self.project_repo = project_repo
        self.campaign_repo = campaign_repo
        self.material_repo = material_repo
    
    async def abstract_context(
        self,
        session_state: SessionState,
        user_id: str
    ) -> str:
        """
        从 session_state.context 的关联 ID，查询 DB（Layer 0），
        抽象成业务语义文本。
        
        返回：给 Agent 的业务上下文摘要（Markdown 格式）
        """
        lines = ["# 当前工作现场\n"]
        
        # 1. 项目上下文
        if session_state.context.project_id:
            project = await self.project_repo.get(session_state.context.project_id, user_id)
            if project:
                lines.append(f"## 项目：{project.name}")
                lines.append(f"- 类型：{project.game_type}")
                lines.append(f"- 目标市场：{project.target_market}")
                lines.append(f"- 总预算：¥{project.total_budget:,}")
                lines.append(f"- 已消耗：¥{project.spent:,}")
                lines.append(f"- 状态：{project.status}")
                lines.append("")
        
        # 2. 广告计划上下文
        if session_state.context.campaign_ids:
            campaigns = []
            for cid in session_state.context.campaign_ids:
                c = await self.campaign_repo.get(cid, user_id)
                if c:
                    campaigns.append(c)
            
            if campaigns:
                lines.append(f"## 广告计划（{len(campaigns)} 个）\n")
                for c in campaigns:
                    budget_used = (c.spent / c.budget * 100) if c.budget > 0 else 0
                    lines.append(f"### {c.name}")
                    lines.append(f"- 平台：{c.platform}")
                    lines.append(f"- 预算：¥{c.budget:,}（已用 {budget_used:.1f}%）")
                    lines.append(f"- 状态：{c.status}")
                    lines.append("")
        
        # 3. 素材上下文
        if session_state.context.material_ids:
            materials = []
            for mid in session_state.context.material_ids:
                m = await self.material_repo.get(mid, user_id)
                if m:
                    materials.append(m)
            
            if materials:
                lines.append(f"## 素材（{len(materials)} 个）\n")
                by_type = {}
                for m in materials:
                    by_type.setdefault(m.type, []).append(m)
                for mtype, mlist in by_type.items():
                    lines.append(f"- {mtype}：{len(mlist)} 个")
                lines.append("")
        
        # 4. 执行状态
        if session_state.execution.current_phase:
            lines.append(f"## 当前阶段\n")
            lines.append(f"**{session_state.execution.current_phase}**")
            if session_state.execution.completed_phases:
                lines.append(f"\n已完成：{', '.join(session_state.execution.completed_phases)}")
            lines.append("")
        
        # 5. 待确认操作
        if session_state.execution.pending_hitl:
            lines.append(f"## 待确认操作（{len(session_state.execution.pending_hitl)} 项）\n")
            for hitl in session_state.execution.pending_hitl:
                lines.append(f"- {hitl.get('type')}: {hitl.get('detail')}")
            lines.append("")
        
        # 6. 最近变更
        if session_state.changelog:
            recent = session_state.changelog[-3:]  # 最近 3 条
            lines.append(f"## 最近变更\n")
            for entry in recent:
                lines.append(f"- {entry.entity_type} `{entry.field}`: {entry.old_value} → {entry.new_value}")
            lines.append("")
        
        # 7. 对话摘要（如有 compaction）
        if session_state.conversation_summary:
            lines.append(f"## 对话摘要\n")
            lines.append(session_state.conversation_summary)
            lines.append("")
        
        # 8. 前端状态
        if session_state.ui_snapshot:
            lines.append(f"## 用户当前状态\n")
            if "route" in session_state.ui_snapshot:
                lines.append(f"- 页面：{session_state.ui_snapshot['route']}")
            if "workspace_tab" in session_state.ui_snapshot:
                lines.append(f"- 工作区 Tab：{session_state.ui_snapshot['workspace_tab']}")
            if "draft_edits" in session_state.ui_snapshot and session_state.ui_snapshot["draft_edits"]:
                lines.append(f"- 未保存草稿：{len(session_state.ui_snapshot['draft_edits'])} 项")
            lines.append("")
        
        return "\n".join(lines)
```

### 新增文件

```
backend/app/services/context_abstractor.py   ← 业务上下文抽象器
backend/tests/e2e/block2_context_abstraction.py ← 测试脚本
```

### 验证点

**测试脚本要验证**：

1. 空 session_state 抽象结果正确
2. 只有 project_id 时抽象结果包含项目信息
3. 有 project + campaigns 时抽象结果包含计划列表
4. 有 materials 时抽象结果包含素材统计
5. 有 current_phase 时抽象结果包含当前阶段
6. 有 pending_hitl 时抽象结果包含待确认操作
7. 有 changelog 时抽象结果包含最近变更
8. 有 conversation_summary 时抽象结果包含对话摘要
9. 有 ui_snapshot 时抽象结果包含前端状态
10. 综合场景：完整的业务上下文抽象（项目+计划+素材+执行状态）

### 执行

```bash
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block2_context_abstraction.py

# 预期输出
✓ 1/10 空 session_state
✓ 2/10 只有 project
✓ 3/10 project + campaigns
✓ 4/10 materials
✓ 5/10 current_phase
✓ 6/10 pending_hitl
✓ 7/10 changelog
✓ 8/10 conversation_summary
✓ 9/10 ui_snapshot
✓ 10/10 综合场景

Block 2: Business Context Abstraction ✓ 10/10

示例输出（综合场景）：
# 当前工作现场

## 项目：LongTaskDemo
- 类型：RPG
- 目标市场：全球
- 总预算：¥50,000
- 已消耗：¥7,770
- 状态：active

## 广告计划（2 个）

### 计划 A · 夏季促销
- 平台：Meta
- 预算：¥5,000（已用 97.2%）
- 状态：RUNNING

### 计划 B · 品牌词
- 平台：Google
- 预算：¥3,000（已用 97.0%）
- 状态：RUNNING

## 素材（5 个）

- image：3 个
- copy：2 个

## 当前阶段

**budget_adjustment**

已完成：project_creation, campaign_creation, material_generation, data_analysis

## 最近变更

- campaign `budget`: 5000 → 4000
- campaign `budget`: 3000 → 4000

## 对话摘要

用户创建了 RPG 项目 LongTaskDemo，配置了 Meta 和 Google 两个计划，生成了 AI 素材，投放 7 天后分析了数据，发现 Google ROI 更高，正在调整预算分配。

## 用户当前状态

- 页面：/projects/6c0ad836-e32c-4075-91c5-3c72691c0de8
- 工作区 Tab：budget
```

---

## Block 3: Backend Agent Gateway + Context Injection

### 目标

在 backend 实现 Agent Gateway 路由，作为 frontend 和 agent-service 之间的 **业务上下文管理层**（不是简单 proxy）。

核心职责：
1. JWT 校验
2. Session State 维护（Layer 1）
3. 业务上下文注入到 Agent prompt
4. SSE 透传（不缓冲）
5. 响应 agent-service 返回，更新 Session State

### 架构理解

**错误理解**：backend 只是转发 + JWT 校验
```
frontend → backend (JWT校验) → agent-service (直接转发参数)
```

**正确理解**：backend 是业务上下文管理者
```
frontend → backend:
  ① 校验 JWT
  ② 查询/创建 Session State (Layer 1)
  ③ 抽象业务上下文（从 Layer 0 + Layer 1）
  ④ 构建 business_context_summary
  ⑤ 转发给 agent-service: {prompt, session_id, jwt, business_context}
  
agent-service:
  ① 从 backend 接收 business_context
  ② 注入到 system prompt
  ③ 从 SQLiteSession 读取近 N 轮对话（Layer 2）
  ④ 构建完整 prompt 执行
  ⑤ SSE 流式返回

backend:
  ① SSE 透传回 frontend
  ② 监听 agent 工具调用事件，更新 Session State
```

### 新增路由

```
POST /api/v1/agent/sessions          → 创建 session（backend + agent-service 同步创建）
GET  /api/v1/agent/sessions          → 列出 session
POST /api/v1/agent/sessions/{id}/archive → 归档 session
POST /api/v1/agent/runs              → 执行 Agent（SSE）
GET  /api/v1/agent/health            → 健康检查（转发 agent-service）
```

### 新增文件

```
backend/app/api/v1/agent_routes.py        ← Agent Gateway 路由
backend/app/services/agent_gateway.py     ← agent-service HTTP 客户端
backend/app/api/v1/router.py              ← 修改：注册 agent 路由
backend/tests/e2e/block3_agent_gateway.py ← 测试脚本
```

### Agent Gateway 实现要点

```python
# backend/app/services/agent_gateway.py

import httpx
from typing import AsyncGenerator


class AgentGatewayService:
    """Agent Gateway：连接 agent-service"""
    
    def __init__(self, agent_service_url: str = "http://127.0.0.1:8020"):
        self.base_url = agent_service_url
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def create_session(self, jwt: str, title: str = "新对话") -> dict:
        """创建 session（转发到 agent-service）"""
        resp = await self.client.post(
            f"{self.base_url}/api/agent/sessions",
            json={"title": title},
            headers={"Authorization": f"Bearer {jwt}"},
        )
        resp.raise_for_status()
        return resp.json()
    
    async def list_sessions(self, jwt: str) -> list[dict]:
        """列出 session（转发到 agent-service）"""
        resp = await self.client.get(
            f"{self.base_url}/api/agent/sessions",
            headers={"Authorization": f"Bearer {jwt}"},
        )
        resp.raise_for_status()
        return resp.json()
    
    async def stream_run(
        self,
        jwt: str,
        prompt: str,
        session_id: str,
        business_context: str,  # ← 关键：业务上下文注入
    ) -> AsyncGenerator[bytes, None]:
        """
        流式执行 Agent（SSE）
        
        不是简单转发 prompt，而是附带 business_context
        """
        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/agent/runs",
            json={
                "prompt": prompt,
                "session_id": session_id,
                "business_context": business_context,  # ← 注入
            },
            headers={
                "Authorization": f"Bearer {jwt}",
                "Accept": "text/event-stream",
            },
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk
```

```python
# backend/app/api/v1/agent_routes.py

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from app.api.deps import get_current_user
from app.services.agent_gateway import AgentGatewayService
from app.services.context_abstractor import BusinessContextAbstractor
from app.repositories.session_state_repo import SessionStateRepository

router = APIRouter(prefix="/agent", tags=["agent"])


def get_gateway() -> AgentGatewayService:
    return AgentGatewayService()


def get_context_abstractor() -> BusinessContextAbstractor:
    # 注入各 repo
    from app.repositories.factory import get_project_repo, get_campaign_repo, get_material_repo
    return BusinessContextAbstractor(
        project_repo=get_project_repo(),
        campaign_repo=get_campaign_repo(),
        material_repo=get_material_repo(),
    )


def get_session_state_repo() -> SessionStateRepository:
    return SessionStateRepository()


@router.post("/sessions")
async def create_session(
    user: dict = Depends(get_current_user),
    gateway: AgentGatewayService = Depends(get_gateway),
    state_repo: SessionStateRepository = Depends(get_session_state_repo),
):
    """创建 session（backend + agent-service 同步）"""
    from app.models.session_state import SessionState
    from datetime import datetime
    
    # 1. 在 agent-service 创建 session
    jwt = user.get("token") or ""
    agent_session = await gateway.create_session(jwt, title="新对话")
    
    # 2. 在 backend 创建 Session State（Layer 1）
    session_state = SessionState(
        session_id=agent_session["session_id"],
        user_id=user["id"],
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )
    state_repo.create(session_state)
    
    return {"session_id": agent_session["session_id"], "title": agent_session["title"]}


@router.get("/sessions")
async def list_sessions(
    user: dict = Depends(get_current_user),
    gateway: AgentGatewayService = Depends(get_gateway),
):
    """列出 session（转发到 agent-service）"""
    jwt = user.get("token") or ""
    return await gateway.list_sessions(jwt)


@router.post("/runs")
async def run_agent(
    request: Request,
    user: dict = Depends(get_current_user),
    gateway: AgentGatewayService = Depends(get_gateway),
    abstractor: BusinessContextAbstractor = Depends(get_context_abstractor),
    state_repo: SessionStateRepository = Depends(get_session_state_repo),
):
    """
    流式执行 Agent（SSE）
    
    核心流程：
    1. 接收 frontend 请求
    2. 查询/更新 Session State（Layer 1）
    3. 抽象业务上下文
    4. 转发给 agent-service（附带 business_context）
    5. SSE 透传回 frontend
    """
    body = await request.json()
    prompt = body.get("prompt", "")
    session_id = body.get("session_id")
    
    # 1. 查询 Session State（Layer 1）
    session_state = state_repo.get(session_id, user["id"])
    if not session_state:
        from app.models.session_state import SessionState
        from datetime import datetime
        session_state = SessionState(
            session_id=session_id,
            user_id=user["id"],
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        state_repo.create(session_state)
    
    # 2. 抽象业务上下文（从 Layer 0 + Layer 1）
    business_context = await abstractor.abstract_context(session_state, user["id"])
    
    # 3. 转发给 agent-service（注入 business_context）
    jwt = user.get("token") or ""
    
    async def stream_generator():
        async for chunk in gateway.stream_run(jwt, prompt, session_id, business_context):
            yield chunk
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )
```

### agent-service 修改

**agent-service 需要接收 business_context 并注入到 prompt**：

```python
# aniforce-agent/app/api/runs.py

@router.post("")
async def run_agent(request: Request, ...):
    body = await request.json()
    prompt = body.get("prompt", "")
    session_id = body.get("session_id")
    business_context = body.get("business_context", "")  # ← 新增
    
    # 构建 system prompt（注入业务上下文）
    system_prompt_parts = [
        "你是 ANIFORCE 的 AI 助手，协助用户管理广告投放任务。",
    ]
    
    if business_context:
        system_prompt_parts.append("\n---\n")
        system_prompt_parts.append(business_context)  # ← 注入
    
    system_prompt = "\n".join(system_prompt_parts)
    
    # 执行 Agent...
```

### 验证点

**测试脚本要验证**：

1. 创建 session 成功（backend + agent-service 同步）
2. 列出 session 包含刚创建的
3. POST /runs 返回 SSE 流
4. SSE 流中包含 message.updated 事件
5. Agent 执行时能看到 business_context（通过工具调用验证）
6. 跨用户 session 访问返回 404
7. Session State（Layer 1）正确创建
8. 业务上下文注入到 Agent prompt 成功
9. SSE 流正确透传（不缓冲）
10. 多轮对话 session_id 复用正确

### 执行

```bash
# 先启动 agent-service
cd aniforce-agent && ./start_dev.sh

# 再启动 backend
cd backend && UV_CACHE_DIR=./uv_cache uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 &

# 运行测试
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block3_agent_gateway.py

# 预期输出
✓ 1/10 创建 session
✓ 2/10 列出 session
✓ 3/10 POST /runs SSE
✓ 4/10 SSE message.updated
✓ 5/10 Agent 看到 business_context
✓ 6/10 跨用户隔离
✓ 7/10 Session State 创建
✓ 8/10 业务上下文注入
✓ 9/10 SSE 透传
✓ 10/10 多轮对话

Block 3: Backend Agent Gateway + Context Injection ✓ 10/10
```

---

## Block 4: context_snapshot 定义与传输

### 目标

定义前端 context_snapshot 协议，前端发消息时携带当前 UI 状态（Layer 3），backend 合并到 Session State（Layer 1）的 ui_snapshot 字段。

### context_snapshot 协议

```typescript
// frontend/packages/main-app/src/types/agent.ts

interface AgentContextSnapshot {
  route: string                      // 当前路由，如 "/projects/xxx"
  workspace_tab: string              // 当前 tab：context | creative | analysis | budget | audit
  active_project_id: string | null
  active_campaign_id: string | null
  selected_entities: Array<{
    type: "project" | "campaign" | "material"
    id: string
    name: string
  }>
  draft_edits: Record<string, {      // key = entity_type:entity_id:field
    entity_type: string
    entity_id: string
    field: string
    old_value: any
    new_value: any
    saved: boolean
  }>
  recent_ui_events: Array<{          // 最近几个关键 UI 事件
    type: string                     // "tab_switched" | "entity_selected" | "edit_started"
    payload: Record<string, any>
    timestamp: number
  }>
}
```

### 数据流

```
1. 前端用户点击"发送消息"
2. 收集当前 UI 状态 → context_snapshot
3. POST /api/v1/agent/runs { prompt, session_id, context_snapshot }
4. backend 接收 → 更新 session_state.ui_snapshot
5. backend 抽象业务上下文时，包含 ui_snapshot 信息
6. Agent 执行时能看到"用户当前在预算面板，正在编辑 campaign A 的预算"
```

### 新增文件

```
frontend/packages/main-app/src/types/agent.ts      ← context_snapshot 类型定义
frontend/packages/main-app/src/composables/useHomeAgentSession.ts ← 修改：收集 context_snapshot
backend/app/api/v1/agent_routes.py                 ← 修改：接收 context_snapshot
backend/tests/e2e/block4_context_snapshot.py       ← 测试脚本
```

### Frontend 实现要点

```typescript
// frontend/packages/main-app/src/composables/useHomeAgentSession.ts

export function useHomeAgentSession() {
  const router = useRouter()
  const route = useRoute()
  
  function collectContextSnapshot(): AgentContextSnapshot {
    return {
      route: route.path,
      workspace_tab: currentTab.value || 'context',
      active_project_id: activeProjectId.value,
      active_campaign_id: activeCampaignId.value,
      selected_entities: selectedEntities.value.map(e => ({
        type: e.type,
        id: e.id,
        name: e.name,
      })),
      draft_edits: Object.fromEntries(
        Object.entries(draftEdits.value).map(([key, edit]) => [
          key,
          {
            entity_type: edit.entity_type,
            entity_id: edit.entity_id,
            field: edit.field,
            old_value: edit.old_value,
            new_value: edit.new_value,
            saved: false,
          },
        ])
      ),
      recent_ui_events: recentEvents.value.slice(-5),
    }
  }
  
  async function send(message: string) {
    const context_snapshot = collectContextSnapshot()
    
    // 调用 backend agent API（不再直连 agent-service）
    for await (const event of streamAgentMessage(
      currentSessionId.value,
      message,
      'conversation',
      context_snapshot  // ← 传递
    )) {
      handleEvent(event)
    }
  }
  
  return { send, ... }
}
```

```typescript
// frontend/packages/main-app/src/api/agent.ts

export async function* streamAgentMessage(
  sessionId: string,
  message: string,
  taskType = 'conversation',
  contextSnapshot?: AgentContextSnapshot  // ← 新增参数
): AsyncGenerator<AgentStreamEvent, void, unknown> {
  const token = localStorage.getItem('animagus_token')
  const response = await fetch('/api/v1/agent/runs', {  // ← 改为 backend
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : ),
    },
    body: JSON.stringify({
      prompt: message,
      session_id: sessionId,
      task_type: taskType,
      context_snapshot: contextSnapshot,  // ← 传递
    }),
  })
  // ...
}
```

### Backend 实现要点

```python
# backend/app/api/v1/agent_routes.py

@router.post("/runs")
async def run_agent(
    request: Request,
    user: dict = Depends(get_current_user),
    gateway: AgentGatewayService = Depends(get_gateway),
    abstractor: BusinessContextAbstractor = Depends(get_context_abstractor),
    state_repo: SessionStateRepository = Depends(get_session_state_repo),
):
    body = await request.json()
    prompt = body.get("prompt", "")
    session_id = body.get("session_id")
    context_snapshot = body.get("context_snapshot")  # ← 接收
    
    # 查询 Session State
    session_state = state_repo.get(session_id, user["id"])
    if not session_state:
        # 创建...
        pass
    
    # 更新 ui_snapshot（Layer 3 → Layer 1）
    if context_snapshot:
        session_state.ui_snapshot = context_snapshot
        state_repo.update(session_state)
    
    # 抽象业务上下文（包含 ui_snapshot 信息）
    business_context = await abstractor.abstract_context(session_state, user["id"])
    
    # 转发...
```

### 验证点

**测试脚本要验证**：

1. 前端发送消息带 context_snapshot
2. backend 正确接收 context_snapshot
3. Session State 的 ui_snapshot 字段正确更新
4. 业务上下文抽象包含 ui_snapshot 信息
5. Agent 能看到"用户当前在预算面板"
6. Agent 能看到"用户有未保存草稿"
7. 多次发送，ui_snapshot 正确更新
8. context_snapshot 为空时不报错
9. 前端切换 tab，下次发送的 context_snapshot 包含新 tab
10. 综合场景：完整的 context_snapshot 传输和使用

### 执行

```bash
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block4_context_snapshot.py

# 预期输出
✓ 1/10 发送带 context_snapshot
✓ 2/10 backend 接收
✓ 3/10 ui_snapshot 更新
✓ 4/10 业务上下文包含 ui_snapshot
✓ 5/10 Agent 看到当前面板
✓ 6/10 Agent 看到草稿
✓ 7/10 多次更新
✓ 8/10 空 context_snapshot
✓ 9/10 tab 切换
✓ 10/10 综合场景

Block 4: context_snapshot 定义与传输 ✓ 10/10
```

---

## Block 5: Side Effect 语义事件系统

### 目标

实现 side_effect 语义事件：Agent 通过 MCP 工具调用 backend REST 修改业务数据后，backend 发出 **语义事件**（不是 CRUD 通知），前端根据事件类型刷新对应 Panel。

### 核心理解

**错误示例**（CRUD 通知）：
```
event: data_changed
data: {type: "campaign.updated", id: "xxx", field: "budget", old: 5000, new: 4000}
```

**正确示例**（语义事件）：
```
event: side_effect
data: {
  type: "act.budget_adjusted",
  act_id: "act_9_budget_adjustment",
  panel: "budget",
  summary: "根据 ROI 分析，将 Meta 预算降低 1000，Google 预算提升 1000",
  entities_affected: [
    {type: "campaign", id: "xxx", name: "计划 A"},
    {type: "campaign", id: "yyy", name: "计划 B"}
  ],
  recommendation: {
    refresh_panels: ["budget", "context"],
    highlight_entities: ["xxx", "yyy"]
  }
}
```

### 事件类型设计

```python
# backend/app/models/side_effect.py

class SideEffectEvent(BaseModel):
    """Side Effect 语义事件"""
    type: str                          # "act.completed" | "act.budget_adjusted" | "act.campaign_launched"
    act_id: Optional[str]              # 关联的 Act ID
    panel: Optional[str]               # 推荐前端展示的 Panel：context | creative | analysis | budget | audit
    summary: str                       # 事件摘要（人类可读）
    entities_affected: list[dict]      # 受影响的实体
    recommendation: Optional[dict]     # 给前端的建议：refresh_panels, highlight_entities
    timestamp: str
```

### 实现要点

**backend 在处理 MCP 工具调用后，生成 side_effect 事件**：

```python
# backend/app/api/v1/campaigns.py

@router.post("")
async def create_campaign(
    payload: CampaignCreate,
    user: dict = Depends(get_current_user),
    repo: CampaignRepository = Depends(get_campaign_repo),
    state_repo: SessionStateRepository = Depends(get_session_state_repo),
    event_queue: SideEffectEventQueue = Depends(get_event_queue),  # ← 新增
):
    # 创建 campaign
    campaign = await repo.create(payload, user["id"])
    
    # 更新 Session State（Layer 1）
    session_id = request.state.current_session_id  # 从 context 获取
    if session_id:
        session_state = state_repo.get(session_id, user["id"])
        if session_state:
            # 追加到 context.campaign_ids
            if campaign.id not in session_state.context.campaign_ids:
                session_state.context.campaign_ids.append(campaign.id)
            
            # 追加到 changelog
            session_state.changelog.append(ChangelogEntry(
                entity_type="campaign",
                entity_id=campaign.id,
                field="created",
                old_value=None,
                new_value=campaign.name,
                timestamp=datetime.utcnow().isoformat(),
                rollbackable=False,
                act_id="act_2_campaign_creation",
            ))
            
            state_repo.update(session_state)
            
            # 发出 side_effect 事件
            event_queue.push(session_id, SideEffectEvent(
                type="act.campaign_created",
                act_id="act_2_campaign_creation",
                panel="context",
                summary=f"创建广告计划「{campaign.name}」({campaign.platform}，预算 ¥{campaign.budget:,})",
                entities_affected=[
                    {"type": "campaign", "id": campaign.id, "name": campaign.name}
                ],
                recommendation={
                    "refresh_panels": ["context"],
                    "highlight_entities": [campaign.id],
                },
                timestamp=datetime.utcnow().isoformat(),
            ))
    
    return campaign
```

**SSE 流中混入 side_effect 事件**：

```python
# backend/app/api/v1/agent_routes.py

@router.post("/runs")
async def run_agent(...):
    # ...
    
    async def stream_generator():
        # 转发 agent-service 的 SSE 流
        async for chunk in gateway.stream_run(jwt, prompt, session_id, business_context):
            yield chunk
        
        # SSE 流结束后，检查是否有 side_effect 事件
        event_queue = get_event_queue()
        events = event_queue.pop_all(session_id)
        for event in events:
            # 发送 side_effect 事件
            yield f"event: side_effect\n".encode()
            yield f"data: {event.model_dump_json()}\n\n".encode()
    
    return StreamingResponse(stream_generator(), media_type="text/event-stream")
```

### 前端处理

```typescript
// frontend/packages/main-app/src/composables/useHomeAgentSession.ts

function handleEvent(event: AgentStreamEvent) {
  if (event.event === 'side_effect') {
    const sideEffect = event.data as SideEffectEvent
    
    // 根据事件类型刷新对应 Panel
    if (sideEffect.recommendation?.refresh_panels) {
      for (const panel of sideEffect.recommendation.refresh_panels) {
        refreshPanel(panel)
      }
    }
    
    // 高亮受影响的实体
    if (sideEffect.recommendation?.highlight_entities) {
      highlightEntities(sideEffect.recommendation.highlight_entities)
    }
    
    // 推荐切换 Panel
    if (sideEffect.panel && autoSwitchPanel.value) {
      switchToPanel(sideEffect.panel)
    }
  }
}
```

### 验证点

1. Agent 创建 project 后发出 side_effect 事件
2. 事件类型为 "act.project_created"
3. 事件包含正确的 panel 推荐
4. 事件包含受影响的实体列表
5. Agent 创建 campaign 后发出 side_effect 事件
6. Agent 更新 budget 后发出 side_effect 事件
7. 前端收到 side_effect 后刷新对应 Panel
8. Session State changelog 正确记录变更
9. Session State context 正确更新关联实体
10. 综合场景：完整的 Act → side_effect → 前端刷新流程

### 执行

```bash
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block5_side_effects.py
```

---

## Block 6: LLM Context Compaction

### 目标

解决 LLM 上下文窗口限制：当 SQLiteSession（Layer 2）对话历史超过阈值时，压缩更早的对话为摘要，存入 Session State（Layer 1）的 conversation_summary，Agent 后续执行从摘要 + 最近对话构建上下文。

### Compaction 机制

```
Layer 2 (SQLiteSession) 对话历史：
  [消息 1-50]  ← 超出阈值

Compaction 后：
  Layer 1 (conversation_summary):
    "用户创建了 RPG 项目，配置了 2 个计划，生成了素材，完成了数据分析"
  
  Layer 2 (SQLiteSession):
    [消息 41-50]  ← 只保留最近 10 轮
```

### 一期简化方案

不做 LLM 摘要（成本高），用规则压缩：

```python
# backend/app/services/compaction_service.py

class CompactionService:
    """对话历史压缩服务"""
    
    MAX_MESSAGES = 50  # SQLiteSession 最多保留 50 条
    KEEP_RECENT = 10   # 压缩时保留最近 10 条
    
    async def check_and_compact(
        self,
        session_id: str,
        user_id: str,
        agent_gateway: AgentGatewayService,
        state_repo: SessionStateRepository,
    ):
        """检查并压缩对话历史"""
        # 1. 从 agent-service 查询消息数
        message_count = await agent_gateway.get_message_count(session_id)
        
        if message_count <= self.MAX_MESSAGES:
            return  # 无需压缩
        
        # 2. 获取所有消息
        messages = await agent_gateway.get_messages(session_id)
        
        # 3. 压缩规则摘要
        old_messages = messages[:-self.KEEP_RECENT]
        summary_parts = []
        
        # 统计关键动作
        actions = {"created_project": 0, "created_campaign": 0, "generated_material": 0}
        for msg in old_messages:
            if "create_project" in str(msg):
                actions["created_project"] += 1
            elif "create_campaign" in str(msg):
                actions["created_campaign"] += 1
            elif "generate_material" in str(msg):
                actions["generated_material"] += 1
        
        if actions["created_project"] > 0:
            summary_parts.append(f"创建了 {actions['created_project']} 个项目")
        if actions["created_campaign"] > 0:
            summary_parts.append(f"配置了 {actions['created_campaign']} 个广告计划")
        if actions["generated_material"] > 0:
            summary_parts.append(f"生成了 {actions['generated_material']} 批素材")
        
        summary = "用户和 Agent 完成了：" + "、".join(summary_parts) + "。"
        
        # 4. 存入 Session State
        session_state = state_repo.get(session_id, user_id)
        if session_state:
            session_state.conversation_summary = summary
            state_repo.update(session_state)
        
        # 5. 删除 agent-service 的旧消息
        await agent_gateway.delete_old_messages(session_id, keep_recent=self.KEEP_RECENT)
```

### 验证点

1. 对话历史超过 50 条时触发 compaction
2. conversation_summary 正确生成
3. SQLiteSession 只保留最近 10 条
4. Agent 后续执行能看到 conversation_summary
5. 压缩后 Agent 仍能理解之前的上下文
6. 多次压缩，summary 累积正确
7. 服务重启后 summary 仍在
8. 压缩不影响正在进行的对话
9. 压缩后 Session State 正确更新
10. 综合场景：长对话 compaction 全流程

### 执行

```bash
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block6_compaction.py
```

---

## Block 7: Frontend 完整集成

### 目标

前端收回直连 agent-service，改走 backend gateway。完成完整的前后端联调。

### 前端修改清单

```
1. vite.config.ts
   - 去掉 /api/agent → 8020 的代理
   - 所有 /api/* 统一走 backend:8010

2. src/api/agent.ts
   - streamAgentMessage 改为 POST /api/v1/agent/runs
   - createAgentSession 改为 POST /api/v1/agent/sessions
   - listAgentSessions 改为 GET /api/v1/agent/sessions

3. src/composables/useHomeAgentSession.ts
   - send() 方法收集 context_snapshot
   - SSE 事件处理新增 side_effect 分支
   - side_effect 事件触发对应 Panel 数据刷新
```

### 端到端验证剧本

```
1. 用户登录
2. 创建新 session
3. 发送消息："创建一个 RPG 游戏项目，总预算 50000"
   → SSE 返回 Agent 回复 + side_effect: act.project_created
   → Workspace context panel 显示新项目

4. 追问："为这个项目创建两个计划，Meta 5000，Google 3000"
   → Agent 调 MCP 工具 → backend 创建 campaign → side_effect: act.campaign_created
   → Workspace context panel 显示两个计划

5. 追问："把这两个计划状态改成 active"
   → Agent 调 MCP 工具 → backend 更新状态 → side_effect: act.campaign_launched
   → Workspace 显示新状态

6. 追问："总结一下我们完成了什么"
   → Agent 从 business_context 了解全局
   → 返回总结
```

### 执行

```bash
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block7_frontend_integration.py
```

---

## 文件清单

### 新增文件

```
backend/app/models/session_state.py              ← SessionState pydantic 模型
backend/app/models/side_effect.py                ← SideEffect 事件模型
backend/app/repositories/session_state_repo.py   ← Session State Repository
backend/app/services/context_abstractor.py       ← 业务上下文抽象器
backend/app/services/agent_gateway.py            ← agent-service HTTP 客户端
backend/app/services/compaction_service.py       ← 对话历史压缩服务
backend/app/services/side_effect_queue.py        ← Side Effect 事件队列
backend/app/api/v1/agent_routes.py               ← Agent Gateway 路由

backend/tests/e2e/block1_session_state.py
backend/tests/e2e/block2_context_abstraction.py
backend/tests/e2e/block3_agent_gateway.py
backend/tests/e2e/block4_context_snapshot.py
backend/tests/e2e/block5_side_effects.py
backend/tests/e2e/block6_compaction.py
backend/tests/e2e/block7_frontend_integration.py

frontend/packages/main-app/src/types/agent.ts    ← context_snapshot 类型定义
```

### 修改文件

```
backend/app/api/v1/router.py                     ← 注册 agent 路由
backend/app/api/v1/campaigns.py                  ← 发出 side_effect 事件
backend/app/api/v1/projects.py                   ← 发出 side_effect 事件
backend/app/api/v1/materials.py                  ← 发出 side_effect 事件

aniforce-agent/app/api/runs.py                   ← 接收 business_context 并注入 prompt

frontend/packages/main-app/vite.config.ts        ← 收回 /api/agent 代理
frontend/packages/main-app/src/api/agent.ts      ← 改走 /api/v1/agent/*
frontend/packages/main-app/src/composables/useHomeAgentSession.ts ← 收集 context_snapshot + 处理 side_effect
```

---

## 维护规则

### 1. 改一个 Block，测一个 Block

不积压未验证的改动。每个 Block 开发完成后立即运行对应测试脚本，确保通过后再进入下一个 Block。

### 2. 真实数据，不造假

- 使用 backend 真实 JWT
- 使用真实的 project/campaign/material 数据
- 不造假 side_effect 事件
- 不 mock agent-service 响应

### 3. 日志留底

每次测试输出到 `backend/logs/e2e_blockN_YYMMDD.log`，方便回溯。

### 4. 失败即停

Block N 失败不继续 N+1，先修 N。避免错误累积。

### 5. 手册同步

Block 完成后更新本手册 Block 清单的"状态"列。

### 6. 先确保服务运行

所有 Block 都依赖：
- agent-service 正常运行在 8020
- backend 正常运行在 8010（从 Block 3 开始）

### 7. Session State 是抽象层，不是 CRUD

开发时记住：
- Session State 不是简单存 JSON
- 要抽象业务语义，不是堆数据
- side_effect 是语义事件，不是 CRUD 通知
- business_context 是给 Agent 的业务摘要，不是原始数据

### 8. 前端是投影，不是事实源

- 前端不维护完整业务状态
- 前端响应 side_effect 事件刷新 Panel
- 打开 session 时重新拉取 Layer 0 + Layer 1 重建视图

---

## 开发流程

### Phase 1: 基础设施（Block 1-2）

```bash
# Block 1: Session State Model + Repository
cd backend
# 1. 创建 app/models/session_state.py
# 2. 创建 app/repositories/session_state_repo.py
# 3. 创建 tests/e2e/block1_session_state.py
# 4. 运行测试
UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block1_session_state.py

# Block 2: Business Context Abstraction
# 1. 创建 app/services/context_abstractor.py
# 2. 创建 tests/e2e/block2_context_abstraction.py
# 3. 运行测试
UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block2_context_abstraction.py
```

### Phase 2: Gateway + Context Injection（Block 3-4）

```bash
# Block 3: Backend Agent Gateway + Context Injection
# 1. 创建 app/services/agent_gateway.py
# 2. 创建 app/api/v1/agent_routes.py
# 3. 修改 app/api/v1/router.py 注册路由
# 4. 修改 aniforce-agent/app/api/runs.py 接收 business_context
# 5. 启动 agent-service: cd aniforce-agent && ./start_dev.sh
# 6. 启动 backend: UV_CACHE_DIR=./uv_cache uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
# 7. 创建 tests/e2e/block3_agent_gateway.py
# 8. 运行测试
UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block3_agent_gateway.py

# Block 4: context_snapshot
# 1. 创建 frontend/packages/main-app/src/types/agent.ts
# 2. 修改 frontend/packages/main-app/src/composables/useHomeAgentSession.ts
# 3. 修改 frontend/packages/main-app/src/api/agent.ts
# 4. 修改 backend/app/api/v1/agent_routes.py
# 5. 创建 tests/e2e/block4_context_snapshot.py
# 6. 运行测试
UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block4_context_snapshot.py
```

### Phase 3: Side Effect + Compaction（Block 5-6）

```bash
# Block 5: Side Effect Events
# 1. 创建 app/models/side_effect.py
# 2. 创建 app/services/side_effect_queue.py
# 3. 修改 app/api/v1/campaigns.py 发出事件
# 4. 修改 app/api/v1/projects.py 发出事件
# 5. 修改 app/api/v1/agent_routes.py SSE 混入事件
# 6. 修改 frontend useHomeAgentSession.ts 处理 side_effect
# 7. 创建 tests/e2e/block5_side_effects.py
# 8. 运行测试
UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block5_side_effects.py

# Block 6: Compaction
# 1. 创建 app/services/compaction_service.py
# 2. 修改 app/api/v1/agent_routes.py 每轮后检查 compaction
# 3. 创建 tests/e2e/block6_compaction.py
# 4. 运行测试
UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block6_compaction.py
```

### Phase 4: Frontend 完整集成（Block 7）

```bash
# Block 7: Frontend Integration
# 1. 修改 frontend/packages/main-app/vite.config.ts 去掉 /api/agent 代理
# 2. 修改 frontend/packages/main-app/src/api/agent.ts 改走 /api/v1/agent/*
# 3. 启动三端服务
# 4. 创建 tests/e2e/block7_frontend_integration.py
# 5. 运行测试（端到端场景）
UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block7_frontend_integration.py
```

---

## 关键设计决策回顾

### 决策 1: Session State 是抽象层

不是简单存 JSON，而是从 Layer 0 抽象业务语义，注入到 Layer 2（LLM 上下文）。

### 决策 2: Backend 是 Session State Manager

不是简单 proxy，而是业务上下文管理者：
- 接收 context_snapshot（Layer 3）
- 查询 DB（Layer 0）
- 维护 Session State（Layer 1）
- 抽象业务上下文注入 Agent prompt
- 发出 side_effect 语义事件

### 决策 3: side_effect 是语义事件

不是 CRUD 通知，而是 Act 级别的业务动作完成通知：
- `act.project_created`
- `act.campaign_launched`
- `act.budget_adjusted`

### 决策 4: LLM 上下文 compaction

SQLiteSession（Layer 2）只存对话历史，有上限。超限时压缩，摘要存 Layer 1。

### 决策 5: Frontend 是投影

不是事实源，响应 side_effect 刷新 Panel。打开 session 时从 Layer 0 + Layer 1 重建视图。

---

## FAQ

### Q1: 为什么不让 frontend 直连 agent-service？

A: 因为 agent-service 是内部服务，不应该暴露给前端。backend 拥有用户态、业务逻辑和状态管理职责。

### Q2: 为什么不把 Session State 存在 agent-service？

A: 因为 Session State 是业务上下文抽象，需要访问 Layer 0（backend DB）。agent-service 只负责 LLM 对话（Layer 2），不应该耦合业务逻辑。

### Q3: 为什么 side_effect 不直接是数据变更通知？

A: 因为前端需要的是"完成了什么业务动作"，不是"改了哪个字段"。语义事件让前端理解业务意图，做出正确的 UI 响应（刷新哪个 Panel、高亮哪些实体）。

### Q4: 为什么不用 LLM 做 compaction 摘要？

A: 一期用规则压缩，成本低、速度快、可控。二期可以引入 LLM 摘要，但要权衡成本和延迟。

### Q5: 如果 backend 和 agent-service 的 state 不一致怎么办？

A: Session State（Layer 1）是权威源。agent-service 的 SQLiteSession（Layer 2）只是对话缓存。如果不一致，以 Layer 1 为准，重新注入到 Agent prompt。

### Q6: context_snapshot 会不会太大？

A: 只传必要字段：route, tab, selected_entities, draft_edits。不传完整实体数据。前端本地维护，按需发送。

### Q7: 如何支持回滚？

A: Session State 的 changelog 记录了所有变更，标记 rollbackable。回滚时反向应用 changelog，更新 Layer 0 和 Layer 1。

### Q8: 如何支持多人协作？

A: Session State 是 user_id + session_id 隔离的。多人协作需要引入 workspace 概念，不同用户共享同一个 workspace 的 Session State。（二期需求）

---

## 结论

Session State Manager 不是简单的三层转发，而是业务上下文的抽象层和状态管理者。它连接 Layer 0（权威数据）、Layer 1（业务上下文持久化）、Layer 2（LLM 对话缓存）、Layer 3（前端临时状态），为 Agent 提供结构化的业务语义，为前端提供 Act-driven 的投影数据。

开发时记住：**抽象业务语义，不是堆数据**。

---

# v2.1 补充：真实场景兼容与工程化设计

> 本节修正 v2.0 过度聚焦"结构化长程任务"的问题。真实产品不是只有 Act 1-10 的投放全流程，用户还会闲聊、查资料、试用素材生成、单点查询、中途切换目标、失败后恢复、跨页面继续工作。本系统必须以可扩展的 Session Runtime 兼容这些场景。

---

## 0. 真实场景分类与兼容原则

### 0.1 真实用户场景

| 场景 | 示例 | 是否需要 Act | 是否需要业务实体 | 是否产生 side_effect |
|---|---|---:|---:|---:|
| 闲聊探索 | "你能帮我做什么？" | 否 | 否 | 可选 recommendation |
| 产品/投放咨询 | "RPG 游戏适合投 Meta 还是 Google？" | 否 | 可选 | 可选 recommendation |
| 资料查询 | "帮我查一下上个月 Meta 花了多少钱" | 否 | 可选 | data.query_result |
| 单点生成 | "给我写 5 条 Facebook 广告文案" | 可选 | 可选 | content.generated |
| 结构化任务 | "创建项目、配计划、生成素材、上线" | 是 | 是 | act.* |
| 中途切换 | "先别建项目了，看看老项目 ROI" | 可变 | 可变 | mode.switched + data.* |
| 已有工作区继续 | "继续上次那个预算调整" | 是 | 是 | act.* |
| 回滚/重跑 | "撤回刚才预算调整，换个方案" | 是 | 是 | act.rolled_back / act.replayed |
| 体验型试用 | "生成几张素材看看效果" | 可选 | 可选 | content.preview_generated |
| 故障恢复 | "刚才断了，继续" | 是/否 | 可选 | runtime.resumed |

### 0.2 核心兼容原则

1. **不预设用户一定在完成长程任务**：默认是 `exploratory`，只有识别到明确业务目标时才进入结构化模式。
2. **Act 是可选编排单元，不是所有 session 都必须有 Act**。
3. **Panel 是投影建议，不是 Agent 控制 UI 的命令**。
4. **side_effect 是语义事件，不局限于 act.*，还包括 data.*、content.*、recommendation.*、runtime.*。**
5. **Session State 是可扩展 envelope，核心字段稳定，业务扩展放入 typed payload。**
6. **Agent 服务保持运行时纯粹：编排、工具、Skill、沙箱在 agent-service；业务事实和 Session State 在 backend。**

---

## 1. Session Runtime 抽象升级

### 1.1 Session Mode

新增 `SessionMode`，不要把所有会话都塞进结构化 Act：

```python
class SessionMode(str, Enum):
    EXPLORATORY = "exploratory"          # 闲聊、探索、问能做什么
    CONSULTATION = "consultation"        # 策略咨询、资料解释、建议
    QUICK_ACTION = "quick_action"        # 单点操作：查询、生成、修改
    STRUCTURED_TASK = "structured_task"  # 多步长程任务，有 Act/DAG
    RECOVERY = "recovery"                # 断线恢复、失败恢复、继续上次任务
```

### 1.2 Intent Recognition

每轮 run 前 backend 先做轻量 intent 判断；一期可以规则实现，二期可让 Agent 自判断并回写。

```python
class SessionIntent(BaseModel):
    mode: SessionMode
    intent_type: str                 # chat | query | generate | optimize | create | update | recover
    confidence: float
    target_entities: list[dict] = [] # 用户明确提到的 project/campaign/material
    suggested_panels: list[str] = [] # context/creative/analysis/budget/audit
    requires_business_context: bool = False
    requires_hitl: bool = False
```

规则示例：

```text
"你能做什么" / "介绍一下" → EXPLORATORY / chat
"查一下" / "多少" / "ROI" → QUICK_ACTION / query
"生成" / "写几条" / "素材" → QUICK_ACTION / generate
"创建项目" / "配计划" / "上线" → STRUCTURED_TASK / create
"继续" / "刚才" / "断了" → RECOVERY / recover
```

### 1.3 SessionState Schema 升级

Session State 必须支持多场景，而不是只支持项目/计划/素材。

```python
class SessionState(BaseModel):
    session_id: str
    user_id: str

    # 会话模式和意图
    mode: SessionMode = SessionMode.EXPLORATORY
    intent: Optional[SessionIntent] = None

    # Layer 1 业务上下文 envelope
    context: BusinessContext = Field(default_factory=BusinessContext)

    # 结构化任务才使用 execution；闲聊/查询可以为空
    execution: Optional[ExecutionState] = None

    # 变更历史和事件历史
    changelog: list[ChangelogEntry] = Field(default_factory=list)
    side_effect_log: list[SideEffectEvent] = Field(default_factory=list)

    # LLM 历史压缩摘要
    conversation_summary: Optional[str] = None

    # 前端临时状态快照
    ui_snapshot: Optional[dict] = None

    # 工程字段
    version: int = 1                  # 乐观锁
    status: str = "active"           # active/archived/recovering/error
    last_error: Optional[dict] = None
    created_at: str
    updated_at: str
```

### 1.4 BusinessContext 升级

```python
class BusinessContext(BaseModel):
    # 业务实体引用，不保存完整权威数据
    project_id: Optional[str] = None
    campaign_ids: list[str] = Field(default_factory=list)
    material_ids: list[str] = Field(default_factory=list)

    # 查询/分析型上下文
    query_context: dict = Field(default_factory=dict)
    # 例：{"time_range": "last_month", "platform": "Meta", "metrics": ["spend", "roi"]}

    # 生成型上下文
    generation_context: dict = Field(default_factory=dict)
    # 例：{"content_type": "ad_copy", "platform": "Facebook", "tone": "casual"}

    # 咨询型上下文
    consultation_context: dict = Field(default_factory=dict)
    # 例：{"topic": "channel_strategy", "game_type": "RPG", "market": "US"}

    # active_entities 是摘要缓存，不是事实源
    active_entities: dict = Field(default_factory=dict)
```

---

## 2. 多场景上下文构建策略

### 2.1 Context Abstractor 不再只有一种输出

`BusinessContextAbstractor` 需要按 `SessionMode + intent_type` 选择策略：

```python
class BusinessContextAbstractor:
    async def abstract_context(self, state: SessionState, user_id: str) -> BusinessContextSummary:
        if state.mode == SessionMode.EXPLORATORY:
            return await self._abstract_exploratory(state, user_id)
        if state.mode == SessionMode.CONSULTATION:
            return await self._abstract_consultation(state, user_id)
        if state.mode == SessionMode.QUICK_ACTION:
            return await self._abstract_quick_action(state, user_id)
        if state.mode == SessionMode.STRUCTURED_TASK:
            return await self._abstract_structured_task(state, user_id)
        if state.mode == SessionMode.RECOVERY:
            return await self._abstract_recovery(state, user_id)
```

### 2.2 输出不只是纯文本

```python
class BusinessContextSummary(BaseModel):
    mode: SessionMode
    text: str                         # 注入 Agent prompt 的文本摘要
    entity_refs: list[dict] = []       # project/campaign/material 引用
    constraints: list[str] = []        # 约束：预算不能超、写操作需 HITL
    recommended_tools: list[str] = []  # 可提示 Agent 优先用哪些工具
    recommended_skills: list[str] = [] # 可提示 Agent 加载哪些 Skill
    panel_hints: list[str] = []        # 给前端的投影建议
```

### 2.3 场景策略

#### 闲聊探索

```text
输入：用户问"你能做什么？"
上下文：
- 不强行关联项目
- 可读取用户最近活跃项目摘要，但不塞完整数据
- 推荐能力范围：建项目、配计划、生素材、查数据、调预算
side_effect：recommendation.explore（可选）
```

#### 资料查询

```text
输入："查一下上个月 Meta 花了多少钱"
上下文：
- query_context.time_range = last_month
- query_context.platform = Meta
- 查询 backend performance/campaign 聚合接口
side_effect：data.query_result
panel：analysis
```

#### 单点生成

```text
输入："给我写 5 条 Facebook 广告文案"
上下文：
- generation_context.content_type = ad_copy
- generation_context.platform = Facebook
- 若没有 project_id，允许生成 preview，不落正式素材库
side_effect：content.preview_generated 或 content.generated
panel：creative
```

#### 结构化任务

```text
输入："创建项目并配两个计划"
上下文：
- mode = STRUCTURED_TASK
- execution.current_act = project_creation
- execution.plan_dag = [...]
side_effect：act.project_created / act.campaign_created
panel：context
```

#### 中途切换

```text
输入："先别生成素材了，看看 ROI"
处理：
- mode 可从 STRUCTURED_TASK 临时切到 QUICK_ACTION
- execution 暂停当前 Act，不丢弃
- context.query_context 写入 ROI 查询条件
side_effect：mode.switched + data.query_result
```

---

## 3. Frontend 状态管理设计

### 3.1 前端不是事实源，但必须有稳定状态机

前端三类状态：

| 状态 | 来源 | 存储 | 刷新策略 |
|---|---|---|---|
| 权威业务数据 | backend API | Pinia/组件状态缓存 | side_effect 后重新拉取 |
| Session 投影状态 | backend Session State | Pinia agent store | session 切换/重连时拉取 |
| 本地临时状态 | 用户操作 | Pinia/local component | context_snapshot 上报 |

### 3.2 推荐 Store 拆分

```text
src/store/agent.ts
  - sessions
  - currentSessionId
  - streamStatus: idle/connecting/streaming/reconnecting/error
  - messages
  - runtimeEvents
  - sideEffects

src/store/workspace.ts
  - activePanel
  - activeProjectId
  - activeCampaignId
  - panelDataCache
  - highlightedEntities
  - stalePanels

src/store/draft.ts
  - draftEdits
  - conflictDrafts
  - dirtyFields

src/store/sse.ts 或 composable
  - connectionId
  - lastEventId
  - reconnectCount
  - missedEventRecoveryRequired
```

### 3.3 数据刷新原则

1. `side_effect` 不直接修改复杂本地实体，只标记 panel stale。
2. stale panel 通过 backend API 重新拉取权威数据。
3. 本地草稿不被 side_effect 静默覆盖。
4. 如果 side_effect 修改了用户正在编辑的字段，进入 conflict 状态。

```typescript
function handleSideEffect(event: SideEffectEvent) {
  workspaceStore.recordSideEffect(event)

  for (const panel of event.recommendation?.refresh_panels || []) {
    workspaceStore.markPanelStale(panel)
  }

  const conflicts = draftStore.detectConflicts(event.entities_affected)
  if (conflicts.length) {
    draftStore.markConflicts(conflicts)
    notifyUser('Agent 修改了你正在编辑的数据，请确认保留草稿还是使用最新结果')
    return
  }

  workspaceStore.refreshStalePanels()
}
```

### 3.4 SSE 断线重连

前端必须维护 `last_event_id`：

```text
正常：SSE event id 单调递增
断线：前端记录 last_event_id
重连：GET /api/v1/agent/sessions/{id}/events?after=last_event_id
恢复：补齐 missed side_effect，再继续 stream
```

一期可以简化：断线后重新拉 Layer 0 + Layer 1 重建视图，不补事件流。

### 3.5 多 Tab 同步

使用 `BroadcastChannel`：

```typescript
const channel = new BroadcastChannel('aniforce-agent-session')

channel.postMessage({ type: 'side_effect', sessionId, event })
channel.postMessage({ type: 'session_switched', sessionId })
channel.postMessage({ type: 'draft_updated', draftKey })
```

同 session 多 tab 同时发送消息时，前端必须提示：

```text
当前 Session 正在另一个窗口执行任务，请等待完成或新建 Session。
```

---

## 4. Agent 端编排设计

### 4.1 Agent-Service 职责边界

agent-service 负责：

```text
- LLM runtime
- OpenAI Agents SDK 调用
- MCP 工具注册和执行
- Skill 加载
- sandbox 文件隔离
- SQLiteSession 对话历史
- 同 session run 串行锁
```

agent-service 不负责：

```text
- 权威业务状态
- 用户权限最终判断
- Session State Layer 1
- 前端 UI 控制
```

### 4.2 编排模式

Agent 需要支持三种编排：

| 编排模式 | 适用场景 | 机制 |
|---|---|---|
| Freeform | 闲聊、咨询 | 直接模型回复，少量工具 |
| Quick Tool | 查询、生成、单点操作 | intent → 选工具 → 执行 → 解释结果 |
| Structured DAG | 长程任务 | plan_dag → act → tool steps → HITL → side_effect |

### 4.3 Act DAG，而不是固定线性剧本

```python
class ActNode(BaseModel):
    act_id: str
    type: str                         # project_creation/campaign_creation/material_generation/analysis/budget_adjustment
    status: str                       # pending/running/waiting_hitl/completed/failed/skipped
    depends_on: list[str] = []
    panel: Optional[str] = None
    required_tools: list[str] = []
    required_hitl: bool = False
    retry_policy: Optional[dict] = None
```

### 4.4 HITL 中断/恢复

```text
Agent 工具准备写操作
  → 创建 pending_hitl
  → SSE: hitl.confirmation_required
  → runtime 暂停，不继续执行后续 Act
用户确认
  → POST /api/v1/agent/hitl/{operation_id}/confirm
  → backend 更新 Session State
  → agent-service resume run
用户拒绝
  → operation status = rejected
  → Agent 解释影响并询问替代方案
```

### 4.5 长任务异步化

素材生成、批量分析等长任务不能阻塞单个 SSE 过久。

```text
Agent 调工具 submit_generation_job
  → backend 创建 job
  → 返回 job_id
  → SSE: runtime.job_submitted
  → 前端显示进度
  → Agent/前端轮询或订阅 job status
  → 完成后 side_effect: content.generated
```

---

## 5. 工具、Skill、沙箱联调设计

### 5.1 工具分层

| 层 | 位置 | 职责 |
|---|---|---|
| MCP Tool Schema | agent-service FastMCP | 定义 LLM 可见工具 |
| Tool Adapter | agent-service | 参数校验、调用 backend_client |
| Backend REST | backend | 权限、业务校验、DB 写入、Session State 更新 |
| Side Effect Producer | backend | 生成语义事件 |

### 5.2 工具规范

每个工具必须定义：

```text
- name：稳定，不随文案变化
- description：告诉 Agent 何时用，不要过宽泛
- input_schema：严格类型，字段有默认值和枚举
- idempotency_key：写操作必须支持
- required_permission：需要的权限
- hitl_policy：是否必须人工确认
- side_effect_type：成功后可能产生的语义事件
- timeout_seconds：工具级超时
- retry_policy：可重试/不可重试
```

### 5.3 工具错误格式

```python
class ToolError(BaseModel):
    code: str                         # VALIDATION_ERROR / AUTH_ERROR / RATE_LIMIT / BACKEND_UNAVAILABLE
    message: str
    retryable: bool
    user_message: str                 # 给用户看的解释
    debug: dict = {}                  # 不包含密钥
```

### 5.4 Skill 设计

Skill 不是工具本身，而是工具组合和领域策略。

```text
campaign-planning skill:
  - 何时触发：用户要建项目/计划/预算
  - 使用工具：create_project, create_campaign, update_budget
  - 业务约束：预算不超过项目总预算，写操作 HITL

creative-generation skill:
  - 何时触发：生成素材/文案/创意建议
  - 使用工具：generate_material, create_material
  - 支持 preview 模式：未绑定项目时不落正式库
```

### 5.5 沙箱边界

```text
sandbox 隔离：
- 文件系统：runtime/agent/sandbox/{session_id}
- 临时脚本、生成文件、分析结果都落 sandbox
- 不允许写 backend/data、项目源码、系统路径

不由 sandbox 隔离：
- backend REST 写数据库
- 权限由 JWT + backend 鉴权控制
- 幂等由 backend 保证
```

### 5.6 新增工具联调流程

```text
1. 定义 MCP tool schema
2. 实现 agent-service Tool Adapter
3. 确认 backend REST API 已存在或新增
4. backend REST 写入 side_effect producer
5. 写工具级测试：直接调用 MCP tool
6. 写 agent run 测试：自然语言触发工具
7. 写端到端测试：frontend 收到 side_effect 并刷新 panel
```

---

## 6. 并发与一致性设计

### 6.1 并发场景

| 场景 | 风险 | 策略 |
|---|---|---|
| 同 session 双 run | 对话历史、sandbox、Session State 竞态 | session 级锁 |
| 多工具并发写 Session State | changelog 丢失 | 乐观锁 version + retry |
| 前端手动修改 + Agent 修改 | 草稿冲突 | conflict detection |
| backend 多实例 | 内存锁失效 | Redis/DB lock（二期） |
| SSE 断线 | 事件丢失 | event log + 重拉状态 |

### 6.2 Session 级锁

backend 和 agent-service 都需要 session 级串行：

```python
class SessionLockManager:
    async def acquire(self, session_id: str): ...
    async def release(self, session_id: str): ...
```

一期：进程内 `asyncio.Lock`。  
二期：Redis lock，支持多 backend 实例。

### 6.3 乐观锁

Session State 更新带 version：

```sql
UPDATE session_states
SET context_json=?, changelog_json=?, version=version+1
WHERE session_id=? AND user_id=? AND version=?
```

如果更新行数为 0，说明并发冲突：重新读取、merge、最多重试 3 次。

### 6.4 幂等性

所有写工具必须带 `idempotency_key`：

```text
idempotency_key = session_id + run_id + tool_call_id
```

backend 记录：

```sql
CREATE TABLE tool_idempotency_keys (
  key TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  result_json TEXT,
  created_at TEXT NOT NULL
)
```

重复请求直接返回第一次结果，不重复创建项目/计划/素材。

---

## 7. 异常兜底与恢复

### 7.1 错误分类

| 错误 | 示例 | 用户提示 | 系统行为 |
|---|---|---|---|
| AUTH_ERROR | token 过期 | 请重新登录 | 停止 run |
| VALIDATION_ERROR | 参数非法 | 说明字段问题 | 不重试 |
| BACKEND_UNAVAILABLE | backend API 失败 | 服务暂时不可用 | 可重试 |
| AGENT_UNAVAILABLE | agent-service 挂 | AI 服务暂不可用 | 降级 |
| TOOL_TIMEOUT | 素材生成超时 | 任务仍在处理中 | 转异步 job |
| RATE_LIMIT | 模型 429 | 当前请求过多 | 指数退避 |
| STATE_CONFLICT | 版本冲突 | 数据已变化，请确认 | 拉最新状态 |
| SSE_DISCONNECTED | 网络断开 | 正在尝试恢复 | 重连/重拉状态 |

### 7.2 backend → agent-service 失败

```text
1. 连接失败：返回 503 + AGENT_UNAVAILABLE
2. 超时：返回 504 + AGENT_TIMEOUT
3. SSE 中途断：记录 run status = interrupted
4. 前端提示"AI 服务连接中断，可点击继续"
```

### 7.3 agent-service → backend 工具失败

Agent 工具调用 backend REST 失败时：

```text
- 4xx：不可重试，Agent 解释原因
- 401/403：停止，提示权限问题
- 409：状态冲突，Agent 重新读取上下文后再建议
- 429/503/504：按 retry_policy 重试
```

### 7.4 断点恢复

```text
run interrupted:
  - backend Session State.status = recovering
  - 记录 last_successful_side_effect_id
  - 前端重新连接后拉取 Session State
  - 用户点击"继续"
  - backend 发送 recovery_context 给 agent-service
  - Agent 从最近上下文继续
```

---

## 8. 重试策略

### 8.1 默认重试策略

```python
DEFAULT_RETRY_POLICY = {
    "max_attempts": 3,
    "base_delay_ms": 500,
    "max_delay_ms": 5000,
    "backoff": "exponential",
    "jitter": True,
    "retryable_codes": ["BACKEND_UNAVAILABLE", "RATE_LIMIT", "TOOL_TIMEOUT"],
}
```

### 8.2 哪些不能重试

```text
- 已经成功的写操作但没有 idempotency_key
- HITL 被拒绝
- 权限错误
- 参数校验错误
- 预算/业务规则冲突
```

### 8.3 部分失败

批量任务必须返回部分成功结果：

```python
class BatchToolResult(BaseModel):
    success_count: int
    failed_count: int
    succeeded: list[dict]
    failed: list[dict]
    retryable_failed: list[dict]
```

Agent 应解释："10 条素材中 7 条生成成功，3 条失败，可重试失败项。"

---

## 9. 部署架构

### 9.1 开发环境

```text
frontend 3010 → backend 8010 → agent-service 8020
agent-service → backend 8010 /api/v1/*
agent-service FastMCP: /mcp
```

### 9.2 生产推荐拓扑

```text
公网：
  browser → CDN/nginx → frontend static
  browser → HTTPS API Gateway → backend

内网：
  backend → agent-service
  agent-service → backend internal API

数据：
  backend DB: PostgreSQL（生产推荐）
  Session State: PostgreSQL JSONB / Redis（二期可拆）
  agent SQLiteSession: 初期本地盘；多实例时迁移中心化 session store
```

### 9.3 多实例注意

| 服务 | 多实例问题 | 方案 |
|---|---|---|
| frontend | 无状态 | CDN/静态部署 |
| backend | session lock / SSE | Redis lock + event log |
| agent-service | SQLiteSession 本地状态 | sticky session 或中心化 session store |
| SSE | 长连接负载均衡 | sticky session / gateway timeout 配置 |

### 9.4 配置项

```text
BACKEND_BASE_URL=http://127.0.0.1:8010
AGENT_SERVICE_URL=http://127.0.0.1:8020
AGENT_SERVICE_INTERNAL_TOKEN=...
SESSION_STATE_DB_URL=...
SSE_HEARTBEAT_INTERVAL_SECONDS=15
AGENT_RUN_TIMEOUT_SECONDS=300
TOOL_TIMEOUT_SECONDS=60
SESSION_LOCK_TIMEOUT_SECONDS=600
```

---

## 10. 监控、日志、审计

### 10.1 必须记录的日志

```text
backend:
- run_id, session_id, user_id
- intent recognition 结果
- business_context 构建耗时
- agent-service 请求耗时
- side_effect 事件
- Session State version 更新
- 工具调用写操作审计

agent-service:
- run_id, session_id
- model, token usage, cost
- tool_call start/end/error
- sandbox path
- SQLiteSession message count
- compaction 触发记录

frontend:
- SSE connect/disconnect/reconnect
- last_event_id
- side_effect handling
- panel refresh result
- draft conflict
```

### 10.2 指标

```text
- run 成功率 / 失败率
- TTFT（首 token 延迟）
- 工具调用成功率
- side_effect 处理成功率
- SSE 断线率
- Session State 冲突率
- compaction 触发次数
- 平均 token/cost
```

### 10.3 审计

所有写操作必须可审计：

```text
who: user_id
when: timestamp
where: session_id/run_id/tool_call_id
what: entity_type/entity_id/field old→new
why: act_id / user prompt summary
rollbackable: true/false
```

---

## 11. 测试矩阵升级

原 Block 1-7 是功能路径测试，还必须补充工程测试：

| Block | 新增工程测试 |
|---|---|
| Block 1 | 乐观锁冲突、并发更新、version retry |
| Block 2 | 多 mode 上下文抽象：闲聊/查询/生成/结构化 |
| Block 3 | agent-service 挂掉、超时、SSE 中断 |
| Block 4 | context_snapshot 缺字段、超大草稿、tab 切换 |
| Block 5 | side_effect replay、事件丢失后重建视图、draft conflict |
| Block 6 | compaction 后恢复、重复 compaction、summary 累积 |
| Block 7 | frontend 断线重连、多 tab、用户+Agent 并发修改 |

新增 Block：

```text
Block 8: Concurrency & Idempotency
  - 同 session 双 run 串行
  - 幂等 key 防重复创建
  - version conflict retry

Block 9: Failure Recovery
  - agent-service unavailable
  - backend tool 503
  - SSE disconnected
  - run resume

Block 10: Deployment Smoke
  - 三端健康检查
  - 内网 URL 配置
  - CORS / auth / timeout

Block 11: Observability & Audit
  - run_id 全链路串联
  - tool audit log
  - side_effect log
```

---

## 12. 更新后的完整 Block 清单

| Block | 交付物 | 重点 |
|---|---|---|
| 0 | Intent Recognition | 多场景入口，不预设长程任务 |
| 1 | Session State Model + Repository | Layer 1 envelope、version、event log |
| 2 | Business Context Abstraction | 多 mode 上下文摘要 |
| 3 | Backend Agent Gateway + Context Injection | backend 是状态管理者，不是 proxy |
| 4 | context_snapshot 传输 | Layer 3 → Layer 1，草稿/选中/路由 |
| 5 | Side Effect 语义事件系统 | act/data/content/recommendation/runtime |
| 6 | LLM Context Compaction | Layer 2 压缩到 Layer 1 |
| 7 | Frontend 状态管理集成 | Store、SSE、Panel stale、冲突处理 |
| 8 | Tool/Skill/Sandbox 联调 | 工具规范、Skill 策略、sandbox 边界 |
| 9 | Concurrency & Idempotency | session lock、version、idempotency key |
| 10 | Failure Recovery & Retry | 超时、重试、恢复、降级 |
| 11 | Deployment & Observability | 部署拓扑、日志、指标、审计 |
| 12 | Full E2E Real Scenarios | 闲聊/查询/生成/结构化/恢复全场景 |

---

## 13. Full E2E 真实场景验收

最终不是只跑 campaign 全流程，还要跑以下真实 case：

### Case A：闲聊探索

```text
用户：你能帮我做什么？
期望：
- mode = exploratory
- 不强制创建 project/session act
- Agent 介绍能力
- 可 side_effect: recommendation.explore
```

### Case B：资料查询

```text
用户：查一下我上个月 Meta 花了多少钱
期望：
- mode = quick_action
- query_context 正确
- 调 backend 查询/聚合接口
- side_effect: data.query_result
- panel hint = analysis
```

### Case C：素材体验

```text
用户：给我写 5 条 Facebook 广告文案，轻松一点
期望：
- mode = quick_action
- generation_context 正确
- 若无 project_id，生成 preview，不落正式素材库
- side_effect: content.preview_generated
- panel hint = creative
```

### Case D：结构化任务

```text
用户：创建一个 RPG 项目，预算 50000，再配两个计划
期望：
- mode = structured_task
- execution.plan_dag 生成
- HITL 触发
- 工具按依赖顺序执行
- side_effect: act.project_created / act.campaign_created
```

### Case E：中途切换

```text
用户：先别生成素材了，看看这两个计划 ROI
期望：
- 当前 Act 暂停
- mode 临时 quick_action
- data.query_result 返回
- 之后可继续原 Act
```

### Case F：断线恢复

```text
执行中断开 SSE
期望：
- frontend streamStatus = reconnecting/error
- backend run status = interrupted/recovering
- 重新进入 session 后重建 Layer 0 + Layer 1 视图
- 用户点击继续后 runtime.resumed
```

### Case G：并发冲突

```text
用户正在编辑 campaign A 预算
Agent 同时调整 campaign A 预算
期望：
- 前端检测 draft conflict
- 不静默覆盖草稿
- 用户选择保留草稿或使用 Agent 修改
```

### Case H：工具失败重试

```text
create_campaign 第一次 503，第二次成功
期望：
- idempotency_key 不变
- 最多创建一个 campaign
- changelog 只有一条成功记录
```

---

## 14. 开发顺序修订

不要直接从 Gateway 开始。正确顺序：

```text
Phase 0：补模型抽象
  Block 0 Intent Recognition
  Block 1 Session State envelope + version + event log

Phase 1：补上下文能力
  Block 2 多 mode Business Context Abstractor
  Block 4 context_snapshot

Phase 2：打通运行链路
  Block 3 Backend Gateway + Agent context injection
  Block 8 Tool/Skill/Sandbox 联调

Phase 3：打通投影链路
  Block 5 Side Effect 事件
  Block 7 Frontend Store + SSE + Panel stale

Phase 4：工程安全
  Block 9 并发与幂等
  Block 10 异常恢复与重试
  Block 6 compaction（也可提前基础版）

Phase 5：上线准备
  Block 11 部署与观测
  Block 12 全真实场景 E2E
```

---

## 15. 重要结论

Session State Manager 不是"为了 campaign 全流程演示"写的，它是 ANIFORCE Agent 产品的运行时底座。它必须兼容：

```text
- 无任务闲聊
- 查询分析
- 素材体验
- 单点工具动作
- 结构化长程任务
- 中途切换
- 回滚重跑
- 断线恢复
- 并发冲突
- 生产部署
```

因此开发时不能把 Act、Panel、Project 当成硬编码主线。正确抽象是：

```text
Session Runtime
  → Intent
  → Mode
  → Business Context Summary
  → Agent Orchestration
  → Tool/Skill/Sandbox Execution
  → Session State Mutation
  → Semantic Side Effect
  → Frontend Projection
```


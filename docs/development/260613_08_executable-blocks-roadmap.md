# ANIFORCE 可执行开发路线图

**版本**: v2.0（基于真实项目状态）  
**创建日期**: 2025-06-13  
**预计完成时间**: 5-7 周  
**当前状态**: 📋 规划中

---

## 📋 项目概述

### 核心目标
在现有基础上，分两个阶段完成：
1. **阶段 1**: Agent 编排能力（Plan-Execute + Skills）
2. **阶段 2**: AG-UI 协议集成（前后端协同）

### 技术栈
- **Backend**: OpenAI Agents SDK（已有）+ Plan-Execute 框架（新增）+ Skills（新增）
- **Frontend**: Vue 3（已有）+ AG-UI 事件处理（新增）
- **协议**: AG-UI Protocol（新增）

### 核心原则
- ✅ 基于现有代码增量开发
- ✅ 每个 Block 独立可测试
- ✅ 100% 向后兼容
- ✅ 先 Agent 编排，后 AG-UI

---

## 🗓️ 总体规划

### 阶段 1: Agent 编排（2-3 周）

| Block | 内容 | 工作量 | 优先级 |
|-------|------|--------|--------|
| **Block 1** | Skills 系统基础 | 3-4 天 | P0 |
| **Block 2** | 创建核心 Skills | 2-3 天 | P0 |
| **Block 3** | Plan-Execute 框架 | 4-5 天 | P0 |
| **Block 4** | System Prompt 增强 | 2-3 天 | P0 |

### 阶段 2: AG-UI 协议（2-3 周）

| Block | 内容 | 工作量 | 优先级 |
|-------|------|--------|--------|
| **Block 5** | Shared State | 2-3 天 | P0 |
| **Block 6** | Human-in-the-Loop | 2-3 天 | P0 |
| **Block 7** | Generative UI | 3-4 天 | P1 |
| **Block 8** | Frontend Actions | 2-3 天 | P1 |
| **Block 9** | AG-UI 路由集成 | 2-3 天 | P0 |

### 阶段 3: 测试与优化（1 周）

| Block | 内容 | 工作量 | 优先级 |
|-------|------|--------|--------|
| **Block 10** | E2E 测试 | 3-4 天 | P0 |
| **Block 11** | 生产部署 | 2-3 天 | P0 |

**总计**: 25-35 天 → **5-7 周**

---

## 📊 进度追踪表

### 阶段 1: Agent 编排
- [ ] Block 1: Skills 系统基础 - 0%
- [ ] Block 2: 创建核心 Skills - 0%
- [ ] Block 3: Plan-Execute 框架 - 0%
- [ ] Block 4: System Prompt 增强 - 0%

### 阶段 2: AG-UI 协议
- [ ] Block 5: Shared State - 0%
- [ ] Block 6: Human-in-the-Loop - 0%
- [ ] Block 7: Generative UI - 0%
- [ ] Block 8: Frontend Actions - 0%
- [ ] Block 9: AG-UI 路由集成 - 0%

### 阶段 3: 测试与优化
- [ ] Block 10: E2E 测试 - 0%
- [ ] Block 11: 生产部署 - 0%

### 里程碑
- [ ] 🎯 MVP-1: Skills 系统可用（Block 1-2）
- [ ] 🎯 MVP-2: 完整 Agent 编排（Block 1-4）
- [ ] 🎯 MVP-3: AG-UI 基础能力（Block 5-6）
- [ ] 🎯 MVP-4: 完整产品（Block 1-11）

---


## 🎯 阶段 1: Agent 编排

---

## Block 1: Skills 系统基础

### 📅 基本信息
- **预计工作量**: 3-4 天
- **开始日期**: TBD
- **完成日期**: TBD
- **状态**: 📋 待开始
- **依赖**: 无
- **优先级**: P0（必须）

---

### 🎯 目标
实现 Skills 加载和管理系统，让 Agent 能够发现和使用 Skills。

---

### 📝 背景说明

**什么是 Skills？**
Skills 是封装了领域知识的工作流定义，以 SKILL.md 文件形式存储。

**OpenAI Agents SDK 的 Skills 机制**：
```python
from agents.sandbox import SandboxAgent
from agents.sandbox.capabilities import Skills, LocalDirLazySkillSource
from agents.sandbox.entries import LocalDir

agent = SandboxAgent(
    name="ANIFORCE Assistant",
    capabilities=Capabilities.default() + [
        Skills(
            lazy_from=LocalDirLazySkillSource(
                source=LocalDir(src="backend/runtime/skills")
            )
        )
    ]
)
```

SDK 会自动：
1. 扫描 `backend/runtime/skills/` 目录
2. 读取所有 `SKILL.md` 文件
3. 提取 name 和 description（从 frontmatter）
4. 生成 Skills 索引并注入到 System Prompt
5. 当 Agent 调用 `load_skill("skill-name")` 时，将 Skill 复制到 Sandbox

---

### 📋 任务清单

#### 1.1 定义 SKILL.md 规范（0.5 天）

**文件**: `docs/development/skills-specification.md`

- [ ] 编写 SKILL.md 格式规范文档
  - [ ] Frontmatter 格式（name, description）
  - [ ] 正文结构（目标、输入、输出、工作流、约束）
  - [ ] 示例模板
  - [ ] 最佳实践

**交付物**: `skills-specification.md`

**规范示例**:
```markdown
---
name: project-management
description: 项目管理：创建、查询、更新、删除项目
---

# 项目管理 Skill

## 目标
帮助用户管理广告投放项目的全生命周期

## 输入
- 用户自然语言需求
- 项目相关参数

## 输出
- 结构化项目信息
- 操作确认消息

## 工作流

### 创建项目
1. 提取项目信息（名称、预算、描述）
2. 调用 MCP Tool: `create_project`
3. 返回项目 ID 和确认消息

### 查询项目
1. 调用 MCP Tool: `list_projects` 或 `get_project_detail`
2. 格式化展示项目信息

### 删除项目（需要确认）
1. 获取项目详情
2. 展示影响范围
3. 请求用户确认
4. 执行删除

## 硬约束
- 预算必须 > 0
- 项目名称不能为空
- 删除操作必须经用户确认
```

---

#### 1.2 创建 Skills 目录结构（0.5 天）

**创建目录**:
```bash
mkdir -p backend/runtime/skills/project-management
mkdir -p backend/runtime/skills/campaign-management
mkdir -p backend/runtime/skills/data-analysis
mkdir -p backend/runtime/skills/hitl-operations
```

**创建占位文件**:
```bash
# 每个目录下创建空的 SKILL.md
touch backend/runtime/skills/project-management/SKILL.md
touch backend/runtime/skills/campaign-management/SKILL.md
touch backend/runtime/skills/data-analysis/SKILL.md
touch backend/runtime/skills/hitl-operations/SKILL.md
```

**交付物**: 4 个空目录 + 4 个空 SKILL.md

---

#### 1.3 修改 OpenAI Adapter 支持 Skills（1 天）

**文件**: `backend/app/agent_platform/adapters/openai_adapter.py`

**修改点**:

```python
# 在 OpenAISDKAdapter 类中添加
from agents.sandbox import SandboxAgent
from agents.sandbox.capabilities import Capabilities, Skills, LocalDirLazySkillSource
from agents.sandbox.entries import LocalDir
from pathlib import Path

class OpenAISDKAdapter:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        enable_tracing: bool = True,
        skills_dir: Optional[str] = None,  # 新增
    ):
        # ... 现有代码 ...
        self.skills_dir = skills_dir or "backend/runtime/skills"
    
    def create_agent(
        self,
        name: str,
        instructions: str,
        mcp_servers: list = None,
        enable_skills: bool = True,  # 新增参数
    ) -> Agent:
        """创建 Agent（支持 Skills）"""
        
        if enable_skills and Path(self.skills_dir).exists():
            # 使用 SandboxAgent（支持 Skills）
            agent = SandboxAgent(
                name=name,
                instructions=instructions,
                model=self.model,
                mcp_servers=mcp_servers or [],
                capabilities=Capabilities.default() + [
                    Skills(
                        lazy_from=LocalDirLazySkillSource(
                            source=LocalDir(src=self.skills_dir)
                        )
                    )
                ]
            )
            logger.info(f"[SDK] Created SandboxAgent with Skills: {self.skills_dir}")
        else:
            # 使用普通 Agent（向后兼容）
            agent = Agent(
                name=name,
                instructions=instructions,
                model=self.model,
                mcp_servers=mcp_servers or [],
            )
            logger.info(f"[SDK] Created Agent without Skills")
        
        return agent
```

**测试点**:
- [ ] Skills 目录存在时，创建 SandboxAgent
- [ ] Skills 目录不存在时，降级为普通 Agent
- [ ] 不影响现有功能

**交付物**: 修改后的 `openai_adapter.py`

---

#### 1.4 配置 Skills 路径（0.5 天）

**文件**: `backend/.env`

添加配置:
```bash
# Skills
SKILLS_DIR=backend/runtime/skills
```

**文件**: `backend/app/config/settings.py`

```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # Skills 配置
    SKILLS_DIR: str = "backend/runtime/skills"
```

**文件**: 修改 Runtime 初始化

`backend/app/api/v1/agent/routes.py`:
```python
_adapter = OpenAISDKAdapter(
    model=getattr(_settings, "OPENAI_AGENTS_MODEL", "gpt-4o-mini"),
    api_key=_settings.OPENAI_API_KEY,
    base_url=getattr(_settings, "OPENAI_BASE_URL", None),
    enable_tracing=getattr(_settings, "AGENT_TRACING_ENABLED", True),
    skills_dir=_settings.SKILLS_DIR,  # 新增
)
```

**交付物**: 配置文件修改

---

#### 1.5 测试 Skills 加载（1 天）

**创建测试 Skill**:

`backend/runtime/skills/test-skill/SKILL.md`:
```markdown
---
name: test-skill
description: 测试 Skill，用于验证加载机制
---

# 测试 Skill

## 目标
验证 Skills 系统正常工作

## 工作流
返回固定消息: "Hello from test-skill!"
```

**创建测试脚本**:

`backend/tests/test_skills_loading.py`:
```python
import pytest
from app.agent_platform.adapters.openai_adapter import OpenAISDKAdapter
from pathlib import Path

def test_skills_loading():
    """测试 Skills 加载"""
    adapter = OpenAISDKAdapter(
        skills_dir="backend/runtime/skills"
    )
    
    # 创建 Agent
    agent = adapter.create_agent(
        name="Test Agent",
        instructions="你是测试 Agent",
        enable_skills=True
    )
    
    # 验证 Agent 是 SandboxAgent
    from agents.sandbox import SandboxAgent
    assert isinstance(agent, SandboxAgent)
    
    # TODO: 验证 Skills 索引被注入到 instructions
    print(f"Agent created: {agent.name}")

def test_without_skills():
    """测试不启用 Skills"""
    adapter = OpenAISDKAdapter(
        skills_dir="backend/runtime/skills"
    )
    
    agent = adapter.create_agent(
        name="Test Agent",
        instructions="你是测试 Agent",
        enable_skills=False  # 不启用
    )
    
    # 验证是普通 Agent
    from agents import Agent
    from agents.sandbox import SandboxAgent
    assert isinstance(agent, Agent)
    assert not isinstance(agent, SandboxAgent)
```

**运行测试**:
```bash
cd backend
UV_CACHE_DIR=./uv_cache uv run pytest tests/test_skills_loading.py -v
```

**交付物**: 测试脚本 + 测试通过截图

---

### ✅ 验收标准

#### 功能验收
- [ ] Skills 目录创建完成（4 个子目录）
- [ ] OpenAI Adapter 支持 Skills 参数
- [ ] 配置文件包含 SKILLS_DIR
- [ ] 测试脚本通过（Skills 正常加载）

#### 测试用例
```bash
# 测试 1: 目录结构
ls -la backend/runtime/skills/
# 预期输出: 看到 4 个子目录

# 测试 2: Skills 加载
cd backend
UV_CACHE_DIR=./uv_cache uv run pytest tests/test_skills_loading.py -v
# 预期输出: 2 个测试通过

# 测试 3: 不影响现有功能
# 启动服务，发送普通对话请求
curl -X POST http://localhost:18003/api/v1/agent/chat/sessions/{session_id}/stream \
  -H "Authorization: Bearer {token}" \
  -d '{"message": "你好"}'
# 预期输出: 正常对话
```

---

### 📦 交付物清单
- [ ] `docs/development/skills-specification.md` - Skills 规范文档
- [ ] `backend/runtime/skills/` - 4 个子目录 + 空 SKILL.md
- [ ] `backend/app/agent_platform/adapters/openai_adapter.py` - 支持 Skills
- [ ] `backend/.env` - 包含 SKILLS_DIR
- [ ] `backend/app/config/settings.py` - 包含 Skills 配置
- [ ] `backend/tests/test_skills_loading.py` - 测试脚本
- [ ] 测试报告（截图 + 结果）

---

### 🐛 风险与问题

**已知风险**:
1. OpenAI SDK 版本兼容性（需要确认 SDK 版本支持 Skills）
2. Skills 目录路径问题（相对路径 vs 绝对路径）

**缓解措施**:
1. 在开发环境先验证 SDK 版本
2. 使用 `Path` 模块处理路径

---

### 📝 开发日志
（开发过程中每天更新）

**示例**:
```
2025-06-XX Day 1:
- 创建了 Skills 目录结构
- 编写了规范文档
- 遇到问题: SDK 版本不支持 Skills
- 解决方案: 升级到 SDK vX.X.X

2025-06-XX Day 2:
- 修改了 OpenAI Adapter
- 创建了测试脚本
- 所有测试通过 ✅
```

---


## Block 2: 创建核心 Skills

### 📅 基本信息
- **预计工作量**: 2-3 天
- **开始日期**: TBD
- **完成日期**: TBD
- **状态**: 📋 待开始
- **依赖**: Block 1（Skills 系统基础）
- **优先级**: P0（必须）

---

### 🎯 目标
创建 4 个核心 Skills，覆盖 ANIFORCE 的主要业务场景。

---

### 📋 任务清单

#### 2.1 Skill 1: project-management（1 天）

**文件**: `backend/runtime/skills/project-management/SKILL.md`

```markdown
---
name: project-management
description: 项目管理：创建、查询、更新、删除项目，预算分析
---

# 项目管理 Skill

## 目标
帮助用户管理广告投放项目的全生命周期

## 输入
- 用户自然语言需求（如"创建 RPG 游戏项目，预算 10 万"）
- 项目 ID（用于查询/更新/删除）

## 输出
- 结构化项目信息
- 操作确认消息
- 预算分析报告（如需要）

## 可用的 MCP Tools
- `list_projects`: 查询项目列表
- `create_project`: 创建新项目
- `get_project_detail`: 查询项目详情
- `update_project`: 更新项目信息
- `delete_project`: 删除项目

## 工作流

### 1. 创建项目
**触发条件**: 用户说"创建项目"、"新建项目"

**步骤**:
1. 从用户输入中提取项目信息：
   - 项目名称（必填）
   - 预算（必填，必须 > 0）
   - 描述（可选）
   - 游戏类型（可选）
2. 调用 MCP Tool: `create_project`
3. 返回项目 ID 和确认消息

**示例**:
```
用户: "帮我创建一个 RPG 游戏项目，预算 10 万"

步骤:
1. 提取: name="RPG游戏项目", budget=100000, game_type="RPG"
2. 调用: create_project(name="RPG游戏项目", budget=100000, ...)
3. 返回: "✅ 已创建项目 'RPG游戏项目'（ID: proj_xxx），预算 ¥100,000"
```

### 2. 查询项目
**触发条件**: 用户说"查看项目"、"项目列表"、"项目详情"

**步骤**:
1. 判断是查询列表还是详情
2. 如果是列表，调用 `list_projects`
3. 如果是详情，调用 `get_project_detail`
4. 格式化展示项目信息

### 3. 更新项目
**触发条件**: 用户说"修改项目"、"更新预算"

**步骤**:
1. 获取项目当前信息: `get_project_detail`
2. 提取要修改的字段
3. 调用 `update_project`
4. 确认更新成功

### 4. 删除项目
**触发条件**: 用户说"删除项目"

**步骤**:
1. 获取项目详情: `get_project_detail`
2. **⚠️ 重要**: 展示项目信息和影响范围（包含多少广告计划）
3. **⚠️ 重要**: 告诉用户"此操作需要确认，请在弹出的对话框中确认"
4. 等待用户通过其他方式确认（当前不支持 HITL，提示用户手动确认）
5. 调用 `delete_project`
6. 返回删除确认

**注意**: 由于当前还没有 HITL 系统（Block 6 才实现），这里只能：
- 展示详细信息
- 明确告知风险
- 提示用户确认
- 不自动执行删除

### 5. 预算分析
**触发条件**: 用户说"分析预算"、"预算使用情况"

**步骤**:
1. 查询项目详情和关联的广告计划
2. 计算预算使用率
3. 生成分析报告

## 硬约束
- 预算必须 > 0
- 项目名称不能为空
- 删除操作必须明确告知风险
- 所有 MCP 调用失败必须返回清晰的错误信息

## 示例对话

**场景 1: 创建项目**
```
用户: "帮我创建一个模拟经营游戏的广告项目，预算 5 万"
AI: [使用 project-management Skill]
    1. 提取信息...
    2. 调用 create_project...
    ✅ 已创建项目 "模拟经营游戏广告项目"（ID: proj_123）
    - 预算: ¥50,000
    - 游戏类型: 模拟经营
    
    接下来您可以为这个项目创建广告计划。
```

**场景 2: 查询项目**
```
用户: "我有哪些项目？"
AI: [使用 project-management Skill]
    您目前有 3 个项目：
    
    1. RPG 游戏项目
       - 预算: ¥100,000
       - 状态: 进行中
       - 广告计划: 5 个
    
    2. 休闲游戏项目
       - 预算: ¥50,000
       - 状态: 进行中
       - 广告计划: 3 个
    
    3. 模拟经营游戏项目
       - 预算: ¥80,000
       - 状态: 已完成
       - 广告计划: 8 个
```

**场景 3: 删除项目（当前版本）**
```
用户: "删除测试项目"
AI: [使用 project-management Skill]
    ⚠️ 您确定要删除项目 "测试项目" 吗？
    
    项目信息：
    - 项目 ID: proj_456
    - 包含广告计划: 2 个
    - 总预算: ¥10,000
    
    ⚠️ 此操作不可逆！删除后所有关联的广告计划也会被删除。
    
    如果确认删除，请回复 "确认删除测试项目"
```
```

**任务**:
- [ ] 编写完整的 SKILL.md
- [ ] 包含所有 5 个工作流
- [ ] 包含 3 个示例对话
- [ ] 验证 MCP Tools 名称正确

---

#### 2.2 Skill 2: campaign-management（0.5 天）

**文件**: `backend/runtime/skills/campaign-management/SKILL.md`

**内容**:（类似 project-management，但针对广告计划）
- 创建广告计划
- 查询广告计划
- 更新广告计划
- 删除广告计划
- 暂停/启动广告计划

**MCP Tools**:
- `list_campaigns`
- `create_campaign`
- `get_campaign_detail`
- `update_campaign`
- `delete_campaign`

**任务**:
- [ ] 编写完整的 SKILL.md
- [ ] 至少 3 个工作流
- [ ] 至少 2 个示例对话

---

#### 2.3 Skill 3: data-analysis（0.5 天）

**文件**: `backend/runtime/skills/data-analysis/SKILL.md`

**目标**: 数据分析和报告生成

**工作流**:
1. **项目数据分析**: 分析项目的整体表现
2. **广告计划对比**: 对比多个广告计划的效果
3. **趋势分析**: 分析数据趋势（需要时间序列数据）

**注意**: 当前可能没有专门的数据分析 MCP Tools，可以：
- 使用 `get_project_detail` 和 `get_campaign_detail` 获取数据
- 在 Skill 中描述如何组织和展示数据
- 为未来的数据分析 API 预留接口

**任务**:
- [ ] 编写 SKILL.md
- [ ] 定义 2-3 个分析场景
- [ ] 说明当前能做什么、未来能做什么

---

#### 2.4 Skill 4: hitl-operations（0.5 天）

**文件**: `backend/runtime/skills/hitl-operations/SKILL.md`

**目标**: 处理需要用户确认的操作（当前版本的权宜之计）

**工作流**:
1. **删除确认**: 删除项目/广告计划前的确认流程
2. **批量操作确认**: 批量修改前的确认
3. **高风险操作提示**: 明确告知用户风险

**当前实现方式**（Block 6 之前）:
- 展示详细信息
- 明确告知风险
- 要求用户明确回复（如"确认删除 XXX"）
- 验证用户回复后再执行

**未来实现方式**（Block 6 之后）:
- 调用 HITL Manager
- 弹出确认对话框
- 等待用户点击按钮

**任务**:
- [ ] 编写 SKILL.md
- [ ] 定义确认流程
- [ ] 说明当前版本 vs 未来版本的差异

---

### ✅ 验收标准

#### 功能验收
- [ ] 4 个 SKILL.md 文件创建完成
- [ ] 每个 Skill 包含完整的工作流定义
- [ ] 每个 Skill 包含示例对话
- [ ] 所有 MCP Tool 名称正确

#### 测试用例

**测试 1: Agent 能否看到 Skills**
```python
# 创建 Agent，查看 instructions 是否包含 Skills 索引
agent = adapter.create_agent(
    name="Test",
    instructions="测试",
    enable_skills=True
)

# 检查 agent.instructions 是否包含:
# - "Available skills:"
# - "project-management"
# - "campaign-management"
# 等
```

**测试 2: 实际对话测试**
```
用户: "帮我创建一个 RPG 游戏项目"
预期: Agent 使用 project-management Skill，调用 create_project
```

**测试 3: Skills 内容正确性**
```bash
# 手动检查每个 SKILL.md
cat backend/runtime/skills/project-management/SKILL.md
# 验证: frontmatter 正确，工作流完整，示例清晰
```

---

### 📦 交付物清单
- [ ] `project-management/SKILL.md` - 完整的项目管理 Skill
- [ ] `campaign-management/SKILL.md` - 完整的广告计划管理 Skill
- [ ] `data-analysis/SKILL.md` - 数据分析 Skill
- [ ] `hitl-operations/SKILL.md` - 确认操作 Skill
- [ ] 测试报告（验证 Skills 被正确加载）

---

### 🐛 风险与问题

**已知风险**:
1. Skills 描述不够清晰，Agent 可能不知道何时使用
2. MCP Tools 功能有限，某些 Skill 无法完全实现

**缓解措施**:
1. 在 Skill 中明确"触发条件"
2. 标注"当前版本"vs"未来版本"的功能差异

---

### 📝 开发日志
（开发过程中每天更新）


## Block 3: Plan-Execute 框架

### 📅 基本信息
- **预计工作量**: 4-5 天
- **开始日期**: TBD
- **完成日期**: TBD
- **状态**: 📋 待开始
- **依赖**: Block 1-2（Skills 系统）
- **优先级**: P0（必须）

---

### 🎯 目标
实现 Plan-Execute 框架，让 Agent 能够分解复杂任务并逐步执行。

---

### 📝 背景说明

**什么是 Plan-Execute？**
- **Plan**: Agent 分析任务，生成 Todo List（执行计划）
- **Execute**: Agent 逐个执行 Todo，记录结果
- **Verify**: Agent 验证结果是否符合预期

**为什么需要 Plan-Execute？**
- 复杂任务需要多步骤执行
- 用户可以看到执行进度（Todo List）
- 出错后可以从断点恢复

**参考实现**:
- Cursor/Windsurf 的 TodoWrite 模式
- LangGraph 的 Plan-and-Execute
- Devin/Manus 的任务分解

---

### 📋 任务清单

#### 3.1 设计 Todo 数据结构（0.5 天）

**文件**: `backend/app/agent_platform/models.py`

**新增模型**:
```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class TodoStatus(str, Enum):
    """Todo 状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    SKIPPED = "skipped"      # 跳过

class TodoItem(BaseModel):
    """Todo 项"""
    id: str = Field(..., description="Todo ID")
    title: str = Field(..., description="Todo 标题")
    description: Optional[str] = Field(None, description="详细描述")
    status: TodoStatus = Field(default=TodoStatus.PENDING)
    result: Optional[dict] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    dependencies: List[str] = Field(default_factory=list, description="依赖的 Todo ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)

class ExecutionPlan(BaseModel):
    """执行计划"""
    plan_id: str = Field(..., description="计划 ID")
    task_id: str = Field(..., description="归属任务 ID")
    todos: List[TodoItem] = Field(default_factory=list, description="Todo 列表")
    current_todo_index: int = Field(default=0, description="当前执行的 Todo 索引")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**任务**:
- [ ] 在 `models.py` 中添加上述模型
- [ ] 添加单元测试验证模型正确性

---

#### 3.2 实现 Plan-Execute System Prompt（1 天）

**文件**: `backend/app/agent_platform/prompts.py`

**新增 Prompt**:
```python
PLAN_EXECUTE_SYSTEM_PROMPT = """
你是 ANIFORCE AI 助手，使用 Plan-Execute 模式处理复杂任务。

## 工作模式

当用户的任务比较复杂时，你需要：

### 1. Planning 阶段
分析任务，生成 Todo List（执行计划）。

**Todo List 格式**:
```json
{
  "todos": [
    {
      "id": "todo_1",
      "title": "查询项目详情",
      "description": "调用 get_project_detail 获取项目 A 的详细信息"
    },
    {
      "id": "todo_2",
      "title": "分析数据",
      "description": "分析项目数据，计算关键指标",
      "dependencies": ["todo_1"]
    },
    {
      "id": "todo_3",
      "title": "生成报告",
      "description": "根据分析结果生成优化建议",
      "dependencies": ["todo_2"]
    }
  ]
}
```

**何时需要 Planning?**
- 任务包含多个步骤
- 需要调用多个 Tools/Skills
- 需要条件判断（如果 A 成功则执行 B）
- 用户明确要求"帮我完成 XXX"

**何时不需要 Planning?**
- 简单查询（只需一个 Tool）
- 简单对话
- 用户只是问问题

### 2. Execute 阶段
按顺序执行 Todo List，每完成一个 Todo，报告进度。

**执行规则**:
- 按顺序执行（除非有依赖关系）
- 每个 Todo 执行前，说明"正在执行: {todo.title}"
- 每个 Todo 执行后，说明结果
- 如果某个 Todo 失败，判断是否继续还是停止

### 3. Verify 阶段
所有 Todo 执行完后，验证是否达到目标。

## 可用能力

### Skills
{skills_index}

### MCP Tools
{mcp_tools_list}

## 示例

**用户**: "帮我优化项目 A 的广告投放"

**你的思考**:
这是一个复杂任务，需要多个步骤，应该使用 Plan-Execute 模式。

**你的回复**:
好的，我将帮您优化项目 A 的广告投放。让我先制定执行计划：

📋 执行计划：
1. ✅ 查询项目 A 的详细信息
2. ⏳ 分析广告计划的表现数据
3. ⏳ 识别表现不佳的广告计划
4. ⏳ 生成优化建议
5. ⏳ 请求您确认后执行调整

现在开始执行...

[执行 Todo 1]
正在执行: 查询项目 A 的详细信息
[调用 MCP Tool: get_project_detail]
✅ 已获取项目信息：项目 A，预算 ¥100,000，包含 5 个广告计划

[执行 Todo 2]
正在执行: 分析广告计划的表现数据
...

## 重要约束
- 不要过度规划：简单任务直接执行，不要生成 Todo
- 实时报告进度：用户需要知道你在做什么
- 失败处理：如果某步失败，告诉用户并建议下一步
- 保持简洁：回复 2-3 句话说明当前进度即可
"""

def build_plan_execute_prompt(skills_index: str, mcp_tools_list: str) -> str:
    """构建 Plan-Execute System Prompt"""
    return PLAN_EXECUTE_SYSTEM_PROMPT.format(
        skills_index=skills_index,
        mcp_tools_list=mcp_tools_list
    )
```

**任务**:
- [ ] 创建 `PLAN_EXECUTE_SYSTEM_PROMPT`
- [ ] 实现 `build_plan_execute_prompt()` 函数
- [ ] 测试 Prompt 是否正确渲染

---

#### 3.3 修改 Runtime 支持 Plan-Execute（1.5 天）

**文件**: `backend/app/agent_platform/runtime.py`

**修改 `_get_system_prompt()` 方法**:
```python
def _get_system_prompt(self, task_type: str, mcp_tools: list = None) -> str:
    """
    根据任务类型返回 system prompt
    
    Args:
        task_type: 任务类型
        mcp_tools: MCP Tools 列表（用于生成索引）
    """
    from .prompts import build_plan_execute_prompt
    
    # 生成 Skills 索引（如果启用）
    skills_index = self._generate_skills_index()
    
    # 生成 MCP Tools 列表
    tools_list = self._generate_tools_list(mcp_tools or [])
    
    # 使用 Plan-Execute Prompt
    return build_plan_execute_prompt(skills_index, tools_list)

def _generate_skills_index(self) -> str:
    """生成 Skills 索引（供 Prompt 使用）"""
    # 读取 SKILLS_DIR 下的所有 SKILL.md
    # 提取 name 和 description
    # 生成索引文本
    
    skills_dir = Path(self.adapter.skills_dir)
    if not skills_dir.exists():
        return "（Skills 未启用）"
    
    skills = []
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                # 解析 frontmatter
                content = skill_md.read_text()
                # 简单解析（假设第一行是 ---，第二行开始是 frontmatter）
                lines = content.split('\n')
                if lines[0] == '---':
                    for line in lines[1:]:
                        if line == '---':
                            break
                        if line.startswith('name:'):
                            name = line.split(':', 1)[1].strip()
                        if line.startswith('description:'):
                            desc = line.split(':', 1)[1].strip()
                    skills.append(f"- {name}: {desc}")
    
    if not skills:
        return "（没有可用的 Skills）"
    
    return "\n".join(skills)

def _generate_tools_list(self, mcp_tools: list) -> str:
    """生成 MCP Tools 列表"""
    if not mcp_tools:
        return "（没有可用的 MCP Tools）"
    
    tools = [f"- {tool.get('name', 'unknown')}: {tool.get('description', '')}" 
             for tool in mcp_tools]
    return "\n".join(tools)
```

**任务**:
- [ ] 修改 `_get_system_prompt()` 方法
- [ ] 实现 `_generate_skills_index()` 方法
- [ ] 实现 `_generate_tools_list()` 方法
- [ ] 测试 System Prompt 是否正确生成

---

#### 3.4 实现 Plan 提取逻辑（1 天）

**文件**: `backend/app/agent_platform/plan_parser.py`（新建）

```python
"""
Plan Parser - 从 Agent 输出中提取执行计划
"""

import json
import re
from typing import Optional, List
from loguru import logger
from .models import ExecutionPlan, TodoItem, TodoStatus

class PlanParser:
    """执行计划解析器"""
    
    @staticmethod
    def extract_plan_from_text(text: str, task_id: str) -> Optional[ExecutionPlan]:
        """
        从 Agent 输出文本中提取执行计划
        
        支持多种格式：
        1. JSON 格式（最标准）
        2. Markdown 列表格式
        3. 纯文本列表格式
        
        Args:
            text: Agent 输出文本
            task_id: 任务 ID
        
        Returns:
            ExecutionPlan 或 None
        """
        
        # 尝试 JSON 格式
        plan = PlanParser._extract_json_plan(text, task_id)
        if plan:
            return plan
        
        # 尝试 Markdown 列表格式
        plan = PlanParser._extract_markdown_plan(text, task_id)
        if plan:
            return plan
        
        # 尝试纯文本格式
        plan = PlanParser._extract_text_plan(text, task_id)
        if plan:
            return plan
        
        return None
    
    @staticmethod
    def _extract_json_plan(text: str, task_id: str) -> Optional[ExecutionPlan]:
        """提取 JSON 格式的计划"""
        # 查找 JSON 代码块
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, text, re.DOTALL)
        
        if not match:
            return None
        
        try:
            plan_data = json.loads(match.group(1))
            todos = []
            
            for i, todo_data in enumerate(plan_data.get("todos", [])):
                todos.append(TodoItem(
                    id=todo_data.get("id", f"todo_{i+1}"),
                    title=todo_data.get("title", ""),
                    description=todo_data.get("description"),
                    dependencies=todo_data.get("dependencies", []),
                ))
            
            return ExecutionPlan(
                plan_id=f"plan_{task_id}",
                task_id=task_id,
                todos=todos
            )
        
        except Exception as e:
            logger.warning(f"Failed to parse JSON plan: {e}")
            return None
    
    @staticmethod
    def _extract_markdown_plan(text: str, task_id: str) -> Optional[ExecutionPlan]:
        """提取 Markdown 列表格式的计划"""
        # 查找 "执行计划" 或 "Todo" 后面的列表
        lines = text.split('\n')
        todos = []
        in_plan = False
        
        for line in lines:
            # 判断是否进入计划区域
            if '执行计划' in line or 'Todo' in line or '📋' in line:
                in_plan = True
                continue
            
            # 提取列表项
            if in_plan:
                # 匹配 "1. xxx" 或 "- xxx" 或 "• xxx"
                match = re.match(r'^\s*[\d\-•]\s*[✅⏳❌]?\s*(.+)$', line)
                if match:
                    title = match.group(1).strip()
                    todos.append(TodoItem(
                        id=f"todo_{len(todos)+1}",
                        title=title,
                    ))
                elif line.strip() == '':
                    # 空行，可能结束
                    if len(todos) > 0:
                        break
        
        if len(todos) > 0:
            return ExecutionPlan(
                plan_id=f"plan_{task_id}",
                task_id=task_id,
                todos=todos
            )
        
        return None
    
    @staticmethod
    def _extract_text_plan(text: str, task_id: str) -> Optional[ExecutionPlan]:
        """提取纯文本格式的计划（最宽松）"""
        # TODO: 实现纯文本解析
        return None
```

**任务**:
- [ ] 创建 `plan_parser.py`
- [ ] 实现 3 种格式的解析器
- [ ] 创建单元测试

**测试用例**:
```python
def test_extract_json_plan():
    text = '''
    好的，让我制定执行计划：
    
    ```json
    {
      "todos": [
        {"id": "todo_1", "title": "查询项目", "description": "..."},
        {"id": "todo_2", "title": "分析数据", "dependencies": ["todo_1"]}
      ]
    }
    ```
    '''
    
    plan = PlanParser.extract_plan_from_text(text, "task_123")
    assert plan is not None
    assert len(plan.todos) == 2
    assert plan.todos[0].title == "查询项目"
```

---

#### 3.5 集成到 Runtime（0.5 天）

**文件**: `backend/app/agent_platform/runtime.py`

在 `stream_events()` 中添加 Plan 提取逻辑：

```python
async def stream_events(self, result: RunResult, task_id: str, ...) -> AsyncIterator[AgentTaskEvent]:
    """流式读取 SDK 事件"""
    
    from .plan_parser import PlanParser
    
    assistant_message_content = ""
    plan_extracted = False
    
    async for sdk_event in result.stream_events():
        # ... 现有事件处理 ...
        
        # 累积 assistant 消息
        if sdk_event.type == "message.delta":
            assistant_message_content += sdk_event.delta
            
            # 尝试提取 Plan（当消息足够长时）
            if not plan_extracted and len(assistant_message_content) > 100:
                plan = PlanParser.extract_plan_from_text(
                    assistant_message_content,
                    task_id
                )
                
                if plan:
                    # 推送 Plan 事件
                    sequence += 1
                    plan_event = AgentTaskEvent(
                        event_id=f"event_{task_id}_{sequence}",
                        task_id=task_id,
                        event_type="plan.created",  # 新事件类型
                        payload={"plan": plan.dict()},
                        sequence=sequence,
                    )
                    await self.repo.append_event(plan_event)
                    yield plan_event
                    
                    plan_extracted = True
```

**任务**:
- [ ] 在 Runtime 中集成 Plan 提取
- [ ] 添加新事件类型 `plan.created`
- [ ] 测试 Plan 事件是否正确推送

---

### ✅ 验收标准

#### 功能验收
- [ ] Todo 数据模型定义完成
- [ ] Plan-Execute System Prompt 完成
- [ ] Runtime 生成正确的 System Prompt（包含 Skills 和 Tools 索引）
- [ ] PlanParser 能解析至少 2 种格式
- [ ] Plan 事件能正确推送到前端

#### 测试用例

**测试 1: System Prompt 生成**
```python
prompt = runtime._get_system_prompt("conversation", mcp_tools=[...])
# 验证包含:
# - "Plan-Execute"
# - Skills 索引
# - Tools 列表
assert "Plan-Execute" in prompt
assert "project-management" in prompt
```

**测试 2: Plan 提取**
```python
text = "执行计划：\n1. 查询项目\n2. 分析数据"
plan = PlanParser.extract_plan_from_text(text, "task_123")
assert len(plan.todos) == 2
```

**测试 3: E2E 测试**
```
用户: "帮我优化项目 A"
预期:
1. Agent 生成 Plan（包含 3-5 个 Todo）
2. 前端收到 plan.created 事件
3. Agent 逐步执行每个 Todo
```

---

### 📦 交付物清单
- [ ] `models.py` - Todo 和 Plan 模型
- [ ] `prompts.py` - Plan-Execute Prompt
- [ ] `plan_parser.py` - Plan 解析器
- [ ] `runtime.py` - 集成 Plan 提取
- [ ] 单元测试 + E2E 测试报告

---

### 🐛 风险与问题

**已知风险**:
1. Agent 可能不按格式输出 Plan
2. Plan 解析可能失败

**缓解措施**:
1. 在 Prompt 中明确要求格式
2. 支持多种解析格式（宽松匹配）
3. 即使解析失败，Agent 仍能正常工作（降级为普通模式）

---

### 📝 开发日志
（开发过程中每天更新）


## Block 4: System Prompt 增强与测试

### 📅 基本信息
- **预计工作量**: 2-3 天
- **开始日期**: TBD
- **完成日期**: TBD
- **状态**: 📋 待开始
- **依赖**: Block 1-3
- **优先级**: P0（必须）

---

### 🎯 目标
完善 System Prompt，测试和优化 Agent 编排能力，确保 Plan-Execute + Skills 工作正常。

---

### 📋 任务清单

#### 4.1 完善 System Prompt（1 天）
- [ ] 添加决策规则（何时用 Plan、何时用 Skills、何时直接回答）
- [ ] 添加错误处理指导
- [ ] 添加输出格式规范
- [ ] 测试多轮对话的上下文保持

#### 4.2 E2E 测试（1-2 天）
- [ ] 测试场景 1: 简单查询（不需要 Plan）
- [ ] 测试场景 2: 复杂任务（需要 Plan）
- [ ] 测试场景 3: Skills 调用
- [ ] 测试场景 4: 错误处理
- [ ] 测试场景 5: 多轮对话

#### 4.3 调优（0.5-1 天）
- [ ] 根据测试结果调整 Prompt
- [ ] 优化 Plan 生成质量
- [ ] 优化 Skills 选择准确性

---

### ✅ 验收标准

**MVP-2 里程碑达成标准**：
- [ ] Agent 能够分解复杂任务（生成 Plan）
- [ ] Agent 能够调用 Skills
- [ ] Agent 能够使用 MCP Tools
- [ ] 简单任务不过度规划（直接回答）
- [ ] 通过 5 个 E2E 测试场景

---

### 📦 交付物
- [ ] 完善的 System Prompt
- [ ] E2E 测试报告（5 个场景 + 截图）
- [ ] 调优记录文档

---

---

## 🎯 阶段 2: AG-UI 协议集成

**重要说明**: 阶段 2 的所有 Block（5-9）与阶段 1 **不冲突**，它们是在现有 Agent 编排能力基础上，增加前后端协同能力。

---

## Block 5: Shared State（状态同步）

### 📅 基本信息
- **预计工作量**: 2-3 天
- **依赖**: Block 1-4（Agent 编排基础）
- **优先级**: P0

### 🎯 目标
实现前后端状态同步，让 Agent 知道用户当前上下文。

### 📋 核心任务
1. Backend: 创建 `agui_state.py` (~200 行)
2. Frontend: 创建 `useSharedState.ts` (~80 行)
3. 集成到现有组件（ProjectList.vue 等）
4. 测试双向同步

**详细任务清单**: 参考之前写的 Block 1 内容（现在是 Block 5）

---

## Block 6: Human-in-the-Loop（人机协作）

### 📅 基本信息
- **预计工作量**: 2-3 天
- **依赖**: Block 5
- **优先级**: P0

### 🎯 目标
实现危险操作确认机制。

### 📋 核心任务
1. Backend: 创建 `agui_hitl.py` (~150 行)
2. Backend API: `/agui/hitl/{operation_id}/respond`
3. Frontend: 创建 `useHITL.ts` (~50 行)
4. 集成到 Skills（修改 hitl-operations Skill）
5. 测试确认流程

---

## Block 7: Generative UI（动态生成 UI）

### 📅 基本信息
- **预计工作量**: 3-4 天
- **依赖**: Block 5
- **优先级**: P1（重要但非必须）

### 🎯 目标
Agent 能够动态生成图表、表格等 UI 组件。

### 📋 核心任务
1. Backend: 创建 `agui_genui.py` (~150 行)
2. Frontend: 创建 `GenerativeUIRenderer.vue` (~200 行)
3. 实现图表组件（ECharts）
4. 实现表格组件
5. 实现指标卡片
6. 测试 UI 生成

---

## Block 8: Frontend Actions（前端控制）

### 📅 基本信息
- **预计工作量**: 2-3 天
- **依赖**: Block 5
- **优先级**: P1

### 🎯 目标
Agent 能够控制前端行为（导航、刷新等）。

### 📋 核心任务
1. Backend: 创建 `agui_frontend_actions.py` (~100 行)
2. Frontend: 创建 `useFrontendActions.ts` (~100 行)
3. 实现 6 个核心 Actions（navigate、open_dialog 等）
4. 测试 Actions 执行

---

## Block 9: AG-UI 路由集成

### 📅 基本信息
- **预计工作量**: 2-3 天
- **依赖**: Block 5-8
- **优先级**: P0

### 🎯 目标
统一 AG-UI 端点，完成完整集成。

### 📋 核心任务
1. 创建 `/api/v1/agent/agui/stream` 端点
2. 实现事件转换层（OpenAI Events → AG-UI Events）
3. 集成所有 AG-UI 能力
4. Frontend 完整集成
5. E2E 测试

**详细设计**: 参考之前的设计文档

---

---

## 🎯 阶段 3: 测试与优化

---

## Block 10: E2E 测试

### 📅 基本信息
- **预计工作量**: 3-4 天
- **依赖**: Block 1-9
- **优先级**: P0

### 📋 核心任务
1. 完整功能测试（20+ 测试场景）
2. 性能测试（响应时间、并发）
3. 压力测试
4. 错误恢复测试
5. 浏览器兼容性测试

---

## Block 11: 生产部署

### 📅 基本信息
- **预计工作量**: 2-3 天
- **依赖**: Block 10
- **优先级**: P0

### 📋 核心任务
1. 生产环境配置
2. 监控和日志
3. 备份和恢复方案
4. 灰度发布计划
5. 用户文档

---

---

## 📊 总结

### 代码量估算

| 阶段 | 模块 | 代码量 |
|------|------|--------|
| **阶段 1** | Skills 系统 | ~300 行 |
| | Plan-Execute 框架 | ~500 行 |
| | System Prompt | ~200 行 |
| | 测试代码 | ~300 行 |
| **阶段 2** | Shared State | ~300 行 |
| | HITL | ~200 行 |
| | Generative UI | ~350 行 |
| | Frontend Actions | ~200 行 |
| | AG-UI 路由 | ~150 行 |
| **总计** | | **~2500 行** |

### 时间估算

| 阶段 | 时间 |
|------|------|
| 阶段 1: Agent 编排 | 2-3 周 |
| 阶段 2: AG-UI 协议 | 2-3 周 |
| 阶段 3: 测试与优化 | 1 周 |
| **总计** | **5-7 周** |

---

## 🚀 下一步行动

### 立即开始
1. **Review 本文档**，确认路线图
2. **创建 GitHub Issues**（每个 Block 一个 Issue）
3. **开始 Block 1**: Skills 系统基础

### 开发流程
1. 每个 Block 开始前，阅读任务清单
2. 开发过程中，更新开发日志
3. 完成后，验收并标记 ✅
4. 提交代码，关闭 Issue
5. 开始下一个 Block

### 里程碑检查点
- **Week 2**: 完成 Block 1-2（MVP-1: Skills 可用）
- **Week 3**: 完成 Block 3-4（MVP-2: 完整 Agent 编排）
- **Week 5**: 完成 Block 5-6（MVP-3: AG-UI 基础）
- **Week 7**: 完成 Block 7-11（MVP-4: 完整产品）

---

## 📝 版本历史

- **v2.0** (2025-06-13): 基于真实项目状态重写
- **v1.0** (2025-06-13): 初始版本（已废弃）


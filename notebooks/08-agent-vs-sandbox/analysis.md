# Agent vs SandboxAgent 选型分析

## 核心结论（TL;DR）

**对 ANIFORCE 游戏营销 Agent 平台的推荐：**

```text
主 Agent 使用：Agent（常规 Agent）
MCP 工具：必须保留
Skills：不使用（不是 SandboxAgent 独有，但确实只在 sandbox 场景有意义）
Sandbox：按需使用，不作为默认基础设施
```

---

## 1. Agent vs SandboxAgent 的本质区别

### 1.1 类继承关系

```python
Agent[TContext]                    # 常规 Agent
  ↓
SandboxAgent[TContext]             # 继承 Agent，添加 sandbox 配置
```

**SandboxAgent 本质上就是 Agent + sandbox 配置**。它不是完全不同的类型，而是 Agent 的一个子类。

### 1.2 SandboxAgent 额外提供的字段

```python
@dataclass
class SandboxAgent(Agent[TContext]):
    default_manifest: Manifest | None = None
    base_instructions: str | Callable | None = None
    capabilities: Sequence[Capability] = field(default_factory=Capabilities.default)
    run_as: User | str | None = None
```

**核心差异：**

- `default_manifest`: 定义 sandbox 工作区结构
- `capabilities`: sandbox 能力（Filesystem / Shell / Skills / Compaction）
- `run_as`: sandbox 执行用户身份
- `base_instructions`: 覆盖 SDK sandbox 基础提示词

### 1.3 Capabilities.default()

```python
Capabilities.default() = [
    Filesystem(),  # 文件读写能力
    Shell(),       # 命令执行能力
    Compaction(),  # 上下文压缩能力
]
```

注意：**Skills 不在 default 里**，需要显式添加。

---

## 2. Skills 是否是 SandboxAgent 独有？

### 2.1 技术上的答案

**Skills 不是 SandboxAgent 的独占能力，但确实只在 sandbox 场景有意义。**

原因：

1. **Skills 是一个 Capability**

   ```python
   class Skills(Capability):
       type: Literal["skills"] = "skills"
       skills: list[Skill] = []
       from_: BaseEntry | None = None
       lazy_from: LazySkillSource | None = None
       skills_path: str = ".agents"
   ```
2. **Capability 的核心职责：**

   - `process_manifest(manifest)` - 修改 Manifest，注入 skill 文件到工作区
   - `instructions(manifest)` - 生成 LLM 可见的 skills 索引和使用说明
   - `tools()` - 提供 `load_skill` 工具（lazy 模式）
   - `bind(session)` - 绑定到 SandboxSession
3. **Skills 依赖 Sandbox 的原因：**

   - Skills 需要把 `SKILL.md` / `scripts/` / `references/` / `assets/` 物化到 sandbox 工作区
   - LLM 需要通过 Filesystem capability 读取 `SKILL.md`
   - LLM 需要通过 Shell capability 执行 `scripts/`
   - Skills 的 `lazy_from` 需要 `load_skill` 工具调用 `session.read()` / `LocalDir.apply()`

### 2.2 能否在普通 Agent 中使用 Skills？

**理论上不行，实际上也不应该。**

原因：

- Skills 的 `process_manifest()` 需要修改 Manifest
- Skills 的 `instructions()` 需要读取 sandbox session 中的 `SKILL.md` 文件
- Skills 的 `load_skill` 工具需要 `BaseSandboxSession`
- 普通 Agent 没有 sandbox session，无法执行这些操作

**替代方案：**

如果想在普通 Agent 中实现类似功能：

```python
# 方案 A：手动注入 instructions
agent = Agent(
    name="Assistant",
    instructions=f"""
你是营销助手。

## 可用技能
- analyze_campaign: 分析广告投放数据
- generate_creative_brief: 生成素材创意 brief

## 技能使用说明
...
""",
    tools=[analyze_campaign_tool, generate_creative_brief_tool],
)

# 方案 B：使用 MCP 工具暴露技能
@mcp.tool()
async def analyze_campaign(...):
    # 技能实现
    pass
```

---

## 3. ANIFORCE 场景分析

### 3.1 当前业务特点

**ANIFORCE 是游戏营销 SaaS 平台，核心场景：**

- 项目管理（创建项目、配置预算、设置目标市场）
- 广告计划管理（创建 campaign、设置平台、预算分配）
- 素材管理（上传素材、分析素材表现、生成素材 brief）
- 数据分析（投放数据分析、ROI 分析、趋势预测）
- 报告生成（投放报告、素材分析报告、策略建议）

**关键约束：**

- Backend PostgreSQL 是业务事实源
- MCP 工具通过 backend_client 调用 REST API
- 权限校验在 Backend 侧
- 多租户隔离通过 JWT token
- 前端 Workspace 状态通过 context_snapshot 传递

### 3.2 是否需要 Sandbox？

#### 场景分类

| 场景类型                               | 是否需要 Sandbox | 推荐方案                          |
| -------------------------------------- | ---------------- | --------------------------------- |
| **问答查询**                     | ❌ 不需要        | Agent + MCP tools                 |
| 简单数据查询（列出项目、查看campaign） | ❌ 不需要        | Agent + MCP tools                 |
| 简单数据分析（单表查询、简单聚合）     | ❌ 不需要        | Agent + MCP tools                 |
| **单文件生成**                   | ⚠️ 可选        | Agent + MCP tools 或 轻量 Sandbox |
| 生成营销报告（单个 markdown）          | ⚠️ 可选        | Agent 直接返回 markdown 文本      |
| 生成素材 brief（单个 JSON/markdown）   | ⚠️ 可选        | Agent 直接返回 JSON 文本          |
| **多文件产物**                   | ✅ 需要          | SandboxAgent + artifact upload    |
| 生成素材包（多个图片 + 配置文件）      | ✅ 需要          | SandboxAgent + output/ 扫描上传   |
| 生成投放配置（多平台配置文件）         | ✅ 需要          | SandboxAgent + output/ 扫描上传   |
| 复杂数据分析（需要写 Python 脚本）     | ✅ 需要          | SandboxAgent + Python 环境        |
| **多轮文件编辑**                 | ✅ 需要          | SandboxAgent + snapshot           |
| 持续修改同一份 creative_brief.md       | ✅ 需要          | SandboxAgent + 恢复 snapshot      |
| 迭代完善投放策略文档                   | ✅ 需要          | SandboxAgent + 恢复 snapshot      |
| **不可信代码执行**               | ✅ 强烈需要      | SandboxAgent + DockerSandbox      |
| 执行用户上传的 Python 分析脚本         | ✅ 强烈需要      | Docker 隔离                       |
| 处理用户上传的素材文件（ffmpeg）       | ✅ 强烈需要      | Docker 隔离                       |

#### 统计估算

假设 ANIFORCE 的任务分布：

- 70% - 问答查询 + 简单查询 → **不需要 Sandbox**
- 20% - 单文件生成 + 简单分析 → **可选 Sandbox**
- 8% - 多文件产物 + 多轮编辑 → **需要 Sandbox**
- 2% - 不可信代码执行 → **强烈需要 Docker Sandbox**

**结论：大部分任务不需要完整 Sandbox**

### 3.3 Skills 对 ANIFORCE 的价值

#### Skills 的典型用途

```text
Skills 适合：
- 代码生成（Web 开发、移动开发、后端 API）
- 数据分析脚本（Python、R、SQL）
- DevOps 自动化（Terraform、Kubernetes、CI/CD）
- 文档编写（技术文档、API 文档、架构设计）
- 测试用例生成（单元测试、集成测试）
```

#### ANIFORCE 是否需要 Skills？

**短期（MVP）：不需要**

原因：

- ANIFORCE 的核心任务是营销管理，不是代码生成
- 营销知识可以直接写在 instructions 或 system prompt 里
- 复杂营销逻辑更适合封装成 MCP 工具
- Skills 增加学习成本和维护负担

**中长期（扩展能力）：可能需要**

适合的场景：

```text
Skill: generate_ad_creative_brief
描述：生成符合品牌调性的广告素材创意 brief
包含：
  - scripts/analyze_brand_guidelines.py
  - references/successful_creative_examples.md
  - assets/creative_brief_template.md

Skill: analyze_campaign_performance
描述：分析广告投放数据，生成优化建议
包含：
  - scripts/calculate_roi.py
  - scripts/detect_anomaly.py
  - references/performance_metrics_guide.md

Skill: generate_platform_config
描述：生成各平台投放配置文件
包含：
  - scripts/validate_meta_config.py
  - scripts/validate_tiktok_config.py
  - assets/meta_campaign_template.json
  - assets/tiktok_campaign_template.json
```

但即使这些场景，也可以用 MCP 工具实现：

```python
@mcp.tool()
async def generate_ad_creative_brief(
    project_id: str,
    brand_guidelines: str,
    target_audience: str
) -> dict:
    # 内部调用 brand analysis logic
    # 读取 successful examples from DB
    # 生成 creative brief
    pass
```

**Skills vs MCP 工具对比：**

| 维度                 | Skills                                   | MCP 工具             |
| -------------------- | ---------------------------------------- | -------------------- |
| **实现复杂度** | 需要 Sandbox + Manifest + 文件物化       | 直接 Python 函数     |
| **调试难度**   | 需要检查 SKILL.md、scripts、sandbox 状态 | 直接打断点           |
| **版本管理**   | Git repo + manifest 配置                 | 直接 Python 代码     |
| **动态加载**   | 支持 lazy_from Git                       | 需要重启服务         |
| **权限校验**   | 依赖 sandbox 用户权限                    | 可以直接读 JWT token |
| **审计日志**   | 需要扫描 sandbox 文件操作                | 直接记录函数调用     |
| **成本**       | 每次 run 需要 sandbox 开销               | 无额外开销           |

**ANIFORCE 推荐：优先使用 MCP 工具，只在以下情况考虑 Skills：**

- 营销团队需要自己编写和维护技能包
- 技能需要独立版本发布
- 不同客户需要不同技能包
- 技能涉及复杂的多文件操作和脚本执行

---

## 4. 推荐架构

### 4.1 短期架构（MVP）

```python
# aniforce-agent/app/agent/openai_adapter.py

def create_agent(
    self,
    name: str,
    instructions: str | Callable,
    mcp_servers: list,
    session_id: str | None = None,
) -> Agent:
    """创建常规 Agent（不是 SandboxAgent）"""
  
    agent = Agent(
        name=name,
        instructions=instructions,
        model=self.model,
        mcp_servers=mcp_servers,  # MCP 工具
        # 不使用 capabilities
        # 不使用 default_manifest
    )
  
    return agent
```

**优点：**

- 简单、稳定、易调试
- 延迟低（不需要创建 sandbox）
- 多实例友好（无状态）
- 成本低（不需要 sandbox 资源）

**适合场景：**

- 问答查询
- 项目/campaign/素材管理
- 简单数据分析
- 单文件报告生成

### 4.2 中期架构（混合模式）

根据任务类型动态选择：

```python
# aniforce-agent/app/agent/runtime.py

async def run_task(self, task: AgentTask, user_input: str):
    # 根据任务类型选择 Agent 类型
    if task.task_type in ["sandbox_required", "complex_analysis", "multi_file_generation"]:
        agent = self._create_sandbox_agent(task)
        run_config = RunConfig(
            sandbox=SandboxRunConfig(
                client=UnixLocalSandboxClient(),
                manifest=self._build_manifest(task),
            )
        )
    else:
        agent = self._create_agent(task)
        run_config = RunConfig()
  
    result = Runner.run_streamed(agent, user_input, run_config=run_config)
    # ...
```

**优点：**

- 灵活，按需使用 sandbox
- 简单任务保持低延迟
- 复杂任务享受 sandbox 隔离

**适合场景：**

- 70% 简单任务走常规 Agent
- 30% 复杂任务走 SandboxAgent

### 4.3 长期架构（强隔离 + Skills）

如果未来需要强隔离和 Skills：

```python
# aniforce-agent/app/agent/openai_adapter.py

def create_sandbox_agent(
    self,
    name: str,
    instructions: str | Callable,
    mcp_servers: list,
    skills_dir: Path | None = None,
    session_id: str | None = None,
) -> SandboxAgent:
    """创建 SandboxAgent"""
  
    capabilities = [
        Filesystem(),
        Shell(),
        Compaction(),
    ]
  
    if skills_dir:
        capabilities.append(
            Skills(
                lazy_from=LocalDirLazySkillSource(
                    source=LocalDir(src=skills_dir)
                ),
                skills_path=".agents",
            )
        )
  
    agent = SandboxAgent(
        name=name,
        instructions=instructions,
        model=self.model,
        mcp_servers=mcp_servers,
        capabilities=capabilities,
        default_manifest=Manifest(
            root="/workspace",
            users=[User(name="analyst")],
            entries={
                "output": Dir(),
            },
        ),
        run_as="analyst",
    )
  
    return agent
```

---

## 5. Skills 实现建议（如果未来需要）

### 5.1 Skills 目录结构

```text
skills/
├── generate_creative_brief/
│   ├── SKILL.md                # 主文档
│   ├── scripts/
│   │   ├── analyze_brand.py
│   │   └── generate_brief.py
│   ├── references/
│   │   ├── brand_guidelines.md
│   │   └── creative_examples.json
│   └── assets/
│       └── brief_template.md
├── analyze_campaign/
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── calculate_metrics.py
│   │   └── detect_anomaly.py
│   └── references/
│       └── metrics_guide.md
└── generate_platform_config/
    ├── SKILL.md
    ├── scripts/
    │   └── validate_config.py
    └── assets/
        ├── meta_template.json
        └── tiktok_template.json
```

### 5.2 SKILL.md 示例

```markdown
---
name: generate_creative_brief
description: 生成符合品牌调性的广告素材创意 brief
---

# Generate Creative Brief

## Purpose
根据项目品牌调性、目标受众、投放平台生成创意 brief。

## When to use
- 用户要求生成素材 brief
- 用户要求生成创意方向
- 用户提到"创意"、"素材策划"

## Workflow
1. 读取 `references/brand_guidelines.md` 了解品牌调性
2. 读取项目信息（通过 MCP 工具）
3. 运行 `scripts/analyze_brand.py` 分析品牌特点
4. 使用 `assets/brief_template.md` 生成 brief
5. 运行 `scripts/generate_brief.py` 完成最终输出
6. 保存到 `output/creative_brief.md`

## Files
- `scripts/analyze_brand.py`: 品牌分析脚本
- `scripts/generate_brief.py`: Brief 生成脚本
- `references/brand_guidelines.md`: 品牌调性参考
- `assets/brief_template.md`: Brief 模板
```

### 5.3 配置 lazy Skills

```python
capabilities = [
    Filesystem(),
    Shell(),
    Compaction(),
    Skills(
        lazy_from=LocalDirLazySkillSource(
            source=LocalDir(src="/app/skills")
        ),
        skills_path=".agents",
    ),
]
```

**lazy 模式的好处：**

- Skills 不会在启动时全部加载到 workspace
- LLM 先看到 skills 索引（name + description + path）
- LLM 决定使用某个 skill 时，调用 `load_skill` 工具按需加载
- 减少初始 workspace 体积
- 减少 LLM 初始上下文

---

## 6. 最终推荐

### 6.1 短期（当前）

✅ **使用常规 Agent**

- 简单、稳定、低延迟
- MCP 工具完全够用
- 多实例友好

❌ **不使用 SandboxAgent**

- 增加复杂度
- 增加延迟
- 多实例需要额外架构设计

❌ **不使用 Skills**

- 当前场景不需要
- 营销知识直接写 instructions
- 复杂逻辑封装成 MCP 工具

### 6.2 中期（3-6个月）

⚠️ **按需混合使用 Agent 和 SandboxAgent**

- 简单任务：Agent + MCP
- 复杂任务：SandboxAgent + 轻量 manifest
- 多文件产物：SandboxAgent + output/ 扫描上传
- 不可信代码：Docker Sandbox

❌ **仍不使用 Skills**

- 等待明确的 Skills 需求
- 优先完善 MCP 工具体系

### 6.3 长期（6-12个月）

⚠️ **可选：引入 Skills**

- 前提：营销团队需要自己维护技能包
- 前提：有明确的 Skills 复用场景
- 前提：Sandbox 架构已经稳定

**判断标准：**

```text
如果以下条件满足 >= 3 个，考虑引入 Skills：
1. 有多个复杂的多步骤工作流
2. 工作流涉及多个脚本和参考文档
3. 不同客户需要不同技能包
4. 营销团队需要自己编写技能
5. 技能需要独立版本管理和发布
6. 技能需要跨项目复用
```

---

## 7. 关键决策表

| 问题                            | 答案                                                | 原因                                          |
| ------------------------------- | --------------------------------------------------- | --------------------------------------------- |
| 使用 Agent 还是 SandboxAgent？  | **Agent**                                     | 70%+ 任务不需要 sandbox，保持简单             |
| 是否需要 Sandbox？              | **按需使用**                                  | 只在多文件产物、多轮编辑、不可信代码时才需要  |
| Skills 是 SandboxAgent 独有吗？ | **技术上不是，但确实只在 sandbox 场景有意义** | Skills 依赖 sandbox 工作区、Filesystem、Shell |
| 是否使用 Skills？               | **短期不用，长期可选**                        | 当前 MCP 工具足够，Skills 增加复杂度          |
| MCP 工具 vs Skills？            | **优先 MCP 工具**                             | 简单、直接、易调试、易权限管理                |
| 如何支持多文件产物？            | **SandboxAgent + output/ 扫描上传**           | 需要 sandbox 但不需要 Skills                  |
| 如何支持多轮编辑？              | **SandboxAgent + snapshot**                   | 需要 sandbox 和 snapshot，不需要 Skills       |
| 多实例兼容？                    | **优先 Agent（无状态）**                      | SandboxAgent 需要额外设计 snapshot 存储       |

---

## 8. 迁移路径（如果未来要引入 SandboxAgent）

### Phase 1：保持现状

- 继续使用 Agent + MCP tools
- 观察哪些任务确实需要 sandbox
- 收集 sandbox 需求

### Phase 2：混合模式

- 新增 `task.requires_sandbox` 标志
- 根据标志动态选择 Agent 或 SandboxAgent
- 简单任务继续走 Agent
- 复杂任务走 SandboxAgent

### Phase 3：Sandbox 基础设施

- 实现对象存储 snapshot
- 实现 run 后 output/ 扫描上传
- 实现 artifact metadata 管理
- 可选切换到 DockerSandbox

### Phase 4：可选 Skills

- 评估是否真的需要 Skills
- 如果需要，设计 skills 目录结构
- 实现 lazy Skills 加载
- 营销团队培训

---

## 9. 附录：代码示例

### 9.1 当前推荐（Agent + MCP）

```python
agent = Agent(
    name="ANIFORCE Assistant",
    instructions=workspace_instructions,
    model=model,
    mcp_servers=[mcp_server],
)

result = await Runner.run_streamed(
    agent,
    input=user_input,
    context=workspace_context,
    session=session,
)
```

### 9.2 未来可选（SandboxAgent）

```python
agent = SandboxAgent(
    name="ANIFORCE Complex Task Agent",
    instructions=workspace_instructions,
    model=model,
    mcp_servers=[mcp_server],
    capabilities=[Filesystem(), Shell(), Compaction()],
    default_manifest=Manifest(
        root="/workspace",
        entries={
            "project": LocalDir(src=project_dir),
            "output": Dir(),
        },
    ),
    run_as="analyst",
)

result = await Runner.run_streamed(
    agent,
    input=user_input,
    context=workspace_context,
    session=session,
    run_config=RunConfig(
        sandbox=SandboxRunConfig(
            client=UnixLocalSandboxClient(),
        )
    ),
)

# run 后扫描 output/
output_files = await scan_output(sandbox_session)
await upload_artifacts(output_files, object_storage)
```

### 9.3 未来可选（SandboxAgent + Skills）

```python
agent = SandboxAgent(
    name="ANIFORCE Skills Agent",
    instructions=workspace_instructions,
    model=model,
    mcp_servers=[mcp_server],
    capabilities=[
        Filesystem(),
        Shell(),
        Compaction(),
        Skills(
            lazy_from=LocalDirLazySkillSource(
                source=LocalDir(src="/app/skills")
            ),
            skills_path=".agents",
        ),
    ],
    default_manifest=Manifest(
        root="/workspace",
        entries={"output": Dir()},
    ),
    run_as="analyst",
)
```

---

## 总结

**ANIFORCE 当前最佳选择：Agent + MCP tools**

不需要：

- ❌ SandboxAgent（短期）
- ❌ Skills（短期和中期）
- ❌ 完整 Sandbox 基础设施（短期）

可选（中长期）：

- ⚠️ 按需 SandboxAgent（多文件产物、多轮编辑、不可信代码）
- ⚠️ Snapshot（多轮编辑场景）
- ⚠️ Skills（如果营销团队需要自己维护技能包）

核心原则：

```text
Keep it simple.
Don't introduce complexity until you need it.
MCP tools > Skills for ANIFORCE's use cases.
Sandbox is a capability, not a requirement.
```

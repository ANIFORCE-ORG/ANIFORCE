# Skills 目录结构说明

## 推荐结构

```
backend/runtime/
├── agent/
│   ├── tasks.db           # Agent 任务数据库
│   └── sessions.db        # Session 历史数据库
│
└── skills/                # Skills 定义目录
    ├── project-management/
    │   ├── SKILL.md
    │   └── scripts/       # 可选：辅助脚本
    │
    ├── campaign-optimization/
    │   ├── SKILL.md
    │   └── templates/     # 可选：模板文件
    │
    ├── data-reporting/
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── generate_report.py
    │   └── templates/
    │       └── report_template.md
    │
    └── batch-operations/
        └── SKILL.md
```

## 为什么放在 runtime/ 下？

1. **隔离运行时资源**：Skills、数据库、缓存都是运行时产生/使用的
2. **便于管理**：所有 Agent 运行时资源集中管理
3. **符合规范**：按照开发规范，运行时数据应该集中存放

## 代码配置

```python
from pathlib import Path
from agents.sandbox.capabilities import Skills, LocalDirLazySkillSource
from agents.sandbox.entries import LocalDir

# Skills 在宿主机的位置
SKILLS_DIR = Path("backend/runtime/skills")

agent = SandboxAgent(
    name="ANIFORCE Assistant",
    instructions=SYSTEM_PROMPT,
    capabilities=Capabilities.default() + [
        Skills(
            lazy_from=LocalDirLazySkillSource(
                source=LocalDir(src=SKILLS_DIR)  # 宿主机路径
            )
        )
    ]
)
```

## Skills 工作流程

1. **宿主机**：SDK 读取 `backend/runtime/skills/`
2. **索引生成**：扫描所有 `SKILL.md`，提取 name 和 description
3. **注入 Prompt**：将索引注入到 Agent instructions
4. **Agent 决策**：Agent 看到索引，决定使用某个 Skill
5. **加载 Skill**：Agent 调用 `load_skill("project-management")`
6. **物化到 Sandbox**：SDK 将该 Skill 复制到 Sandbox 的 `.agents/skills/project-management/`
7. **Sandbox 执行**：Agent 在 Sandbox 中读取 `.agents/skills/project-management/SKILL.md` 并执行

## 关键点

- `src=` 路径是**宿主机路径**（SDK 进程可以访问的路径）
- Skills 会被复制到**Sandbox 的 `.agents/skills/` 目录**
- Agent 在 Sandbox 中读取 Skills，不是在宿主机直接读取

## 环境变量

```bash
# backend/.env
SKILLS_DIR=backend/runtime/skills
```


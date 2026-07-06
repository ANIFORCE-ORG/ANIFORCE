# SandboxAgent Manifest 学习简报

## 1. Manifest 的核心作用

`Manifest` 描述一次新沙盒会话启动时的工作区契约。

它回答的问题是：

- 沙盒里的工作区根目录在哪里。
- 启动前应该有哪些文件、目录或本地目录副本。
- 哪些文件是合成出来的，哪些目录来自宿主机。
- 运行时有哪些用户、组、权限和环境变量。
- 是否允许访问工作区之外的特定宿主机绝对路径。

一个典型工作区可以理解成：

```text
/workspace
├── repo/                       # 从宿主机 LocalDir 物化进来
├── workspace_notes/
│   └── task.md                 # Manifest 合成出来的任务文件
└── output/                     # Manifest 创建的输出目录
```

Manifest 不是给模型看的普通说明文字，而是 SDK 和 sandbox backend 用来准备工作区的结构化配置。模型通过 Shell、Filesystem 等能力在这个工作区里操作。

## 2. entry path 和宿主机路径的区别

`Manifest.entries` 的 key 是沙盒工作区内路径，必须是相对路径。

例如：

```python
entries={
    "repo": LocalDir(src=HOST_REPO_DIR),
    "workspace_notes/task.md": File(content=b"task"),
    "output": Dir(),
}
```

这里的含义是：

```text
repo                         沙盒里的目标路径
workspace_notes/task.md      沙盒里的目标路径
output                       沙盒里的目标路径
HOST_REPO_DIR                宿主机上的源目录
```

不要把 `"repo"` 理解成宿主机目录。它是沙盒里的路径。宿主机来源只出现在 `LocalDir(src=...)` 里。

错误示例：

```python
entries={
    "/tmp/report.md": File(content=b"bad"),
    "../outside": Dir(),
}
```

问题是：

- `"/tmp/report.md"` 是绝对路径，不是工作区内相对路径。
- `"../outside"` 试图逃逸工作区。

正确做法通常是：

```python
entries={
    "output/report.md": File(content=b"ok"),
}
```

## 3. File / Dir / LocalDir 的区别

### File

`File` 用来在沙盒工作区里合成一个小文件。

```python
"workspace_notes/task.md": File(
    content=b"# Task\n\nRead repo/task.md and write output/report.md.\n"
)
```

适合放：

- 任务说明。
- 小型配置。
- 小型辅助输入。

它不是从宿主机读取文件，而是由 `content` 直接生成。

### Dir

`Dir` 用来在沙盒工作区里创建一个目录。

```python
"output": Dir()
```

它不会读取宿主机上的同名目录。它只是创建一个空目录或带合成 children 的目录。

适合放：

- 输出目录。
- 合成目录结构。

### LocalDir

`LocalDir` 用来把宿主机目录物化到沙盒工作区。

```python
"repo": LocalDir(src=HOST_REPO_DIR)
```

含义是：

```text
宿主机 HOST_REPO_DIR  ->  沙盒 /workspace/repo
```

适合放：

- 要让 agent 检查或修改的本地代码仓库。
- 本地准备好的样例数据。
- 本地技能目录。

## 4. 推荐的 Manifest 写法

推荐把 `root` 写成沙盒内路径，例如 `/workspace`，而不是本机绝对路径。

```python
from agents.sandbox import FileMode, Manifest, Permissions, User
from agents.sandbox.entries import Dir, File, LocalDir
from agents.sandbox.manifest import Environment

private_permissions = Permissions(
    owner=FileMode.READ | FileMode.WRITE,
    group=FileMode.NONE,
    other=FileMode.NONE,
)

output_permissions = Permissions(
    owner=FileMode.ALL,
    group=FileMode.ALL,
    other=FileMode.NONE,
)

basic_manifest = Manifest(
    root="/workspace",
    users=[User(name="analyst")],
    environment=Environment(value={
        "DEMO_ENV": "manifest-env-visible-in-sandbox",
    }),
    entries={
        "repo": LocalDir(src=HOST_REPO_DIR),
        "workspace_notes/task.md": File(
            content=(
                b"# Manifest demo task\n\n"
                b"1. Read repo/task.md.\n"
                b"2. Write a short report to output/manifest_report.md.\n"
            ),
            permissions=private_permissions,
        ),
        "output": Dir(permissions=output_permissions),
    },
)
```

注意：当前 SDK 里 `environment` 应使用 `Environment(value={...})`，不要直接传普通 dict。

## 5. 用户、组和权限

Sandbox 的权限模型沿用 Unix/Linux 文件权限概念。

每个文件或目录有三类访问主体：

```text
owner  文件/目录的拥有者
group  文件/目录所属用户组里的成员
other  其他所有用户
```

权限位包括：

```text
READ   读
WRITE  写
EXEC   执行；对目录表示可进入、可访问目录下路径
ALL    READ | WRITE | EXEC
NONE   无权限
```

例如：

```python
Permissions(
    owner=FileMode.ALL,
    group=FileMode.ALL,
    other=FileMode.NONE,
)
```

含义是：

```text
owner 可读可写可执行
group 可读可写可执行
other 无权限
```

对目录来说，`EXEC` 很重要。没有 `EXEC`，即使有 `READ`，也可能无法进入目录或访问目录下文件。

## 6. 用户和组怎么声明

用户通过 `User` 声明，组通过 `Group` 声明。

```python
from agents.sandbox import Group, User

analyst = User(name="analyst")
reviewer = User(name="reviewer")

reviewers = Group(
    name="reviewers",
    users=[analyst, reviewer],
)

manifest = Manifest(
    users=[analyst, reviewer],
    groups=[reviewers],
    entries={
        "shared": Dir(
            group=reviewers,
            permissions=Permissions(
                owner=FileMode.ALL,
                group=FileMode.READ | FileMode.EXEC,
                other=FileMode.NONE,
            ),
        ),
    },
)
```

让 agent 以某个用户身份运行：

```python
agent = SandboxAgent(
    name="demo",
    model=model,
    instructions="...",
    default_manifest=manifest,
    run_as=analyst,
)
```

这表示 agent 的 shell 和文件操作应该以 `analyst` 身份执行。

## 7. 隔离机制

隔离有两层。

第一层是工作区隔离：

```text
/workspace
├── repo/
├── workspace_notes/
└── output/
```

Manifest entry path 只能声明工作区内的相对路径。这样清单不会随意把文件放到工作区外。

第二层是用户和权限隔离：

```text
owner / group / other
```

例如：

```python
private_permissions = Permissions(
    owner=FileMode.READ | FileMode.WRITE,
    group=FileMode.NONE,
    other=FileMode.NONE,
)
```

表示只有 owner 可以读写，组用户和其他用户都没有权限。

但权限是否真正强制执行，取决于 sandbox backend：

- 本地 Unix sandbox 会尽量映射到本地文件权限和执行用户。
- Docker sandbox 可以通过容器用户、文件权限和挂载策略隔离。
- 托管 sandbox 由服务端环境强制执行。
- 只在 Python 里构造 `Manifest` 对象，并不会自动产生系统级隔离。

## 8. extra_path_grants 的作用

默认情况下，Manifest 只应该描述工作区内的内容。

只有在两类场景下才考虑 `extra_path_grants`：

1. agent 需要访问工作区外的某个具体绝对路径。
2. `LocalFile.src` 或 `LocalDir.src` 需要复制 SDK 进程工作目录之外的受信任本地源。

示例：

```python
from agents.sandbox import SandboxPathGrant

manifest = Manifest(
    root="/workspace",
    entries={
        "repo": LocalDir(src=HOST_REPO_DIR),
        "output": Dir(),
    },
    extra_path_grants=(
        SandboxPathGrant(
            path="/opt/toolchain",
            read_only=True,
            description="trusted read-only runtime outside workspace",
        ),
    ),
)
```

使用原则：

- `extra_path_grants` 是受信任配置，不要从模型输出或不可信输入里生成。
- 能不用就不用。
- 能授权只读就不要授权可写。
- 授权具体路径，不要授权过大的目录范围。

## 9. 推荐心智模型

可以把 Manifest 理解为一份“工作区启动配方”：

```text
root     沙盒内部工作区根目录
entries  工作区里预置哪些路径
File     合成一个小文件
Dir      创建一个目录
LocalDir 把宿主机目录复制/物化进工作区
users    声明沙盒用户
groups   声明用户组
permissions 控制 owner/group/other 权限
environment 注入环境变量
extra_path_grants 特批访问工作区外路径
```

写 agent instructions 时，优先使用相对工作区路径：

```text
读取 repo/task.md
运行 repo/tests/test_xxx.sh
写入 output/report.md
```

不要在 instructions 里绑定宿主机绝对路径。这样同一份 Manifest 和任务说明更容易在本地、Docker 和托管 sandbox 之间迁移。
---

# Snapshot 和生命周期管理

## 10. Snapshot 的本质

`Snapshot` 本质上是 **工作区文件状态的压缩包**。本地实现就是一个 `.tar` 文件。

它保存的是：

```text
沙盒工作区里的文件状态
例如：
  /workspace/repo/...
  /workspace/output/report.md
  /workspace/workspace_notes/task.md
```

它**不**保存：

```text
模型推理过程
tool call 历史
stdout/stderr 完整日志
Runner.run 的 result.new_items
session_state
```

所以更准确地说：

```text
Snapshot = 某次沙盒工作区的文件系统状态快照
```

执行记录要看 `result.new_items`、日志文件、tracing 或你自己写的 logger。

## 11. Snapshot 什么时候保存

通常是在 sandbox session 需要持久化的时候保存。

常见触发点：

```text
Runner.run 结束并关闭/停止 sandbox session 时
调用 persist_workspace() 时
pause/resume 这类需要保留工作区状态的流程
sandbox backend 管理 session 生命周期时
```

`SnapshotSpec` 本身不会主动保存。它只是策略。真正保存发生在 sandbox runtime 调用 `snapshot.persist(data)`，其中 `data` 是打包好的工作区 tar 流。

## 12. Snapshot 和 session_state 的区别

```text
SnapshotSpec / snapshot
保存工作区文件状态

session_state
保存某个 sandbox backend 的连接状态（session id、container id、连接信息）
```

所以：

```text
snapshot 解决"文件还在不在"
session_state 解决"上次那个 sandbox 会话怎么重新接上"
```

---

# 生命周期管理

## 13. SDK 拥有 vs 开发者拥有

"生命周期"说的是：一个 sandbox 从创建、启动、被 agent 使用、保存快照、关闭、清理资源，这整套过程由谁负责。

### SDK 拥有生命周期

你只把 `client` 交给 `Runner.run`。SDK 会帮你做完整流程。

适合：一次性任务、跑完就结束、不需要复用 sandbox。

一句话：`SDK 拥有 = Runner.run 自己管 sandbox 的生老病死`

### 开发者拥有生命周期

你自己先创建 sandbox，然后传给 `Runner.run`。你决定什么时候 stop / aclose。

适合：多轮任务、需要复用同一个工作区、需要中途检查文件。

一句话：`开发者拥有 = 你自己管 sandbox 的生命周期，Runner.run 只是借用它`

---

# SandboxRunConfig 选项

## 14. 核心作用

`SandboxRunConfig` 决定：Runner.run 这一次用哪个 sandbox？如果要新建，要怎么初始化？

## 15. 三种 sandbox 来源

```python
SandboxRunConfig(
    client=...,        # SDK 拥有：让 Runner 创建
    session=...,       # 开发者拥有：我已经创建好
    session_state=..., # 恢复旧状态
)
```

优先级：`session > session_state > client 创建新 sandbox`

## 16. manifest / snapshot / options

这些只在 Runner 创建新 sandbox 时有意义：

- `manifest`: 覆盖 agent.default_manifest
- `snapshot`: 从快照恢复工作区文件状态
- `options`: 给 sandbox client 用的创建参数（Docker 镜像、托管 template 等）

## 17. concurrency_limits / archive_limits

- `concurrency_limits`: 控制物化并发数（manifest_entries、local_dir_files）
- `archive_limits`: 控制归档解压资源上限（max_input_bytes、max_extracted_bytes、max_members）

---

# 多用户架构设计

## 18. 三层隔离原则

```text
1. 用户级隔离（User）：多个用户不应该互相看到对方的数据
2. 会话级隔离（Session）：同一用户的不同对话主题应该独立
3. 运行级隔离（Run）：同一会话里的每次 Agent 执行
```

推荐目录结构：

```text
runtime/agent/
├── sandbox/{user_id}/{session_id}/      # 当前活跃 workspace
└── snapshots/{user_id}/{session_id}/    # 快照存档
    ├── run-001.tar
    └── run-002.tar
```

## 19. Sandbox Workspace vs Message History 职责划分

### Message History（对话历史）

```text
= Agent 和用户说了什么
= 纯文本对话上下文
= 存在数据库里
```

负责：用户说了什么、Agent 回复了什么、对话的逻辑顺序

存储：`Backend PostgreSQL: agent_messages` + `Agent Service SQLite: SQLiteSession（运行时缓存）`

### Sandbox Workspace（工作区）

```text
= Agent 在执行过程中产生的文件
= repo/、output/、中间产物
= 存在文件系统里
```

负责：Agent 生成的文件、执行命令产生的中间结果、Skills 输出的文件

存储：`runtime/agent/sandbox/{user_id}/{session_id}/`

快照：`runtime/agent/snapshots/{user_id}/{session_id}/run-001.tar`

## 20. 架构兼容方案

### 核心原则：Backend 是唯一真相源

```text
Backend PostgreSQL          唯一权威的对话历史
Agent Service SQLiteSession 只是运行时缓存，可丢弃可重建
```

### 数据关联

`session_id` 是唯一纽带

```python
# Backend PostgreSQL
AgentSession:
  session_id
  user_id
  latest_snapshot_id      # 指向最新 workspace 快照
  workspace_state         # empty | active | suspended

AgentMessage:
  message_id
  session_id
  role
  content_json
  sequence
```

### 恢复对话流程

1. Backend 读取对话历史和 workspace 状态
2. Agent Service 从 Backend 同步对话历史到 SQLiteSession
3. Agent Service 从 latest_snapshot 恢复 workspace
4. Runner.run 执行
5. 新消息和新快照 ID 写回 Backend

### 数据流

```text
用户发消息 → Backend 存 user message
  ↓
Agent Service 读 Backend messages → 同步到 SQLiteSession
  ↓
从 latest_snapshot 恢复 workspace → Runner.run
  ↓
新消息 + 新快照写回 Backend
```

## 21. 最终推荐架构

**短期（1-2 周）**：
1. 加用户级隔离
2. 加快照支持
3. Backend 存 latest_snapshot_id

**中期（1-2 月）**：
4. Agent Service 从 Backend 同步对话历史
5. 支持恢复对话
6. 新消息和新快照 ID 推回 Backend

**长期（3+ 月）**：
7. 长任务考虑开发者拥有模式
8. 支持暂停/恢复
9. 考虑 Docker sandbox 或托管 sandbox

核心原则：

```text
Message 管对话文本，Workspace 管文件，通过 session_id 和 latest_snapshot_id 关联。
Backend 是消息真相源，Agent Service 每次从 Backend 同步消息、从快照恢复文件，
执行完推回新消息和新快照 ID。
```

---

## 22. 生产环境下 Sandbox 能力的取舍

这里关注的不是 SDK 能力怎么写，而是：在 ANIFORCE 这类游戏营销 Agent 平台里，正式生产环境是否需要接入这些 Sandbox 能力，以及多 worker、多实例时如何兼容。

### 22.1 总体判断

Sandbox 不应该成为每一次用户请求都必须经过的基础设施。它应该是按任务类型启用的执行能力。

推荐分层：

```text
简单任务：
  不启动完整 sandbox
  或只使用轻量临时 workspace
  不拉 snapshot
  不打包上传
  主要走 Backend + LLM + MCP tools

中等任务：
  启动 sandbox
  注入必要 Manifest
  run 后只上传 output 产物
  不做完整 workspace snapshot

复杂任务：
  启动 sandbox
  拉取 latest snapshot
  生成或修改多文件产物
  上传 artifacts
  更新 latest snapshot
```

对应到游戏营销场景：

```text
问答 / 查询项目 / 简单分析：
  不需要 sandbox snapshot

生成报告 / 素材 brief / 多文件产物：
  使用 sandbox + artifact upload

多轮修改同一批文件：
  使用 snapshot

不可信文件处理 / 复杂 Shell / ffmpeg / Python 分析：
  使用 Docker 或托管 sandbox
```

核心原则：

```text
Backend 是事实源
Object Storage 是文件源
Sandbox 是临时执行环境
Agent Service 是 runtime worker
```

## 23. 多 worker / 多实例下的主要问题

如果使用 `UnixLocalSandboxClient`，workspace 默认落在当前 agent-service 实例的本地磁盘。

例如：

```text
agent-service A: /runtime/agent/sandbox/session_1
agent-service B: /runtime/agent/sandbox/session_1
```

如果用户第一次请求落在 A，第二次请求落在 B，则 B 看不到 A 上的文件。这会导致：

```text
上轮生成文件丢失
workspace 无法恢复
snapshot 不一致
用户继续追问时 Agent 看不到历史产物
多实例扩缩容后状态漂移
```

因此，多实例下不能把本地 sandbox 目录当作长期事实源。

## 24. 常见部署模式

### 24.1 单实例 agent-service

适合 MVP、内测、小流量生产。

```text
Backend 可以多 worker
Agent Service 单实例
Sandbox 使用本地持久盘
产物上传对象存储
```

优点：

```text
简单
调试方便
改造成本低
```

缺点：

```text
agent-service 是瓶颈
实例挂掉时运行中任务丢失
本地 workspace 绑定单机
不适合长期横向扩容
```

这个模式适合当前阶段，但要把本地 sandbox 明确视为 runtime 临时状态，而不是产品事实源。

### 24.2 多实例 + Sticky Routing

同一个 `session_id` 固定路由到同一个 agent-service 实例。

```text
session_id hash -> agent-service instance
```

优点：

```text
保留本地 workspace
实现相对简单
比单实例更容易扩容
```

缺点：

```text
实例故障时恢复困难
扩缩容会打乱 hash 映射
需要额外路由层或调度逻辑
仍然依赖本地磁盘
```

适合作为过渡方案，不建议作为长期终态。

### 24.3 多实例 + 共享持久卷

多个 agent-service 实例挂同一个共享文件系统。

```text
/shared/sandbox/{user_id}/{session_id}
```

可选技术包括：

```text
NFS
EFS
NAS
CephFS
```

优点：

```text
多实例能看到同一份 workspace
改动相对少
```

缺点：

```text
文件锁和并发写入复杂
性能不稳定
权限隔离更难
故障排查复杂
```

适合中小规模内部系统，但不是最云原生的方案。

### 24.4 多实例 + 对象存储 snapshot/artifact

这是更推荐的中长期模式。

```text
run start:
  从对象存储下载 session latest snapshot 或必要输入包
  解压/物化到当前 worker 的临时 sandbox

run executing:
  Agent 在当前 sandbox 中读写文件

run end:
  扫描 output
  上传 artifacts 到对象存储
  必要时打包并上传 latest snapshot
  更新 Backend session_state / artifact metadata
  清理本地临时目录
```

优点：

```text
任意 worker 都可以处理任意 run
agent-service 更接近无状态
适合 Kubernetes / 多实例部署
实例故障后可以通过 Backend + Object Storage 恢复
产物生命周期清晰
```

缺点：

```text
实现成本更高
引入下载、解压、上传等 I/O 开销
简单任务如果也强制走这个流程，会明显变慢
```

因此该模式必须结合任务分层：简单任务不拉 snapshot，不上传完整 workspace。

### 24.5 托管沙盒 Provider

由外部 provider 管理 sandbox 生命周期、隔离、状态和执行环境。

优点：

```text
隔离强
多实例友好
不需要自己维护 Docker/K8s 沙盒细节
可能支持 remote snapshot/session_state
```

缺点：

```text
成本更高
供应商绑定
网络、权限、审计设计更复杂
```

适合大规模生产、强隔离需求、或团队不想维护底层执行环境时使用。

## 25. 各 Sandbox 能力在 ANIFORCE 中的取舍

### 25.1 沙盒客户端切换

短期可以继续使用：

```text
UnixLocalSandboxClient
```

适合：

```text
开发环境
单实例 MVP
受控 Shell
不执行用户上传的不可信代码
```

正式多实例或强隔离时再切到：

```text
DockerSandboxClient
托管 Sandbox Provider
```

触发条件：

```text
多个 agent-service 实例
Kubernetes 部署
需要镜像一致性
需要执行 Python/ffmpeg/复杂 Shell
处理不可信上传文件
需要强资源限制和环境隔离
```

### 25.2 工作区覆盖 Manifest Override

这是生产环境最应该优先接入的能力之一。

原因：同一个 Agent 角色需要针对不同用户、项目、广告系列、素材包运行，但不应该看到全量数据。

推荐由 Backend 的产品状态生成 Manifest 输入：

```text
session_state.linked_entities
context_snapshot
project_id
campaign_id
material_ids
workspace_type
```

典型 workspace：

```text
workspace/
  project/
    project_profile.json
    target_audience.json
  materials/
    selected_assets.json
    thumbnails/
  metrics/
    last_30_days.csv
  output/
    report.md
    campaign_draft.json
    creative_brief.md
```

Manifest 的价值：

```text
限制 Agent 可见数据范围
避免跨项目污染
让 workspace 和业务实体绑定
方便审计和复现
同一个 Agent 可以服务不同任务包
```

### 25.3 沙盒会话注入

生产环境建议接入。

它的价值是让服务端显式控制 sandbox 生命周期，并在 run 后做后处理：

```text
检查生成了哪些文件
读取 output/report.md
读取 output/campaign_draft.json
扫描敏感信息
上传产物到 OSS/S3
写入 Backend artifact 表
更新 workspace projection
清理 sandbox
```

典型流程：

```text
client = UnixLocalSandboxClient()
sandbox = await client.create(manifest=manifest)

async with sandbox:
    result = await Runner.run(
        agent,
        prompt,
        run_config=RunConfig(
            sandbox=SandboxRunConfig(session=sandbox),
        ),
    )

    # run 后扫描 output，上传 artifacts，更新 backend
```

相比让 Runner 隐式创建 sandbox，会话注入更适合生产，因为后处理、上传、清理都更可控。

### 25.4 基于 session_state 的恢复

这里的 `session_state` 是 sandbox runtime/provider 的底层会话状态，不是 Backend 的 `session_states` 产品表。

它适合：

```text
托管沙盒 provider
远程 sandbox
外部 job system
需要跨 worker 重新连接同一个活 sandbox
```

短期不建议接入。只有当使用托管沙盒，或者确实需要 run 迁移/恢复时再考虑。

### 25.5 基于快照的启动 Snapshot

中期需要，但不应该一开始对所有任务强制启用。

适合：

```text
多轮修改同一批文件
继续编辑上次生成的 creative_brief.md
继续完善上次生成的 campaign_plan.json
恢复上次 workspace 中的分析报告和中间文件
```

生产中不要依赖本地 `/tmp` 或单机路径。推荐：

```text
s3://aniforce-snapshots/{user_id}/{session_id}/latest.tar.gz
s3://aniforce-snapshots/{user_id}/{session_id}/runs/{run_id}.tar.gz
```

run start：

```text
下载 latest snapshot -> 解压到临时 sandbox
```

run end：

```text
打包 workspace -> 上传 new snapshot -> 更新 Backend latest_snapshot_uri
```

为了避免简单任务变慢，应只对需要文件连续性的任务启用 snapshot。

### 25.6 Git 技能加载

短期不需要。当前阶段可以使用本地 skills 或把 skills 打进 agent-service 镜像。

中长期在这些情况下使用 Git 技能加载：

```text
多个团队维护 Skills
Skills 有独立发布节奏
不同环境需要不同 skill 版本
需要快速回滚技能包
客户定制技能包
```

生产注意：

```text
pin tag/ref，不直接使用 main
做 repo allowlist
做缓存，避免每次 run git clone
必要时扫描技能内容
```

### 25.7 Agent as Tool / 多 Agent 沙盒边界

短期不需要。

当出现明确分工后再考虑：

```text
主 Agent：营销策略规划
素材 Agent：检查素材质量
数据 Agent：分析投放表现
合规 Agent：检查广告文案风险
平台 Agent：生成 Meta/TikTok 投放配置
```

共享 sandbox 适合只读探索：

```text
素材审阅 Agent 只读 materials/
数据分析 Agent 只读 metrics/
主 Agent 写 output/
```

独立 sandbox 适合：

```text
工具 Agent 会修改文件
工具 Agent 会运行不可信命令
工具 Agent 需要不同镜像
工具 Agent 失败不能污染主 workspace
```

该能力会带来嵌套 run、事件展示、审批、产物归档、成本统计等复杂度，因此不建议过早引入。

### 25.8 与 MCP / 本地业务工具组合

这是 ANIFORCE 的核心模式，必须保留和加强。

正确边界：

```text
Sandbox：
  文件工作区
  临时分析
  生成报告
  生成 JSON draft
  整理素材包

MCP / Backend tools：
  读写业务事实
  权限校验
  调平台 API
  创建项目 / campaign / material
  写 session_state / changelog
```

不要让 sandbox 直接成为业务事实源。所有业务写入都应通过 Backend/MCP tool，并且要：

```text
带 user_id / org_id / session_id / run_id
做权限校验
写操作幂等
记录 changelog / side_effect
高风险操作走 HITL 审批
```

### 25.9 Memory

短期不建议直接接 SDK Memory。

游戏营销场景未来可能需要记住：

```text
用户广告文案风格偏好
游戏项目品牌调性
历史高转化素材特点
投放地区和预算偏好
```

但这些更适合先由 Backend 显式管理：

```text
user_preferences
project_strategy_notes
brand_guidelines
winning_creative_patterns
```

之后在 run start 时把这些信息注入 workspace：

```text
memory/
  user_preferences.md
  brand_guidelines.md
  historical_winners.md
```

长期再考虑 SDK Memory。不要让 Agent 在本地 sandbox 文件里形成不可审计的长期记忆。

## 26. 简单任务的延迟问题

如果所有任务都走完整流程：

```text
下载 snapshot
创建 sandbox
运行 Agent
扫描 workspace
打包 snapshot
上传对象存储
更新 backend
```

简单任务的耗时会显著上升。

因此生产系统必须做任务分层，而不是一刀切。

推荐策略：

```text
简单问答：
  Backend + LLM + MCP tools
  不启完整 sandbox
  不做 snapshot

轻量文件产物：
  启 sandbox
  只上传 output artifacts
  不上传完整 snapshot

多轮文件编辑：
  启 sandbox
  拉 latest snapshot
  run 后更新 snapshot

高风险文件处理：
  Docker/托管 sandbox
  严格资源限制和文件隔离
```

这样可以避免为了复杂任务的可靠性，拖慢所有简单任务。

## 27. 推荐演进路线

### Phase 1：生产 MVP

目标是让 sandbox 在生产中可控、可审计，但不过度复杂。

建议接入：

```text
UnixLocalSandboxClient
Manifest Override
Sandbox Session Injection
run 后扫描 output
上传 artifacts 到对象存储
Backend 记录 artifact metadata
workspace projection 从 Backend 读取
限制 Shell 能力
agent-service 单实例或 sticky routing
```

暂不接入：

```text
Docker sandbox
SDK Memory
Agent as Tool
sandbox session_state 恢复
全量 snapshot
```

### Phase 2：多实例兼容

目标是让 agent-service 可以横向扩展。

建议接入：

```text
对象存储 latest snapshot
run start 下载 snapshot
run end 上传 artifacts 和必要 snapshot
本地 sandbox 改成 per-run 临时目录
run lease / session lock
可选 DockerSandboxClient
```

这时状态边界应变成：

```text
DB：业务事实
Object Storage：文件事实
Sandbox：临时执行环境
```

### Phase 3：强隔离和复杂任务

目标是支持复杂营销自动化、多 Agent、强安全和更大规模。

建议接入：

```text
Docker 或托管 sandbox
Git skills pinned version
Agent as Tool
Backend-managed memory/profile
HITL 审批
细粒度权限 Manifest
```

## 28. 最终推荐表

| 能力 | 是否需要 | 建议时机 | 多实例注意点 |
|---|---:|---|---|
| 沙盒客户端切换 | 需要但不急 | 生产多实例 / 强隔离时 | UnixLocal 依赖本机；Docker/托管更适合横向扩展 |
| 工作区覆盖 Manifest | 非常需要 | 现在就该设计 | Manifest 来源应来自 Backend session_state，不要本地硬编码 |
| 沙盒会话注入 | 非常需要 | 现在就该设计 | run 后上传产物，避免依赖本机 workspace |
| session_state 恢复 | 暂不需要 | 托管沙盒/远程恢复时 | 不要和 Backend session_states 混淆 |
| 快照启动 Snapshot | 需要 | 第二阶段 | 生产用对象存储 snapshot，不依赖本地 `/tmp` |
| Git 技能加载 | 未来需要 | Skills 独立发版后 | pin tag/ref，缓存，不直接使用 main |
| Agent as Tool | 未来可能需要 | 多 Agent 分工明确后 | 事件、审批、产物、成本统计会复杂 |
| MCP/本地工具组合 | 必须需要 | 当前核心模式 | 工具写操作要幂等、带权限、写 changelog |
| Memory | 未来可能需要 | 偏好/品牌长期沉淀后 | 优先 Backend-managed memory，不要本地文件乱记 |

## 29. 对 ANIFORCE 的当前建议

当前不要一次性接入所有 sandbox 能力。推荐短期生产组合：

```text
UnixLocalSandboxClient
Manifest Override
Sandbox Session Injection
output artifact upload
Backend session_state / artifacts / workspace projection
agent-service 单实例或 sticky routing
```

中期再演进到：

```text
DockerSandboxClient 或托管 sandbox
Object Storage snapshot
per-run temporary sandbox
run end snapshot publish
多实例 agent-service
```

最终目标：

```text
Backend 是事实源
Object Storage 是文件源
Sandbox 是临时执行环境
Agent Service 是无状态或弱状态 worker
```

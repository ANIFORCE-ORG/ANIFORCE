# %% [markdown]
# # SandboxAgent Manifest Study Cells
#
# 这是一个 VS Code / Jupyter 可逐格运行的 Python 脚本。
# 每个 cell 只演示一个概念，方便调试和理解。

# %%
from __future__ import annotations

import json
from pathlib import Path

from agents.sandbox import FileMode, Group, LocalSnapshotSpec, Manifest, Permissions, RemoteSnapshotSpec, SandboxPathGrant, User
from agents.run import RunConfig
from agents.sandbox import SandboxRunConfig
from agents.sandbox.entries import Dir, File, LocalDir
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient
from agents.sandbox.manifest import Environment


# %% [markdown]
# ## 1. 找到当前 sandbox 示例目录
#
# 支持从项目根目录或 `notebooks/02-sandbox` 目录运行。

# %%
def resolve_paths(start: Path) -> tuple[Path, Path]:
    start = start.resolve()
    for path in (start, *start.parents):
        if path.name == "02-sandbox" and path.parent.name == "notebooks":
            return path.parents[1], path
        candidate = path / "notebooks" / "02-sandbox"
        if (candidate / "repo").is_dir():
            return path, candidate
    raise RuntimeError(f"Cannot resolve paths from {start}")


PROJECT_ROOT, EXAMPLE_DIR = resolve_paths(Path.cwd())
HOST_REPO_DIR = EXAMPLE_DIR / "repo"
HOST_SKILLS_DIR = EXAMPLE_DIR / "skills"

print("PROJECT_ROOT =", PROJECT_ROOT)
print("EXAMPLE_DIR  =", EXAMPLE_DIR)
print("HOST_REPO_DIR=", HOST_REPO_DIR)
print("repo exists  =", HOST_REPO_DIR.is_dir())


# %% [markdown]
# ## 2. 小工具：漂亮打印 Manifest

# %%
def dump(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def pretty(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


# %% [markdown]
# ## 3. 最小 Manifest：File / Dir / LocalDir
#
# 观察重点：
# - entries 的 key 是沙盒内相对路径。
# - LocalDir.src 是宿主机路径。
# - File 是合成文件。
# - Dir 是沙盒内目录。

# %%
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

manifest = Manifest(
    root="/workspace",
    users=[User(name="analyst")],
    environment=Environment(value={
        "DEMO_ENV": "manifest-env-visible-in-sandbox",
    }),
    entries={
        "repo": LocalDir(src=HOST_REPO_DIR),
        "workspace_notes/task.md": File(
            content=b"Read repo/task.md and write output/report.md.\n",
            permissions=private_permissions,
        ),
        "output": Dir(permissions=output_permissions),
    },
)

pretty({
    "root": manifest.root,
    "entries": {str(k): type(v).__name__ for k, v in manifest.entries.items()},
    "users": [u.name for u in manifest.users],
    "environment": dump(manifest.environment),
})


# %% [markdown]
# ## 4. Manifest.describe：看看沙盒工作区长什么样

# %%
print(manifest.describe(depth=None))


# %% [markdown]
# ## 5. entry path 自检：必须是相对路径，不能逃逸工作区

# %%
def assert_manifest_entry_paths(m: Manifest) -> None:
    bad_paths = []
    for raw_path in m.entries:
        path = Path(raw_path)
        if path.is_absolute() or ".." in path.parts:
            bad_paths.append(str(raw_path))
    if bad_paths:
        raise ValueError(f"bad entry paths: {bad_paths}")


for label, entries in {
    "bad absolute": {"/tmp/report.md": File(content=b"bad")},
    "bad escape": {"../outside": Dir()},
    "good relative": {"output/report.md": File(content=b"ok")},
}.items():
    try:
        assert_manifest_entry_paths(Manifest(entries=entries))
        print(label, "=> OK")
    except ValueError as exc:
        print(label, "=>", exc)


# %% [markdown]
# ## 6. 权限对象：owner / group / other
#
# `repr(permission)` 会显示类似 Unix 权限的字符串。

# %%
examples = {
    "private_file": Permissions(
        owner=FileMode.READ | FileMode.WRITE,
        group=FileMode.NONE,
        other=FileMode.NONE,
    ),
    "shared_output_dir": Permissions(
        owner=FileMode.ALL,
        group=FileMode.ALL,
        other=FileMode.NONE,
        directory=True,
    ),
    "public_readonly_file": Permissions(
        owner=FileMode.READ | FileMode.WRITE,
        group=FileMode.READ,
        other=FileMode.READ,
    ),
}

for name, permissions in examples.items():
    print(name, "=>", permissions, "mode=", oct(permissions.to_mode()))


# %% [markdown]
# ## 7. 用户和组：声明身份，不等于已经运行
#
# Manifest 里声明用户和组；真正执行身份由 SandboxAgent(run_as=...) 决定。

# %%
analyst = User(name="analyst")
reviewer = User(name="reviewer")
reviewers = Group(name="reviewers", users=[analyst, reviewer])

team_manifest = Manifest(
    root="/workspace",
    users=[analyst, reviewer],
    groups=[reviewers],
    entries={
        "shared": Dir(
            group=reviewers,
            permissions=Permissions(
                owner=FileMode.ALL,
                group=FileMode.READ | FileMode.EXEC,
                other=FileMode.NONE,
                directory=True,
            ),
        ),
        "private/task.md": File(
            content=b"only owner should read this\n",
            permissions=Permissions(
                owner=FileMode.READ | FileMode.WRITE,
                group=FileMode.NONE,
                other=FileMode.NONE,
            ),
        ),
    },
)

pretty({
    "users": [u.name for u in team_manifest.users],
    "groups": [{"name": g.name, "users": [u.name for u in g.users]} for g in team_manifest.groups],
    "entries": {str(k): type(v).__name__ for k, v in team_manifest.entries.items()},
})


# %% [markdown]
# ## 8. extra_path_grants：只给工作区外的可信绝对路径开口
#
# 这里只展示配置，不实际访问 `/opt/toolchain`。

# %%
grant_manifest = Manifest(
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

pretty({
    "entries": {str(k): type(v).__name__ for k, v in grant_manifest.entries.items()},
    "extra_path_grants": dump(grant_manifest.extra_path_grants),
})


# %% [markdown]
# ## 9. 最后总结：这几个对象分别负责什么

# %%
summary = {
    "Manifest": "描述沙盒工作区启动配方",
    "File": "在沙盒里合成一个小文件",
    "Dir": "在沙盒里创建目录",
    "LocalDir": "把宿主机目录物化到沙盒里",
    "User": "声明沙盒用户",
    "Group": "声明沙盒用户组",
    "Permissions": "控制 owner/group/other 的读写执行权限",
    "SandboxPathGrant": "特批访问工作区外的可信绝对路径",
}
pretty(summary)


# %% [markdown]
# ## 10. SnapshotSpec：工作区快照策略
#
# Manifest 负责“新工作区里应该有什么”。
# SnapshotSpec 负责“工作区结束后保存到哪里、下次从哪里恢复”。
#
# LocalSnapshotSpec 会把快照保存成本地 tar 文件。

# %%
# 本模块 imports：复制这个 cell 到 notebook 时也能独立运行。
import io
import tarfile

from agents.sandbox import LocalSnapshotSpec, RemoteSnapshotSpec, resolve_snapshot

SNAPSHOT_BASE_DIR = PROJECT_ROOT / "drafts" / "260701" / "sandbox_snapshots"

local_snapshot_spec = LocalSnapshotSpec(base_path=SNAPSHOT_BASE_DIR)
remote_snapshot_spec = RemoteSnapshotSpec(client_dependency_key="my_snapshot_client")

pretty({
    "local_snapshot_spec": dump(local_snapshot_spec),
    "remote_snapshot_spec": dump(remote_snapshot_spec),
    "snapshot_base_dir": str(SNAPSHOT_BASE_DIR),
})


# %% [markdown]
# ## 11. spec.build / resolve_snapshot：从策略生成具体快照对象
#
# spec 是策略；snapshot 是某一次会话对应的具体快照。
# snapshot_id 必须是单个文件名片段，例如 `demo-session-01`。

# %%
snapshot_id = "demo-session-01"
local_snapshot = local_snapshot_spec.build(snapshot_id)
resolved_snapshot = resolve_snapshot(local_snapshot_spec, snapshot_id)

pretty({
    "local_snapshot": dump(local_snapshot),
    "resolved_snapshot": dump(resolved_snapshot),
    "expected_file": str(SNAPSHOT_BASE_DIR / f"{snapshot_id}.tar"),
})


# %% [markdown]
# ## 12. 模拟 persist / restore：保存和恢复 tar 快照
#
# 这里不启动真实 sandbox，只模拟 Snapshot 保存的数据流。
# 真实 sandbox 会把工作区打包成 tar，再调用 snapshot.persist(...）。

# %%
async def make_demo_workspace_tar() -> io.BytesIO:
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as tar:
        content = b"hello from snapshot\n"
        info = tarfile.TarInfo("output/report.md")
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    data.seek(0)
    return data


data = await make_demo_workspace_tar()
await local_snapshot.persist(data)
print("persisted=", SNAPSHOT_BASE_DIR / f"{snapshot_id}.tar")
print("restorable=", await local_snapshot.restorable())

restored = await local_snapshot.restore()
with tarfile.open(fileobj=restored, mode="r") as tar:
    print("tar names=", tar.getnames())
    report = tar.extractfile("output/report.md").read().decode()
    print("output/report.md=", report.strip())


# %% [markdown]
# ## 13. 沙盒生命周期：SDK 拥有
#
# 适合“一次 Runner.run 用完就结束”的场景。
#
# 你只传 client，Runner 负责：
# - 创建或恢复 sandbox
# - start
# - 运行工具
# - stop 并持久化 snapshot
# - 清理 runner 拥有的资源

# %%
# 本模块 imports：复制生命周期 cells 到 notebook 时也能看清依赖。
from agents.run import RunConfig
from agents.sandbox import SandboxRunConfig
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient

# UnixLocalSandboxClient 不支持 manifest.users / manifest.groups，
# 因为那会变成在宿主机上创建系统用户/组。
local_lifecycle_manifest = Manifest(
    root="/workspace",
    environment=manifest.environment,
    entries=manifest.entries,
)

sdk_owned_run_config = RunConfig(
    sandbox=SandboxRunConfig(
        client=UnixLocalSandboxClient(),
        manifest=local_lifecycle_manifest,
        snapshot=local_snapshot_spec,
    ),
    tracing_disabled=True,
    workflow_name="sdk-owned sandbox lifecycle demo",
)

pretty({
    "mode": "SDK-owned",
    "sandbox_has_client": sdk_owned_run_config.sandbox.client is not None,
    "sandbox_has_session": sdk_owned_run_config.sandbox.session is not None,
    "manifest_entries": [str(k) for k in local_lifecycle_manifest.entries],
    "snapshot": dump(local_snapshot_spec),
})

# 真实调用长这样：
# result = await Runner.run(agent, "Inspect workspace.", run_config=sdk_owned_run_config)


# %% [markdown]
# ## 14. 沙盒生命周期：开发者拥有 async with
#
# 适合一个实时 sandbox 里连续跑多次 Runner.run。
#
# 你负责 create 和上下文；Runner 只使用这个 session，不会替你关闭它。

# %%
client = UnixLocalSandboxClient()

# 这段会创建并启动一个真实本地 sandbox，但不调用模型。
# async with 退出时会自动走清理路径。
async with await client.create(
    manifest=local_lifecycle_manifest,
    snapshot=local_snapshot_spec,
) as sandbox:
    developer_owned_run_config = RunConfig(
        sandbox=SandboxRunConfig(session=sandbox),
        tracing_disabled=True,
        workflow_name="developer-owned sandbox lifecycle demo",
    )
    pretty({
        "mode": "developer-owned",
        "sandbox_type": type(sandbox).__name__,
        "sandbox_has_client": developer_owned_run_config.sandbox.client is not None,
        "sandbox_has_session": developer_owned_run_config.sandbox.session is not None,
        "state_type": type(sandbox.state).__name__,
    })

    # 同一个 sandbox 可以连续给多次 Runner.run 使用：
    # await Runner.run(agent, "Analyze files.", run_config=developer_owned_run_config)
    # await Runner.run(agent, "Write final report.", run_config=developer_owned_run_config)


# %% [markdown]
# ## 15. 手动生命周期：start / stop / aclose
#
# 不用 async with 时，必须自己保证 finally 里 aclose。
#
# stop(): 持久化 snapshot 支持的工作区状态，不销毁 session 对象。
# aclose(): 完整清理路径，会调用 stop、关闭资源、关闭会话依赖。

# %%
manual_sandbox = await client.create(
    manifest=local_lifecycle_manifest,
    snapshot=local_snapshot_spec,
)

try:
    await manual_sandbox.start()
    print("started manual sandbox")

    # 中途显式保存工作区检查点。
    await manual_sandbox.stop()
    print("stopped and persisted workspace snapshot")

    # 如果只是想显式持久化，也可以用：
    # await manual_sandbox.persist_workspace()
finally:
    await manual_sandbox.aclose()
    print("closed manual sandbox")


# %% [markdown]
# ## 16. SandboxRunConfig：一次运行的沙盒选项
#
# SandboxRunConfig 决定本次 Runner.run 使用哪个 sandbox，会不会创建新会话，
# 以及创建新会话时用哪个 manifest、snapshot、客户端 options。

# %%
# 本模块 imports：复制 SandboxRunConfig cells 到 notebook 时也能看清依赖。
from agents.run import RunConfig
from agents.sandbox import (
    SandboxArchiveLimits,
    SandboxConcurrencyLimits,
    SandboxRunConfig,
)
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient

client = UnixLocalSandboxClient()

basic_sandbox_config = SandboxRunConfig(
    client=client,
    manifest=local_lifecycle_manifest,
    snapshot=local_snapshot_spec,
)

pretty({
    "has_client": basic_sandbox_config.client is not None,
    "has_session": basic_sandbox_config.session is not None,
    "has_session_state": basic_sandbox_config.session_state is not None,
    "manifest_entries": [str(k) for k in basic_sandbox_config.manifest.entries],
    "snapshot": dump(basic_sandbox_config.snapshot),
    "concurrency_limits": dump(basic_sandbox_config.concurrency_limits),
    "archive_limits": dump(basic_sandbox_config.archive_limits),
})


# %% [markdown]
# ## 17. 沙盒来源优先级：session > session_state > client 创建
#
# 三种来源：
# - session：你已经有 live sandbox，Runner 直接复用。
# - session_state：你有序列化状态，Runner 用 client 恢复。
# - client：Runner 自己创建新 sandbox。

# %%
def explain_sandbox_source(config: SandboxRunConfig) -> str:
    if config.session is not None:
        return "reuse live session"
    if config.session_state is not None:
        return "restore from explicit session_state using client"
    if config.client is not None:
        return "create new session using client"
    return "invalid: no session and no client"


source_examples = {
    "client only": SandboxRunConfig(client=client),
    "client + manifest": SandboxRunConfig(client=client, manifest=local_lifecycle_manifest),
    "client + snapshot": SandboxRunConfig(client=client, snapshot=local_snapshot_spec),
}

for label, config in source_examples.items():
    print(label, "=>", explain_sandbox_source(config))

# session 示例需要真实 sandbox 对象，见前面的 developer-owned 生命周期 cell。


# %% [markdown]
# ## 18. manifest 和 snapshot 只在“新会话”时有意义
#
# 如果传入 session=live_sandbox，Runner 复用现有 live session。
# 此时 manifest/snapshot 不负责重新创建工作区。

# %%
new_session_config = SandboxRunConfig(
    client=client,
    manifest=local_lifecycle_manifest,
    snapshot=local_snapshot_spec,
)

# 伪代码：live_session_config = SandboxRunConfig(session=sandbox)

pretty({
    "new_session_config": {
        "source": explain_sandbox_source(new_session_config),
        "manifest_applies": True,
        "snapshot_applies": True,
    },
    "live_session_config": {
        "source": "reuse live session",
        "manifest_applies": "only compatible live manifest updates, not full replacement",
        "snapshot_applies": False,
    },
})


# %% [markdown]
# ## 19. concurrency_limits：控制物化并发
#
# 大 Manifest 或大 LocalDir 复制时，可以限制并发，避免本机资源占用太高。

# %%
default_limits = SandboxConcurrencyLimits()
strict_limits = SandboxConcurrencyLimits(
    manifest_entries=1,
    local_dir_files=1,
)
no_local_file_limit = SandboxConcurrencyLimits(
    manifest_entries=4,
    local_dir_files=None,
)

pretty({
    "default_limits": dump(default_limits),
    "strict_limits": dump(strict_limits),
    "no_local_file_limit": dump(no_local_file_limit),
})

limited_config = SandboxRunConfig(
    client=client,
    manifest=local_lifecycle_manifest,
    concurrency_limits=strict_limits,
)
print("limited_config.concurrency_limits=", limited_config.concurrency_limits)


# %% [markdown]
# ## 20. archive_limits：控制归档解压资源上限
#
# archive_limits=None 表示不启用 SDK 侧归档资源限制。
# SandboxArchiveLimits() 表示启用 SDK 默认阈值。

# %%
default_archive_limits = SandboxArchiveLimits()
strict_archive_limits = SandboxArchiveLimits(
    max_input_bytes=10 * 1024 * 1024,
    max_extracted_bytes=50 * 1024 * 1024,
    max_members=1000,
)
partial_archive_limits = SandboxArchiveLimits(
    max_input_bytes=None,
    max_extracted_bytes=50 * 1024 * 1024,
    max_members=1000,
)

pretty({
    "none_means_no_sdk_archive_limit": None,
    "default_archive_limits": dump(default_archive_limits),
    "strict_archive_limits": dump(strict_archive_limits),
    "partial_archive_limits": dump(partial_archive_limits),
})

archive_limited_config = SandboxRunConfig(
    client=client,
    manifest=local_lifecycle_manifest,
    archive_limits=strict_archive_limits,
)
print("archive_limited_config.archive_limits=", archive_limited_config.archive_limits)


# %% [markdown]
# ## 21. Runner.run 仍然是普通 Runner API
#
# SandboxRunConfig 只是 RunConfig.sandbox 的一部分。
# SandboxAgent 仍然通过 Runner.run / run_sync / run_streamed 执行。

# %%
runner_config = RunConfig(
    sandbox=SandboxRunConfig(
        client=client,
        manifest=local_lifecycle_manifest,
        snapshot=local_snapshot_spec,
        concurrency_limits=SandboxConcurrencyLimits(manifest_entries=2, local_dir_files=2),
        archive_limits=SandboxArchiveLimits(),
    ),
    tracing_disabled=True,
    workflow_name="sandbox run config study",
)

pretty({
    "workflow_name": runner_config.workflow_name,
    "tracing_disabled": runner_config.tracing_disabled,
    "sandbox_source": explain_sandbox_source(runner_config.sandbox),
    "manifest_entries": [str(k) for k in runner_config.sandbox.manifest.entries],
})

# 真实调用仍然是：
# result = await Runner.run(agent, "Inspect workspace.", run_config=runner_config)

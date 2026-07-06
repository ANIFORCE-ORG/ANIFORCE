from __future__ import annotations

import asyncio
import io
import json
import tarfile
from pathlib import Path
from typing import Any

from agents.run import RunConfig
from agents.sandbox import (
    FileMode,
    LocalSnapshotSpec,
    Manifest,
    Permissions,
    RemoteSnapshotSpec,
    SandboxArchiveLimits,
    SandboxConcurrencyLimits,
    SandboxPathGrant,
    SandboxRunConfig,
    User,
    resolve_snapshot,
)
from agents.sandbox.entries import Dir, File, LocalDir
from agents.sandbox.manifest import Environment
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient


def pretty(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


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
SNAPSHOT_BASE_DIR = PROJECT_ROOT / "drafts" / "260701" / "sandbox_snapshots"


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

# UnixLocalSandboxClient 不能 provision manifest.users / manifest.groups。
# 本地生命周期调试时使用这个去掉 users/groups 的清单。
local_lifecycle_manifest = Manifest(
    root="/workspace",
    environment=manifest.environment,
    entries=manifest.entries,
)

local_snapshot_spec = LocalSnapshotSpec(base_path=SNAPSHOT_BASE_DIR)


def demo_paths() -> None:
    print("\n=== demo_paths ===")
    pretty({
        "PROJECT_ROOT": PROJECT_ROOT,
        "EXAMPLE_DIR": EXAMPLE_DIR,
        "HOST_REPO_DIR": HOST_REPO_DIR,
        "repo_exists": HOST_REPO_DIR.is_dir(),
    })


def demo_manifest() -> None:
    print("\n=== demo_manifest ===")
    pretty({
        "root": manifest.root,
        "entries": {str(k): type(v).__name__ for k, v in manifest.entries.items()},
        "users": [u.name for u in manifest.users],
        "environment": dump(manifest.environment),
    })
    print(manifest.describe(depth=None))


def assert_manifest_entry_paths(m: Manifest) -> None:
    bad_paths = []
    for raw_path in m.entries:
        path = Path(raw_path)
        if path.is_absolute() or ".." in path.parts:
            bad_paths.append(str(raw_path))
    if bad_paths:
        raise ValueError(f"bad entry paths: {bad_paths}")


def demo_entry_path_validation() -> None:
    print("\n=== demo_entry_path_validation ===")
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


def demo_permissions() -> None:
    print("\n=== demo_permissions ===")
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


def demo_extra_path_grants() -> None:
    print("\n=== demo_extra_path_grants ===")
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


async def demo_snapshot() -> None:
    print("\n=== demo_snapshot ===")
    snapshot_id = "debug-demo-session-01"
    snapshot = resolve_snapshot(local_snapshot_spec, snapshot_id)

    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as tar:
        content = b"hello from debug snapshot\n"
        info = tarfile.TarInfo("output/report.md")
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    data.seek(0)

    await snapshot.persist(data)
    print("persisted=", SNAPSHOT_BASE_DIR / f"{snapshot_id}.tar")
    print("restorable=", await snapshot.restorable())

    restored = await snapshot.restore()
    with tarfile.open(fileobj=restored, mode="r") as tar:
        print("tar names=", tar.getnames())
        report = tar.extractfile("output/report.md").read().decode()
        print("output/report.md=", report.strip())


async def demo_lifecycle() -> None:
    print("\n=== demo_lifecycle ===")
    client = UnixLocalSandboxClient()

    async with await client.create(
        manifest=local_lifecycle_manifest,
        snapshot=local_snapshot_spec,
    ) as sandbox:
        run_config = RunConfig(
            sandbox=SandboxRunConfig(session=sandbox),
            tracing_disabled=True,
            workflow_name="developer-owned sandbox lifecycle debug",
        )
        pretty({
            "mode": "developer-owned",
            "sandbox_type": type(sandbox).__name__,
            "state_type": type(sandbox.state).__name__,
            "run_config_has_session": run_config.sandbox.session is not None,
        })


def explain_sandbox_source(config: SandboxRunConfig) -> str:
    if config.session is not None:
        return "reuse live session"
    if config.session_state is not None:
        return "restore from explicit session_state using client"
    if config.client is not None:
        return "create new session using client"
    return "invalid: no session and no client"


def demo_sandbox_run_config() -> None:
    print("\n=== demo_sandbox_run_config ===")
    client = UnixLocalSandboxClient()

    examples = {
        "client only": SandboxRunConfig(client=client),
        "client + manifest": SandboxRunConfig(client=client, manifest=local_lifecycle_manifest),
        "client + snapshot": SandboxRunConfig(client=client, snapshot=local_snapshot_spec),
    }
    for label, config in examples.items():
        print(label, "=>", explain_sandbox_source(config))

    config = RunConfig(
        sandbox=SandboxRunConfig(
            client=client,
            manifest=local_lifecycle_manifest,
            snapshot=local_snapshot_spec,
            concurrency_limits=SandboxConcurrencyLimits(manifest_entries=2, local_dir_files=2),
            archive_limits=SandboxArchiveLimits(),
        ),
        tracing_disabled=True,
        workflow_name="sandbox run config debug",
    )
    pretty({
        "workflow_name": config.workflow_name,
        "sandbox_source": explain_sandbox_source(config.sandbox),
        "concurrency_limits": dump(config.sandbox.concurrency_limits),
        "archive_limits": dump(config.sandbox.archive_limits),
    })


def demo_snapshot_specs() -> None:
    print("\n=== demo_snapshot_specs ===")
    remote_snapshot_spec = RemoteSnapshotSpec(client_dependency_key="my_snapshot_client")
    pretty({
        "local_snapshot_spec": dump(local_snapshot_spec),
        "remote_snapshot_spec": dump(remote_snapshot_spec),
    })


async def main() -> None:
    # Keep these calls small. Comment out anything you do not want to step through.
    demo_paths()
    demo_manifest()
    demo_entry_path_validation()
    demo_permissions()
    demo_extra_path_grants()
    demo_snapshot_specs()
    await demo_snapshot()
    await demo_lifecycle()
    demo_sandbox_run_config()


if __name__ == "__main__":
    asyncio.run(main())

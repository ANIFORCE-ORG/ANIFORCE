"""SandboxAgent core concept debugger.

Run from the project root:

    OPENAI_API_KEY=... \
    OPENAI_BASE_URL=https://api.tokenlab.sh/v1 \
    UV_CACHE_DIR=./uv_cache uv run python notebooks/02-sandbox/03_sandbox_core_debug.py

What this script demonstrates:
- SandboxAgent remains a normal Agent, but carries sandbox defaults.
- Manifest defines a new workspace contract.
- Capabilities attach sandbox-native tools: Shell, Filesystem, Skills.
- SandboxRunConfig chooses the live sandbox session provider.
- OpenAIResponsesModel can drive a SandboxAgent via the normal Runner API.

The script writes a timestamped log file under logs/ and keeps stdout concise.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from agents import ModelSettings, OpenAIResponsesModel, Runner
from agents.run import RunConfig
from agents.sandbox import FileMode, Manifest, Permissions, SandboxAgent, SandboxRunConfig, User
from agents.sandbox.capabilities import Filesystem, LocalDirLazySkillSource, Shell, Skills
from agents.sandbox.entries import Dir, File, LocalDir
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient
from openai import AsyncOpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_DIR = Path(__file__).resolve().parent
HOST_SKILLS_DIR = EXAMPLE_DIR / "skills"
LOG_DIR = PROJECT_ROOT / "logs"

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.3-codex")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.tokenlab.sh/v1")
API_KEY = os.getenv("OPENAI_API_KEY")


def now_label() -> str:
    return datetime.now().strftime("%y%m%d_%H%M%S")


class JsonlLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, payload: dict[str, Any] | None = None) -> None:
        record = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "event": event,
            "payload": payload or {},
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def describe_manifest(manifest: Manifest) -> dict[str, Any]:
    return {
        "root": manifest.root,
        "entries": sorted(str(path) for path in manifest.entries.keys()),
        "users": [getattr(user, "name", str(user)) for user in manifest.users],
        "extra_path_grants": [str(grant) for grant in manifest.extra_path_grants],
    }


def build_manifest() -> Manifest:
    """Create a narrow workspace contract for a fresh sandbox session."""
    analyst = User(name="analyst")

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

    return Manifest(
        root=str(EXAMPLE_DIR),
        users=[analyst],
        entries={
            # Existing host repo copied/materialized into the sandbox workspace.
            "repo": LocalDir(src=EXAMPLE_DIR / "repo"),
            # Synthetic task materials created by the Manifest itself.
            "workspace_notes/task.md": File(
                content=(
                    b"# Sandbox core debug task\n\n"
                    b"1. Read repo/task.md.\n"
                    b"2. Inspect repo/credit_note.sh.\n"
                    b"3. Write a short report to output/sandbox_report.md.\n"
                    b"4. Run sh tests/test_credit_note.sh in repo/.\n"
                ),
                permissions=private_permissions,
            ),
            "output": Dir(permissions=output_permissions),
        },
    )


def build_agent(model: OpenAIResponsesModel) -> SandboxAgent[None]:
    analyst = User(name="analyst")
    return SandboxAgent(
        name="沙盒核心概念调试员",
        model=model,
        instructions=(
            "你正在帮助用户学习 Agents SDK 的 SandboxAgent。"
            "请先读取 `workspace_notes/task.md` 和 `repo/task.md`。"
            "请使用 shell 查看 `repo/credit_note.sh` 和测试文件。"
            "不要修改测试期望。"
            "请运行 `cd repo && sh tests/test_credit_note.sh`。"
            "请把你观察到的 Manifest、Shell、Filesystem、Skills、SandboxRunConfig 作用"
            "简要写入 `output/sandbox_report.md`。"
            "最终用中文总结：读了哪些文件、运行了什么命令、生成了哪个报告。"
        ),
        default_manifest=build_manifest(),
        capabilities=[
            Shell(),
            Filesystem(),
            Skills(
                lazy_from=LocalDirLazySkillSource(
                    source=LocalDir(src=HOST_SKILLS_DIR),
                )
            ),
        ],
        run_as=analyst,
        model_settings=ModelSettings(tool_choice="auto"),
    )


async def run_once(logger: JsonlLogger) -> None:
    if not API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required")

    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=90.0,
        max_retries=0,
    )
    model = OpenAIResponsesModel(model=MODEL, openai_client=client)
    agent = build_agent(model)

    logger.write("config", {"base_url": BASE_URL, "model": MODEL})
    logger.write("manifest", describe_manifest(agent.default_manifest))
    logger.write(
        "agent",
        {
            "name": agent.name,
            "capabilities": [type(capability).__name__ for capability in agent.capabilities],
            "run_as": getattr(agent.run_as, "name", str(agent.run_as)),
        },
    )

    start = time.perf_counter()
    result = await Runner.run(
        agent,
        (
            "执行 workspace_notes/task.md 中的调试任务。"
            "重点验证 Responses 模式能否适配 SandboxAgent、Shell、Filesystem 和 Skills。"
        ),
        max_turns=14,
        run_config=RunConfig(
            sandbox=SandboxRunConfig(client=UnixLocalSandboxClient()),
            tracing_disabled=True,
            workflow_name="Sandbox core debugger with Responses model",
        ),
    )
    latency_ms = int((time.perf_counter() - start) * 1000)

    new_items = []
    for item in result.new_items:
        raw_item = getattr(item, "raw_item", None)
        new_items.append(
            {
                "type": type(item).__name__,
                "item_type": getattr(item, "type", None),
                "raw_type": getattr(raw_item, "type", None),
                "preview": str(item)[:1200],
            }
        )

    logger.write(
        "result",
        {
            "latency_ms": latency_ms,
            "final_output": result.final_output,
            "new_items": new_items,
        },
    )

    print("=== FINAL ===")
    print(result.final_output)
    print("\n=== NEW ITEM TYPES ===")
    for item in result.new_items:
        print(f"- {type(item).__name__}: {getattr(item, 'type', None)}")


async def main() -> None:
    log_path = LOG_DIR / f"sandbox_core_debug_{now_label()}.jsonl"
    logger = JsonlLogger(log_path)
    print(f"log_path={log_path}")
    try:
        await run_once(logger)
        logger.write("completed")
    except Exception as exc:
        logger.write("error", {"type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    asyncio.run(main())

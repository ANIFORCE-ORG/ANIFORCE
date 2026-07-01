# %% [markdown]
# # SandboxAgent Core Debug Cells
#
# 这个文件是 notebook cell 风格的 Python 脚本，可以在 VS Code / Jupyter 里按 `# %%` 分段执行。
#
# 运行前设置环境变量：
#
# ```bash
# export OPENAI_API_KEY='...'
# export OPENAI_BASE_URL='https://api.tokenlab.sh/v1'
# export OPENAI_MODEL='gpt-5.3-codex'
# ```
#
# 目标：逐步调试 SandboxAgent 的核心组成：
#
# - OpenAIResponsesModel
# - SandboxAgent
# - Manifest
# - File / Dir / LocalDir
# - Permissions / User / run_as
# - Shell / Filesystem / Skills
# - SandboxRunConfig
# - UnixLocalSandboxClient
# - Runner.run
# - result.new_items

# %%
from __future__ import annotations

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


# %% [markdown]
# ## 1. 基础路径和模型配置

# %%
PROJECT_ROOT = Path.cwd()
EXAMPLE_DIR = PROJECT_ROOT / "notebooks" / "02-sandbox"
HOST_REPO_DIR = EXAMPLE_DIR / "repo"
HOST_SKILLS_DIR = EXAMPLE_DIR / "skills"
LOG_DIR = PROJECT_ROOT / "logs"

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.3-codex")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.tokenlab.sh/v1")
API_KEY = os.getenv("OPENAI_API_KEY")

print("PROJECT_ROOT =", PROJECT_ROOT)
print("EXAMPLE_DIR  =", EXAMPLE_DIR)
print("HOST_REPO_DIR=", HOST_REPO_DIR)
print("HOST_SKILLS_DIR=", HOST_SKILLS_DIR)
print("MODEL=", MODEL)
print("BASE_URL=", BASE_URL)
print("API_KEY set=", bool(API_KEY))

if not API_KEY:
    raise RuntimeError("请先设置 OPENAI_API_KEY 环境变量")


# %% [markdown]
# ## 2. 小工具：JSON dump 和日志

# %%
def now_label() -> str:
    return datetime.now().strftime("%y%m%d_%H%M%S")


def dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    try:
        return json.loads(json.dumps(obj, default=str))
    except TypeError:
        return str(obj)


def pretty(obj: Any, limit: int = 5000) -> None:
    text = json.dumps(dump(obj), ensure_ascii=False, indent=2, default=str)
    print(text[:limit])
    if len(text) > limit:
        print(f"\n... truncated, total chars={len(text)}")


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


log_path = LOG_DIR / f"sandbox_core_cells_{now_label()}.jsonl"
logger = JsonlLogger(log_path)
print("log_path=", log_path)


# %% [markdown]
# ## 3. 构建 OpenAI Responses 模型
#
# 这里验证 `gpt-5.3-codex` 能通过 Agents SDK 的 `OpenAIResponsesModel` 使用。

# %%
client = AsyncOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    timeout=90.0,
    max_retries=0,
)

model = OpenAIResponsesModel(
    model=MODEL,
    openai_client=client,
)

logger.write("model", {"model": MODEL, "base_url": BASE_URL})
print(model)


# %% [markdown]
# ## 4. 构建 Manifest
#
# Manifest 是“新沙盒会话”的工作区契约。
#
# 这里包含：
#
# - `repo`: 从宿主机复制/物化 `notebooks/02-sandbox/repo`
# - `workspace_notes/task.md`: Manifest 合成出来的任务文件
# - `output`: 用于生成报告的目录
# - `users=[analyst]`: 声明沙盒用户

# %%
def build_manifest() -> Manifest:
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
            "repo": LocalDir(src=HOST_REPO_DIR),
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


manifest = build_manifest()
pretty({
    "root": manifest.root,
    "entries": sorted(str(path) for path in manifest.entries.keys()),
    "users": [getattr(user, "name", str(user)) for user in manifest.users],
})
logger.write("manifest", dump(manifest))


# %% [markdown]
# ## 5. 构建 SandboxAgent
#
# 注意：如果传入 `capabilities=[...]`，会替换 SDK 默认 capabilities。
# 所以这里显式包含：
#
# - `Shell()`：提供 `exec_command`
# - `Filesystem()`：提供 `apply_patch` / `view_image`
# - `Skills(...)`：提供技能发现和加载

# %%
def build_agent() -> SandboxAgent[None]:
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
        default_manifest=manifest,
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


agent = build_agent()
pretty({
    "name": agent.name,
    "capabilities": [type(capability).__name__ for capability in agent.capabilities],
    "run_as": getattr(agent.run_as, "name", str(agent.run_as)),
    "model_settings": dump(agent.model_settings),
})
logger.write("agent", {
    "name": agent.name,
    "capabilities": [type(capability).__name__ for capability in agent.capabilities],
    "run_as": getattr(agent.run_as, "name", str(agent.run_as)),
})


# %% [markdown]
# ## 6. 构建 SandboxRunConfig
#
# 这里决定“本次运行如何获得实时沙盒会话”。
#
# 本地调试使用：
#
# ```python
# SandboxRunConfig(client=UnixLocalSandboxClient())
# ```

# %%
sandbox_config = SandboxRunConfig(
    client=UnixLocalSandboxClient(),
)

run_config = RunConfig(
    sandbox=sandbox_config,
    tracing_disabled=True,
    workflow_name="Sandbox core cells debugger with Responses model",
)

print(run_config)
logger.write("run_config", {"sandbox_client": "UnixLocalSandboxClient", "tracing_disabled": True})


# %% [markdown]
# ## 7. 执行一次 Runner.run
#
# 这一格会真正调用模型和本地 sandbox。它会让 agent：
#
# - 读取 Manifest 合成文件 `workspace_notes/task.md`
# - 读取 `repo/task.md`
# - 查看 `repo/credit_note.sh`
# - 运行测试
# - 写 `output/sandbox_report.md`
# - 返回中文总结

# %%
start = time.perf_counter()

result = await Runner.run(
    agent,
    (
        "执行 workspace_notes/task.md 中的调试任务。"
        "重点验证 Responses 模式能否适配 SandboxAgent、Shell、Filesystem 和 Skills。"
    ),
    max_turns=14,
    run_config=run_config,
)

latency_ms = int((time.perf_counter() - start) * 1000)
print("latency_ms=", latency_ms)
print("\n=== FINAL ===")
print(result.final_output)

logger.write("result_final", {"latency_ms": latency_ms, "final_output": result.final_output})


# %% [markdown]
# ## 8. 检查 result.new_items
#
# 这里能看到 Agents SDK 这次运行产生了哪些 item，例如：
#
# - ReasoningItem
# - ToolCallItem
# - ToolCallOutputItem
# - MessageOutputItem

# %%
print("new_items count=", len(result.new_items))
for i, item in enumerate(result.new_items, 1):
    raw_item = getattr(item, "raw_item", None)
    print(f"\n--- ITEM {i}: {type(item).__name__} ---")
    print("item.type=", getattr(item, "type", None))
    print("raw_item.type=", getattr(raw_item, "type", None))
    print(str(item)[:2500])

logger.write("new_items", {
    "items": [
        {
            "type": type(item).__name__,
            "item_type": getattr(item, "type", None),
            "raw_type": getattr(getattr(item, "raw_item", None), "type", None),
            "preview": str(item)[:1200],
        }
        for item in result.new_items
    ]
})


# %% [markdown]
# ## 9. 可选：读取日志文件

# %%
print("log_path=", log_path)
print(log_path.read_text(encoding="utf-8")[-4000:])


# %% [markdown]
# ## 10. 可选：直接运行当前文件
#
# 在 notebook cell 环境里不需要这一格。这个文件主要是给你逐格调试用。

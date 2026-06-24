"""OpenAI Agents SDK HITL 能力调试

测试 HITL 的核心能力：
1. needs_approval=True 工具是否产生 interruptions
2. RunResult.to_state() 是否可序列化
3. approve 后是否可 resume

运行方式：
  cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE
  UV_CACHE_DIR=./uv_cache uv run python drafts/260624/02_hitl_probe.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "aniforce-agent"))

from agents import Agent, Runner, function_tool, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "drafts"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / f"hitl_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"


def load_agent_env():
    env_path = Path("aniforce-agent/.env")
    if not env_path.exists():
        raise RuntimeError("Missing aniforce-agent/.env")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def create_sdk_model():
    load_agent_env()
    set_tracing_disabled(True)
    api_mode = os.environ.get("OPENAI_AGENTS_API", "").strip().lower()
    if api_mode not in {"chat", "chat_completions", "chat-completions"}:
        raise RuntimeError(f"DeepSeek probe requires chat_completions, got {api_mode!r}")
    model = os.environ.get("OPENAI_AGENTS_MODEL", "deepseek-v4-pro")
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )
    return OpenAIChatCompletionsModel(model=model, openai_client=client)


def log_event(event_type: str, data: dict[str, Any]):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"type": event_type, "timestamp": datetime.now().isoformat(), "data": data},
                ensure_ascii=False,
            )
            + "\n"
        )


@function_tool
def get_info(name: str) -> str:
    """获取信息，安全操作。"""
    return f"这是 {name} 的信息"


@function_tool(needs_approval=True)
def delete_project(project_id: str) -> str:
    """删除项目，危险操作，需要审批。"""
    return f"项目 {project_id} 已删除"


def create_agent() -> Agent:
    return Agent(
        name="assistant",
        instructions=(
            "你是一个助手。用户要求删除项目时必须调用 delete_project 工具，"
            "不要只用自然语言回答。"
        ),
        model=create_sdk_model(),
        tools=[get_info, delete_project],
    )


def summarize_interruption(item: Any) -> dict[str, Any]:
    raw_item = getattr(item, "raw_item", None)
    return {
        "type": type(item).__name__,
        "agent": getattr(getattr(item, "agent", None), "name", None),
        "raw_type": type(raw_item).__name__ if raw_item is not None else None,
        "tool_name": getattr(raw_item, "name", None) or getattr(raw_item, "tool_name", None),
        "call_id": getattr(raw_item, "call_id", None),
        "arguments": getattr(raw_item, "arguments", None),
    }


async def test_needs_approval():
    print("\n=== Test 1: needs_approval 工具触发审批 ===")
    result = await Runner.run(create_agent(), "删除项目 proj_123")
    interruptions = list(getattr(result, "interruptions", []) or [])

    log_event(
        "run_with_approval",
        {
            "has_interruptions": bool(interruptions),
            "interruptions_count": len(interruptions),
            "interruptions": [summarize_interruption(item) for item in interruptions],
            "final_output": getattr(result, "final_output", None),
        },
    )

    print(f"interruptions: {len(interruptions)}")
    for item in interruptions:
        print(json.dumps(summarize_interruption(item), ensure_ascii=False))
    return result


async def test_run_state(result: Any):
    print("\n=== Test 2: RunState 序列化 ===")
    if not hasattr(result, "to_state"):
        log_event("run_state_missing", {"has_to_state": False})
        print("Result 没有 to_state()")
        return None

    state = result.to_state()
    state_json = state.to_json()
    state_text = state.to_string()
    log_event(
        "run_state_extracted",
        {
            "state_type": type(state).__name__,
            "json_keys": sorted(state_json.keys()),
            "json_size": len(json.dumps(state_json, ensure_ascii=False)),
            "string_size": len(state_text),
            "interruptions_count": len(state.get_interruptions()),
        },
    )
    print(f"RunState: {type(state).__name__}")
    print(f"state json size: {len(json.dumps(state_json, ensure_ascii=False))}")
    print(f"state interruptions: {len(state.get_interruptions())}")
    return state


async def test_approval_resume(state: Any):
    print("\n=== Test 3: approve 后 resume ===")
    if state is None:
        print("跳过：没有 RunState")
        return

    interruptions = state.get_interruptions()
    if not interruptions:
        print("跳过：没有 interruptions")
        return

    state.approve(interruptions[0])
    resumed = await Runner.run(create_agent(), state)
    log_event(
        "approval_resumed",
        {
            "final_output": resumed.final_output,
            "interruptions_count": len(getattr(resumed, "interruptions", []) or []),
        },
    )
    print(f"resume final_output: {resumed.final_output}")


async def main():
    print("OpenAI Agents SDK HITL 能力调试")
    print(f"日志文件: {log_file}")
    print("=" * 60)
    result = await test_needs_approval()
    state = await test_run_state(result)
    await test_approval_resume(state)
    print("\n" + "=" * 60)
    print(f"测试完成，日志已写入: {log_file}")


if __name__ == "__main__":
    asyncio.run(main())

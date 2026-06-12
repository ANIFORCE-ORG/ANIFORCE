"""Minimal openai-agents SDK probe for ANIFORCE.

Run from ANIFORCE/backend with the shared uv environment:

  UV_CACHE_DIR=./uv_cache uv run python ../drafts/260611/openai_agents_probe.py inspect
  UV_CACHE_DIR=./uv_cache uv run python ../drafts/260611/openai_agents_probe.py run "用一句话说明 ANIFORCE 是什么"
  UV_CACHE_DIR=./uv_cache uv run python ../drafts/260611/openai_agents_probe.py stream "用一句话说明 ANIFORCE 是什么"

Requires OPENAI_API_KEY for run/stream modes.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import os
from pathlib import Path
from typing import Any

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
load_dotenv(BACKEND_DIR / ".env")

DEFAULT_MODEL = os.getenv("OPENAI_AGENTS_MODEL", "gpt-4.1-mini")
DEFAULT_BASE_URL = os.getenv("OPENAI_BASE_URL")


SYSTEM_PROMPT = """
你是 ANIFORCE 的开发调试助手。
回答要简洁、直接，优先帮助开发者理解 openai-agents-python SDK 行为。
""".strip()


def build_model() -> str | OpenAIChatCompletionsModel:
    if DEFAULT_BASE_URL:
        client = AsyncOpenAI(
            base_url=DEFAULT_BASE_URL,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        return OpenAIChatCompletionsModel(
            model=DEFAULT_MODEL,
            openai_client=client,
            strict_feature_validation=False,
        )
    return DEFAULT_MODEL


def build_agent() -> Agent:
    return Agent(
        name="ANIFORCE Debug Assistant",
        instructions=SYSTEM_PROMPT,
        model=build_model(),
    )


def print_result_shape(result: Any) -> None:
    print("\n[result shape]")
    for attr in [
        "final_output",
        "last_agent",
        "new_items",
        "raw_responses",
        "input",
    ]:
        if hasattr(result, attr):
            value = getattr(result, attr)
            if attr in {"new_items", "raw_responses"}:
                print(f"{attr}: {type(value).__name__}[{len(value)}]")
            else:
                print(f"{attr}: {value!r}")

    if hasattr(result, "to_input_list"):
        input_list = result.to_input_list()
        print(f"to_input_list(): list[{len(input_list)}]")

    if hasattr(result, "to_state"):
        state = result.to_state()
        print(f"to_state(): {type(state).__name__}")


def inspect_sdk() -> None:
    import agents
    import importlib.metadata as metadata

    print("agents module:", agents.__file__)
    print("openai-agents version:", metadata.version("openai-agents"))
    print("Agent:", Agent)
    print("OPENAI_BASE_URL:", DEFAULT_BASE_URL or "<default>")
    print("OPENAI_AGENTS_MODEL:", DEFAULT_MODEL)
    print("OPENAI_AGENTS_API:", os.getenv("OPENAI_AGENTS_API", "<default>"))
    print("Runner.run:", inspect.signature(Runner.run))
    print("Runner.run_sync:", inspect.signature(Runner.run_sync))
    print("Runner.run_streamed:", inspect.signature(Runner.run_streamed))

    agent = build_agent()
    print("\n[agent]")
    print("name:", agent.name)
    print("model:", agent.model)
    print("model type:", type(agent.model).__name__)
    print("instructions type:", type(agent.instructions).__name__)


async def run_once(message: str) -> None:
    require_api_key()
    set_tracing_disabled(True)
    agent = build_agent()
    result = await Runner.run(agent, message)
    print("\n[final_output]")
    print(result.final_output)
    print_result_shape(result)


async def stream_once(message: str) -> None:
    require_api_key()
    set_tracing_disabled(True)
    agent = build_agent()
    result = Runner.run_streamed(agent, message)

    print("[stream events]")
    async for event in result.stream_events():
        event_type = getattr(event, "type", None)
        print_event(event_type, event)

    print("\n[stream completed]")
    print("is_complete:", getattr(result, "is_complete", None))
    print("current_agent:", getattr(result, "current_agent", None))
    print_result_shape(result)


def print_event(event_type: str | None, event: Any) -> None:
    if event_type == "raw_response_event":
        data = getattr(event, "data", None)
        data_type = getattr(data, "type", type(data).__name__)
        delta = getattr(data, "delta", None)
        if delta:
            print(f"raw_response_event {data_type}: {delta!r}")
        else:
            print(f"raw_response_event {data_type}")
        return

    if event_type == "run_item_stream_event":
        item = getattr(event, "item", None)
        item_type = getattr(item, "type", type(item).__name__)
        print(f"run_item_stream_event {item_type}")
        return

    if event_type == "agent_updated_stream_event":
        new_agent = getattr(event, "new_agent", None)
        print(f"agent_updated_stream_event {getattr(new_agent, 'name', new_agent)!r}")
        return

    print(f"{event_type or type(event).__name__}: {event!r}")


def require_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Put it in backend/.env or export it before run/stream."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe openai-agents SDK behavior.")
    parser.add_argument("mode", choices=["inspect", "run", "stream"])
    parser.add_argument("message", nargs="?", default="用一句话说明 ANIFORCE 是什么")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "inspect":
        inspect_sdk()
        return
    if args.mode == "run":
        asyncio.run(run_once(args.message))
        return
    if args.mode == "stream":
        asyncio.run(stream_once(args.message))
        return


if __name__ == "__main__":
    main()

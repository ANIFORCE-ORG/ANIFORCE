from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
load_dotenv(BACKEND_DIR / ".env")

MODEL = os.getenv("OPENAI_AGENTS_MODEL", "gpt-4.1-mini")
BASE_URL = os.getenv("OPENAI_BASE_URL")


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump())
    if hasattr(value, "__dict__"):
        return {k: jsonable(v) for k, v in vars(value).items() if not k.startswith("_")}
    return repr(value)


def build_agent() -> Agent:
    if BASE_URL:
        model = OpenAIChatCompletionsModel(
            model=MODEL,
            openai_client=AsyncOpenAI(base_url=BASE_URL, api_key=os.getenv("OPENAI_API_KEY")),
            strict_feature_validation=False,
        )
    else:
        model = MODEL
    return Agent(
        name="ANIFORCE Protocol Dump Agent",
        instructions="只做协议调试。回答要短。不要假装调用工具。",
        model=model,
    )


async def main() -> None:
    set_tracing_disabled(True)
    message = "请用两句话介绍 ANIFORCE，不要使用列表。"
    agent = build_agent()
    result = Runner.run_streamed(agent, message)

    print("# stream_events")
    async for event in result.stream_events():
        event_type = getattr(event, "type", type(event).__name__)
        data = getattr(event, "data", None)
        item = getattr(event, "item", None)
        payload = {
            "event_type": event_type,
            "data_type": getattr(data, "type", None),
            "delta": getattr(data, "delta", None),
            "item_type": getattr(item, "type", None),
            "event": jsonable(event),
        }
        print(json.dumps(payload, ensure_ascii=False, default=str))

    print("# result")
    print(json.dumps({
        "is_complete": getattr(result, "is_complete", None),
        "final_output": getattr(result, "final_output", None),
        "new_items": jsonable(getattr(result, "new_items", [])),
        "raw_responses": jsonable(getattr(result, "raw_responses", [])),
    }, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

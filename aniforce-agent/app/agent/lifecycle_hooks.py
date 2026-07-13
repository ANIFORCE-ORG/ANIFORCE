"""Agents SDK lifecycle hooks for ANIFORCE runtime."""

from __future__ import annotations

from typing import Any

from agents import RunHooks
from loguru import logger

from app.agent.workspace_context import WorkspaceRunContext


class WorkspaceRunHooks(RunHooks[WorkspaceRunContext]):
    """SDK-native run hooks for runtime observability and future projection.

    Keep this hook side-effect-light for now. It records lifecycle signals through
    the SDK's official hook mechanism and does not change the streamed protocol.
    """

    async def on_llm_start(self, context, agent, system_prompt: str | None, input_items: list[Any]) -> None:
        run_context = context.context
        logger.debug(
            "[SDK_HOOK] llm_start run_id={} session_id={} user_id={} agent={} input_items={} system_prompt_len={}",
            run_context.run_id,
            run_context.session_id,
            run_context.user_id,
            getattr(agent, "name", None),
            len(input_items),
            len(system_prompt or ""),
        )

    async def on_llm_end(self, context, agent, response) -> None:
        run_context = context.context
        logger.debug(
            "[SDK_HOOK] llm_end run_id={} session_id={} user_id={} agent={} response_type={}",
            run_context.run_id,
            run_context.session_id,
            run_context.user_id,
            getattr(agent, "name", None),
            type(response).__name__,
        )

    async def on_agent_start(self, context, agent) -> None:
        run_context = context.context
        logger.debug(
            "[SDK_HOOK] agent_start run_id={} session_id={} user_id={} agent={}",
            run_context.run_id,
            run_context.session_id,
            run_context.user_id,
            getattr(agent, "name", None),
        )

    async def on_agent_end(self, context, agent, output: Any) -> None:
        run_context = context.context
        logger.debug(
            "[SDK_HOOK] agent_end run_id={} session_id={} user_id={} agent={} output_type={}",
            run_context.run_id,
            run_context.session_id,
            run_context.user_id,
            getattr(agent, "name", None),
            type(output).__name__,
        )

    async def on_handoff(self, context, from_agent, to_agent) -> None:
        run_context = context.context
        logger.debug(
            "[SDK_HOOK] handoff run_id={} session_id={} user_id={} from_agent={} to_agent={}",
            run_context.run_id,
            run_context.session_id,
            run_context.user_id,
            getattr(from_agent, "name", None),
            getattr(to_agent, "name", None),
        )

    async def on_tool_start(self, context, agent, tool) -> None:
        run_context = context.context
        logger.debug(
            "[SDK_HOOK] tool_start run_id={} session_id={} user_id={} agent={} tool={} tool_call_id={}",
            run_context.run_id,
            run_context.session_id,
            run_context.user_id,
            getattr(agent, "name", None),
            getattr(tool, "name", None),
            getattr(context, "tool_call_id", None),
        )

    async def on_tool_end(self, context, agent, tool, result: object) -> None:
        run_context = context.context
        logger.debug(
            "[SDK_HOOK] tool_end run_id={} session_id={} user_id={} agent={} tool={} tool_call_id={} result_type={} result_len={}",
            run_context.run_id,
            run_context.session_id,
            run_context.user_id,
            getattr(agent, "name", None),
            getattr(tool, "name", None),
            getattr(context, "tool_call_id", None),
            type(result).__name__,
            len(str(result)) if result is not None else 0,
        )

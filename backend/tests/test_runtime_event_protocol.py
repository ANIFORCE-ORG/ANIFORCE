import pytest
import sys
from pathlib import Path

backend_root = Path(__file__).parent.parent
project_root = backend_root.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(project_root / "resources" / "openai-agents-python" / "src"))

from app.agent_platform.models import AgentTask, AgentTaskEvent, AgentTaskStatus, EventType
from app.agent_platform.repositories.memory import MemoryAgentTaskRepository
from app.agent_platform.runtime import AgentRuntime


class _FakeResult:
    final_output = "done"


class _FakeAdapter:
    skills_dir = "runtime/skills"

    def __init__(self, events):
        self._events = events

    def create_agent(self, **kwargs):
        return object()

    def create_session(self, session_id, db_path):
        return object()

    async def run_streamed(self, **kwargs):
        return _FakeResult()

    async def stream_events(self, result, task_id, start_sequence=0):
        for index, event in enumerate(self._events, start=start_sequence + 1):
            event.task_id = task_id
            event.sequence = index
            yield event

    def _extract_usage(self, result):
        return None


def _task(task_id="task_protocol"):
    return AgentTask(
        task_id=task_id,
        user_id="user_1",
        task_type="conversation",
        title="Protocol test",
        status=AgentTaskStatus.PENDING,
        context={},
    )


@pytest.mark.asyncio
async def test_runtime_detects_plan_from_message_delta():
    events = [
        AgentTaskEvent(
            event_id="message_1",
            task_id="placeholder",
            event_type=EventType.MESSAGE_UPDATED,
            payload={
                "delta": (
                    "执行计划\n"
                    "1. 梳理当前协议\n"
                    "2. 修复前端渲染\n"
                    "3. 校验端到端状态\n"
                )
            },
            sequence=0,
        )
    ]
    runtime = AgentRuntime(_FakeAdapter(events), MemoryAgentTaskRepository(), enable_tracing=False)

    emitted = [event async for event in runtime.run_task(_task(), "需要计划")]

    plan_events = [
        event
        for event in emitted
        if event.event_type == EventType.CUSTOM
        and event.payload.get("subtype") == EventType.PLAN_CREATED
    ]
    assert len(plan_events) == 1
    assert [todo["title"] for todo in plan_events[0].payload["todos"]] == [
        "梳理当前协议",
        "修复前端渲染",
        "校验端到端状态",
    ]


@pytest.mark.asyncio
async def test_runtime_tracks_first_todo_when_tool_starts_after_plan():
    events = [
        AgentTaskEvent(
            event_id="message_1",
            task_id="placeholder",
            event_type=EventType.MESSAGE_UPDATED,
            payload={"delta": "执行计划\n1. 查询项目\n2. 汇总结果\n"},
            sequence=0,
        ),
        AgentTaskEvent(
            event_id="tool_1",
            task_id="placeholder",
            event_type=EventType.TOOL_CALL_STARTED,
            payload={"tool_name": "list_projects", "arguments": {"limit": 10}},
            sequence=0,
        ),
    ]
    runtime = AgentRuntime(_FakeAdapter(events), MemoryAgentTaskRepository(), enable_tracing=False)

    emitted = [event async for event in runtime.run_task(_task("task_tool"), "需要工具")]

    todo_events = [
        event
        for event in emitted
        if event.event_type == EventType.CUSTOM
        and event.payload.get("subtype") == EventType.TODO_STARTED
    ]
    assert len(todo_events) == 1
    assert todo_events[0].payload["todo_id"] == "todo_1"
    assert todo_events[0].payload["tool_name"] == "list_projects"

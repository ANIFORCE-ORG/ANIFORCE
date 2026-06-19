"""
Agent Runtime

负责执行 Agent 任务，管理生命周期，推送事件流
支持 Plan-Execute 框架
"""

import asyncio
from typing import AsyncIterator, Optional
from uuid import uuid4
from contextlib import asynccontextmanager

from loguru import logger

from app.models.agent_platform_models import AgentTask, AgentTaskEvent, AgentTaskStatus, EventType, ExecutionPlan, TodoStatus
from app.repositories.base import AgentTaskRepository
from app.agent.openai_adapter import OpenAISDKAdapter
from app.core.errors import AppError, AgentErrorCode, ErrorCategory
from app.core.tracing import get_tracer
from app.agent.prompts import SystemPromptManager
from app.agent.plan_parser import PlanParser


class AgentRuntime:
    """Agent 运行时"""
    
    def __init__(
        self,
        adapter: OpenAISDKAdapter,
        repo: AgentTaskRepository,
        session_db_path: str = "runtime/agent/sessions.db",
        enable_tracing: bool = True,
    ):
        self.adapter = adapter
        self.repo = repo
        self.session_db_path = session_db_path
        self.enable_tracing = enable_tracing
        self.tracer = get_tracer() if enable_tracing else None
        
        # Plan-Execute 状态管理
        self.current_plan: Optional[ExecutionPlan] = None
        
        logger.info(f"AgentRuntime initialized | tracing={enable_tracing}")
    
    @asynccontextmanager
    async def _mcp_connection(self, task: AgentTask):
        """MCP 连接上下文管理器（路径 B：连本进程 /mcp + 多租户隔离）

        通过 tool_meta_resolver 把 task.context['auth_token'] 注入每次 MCP 调用的 _meta，
        server 端工具函数从 request_context.meta['jwt_token'] 读。
        每个 task 独立 resolver，多用户并发不串号。
        """
        from agents.mcp import MCPServerStreamableHttp, MCPToolMetaContext
        from app.config.settings import get_settings

        settings = get_settings()
        mcp_url = f"http://127.0.0.1:{settings.PORT}/mcp"
        jwt_token = (task.context or {}).get("auth_token", "")
        run_meta = (task.context or {}).get("run_meta", {}) or {}

        def _meta_resolver(ctx: MCPToolMetaContext) -> dict[str, str] | None:
            """每次 MCP 工具调用前注入 jwt_token 和 run/session 元信息"""
            meta: dict[str, str] = {}
            if jwt_token:
                meta["jwt_token"] = jwt_token
            if task.session_id:
                meta["session_id"] = task.session_id
            if run_meta.get("run_id"):
                meta["run_id"] = str(run_meta["run_id"])
            return meta or None

        mcp_server = None
        mcp_servers = []

        try:
            mcp_server = MCPServerStreamableHttp(
                name="ANIFORCE Tools",
                params={
                    "url": mcp_url,
                    "timeout": 30,
                },
                cache_tools_list=True,
                max_retry_attempts=2,
                tool_meta_resolver=_meta_resolver,
            )
            await mcp_server.__aenter__()
            mcp_servers.append(mcp_server)
            logger.debug(f"[RUNTIME] MCP server connected: {mcp_url} (jwt={'<present>' if jwt_token else '<missing>'})")

            yield mcp_servers

        finally:
            if mcp_server:
                try:
                    await mcp_server.__aexit__(None, None, None)
                    logger.debug(f"[RUNTIME] MCP server disconnected")
                except Exception as e:
                    logger.warning(f"[RUNTIME] MCP cleanup error: {e}")
    
    async def run_task(
        self,
        task: AgentTask,
        user_input: str,
    ) -> AsyncIterator[AgentTaskEvent]:
        """
        运行任务
        
        Args:
            task: AgentTask 实例
            user_input: 用户输入
            
        Yields:
            AgentTaskEvent（实时事件流）
        """
        task_logger = logger.bind(task_id=task.task_id, user_id=task.user_id)
        
        # 开始 Trace
        trace_ctx = None
        if self.tracer:
            trace_ctx = self.tracer.trace_task(task.task_id, task.user_id, task.task_type)
            trace_ctx.__enter__()
        
        try:
            task_logger.info(f"[RUNTIME] Task started: {task.task_type}")
            self.current_plan = None
            
            # 1. 更新状态为 running
            await self.repo.update_status(task.task_id, AgentTaskStatus.RUNNING)
            
            # 2. 推送 runtime.started 事件
            sequence = await self.repo.count_task_events(task.task_id)
            started_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_STARTED,
                payload={"task_type": task.task_type, "user_input": user_input},
                sequence=sequence,
            )
            await self.repo.append_event(started_event)
            yield started_event
            
            # 3. 创建或复用 Session
            if task.session_id:
                session = self.adapter.create_session(task.session_id, self.session_db_path)
                task_logger.info(f"[RUNTIME] Reusing session: {task.session_id}")
            else:
                session_id = f"session_{uuid4().hex[:16]}"
                session = self.adapter.create_session(session_id, self.session_db_path)
                task.session_id = session_id
                task_logger.info(f"[RUNTIME] Created new session: {session_id}")

            # 4. 使用 MCP 连接上下文管理器
            async with self._mcp_connection(task) as mcp_servers:
                # 5. 创建 Agent（带 MCP 服务 + session 级 sandbox）
                agent = self.adapter.create_agent(
                    name="ANIFORCE Assistant",
                    instructions=self._get_system_prompt(task),
                    mcp_servers=mcp_servers,
                    session_id=task.session_id,
                )
                
                # 6. 执行 Agent
                task_logger.info(f"[RUNTIME] Executing Agent...")
                result = await self.adapter.run_streamed(
                    agent=agent,
                    input_text=user_input,
                    session=session,
                )
                
                # 7. 流式推送事件（增加 Plan 检测）
                message_buffer = []  # 缓存消息内容用于 Plan 检测
                
                async for event in self.adapter.stream_events(result, task.task_id, start_sequence=sequence):
                    await self.repo.append_event(event)
                    yield event
                    sequence = event.sequence
                    
                    # 检测执行计划
                    if event.event_type == EventType.MESSAGE_UPDATED:
                        content = event.payload.get("delta") or event.payload.get("content", "")
                        if content:
                            message_buffer.append(content)
                            
                            # 尝试提取 Plan。流式 delta 可能一次就包含完整计划，不能只读 content。
                            if self.current_plan is None:
                                full_message = "".join(message_buffer)
                                plan_result = await self._detect_and_extract_plan(
                                    full_message,
                                    task.task_id,
                                    sequence
                                )
                                
                                if plan_result:
                                    plan, plan_event = plan_result
                                    await self.repo.append_event(plan_event)
                                    yield plan_event
                                    sequence = plan_event.sequence
                                    message_buffer = []  # 清空缓存
                    
                    # 跟踪 Todo 执行
                    elif event.event_type == EventType.TOOL_CALL_STARTED:
                        tool_name = event.payload.get("tool_name", "unknown")
                        task_logger.info(f"[RUNTIME] Event[{sequence}]: tool_call | tool={tool_name}")
                        
                        # 尝试关联到 Todo
                        todo_event = await self._track_todo_execution(
                            tool_name,
                            task.task_id,
                            sequence
                        )
                        
                        if todo_event:
                            await self.repo.append_event(todo_event)
                            yield todo_event
                            sequence = todo_event.sequence
            
            # 8. 更新状态为 completed
            await self.repo.update_status(task.task_id, AgentTaskStatus.COMPLETED)
            
            usage = self.adapter._extract_usage(result)
            
            # 9. 推送 runtime.completed 事件
            sequence += 1
            completed_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_COMPLETED,
                payload={"final_output": getattr(result, "final_output", None), "usage": usage},
                sequence=sequence,
            )
            await self.repo.append_event(completed_event)
            yield completed_event
            
            task_logger.info(f"[RUNTIME] Task completed successfully")
        
        except asyncio.CancelledError:
            task_logger.warning(f"[RUNTIME] Task cancelled by user")
            await self.repo.update_status(task.task_id, AgentTaskStatus.ABORTED)
            
            sequence += 1
            aborted_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_ABORTED,
                payload={"message": "Task cancelled by user"},
                sequence=sequence,
            )
            await self.repo.append_event(aborted_event)
            yield aborted_event
        
        except AppError as e:
            task_logger.error(f"[RUNTIME] AppError: {e.code.value} - {e.message}")
            await self.repo.update_task_error(task.task_id, e.to_dict())
            await self.repo.update_status(task.task_id, AgentTaskStatus.ERROR)
            
            sequence += 1
            error_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_ERROR,
                payload=e.to_dict(),
                sequence=sequence,
            )
            await self.repo.append_event(error_event)
            yield error_event
        
        except Exception as e:
            task_logger.exception(f"[RUNTIME] Unexpected error: {e}")
            
            error_dict = {
                "code": AgentErrorCode.UNKNOWN_ERROR.value,
                "message": "An unexpected error occurred",
                "internal_message": str(e),
                "category": ErrorCategory.RUNTIME_ERROR.value,
            }
            
            await self.repo.update_task_error(task.task_id, error_dict)
            await self.repo.update_status(task.task_id, AgentTaskStatus.ERROR)
            
            sequence += 1
            error_event = AgentTaskEvent(
                event_id=f"event_{task.task_id}_{sequence}",
                task_id=task.task_id,
                event_type=EventType.RUNTIME_ERROR,
                payload={"code": AgentErrorCode.UNKNOWN_ERROR.value, "message": str(e)},
                sequence=sequence,
            )
            await self.repo.append_event(error_event)
            yield error_event
        
        finally:
            # 结束 Trace
            if trace_ctx:
                trace_ctx.__exit__(None, None, None)
    
    def _get_system_prompt(self, task: AgentTask) -> str:
        """根据任务和 backend 业务上下文返回 system prompt"""
        
        # 获取 MCP Tools 列表（从 adapter 中获取）
        # TODO: 实现动态获取 MCP Tools
        available_mcp_tools = [
            "list_projects",
            "create_project",
            "get_project_detail",
            "update_project",
            "delete_project",
            "list_campaigns",
            "create_campaign",
            "get_campaign_detail",
            "update_campaign",
            "delete_campaign",
        ]
        
        # 使用 Plan-Execute 模式的 System Prompt
        base_prompt = SystemPromptManager.get_plan_execute_prompt(
            skills_dir=self.adapter.skills_dir,
            available_mcp_tools=available_mcp_tools
        )
        business_context_summary = (task.context or {}).get("business_context_summary", "")
        if not business_context_summary:
            return base_prompt
        return (
            f"{base_prompt}\n\n"
            "---\n"
            "# Backend Business Context\n"
            "以下内容由 backend Session State Manager 构建，用于说明当前业务现场。"
            "backend DB 是业务事实源；如需修改业务数据，必须通过 MCP 工具调用 backend REST。\n\n"
            f"{business_context_summary}\n"
            "---"
        )

    async def _detect_and_extract_plan(
        self,
        message_content: str,
        task_id: str,
        current_sequence: int
    ) -> Optional[tuple[ExecutionPlan, AgentTaskEvent]]:
        """
        检测并提取执行计划
        
        Args:
            message_content: Agent 输出的消息内容
            task_id: 任务 ID
            current_sequence: 当前事件序号
            
        Returns:
            (ExecutionPlan, Event) 或 None
        """
        # 尝试从消息中提取 Plan
        plan = PlanParser.extract_plan_from_text(message_content, task_id)
        
        if plan:
            # 保存当前 Plan
            self.current_plan = plan
            
            # 创建 PLAN_CREATED 事件
            plan_event = AgentTaskEvent(
                event_id=f"event_{task_id}_{current_sequence + 1}",
                task_id=task_id,
                event_type=EventType.CUSTOM,
                payload={
                    "subtype": EventType.PLAN_CREATED,
                    "plan_id": plan.plan_id,
                    "todos": [
                        {
                            "id": todo.id,
                            "title": todo.title,
                            "description": todo.description,
                            "status": todo.status.value,
                        }
                        for todo in plan.todos
                    ]
                },
                sequence=current_sequence + 1,
            )
            
            logger.info(f"[RUNTIME] Detected Plan with {len(plan.todos)} todos")
            return (plan, plan_event)
        
        return None
    
    async def _track_todo_execution(
        self,
        tool_name: str,
        task_id: str,
        current_sequence: int
    ) -> Optional[AgentTaskEvent]:
        """
        跟踪 Todo 执行（通过 Tool 调用推断）
        
        Args:
            tool_name: 被调用的工具名称
            task_id: 任务 ID
            current_sequence: 当前事件序号
            
        Returns:
            TODO_STARTED 事件或 None
        """
        if not self.current_plan:
            return None
        
        # 检查是否有待执行的 Todo
        current_todo = None
        for todo in self.current_plan.todos:
            if todo.status.value == "pending":
                current_todo = todo
                break
        
        if current_todo:
            # 标记为 running
            current_todo.status = TodoStatus.RUNNING
            
            # 创建 TODO_STARTED 事件
            todo_event = AgentTaskEvent(
                event_id=f"event_{task_id}_{current_sequence + 1}",
                task_id=task_id,
                event_type=EventType.CUSTOM,
                payload={
                    "subtype": EventType.TODO_STARTED,
                    "todo_id": current_todo.id,
                    "title": current_todo.title,
                    "tool_name": tool_name,
                },
                sequence=current_sequence + 1,
            )
            
            logger.info(f"[RUNTIME] Todo started: {current_todo.id} - {current_todo.title}")
            return todo_event
        
        return None

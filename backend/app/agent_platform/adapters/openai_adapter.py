"""
OpenAI Agents SDK 适配器

遵循 Block 0 规范：
- 业务代码不直接依赖 SDK
- 封装 SDK 调用和事件转换
- 统一错误处理
"""

import os
from typing import AsyncIterator, Optional
from pathlib import Path
from loguru import logger

from agents import (
    Agent,
    Runner,
    SQLiteSession,
    set_default_openai_api,
    set_default_openai_key,
    set_tracing_disabled,
    RunConfig,  # 添加 RunConfig
)
from agents.run import RunResult
from agents.sandbox import SandboxAgent, Manifest
from agents.sandbox.runtime import SandboxRuntime  # 正确的导入路径
from agents.sandbox.capabilities import Capabilities, Skills, LocalDirLazySkillSource
from agents.sandbox.entries import LocalDir

from ..models import AgentTaskEvent, EventType
from ..errors import AppError, AgentErrorCode, ErrorCategory
from ..tracing import get_tracer


class OpenAISDKAdapter:
    """OpenAI Agents SDK 适配器"""
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        enable_tracing: bool = True,
        skills_dir: Optional[str] = None,
        sandbox_dir: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.enable_tracing = enable_tracing
        self.skills_dir = skills_dir or "runtime/skills"
        self.sandbox_dir = sandbox_dir or "runtime/agent/sandbox"
        self.tracer = get_tracer() if enable_tracing else None
        
        # 创建沙箱目录
        Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)
        
        # SDK 默认走 Responses API；当前兼容网关只支持 Chat Completions。
        set_default_openai_api("chat_completions")
        # 项目使用本地 JSONL tracing，禁用 OpenAI 官方 trace export。
        set_tracing_disabled(True)
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            set_default_openai_key(api_key, use_for_tracing=False)
        if base_url:
            os.environ["OPENAI_BASE_URL"] = base_url
        
        logger.info(f"OpenAI SDK Adapter initialized: {model} | tracing={enable_tracing}")
    
    def create_agent(
        self,
        name: str,
        instructions: str,
        mcp_servers: list = None,
        enable_skills: bool = True,
    ) -> Agent:
        """
        创建 Agent（支持 Skills）
        
        Args:
            name: Agent 名称
            instructions: System prompt
            mcp_servers: MCP 服务列表（可选）
            enable_skills: 是否启用 Skills（默认 True）
        """
        # 检查 Skills 目录是否存在
        skills_path = Path(self.skills_dir)
        has_skills = enable_skills and skills_path.exists()
        
        if has_skills:
            # 使用 SandboxAgent（支持 Skills）
            agent = SandboxAgent(
                name=name,
                instructions=instructions,
                model=self.model,
                mcp_servers=mcp_servers or [],
                default_manifest=Manifest(root=self.sandbox_dir),  # 自定义沙箱目录
                capabilities=Capabilities.default() + [
                    Skills(
                        lazy_from=LocalDirLazySkillSource(
                            source=LocalDir(src=self.skills_dir)
                        )
                    )
                ]
            )
            logger.info(f"[SDK] Created SandboxAgent with Skills: {self.skills_dir}")
            logger.info(f"[SDK] Sandbox directory: {self.sandbox_dir}")
        else:
            # 使用普通 Agent（向后兼容）
            agent = Agent(
                name=name,
                instructions=instructions,
                model=self.model,
                mcp_servers=mcp_servers or [],
            )
            logger.info(f"[SDK] Created Agent without Skills (skills_dir not found or disabled)")
        
        logger.debug(f"[SDK] Agent '{name}' with {len(mcp_servers or [])} MCP servers")
        return agent
    
    def create_session(self, session_id: str, db_path: str = "runtime/agent/sessions.db") -> SQLiteSession:
        """
        创建 SDK Session（用于管理对话历史）
        
        Args:
            session_id: Session ID
            db_path: SQLite 数据库路径
        """
        return SQLiteSession(session_id, db_path=db_path)
    
    async def run_streamed(
        self,
        agent: Agent,
        input_text: str,
        session: Optional[SQLiteSession] = None,
    ) -> RunResult:
        """
        流式执行 Agent
        
        Args:
            agent: Agent 实例
            input_text: 用户输入
            session: SDK Session（可选）
            
        Returns:
            RunResult（可以流式读取事件）
        """
        # Trace SDK 调用
        if self.tracer:
            self.tracer.log_sdk_call(
                method="run_streamed",
                agent_name=getattr(agent, "name", "unknown"),
                input_text=input_text,
                session_id=getattr(session, "session_id", None) if session else None,
            )
        
        try:
            # 检查是否是 SandboxAgent
            is_sandbox_agent = isinstance(agent, SandboxAgent)
            
            if is_sandbox_agent:
                # SandboxAgent 需要 RunConfig
                sandbox_runtime = SandboxRuntime(
                    sandbox_dir=self.sandbox_dir,
                )
                config = RunConfig(sandbox=sandbox_runtime)
                result = Runner.run_streamed(
                    agent,
                    input=input_text,
                    session=session,
                    config=config,
                )
            else:
                # 普通 Agent
                result = Runner.run_streamed(
                    agent,
                    input=input_text,
                    session=session,
                )
            
            return result
        except Exception as e:
            logger.exception(f"SDK run_streamed error: {e}")
            raise AppError(
                code=AgentErrorCode.SDK_ERROR,
                message=f"SDK execution failed: {str(e)}",
                category=ErrorCategory.RUNTIME_ERROR,
            )
    
    async def stream_events(
        self,
        result: RunResult,
        task_id: str,
        start_sequence: int = 0,
    ) -> AsyncIterator[AgentTaskEvent]:
        """
        流式读取 SDK 事件并转换为 AgentTaskEvent
        
        Args:
            result: SDK RunResult
            task_id: 任务 ID
            
        Yields:
            AgentTaskEvent
        """
        sequence = start_sequence
        assistant_message_content = ""
        
        try:
            async for event in result.stream_events():
                # Trace SDK 事件
                if self.tracer:
                    self.tracer.log_sdk_event(
                        event_type=getattr(event, "type", "unknown"),
                        event_data={"raw_event": str(type(event).__name__)},
                    )
                
                # 转换 SDK 事件为 AgentTaskEvent
                agent_events = self._transform_sdk_event(
                    sdk_event=event,
                    task_id=task_id,
                    sequence=sequence,
                )
                
                for agent_event in agent_events:
                    sequence += 1
                    agent_event.sequence = sequence
                    
                    # Trace 业务事件
                    if self.tracer:
                        self.tracer.log_agent_event(
                            event_type=agent_event.event_type,
                            payload=agent_event.payload,
                            sequence=agent_event.sequence,
                        )
                    
                    yield agent_event
                    
                    # 累积消息内容
                    if agent_event.event_type == EventType.MESSAGE_UPDATED:
                        delta = agent_event.payload.get("delta", "")
                        assistant_message_content += delta
            
            # 最终输出
            final_output = getattr(result, "final_output", None) or assistant_message_content
            usage = self._extract_usage(result)
            
            # Trace LLM 响应
            if self.tracer:
                self.tracer.log_llm_response(
                    model=self.model,
                    response=final_output,
                )
            
            # 推送 message.completed
            sequence += 1
            completed_event = AgentTaskEvent(
                event_id=f"event_{task_id}_{sequence}",
                task_id=task_id,
                event_type=EventType.MESSAGE_COMPLETED,
                payload={
                    "role": "assistant",
                    "content": final_output,
                    "usage": usage,
                },
                sequence=sequence,
            )
            
            # Trace 业务事件
            if self.tracer:
                self.tracer.log_agent_event(
                    event_type=completed_event.event_type,
                    payload=completed_event.payload,
                    sequence=completed_event.sequence,
                )
            
            yield completed_event
            
        except Exception as e:
            logger.exception(f"SDK stream error: {e}")
            sequence += 1
            yield AgentTaskEvent(
                event_id=f"event_{task_id}_{sequence}",
                task_id=task_id,
                event_type=EventType.RUNTIME_ERROR,
                payload={
                    "code": AgentErrorCode.SDK_ERROR.value,
                    "message": f"SDK stream error: {str(e)}",
                },
                sequence=sequence,
            )
    
    def _extract_usage(self, result: RunResult) -> dict:
        """提取并转换 SDK token usage 为前端兼容格式"""
        context_wrapper = getattr(result, "context_wrapper", None)
        usage = getattr(context_wrapper, "usage", None)
        if not usage:
            return {}

        input_details = getattr(usage, "input_tokens_details", None)
        cache_read = getattr(input_details, "cached_tokens", 0) or 0
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        total_tokens = getattr(usage, "total_tokens", 0) or (input_tokens + output_tokens)

        return {
            "input": input_tokens,
            "output": output_tokens,
            "cacheRead": cache_read,
            "cacheWrite": 0,
            "totalTokens": total_tokens,
        }

    def _transform_sdk_event(
        self,
        sdk_event,
        task_id: str,
        sequence: int,
    ) -> list[AgentTaskEvent]:
        """
        转换 SDK 事件为 AgentTaskEvent
        
        Args:
            sdk_event: SDK 原始事件
            task_id: 任务 ID
            sequence: 序号
            
        Returns:
            AgentTaskEvent 列表（一个 SDK 事件可能产生多个业务事件）
        """
        events = []
        event_type_str = getattr(sdk_event, "type", "unknown")
        
        # 1. raw_response_event（LLM 原始事件）
        if event_type_str == "raw_response_event":
            data = getattr(sdk_event, "data", None)
            if data:
                data_type = getattr(data, "type", "")
                
                # ResponseTextDeltaEvent
                if data_type == "response.output_text.delta":
                    delta = getattr(data, "delta", "")
                    if delta:
                        events.append(AgentTaskEvent(
                            event_id=f"event_{task_id}_{sequence}",
                            task_id=task_id,
                            event_type=EventType.MESSAGE_UPDATED,
                            payload={"delta": delta},
                            sequence=sequence,
                        ))
        
        # 2. run_item_stream_event（工具调用、输出等）
        elif event_type_str == "run_item_stream_event":
            name = getattr(sdk_event, "name", "")
            item = getattr(sdk_event, "item", None)
            
            # tool_called
            if name == "tool_called":
                tool_name = getattr(item, "name", "unknown")
                arguments = getattr(item, "arguments", {})
                
                # Trace 工具调用
                if self.tracer:
                    self.tracer.log_tool_call(
                        tool_name=tool_name,
                        arguments=arguments,
                    )
                
                events.append(AgentTaskEvent(
                    event_id=f"event_{task_id}_{sequence}",
                    task_id=task_id,
                    event_type=EventType.TOOL_CALL_STARTED,
                    payload={
                        "tool_name": tool_name,
                        "arguments": arguments,
                    },
                    sequence=sequence,
                ))
            
            # tool_output
            elif name == "tool_output":
                tool_name = getattr(item, "name", "unknown")
                result = getattr(item, "content", None)
                
                # Trace 工具结果
                if self.tracer:
                    self.tracer.log_tool_call(
                        tool_name=tool_name,
                        arguments={},
                        result=result,
                    )
                
                events.append(AgentTaskEvent(
                    event_id=f"event_{task_id}_{sequence}",
                    task_id=task_id,
                    event_type=EventType.TOOL_CALL_COMPLETED,
                    payload={
                        "tool_name": tool_name,
                        "result": result,
                    },
                    sequence=sequence,
                ))
        
        # 3. agent_updated_stream_event（Agent 切换）
        elif event_type_str == "agent_updated_stream_event":
            new_agent = getattr(sdk_event, "new_agent", None)
            if new_agent:
                events.append(AgentTaskEvent(
                    event_id=f"event_{task_id}_{sequence}",
                    task_id=task_id,
                    event_type=EventType.HANDOFF,
                    payload={
                        "agent_name": getattr(new_agent, "name", "unknown"),
                    },
                    sequence=sequence,
                ))
        
        return events

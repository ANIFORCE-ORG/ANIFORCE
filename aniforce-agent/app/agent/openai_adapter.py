"""
OpenAI Agents SDK 适配器

遵循 Block 0 规范：
- 业务代码不直接依赖 SDK
- 封装 SDK 调用和事件转换
- 统一错误处理
"""

import json
import os
import re
from time import perf_counter
from typing import AsyncIterator, Optional
from pathlib import Path
from loguru import logger
from openai import AsyncOpenAI

from agents import (
    Agent,
    Runner,
    SQLiteSession,
    set_default_openai_api,
    set_default_openai_client,
    set_default_openai_key,
    set_tracing_disabled,
    RunConfig,  # 添加 RunConfig
)
from agents.run import RunResult
from agents.sandbox import SandboxAgent, Manifest, SandboxRunConfig
from agents.sandbox.capabilities import Capabilities, Skills, LocalDirLazySkillSource, Shell
from agents.sandbox.entries import LocalDir
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient
from agents.models.openai_responses import OpenAIResponsesModel  # 添加 Responses API
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

from app.models.agent_platform_models import AgentTaskEvent, EventType
from app.core.errors import AppError, AgentErrorCode, ErrorCategory
from app.core.tracing import get_tracer


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


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
        api_mode: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.enable_tracing = enable_tracing
        self.skills_dir = skills_dir or "runtime/skills"
        self.sandbox_dir = str(Path(sandbox_dir or "runtime/agent/sandbox").resolve())
        self.tracer = get_tracer() if enable_tracing else None
        self._tool_name_by_call_id: dict[str, str] = {}
        
        # 创建沙箱目录
        Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)
        
        self.api_mode = (api_mode or os.environ.get("OPENAI_AGENTS_API") or "responses").strip().lower()
        if self.api_mode in {"chat", "chat_completions", "chat-completions"}:
            self.api_mode = "chat_completions"
        else:
            self.api_mode = "responses"

        set_default_openai_api(self.api_mode)
        # 项目使用本地 JSONL tracing，禁用 OpenAI 官方 trace export。
        set_tracing_disabled(True)
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            set_default_openai_key(api_key, use_for_tracing=False)
        else:
            # fallback：从环境变量读，避免 AsyncOpenAI 报 Missing credentials
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY missing: set it in .env or env var")
        if base_url:
            os.environ["OPENAI_BASE_URL"] = base_url

        self.openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        set_default_openai_client(self.openai_client, use_for_tracing=False)
        
        logger.info(f"OpenAI SDK Adapter initialized: {model} | api={self.api_mode} | tracing={enable_tracing}")
    
    def _generate_skills_index(self) -> str:
        """生成 Skills 索引（用于注入到 System Prompt）"""
        skills_path = Path(self.skills_dir)
        if not skills_path.exists():
            return ""
        
        skills_list = []
        for skill_dir in skills_path.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            
            try:
                content = skill_md.read_text(encoding='utf-8')
                # 解析 frontmatter
                lines = content.split('\n')
                if lines[0].strip() == '---':
                    name = ""
                    description = ""
                    for line in lines[1:]:
                        if line.strip() == '---':
                            break
                        if line.startswith('name:'):
                            name = line.split(':', 1)[1].strip().strip('"')
                        if line.startswith('description:'):
                            description = line.split(':', 1)[1].strip().strip('"')
                    
                    if name and description:
                        skills_list.append(f"- **{name}**: {description}")
                        logger.debug(f"[SDK] Found skill: {name}")
            except Exception as e:
                logger.warning(f"[SDK] Failed to parse skill {skill_dir.name}: {e}")
        
        if not skills_list:
            return ""
        
        index = "以下是可用的专业知识库（Skills），当用户需求涉及相关领域时，请参考对应 Skill 的工作流程：\n\n"
        index += "\n".join(skills_list)
        index += "\n\n**使用方式**: 当用户提及上述领域时，请在回复中引用对应 Skill 的最佳实践。"
        
        return index
    
    def _sandbox_workspace_for_session(self, session_id: Optional[str]) -> str:
        """返回 session 级 sandbox workspace 路径。"""
        safe_session_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", session_id or "anonymous")
        workspace_dir = Path(self.sandbox_dir) / safe_session_id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return str(workspace_dir)

    def create_agent(
        self,
        name: str,
        instructions: str,
        mcp_servers: list = None,
        enable_skills: bool = True,
        session_id: Optional[str] = None,
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
        
        if self.api_mode == "chat_completions":
            sdk_model = OpenAIChatCompletionsModel(
                model=self.model,
                openai_client=self.openai_client,
            )
        else:
            sdk_model = OpenAIResponsesModel(
                model=self.model,
                openai_client=self.openai_client,
            )
        
        if has_skills:
            # 使用 SandboxAgent（支持 Skills + Sandbox 工具）
            # 显式使用 session 级 workspace，保证隔离、可观察、可清理、可 resume。
            workspace_dir = self._sandbox_workspace_for_session(session_id)
            skills_capability = Skills(
                lazy_from=LocalDirLazySkillSource(
                    source=LocalDir(src=self.skills_dir)
                )
            )
            if self.api_mode == "chat_completions":
                capabilities = [Shell(), skills_capability]
                capability_label = "ChatCompletions-compatible Shell + Skills"
            else:
                capabilities = Capabilities.default() + [skills_capability]
                capability_label = "Responses default capabilities + Skills"

            agent = SandboxAgent(
                name=name,
                instructions=instructions,
                model=sdk_model,
                mcp_servers=mcp_servers or [],
                default_manifest=Manifest(root=workspace_dir),
                capabilities=capabilities,
            )
            logger.info(f"[SDK] Created SandboxAgent with {self.api_mode} + {capability_label}: {self.skills_dir}")
            logger.info(f"[SDK] Sandbox workspace: {workspace_dir}")
        else:
            # 使用普通 Agent（向后兼容）
            agent = Agent(
                name=name,
                instructions=instructions,
                model=sdk_model,
                mcp_servers=mcp_servers or [],
            )
            logger.info(f"[SDK] Created Agent with {self.api_mode} (skills disabled)")
        
        logger.debug(f"[SDK] Agent '{name}' with {len(mcp_servers or [])} MCP servers")
        return agent
    
    def create_session(self, session_id: str, db_path: str = "runtime/agent/sessions.db") -> SQLiteSession:
        """
        创建 SDK Session（用于管理对话历史）
        
        Args:
            session_id: Session ID
            db_path: SQLite 数据库路径
        """
        sdk_session_id = session_id
        if self.api_mode == "chat_completions":
            sdk_session_id = f"chat_completions:{session_id}"
        return SQLiteSession(sdk_session_id, db_path=db_path)
    
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
                # SandboxAgent 需要 RunConfig(sandbox=SandboxRunConfig(client=...))
                config = RunConfig(
                    sandbox=SandboxRunConfig(
                        client=UnixLocalSandboxClient()
                    )
                )
                result = Runner.run_streamed(
                    agent,
                    input=input_text,
                    session=session,
                    run_config=config,
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
        stream_start = perf_counter()
        first_raw_logged = False
        first_transformed_logged = False
        first_thinking_delta_logged = False
        first_text_delta_logged = False
        raw_event_count = 0
        transformed_event_count = 0
        pre_delta_raw_counts: dict[str, int] = {}
        
        try:
            async for event in result.stream_events():
                raw_event_count += 1
                raw_summary = self._describe_stream_event(event)
                if not first_text_delta_logged:
                    raw_key = raw_summary.get("key", raw_summary.get("raw_type", "unknown"))
                    pre_delta_raw_counts[raw_key] = pre_delta_raw_counts.get(raw_key, 0) + 1
                    # 特别记录 reasoning 文本内容
                    if raw_summary.get("data_type") == "response.reasoning_text.delta":
                        data = getattr(event, "data", None)
                        delta_text = getattr(data, "delta", "") if data else ""
                        logger.info(
                            "[PERF][agent_first_token] sdk.reasoning_delta raw_index={} delta_text={!r}",
                            raw_event_count,
                            delta_text,
                        )
                    logger.info(
                        "[PERF][agent_first_token] sdk.raw_before_delta elapsed_ms={} raw_index={} raw_type={} data_type={} item_name={} item_type={} delta_chars={} response_status={} output_index={} item_id={}",
                        _elapsed_ms(stream_start),
                        raw_event_count,
                        raw_summary.get("raw_type"),
                        raw_summary.get("data_type"),
                        raw_summary.get("item_name"),
                        raw_summary.get("item_type"),
                        raw_summary.get("delta_chars"),
                        raw_summary.get("response_status"),
                        raw_summary.get("output_index"),
                        raw_summary.get("item_id"),
                    )
                if not first_raw_logged:
                    first_raw_logged = True
                    logger.info(
                        "[PERF][agent_first_token] sdk.first_raw_event elapsed_ms={} raw_type={}",
                        _elapsed_ms(stream_start),
                        getattr(event, "type", "unknown"),
                    )
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
                    transformed_event_count += 1
                    if not first_transformed_logged:
                        first_transformed_logged = True
                        logger.info(
                            "[PERF][agent_first_token] sdk.first_transformed_event elapsed_ms={} raw_events={} event_type={}",
                            _elapsed_ms(stream_start),
                            raw_event_count,
                            agent_event.event_type,
                        )
                    if not first_thinking_delta_logged and agent_event.event_type == EventType.THINKING_UPDATED:
                        first_thinking_delta_logged = True
                        logger.info(
                            "[PERF][agent_first_token] sdk.first_thinking_delta elapsed_ms={} raw_events={} transformed_events={} pre_delta_raw_counts={}",
                            _elapsed_ms(stream_start),
                            raw_event_count,
                            transformed_event_count,
                            pre_delta_raw_counts,
                        )
                    if not first_text_delta_logged and agent_event.event_type == EventType.MESSAGE_UPDATED:
                        first_text_delta_logged = True
                        logger.info(
                            "[PERF][agent_first_token] sdk.first_text_delta elapsed_ms={} raw_events={} transformed_events={} pre_delta_raw_counts={}",
                            _elapsed_ms(stream_start),
                            raw_event_count,
                            transformed_event_count,
                            pre_delta_raw_counts,
                        )
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
            logger.info(
                "[PERF][agent_first_token] sdk.stream_done elapsed_ms={} raw_events={} transformed_events={} usage={}",
                _elapsed_ms(stream_start),
                raw_event_count,
                transformed_event_count,
                usage,
            )
            
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
    
    def _describe_stream_event(self, sdk_event) -> dict:
        """Return compact metadata for one SDK stream event without logging payload content."""
        raw_type = getattr(sdk_event, "type", "unknown")
        summary = {"raw_type": raw_type, "key": raw_type}

        data = getattr(sdk_event, "data", None)
        if data is not None:
            data_type = getattr(data, "type", None)
            summary["data_type"] = data_type
            if data_type:
                summary["key"] = f"{raw_type}:{data_type}"
            delta = getattr(data, "delta", None)
            if isinstance(delta, str):
                summary["delta_chars"] = len(delta)
            summary["response_status"] = getattr(data, "status", None)
            summary["output_index"] = getattr(data, "output_index", None)
            summary["item_id"] = getattr(data, "item_id", None) or getattr(data, "id", None)

        item = getattr(sdk_event, "item", None)
        if item is not None:
            summary["item_name"] = getattr(sdk_event, "name", None)
            summary["item_type"] = getattr(item, "type", None)
            summary["item_id"] = getattr(item, "id", None) or summary.get("item_id")
            if summary.get("item_name"):
                summary["key"] = f"{raw_type}:{summary['item_name']}"

        new_agent = getattr(sdk_event, "new_agent", None)
        if new_agent is not None:
            summary["item_name"] = getattr(new_agent, "name", None)
            summary["key"] = f"{raw_type}:agent_updated"

        return summary

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
                
                # Reasoning/Thinking Delta Event
                elif data_type == "response.reasoning_text.delta":
                    delta = getattr(data, "delta", "")
                    if delta:
                        events.append(AgentTaskEvent(
                            event_id=f"event_{task_id}_{sequence}",
                            task_id=task_id,
                            event_type=EventType.THINKING_UPDATED,
                            payload={"delta": delta},
                            sequence=sequence,
                        ))
        
        # 2. run_item_stream_event（工具调用、输出等）
        elif event_type_str == "run_item_stream_event":
            name = getattr(sdk_event, "name", "")
            item = getattr(sdk_event, "item", None)
            
            # tool_called
            if name == "tool_called":
                tool_info = self._extract_tool_call_info(item)
                if not tool_info:
                    logger.debug(f"[SDK] ignored non-tool tool_called item: {type(item).__name__}")
                    return events
                tool_name = tool_info["tool_name"]
                arguments = tool_info["arguments"]
                tool_call_id = tool_info.get("tool_call_id")
                
                logger.debug(
                    f"[SDK] tool_called event: item_type={type(item).__name__} | "
                    f"run_item_type={getattr(item, 'type', None)} | "
                    f"tool_name={tool_name} | tool_call_id={tool_call_id}"
                )
                
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
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "arguments": arguments,
                    },
                    sequence=sequence,
                ))
            
            # tool_output
            elif name == "tool_output":
                output_info = self._extract_tool_output_info(item)
                if not output_info:
                    logger.debug(f"[SDK] ignored non-tool tool_output item: {type(item).__name__}")
                    return events
                tool_name = output_info["tool_name"]
                result = output_info.get("result")
                tool_call_id = output_info.get("tool_call_id")
                
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
                        "tool_call_id": tool_call_id,
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

    def _extract_tool_call_info(self, item) -> Optional[dict]:
        """Extract tool call metadata from SDK RunItem wrappers."""
        if not item or getattr(item, "type", None) != "tool_call_item":
            return None

        raw_item = getattr(item, "raw_item", item)
        tool_name = getattr(item, "tool_name", None) or self._read_field(raw_item, "name")
        if not tool_name:
            return None

        arguments = self._read_field(raw_item, "arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except Exception:
                arguments = {"raw": arguments}
        elif arguments is None:
            arguments = {}

        tool_call_id = getattr(item, "call_id", None) or self._read_field(raw_item, "call_id") or self._read_field(raw_item, "id")
        if tool_call_id:
            self._tool_name_by_call_id[str(tool_call_id)] = str(tool_name)

        return {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "arguments": arguments,
        }

    def _extract_tool_output_info(self, item) -> Optional[dict]:
        """Extract tool output metadata from SDK RunItem wrappers."""
        if not item or getattr(item, "type", None) != "tool_call_output_item":
            return None

        raw_item = getattr(item, "raw_item", item)
        tool_call_id = getattr(item, "call_id", None) or self._read_field(raw_item, "call_id") or self._read_field(raw_item, "id")
        result = getattr(item, "output", None)
        if result is None:
            result = self._read_field(raw_item, "output") or self._read_field(raw_item, "content")

        return {
            "tool_call_id": tool_call_id,
            "tool_name": self._tool_name_by_call_id.get(str(tool_call_id), "unknown") if tool_call_id else "unknown",
            "result": self._normalize_tool_result(result),
        }

    def _read_field(self, value, field: str, default=None):
        if isinstance(value, dict):
            return value.get(field, default)
        return getattr(value, field, default)

    def _normalize_tool_result(self, result):
        if isinstance(result, list):
            texts = []
            for entry in result:
                text = self._read_field(entry, "text")
                if text is not None:
                    texts.append(str(text))
            if texts:
                return "\n".join(texts)
        return result

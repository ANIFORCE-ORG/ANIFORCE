"""
本地化 Agent Tracing 系统

不使用 OpenAI 官方 tracing，完全本地化：
- 记录所有 SDK 调用
- 记录事件流
- 记录 LLM 请求和响应
- 输出到日志和本地文件

遵循 Block 0 规范：
- 敏感数据脱敏
- 结构化日志
"""

import json
import time
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from contextlib import contextmanager
from loguru import logger


class LocalTracer:
    """本地 Tracing 系统"""
    
    def __init__(self, trace_dir: str = "runtime/agent/traces"):
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._current_trace_id: Optional[str] = None
        self._current_trace_file: Optional[Path] = None
        self._trace_data: list = []
        
        logger.info(f"LocalTracer initialized: {self.trace_dir}")
    
    @contextmanager
    def trace_task(self, task_id: str, user_id: str, task_type: str):
        """
        Trace 一个完整的 Task 执行
        
        用法：
            with tracer.trace_task(task_id, user_id, task_type):
                # 执行任务
        """
        trace_id = f"{task_id}_{int(time.time() * 1000)}"
        self._current_trace_id = trace_id
        self._trace_data = []
        
        # Trace 文件路径
        date_dir = datetime.now().strftime("%Y%m%d")
        trace_file = self.trace_dir / date_dir / f"{trace_id}.jsonl"
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        self._current_trace_file = trace_file
        
        # 记录开始
        start_time = time.time()
        self._log_event({
            "event": "trace.start",
            "trace_id": trace_id,
            "task_id": task_id,
            "user_id": user_id,
            "task_type": task_type,
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.bind(trace_id=trace_id, task_id=task_id).info(
            f"[TRACE] Task started: {task_type}"
        )
        
        try:
            yield trace_id
        except Exception as e:
            # 记录异常
            self._log_event({
                "event": "trace.error",
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat(),
            })
            raise
        finally:
            # 记录结束
            duration = time.time() - start_time
            self._log_event({
                "event": "trace.end",
                "duration_ms": int(duration * 1000),
                "timestamp": datetime.now().isoformat(),
            })
            
            logger.bind(trace_id=trace_id, task_id=task_id).info(
                f"[TRACE] Task completed in {duration:.2f}s"
            )
            
            # 重置
            self._current_trace_id = None
            self._current_trace_file = None
            self._trace_data = []
    
    def log_sdk_call(
        self,
        method: str,
        agent_name: str,
        input_text: str,
        session_id: Optional[str] = None,
    ):
        """记录 SDK 调用"""
        self._log_event({
            "event": "sdk.call",
            "method": method,
            "agent_name": agent_name,
            "input_text": self._sanitize(input_text, max_len=200),
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.bind(trace_id=self._current_trace_id).debug(
            f"[TRACE] SDK call: {method} | agent={agent_name} | session={session_id}"
        )
    
    def log_sdk_event(
        self,
        event_type: str,
        event_data: dict,
    ):
        """记录 SDK 事件"""
        self._log_event({
            "event": "sdk.event",
            "event_type": event_type,
            "data": self._sanitize_dict(event_data),
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.bind(trace_id=self._current_trace_id).debug(
            f"[TRACE] SDK event: {event_type}"
        )
    
    def log_llm_request(
        self,
        model: str,
        messages: list,
        metadata: Optional[dict] = None,
    ):
        """记录 LLM 请求"""
        self._log_event({
            "event": "llm.request",
            "model": model,
            "messages": self._sanitize_messages(messages),
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.bind(trace_id=self._current_trace_id).info(
            f"[TRACE] LLM request: {model} | messages={len(messages)}"
        )
    
    def log_llm_response(
        self,
        model: str,
        response: str,
        usage: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ):
        """记录 LLM 响应"""
        self._log_event({
            "event": "llm.response",
            "model": model,
            "response": self._sanitize(response, max_len=500),
            "usage": usage or {},
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.bind(trace_id=self._current_trace_id).info(
            f"[TRACE] LLM response: {model} | response_len={len(response)}"
        )
    
    def log_agent_event(
        self,
        event_type: str,
        payload: dict,
        sequence: int,
    ):
        """记录业务事件"""
        self._log_event({
            "event": "agent.event",
            "event_type": event_type,
            "payload": self._sanitize_dict(payload),
            "sequence": sequence,
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.bind(trace_id=self._current_trace_id).debug(
            f"[TRACE] Agent event[{sequence}]: {event_type}"
        )
    
    def log_tool_call(
        self,
        tool_name: str,
        arguments: dict,
        result: Any = None,
        error: Optional[str] = None,
    ):
        """记录工具调用"""
        self._log_event({
            "event": "tool.call",
            "tool_name": tool_name,
            "arguments": self._sanitize_dict(arguments),
            "result": self._sanitize(str(result), max_len=500) if result else None,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })
        
        status = "error" if error else "success"
        logger.bind(trace_id=self._current_trace_id).info(
            f"[TRACE] Tool call: {tool_name} | status={status}"
        )
    
    def _log_event(self, event: dict):
        """写入事件到 trace 文件"""
        if not self._current_trace_file:
            return
        
        # 添加 trace_id
        event["trace_id"] = self._current_trace_id
        
        # 写入 JSONL
        with open(self._current_trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        
        # 缓存到内存
        self._trace_data.append(event)
    
    def _sanitize(self, text: str, max_len: int = 200) -> str:
        """脱敏和截断文本"""
        if not text:
            return ""
        
        # 截断
        if len(text) > max_len:
            return text[:max_len] + "..."
        
        return text
    
    def _sanitize_dict(self, data: dict) -> dict:
        """脱敏字典"""
        if not data:
            return {}
        
        sanitized = {}
        for key, value in data.items():
            # 敏感字段脱敏
            if key.lower() in {"api_key", "token", "secret", "password"}:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, str):
                sanitized[key] = self._sanitize(value, max_len=500)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_dict(v) if isinstance(v, dict) else v for v in value[:10]]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_messages(self, messages: list) -> list:
        """脱敏消息列表"""
        if not messages:
            return []
        
        return [
            {
                "role": msg.get("role", "unknown"),
                "content": self._sanitize(msg.get("content", ""), max_len=500),
            }
            for msg in messages[:10]  # 最多记录 10 条
        ]


# 全局 tracer 实例
_tracer: Optional[LocalTracer] = None


def get_tracer() -> LocalTracer:
    """获取全局 tracer 实例"""
    global _tracer
    if _tracer is None:
        _tracer = LocalTracer()
    return _tracer

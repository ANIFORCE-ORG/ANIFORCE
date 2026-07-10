"""Runtime session history API.

从 agent.db SQLAlchemySession 读取 SDK 原生对话历史，
转换成前端可消费的 blocks 格式。

这是 session 历史的唯一事实源，backend 不再双写 agent_messages。
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.agent.runtime import AgentRuntime
from app.agent.runtime_sessions import RuntimeSessionNotRegistered, RuntimeSessionOwnerMismatch
from app.auth import get_current_user
from app.core.errors import unexpected_error_payload

router = APIRouter(prefix="/runtime/sessions", tags=["runtime-sessions"])


def get_runtime() -> AgentRuntime:
    from app.main import _runtime
    return _runtime


@router.get("/{session_id}/history")
async def get_session_history(
    session_id: str,
    user: dict = Depends(get_current_user),
    runtime: AgentRuntime = Depends(get_runtime),
):
    """读取 SDK session 历史并转成 blocks 格式。"""
    try:
        items = await runtime.get_session_history(session_id, user["id"])
        messages = _items_to_messages(items)
        return {"session_id": session_id, "messages": messages}
    except RuntimeSessionOwnerMismatch as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "SESSION_FORBIDDEN", "message": "Session does not belong to current user"},
        ) from exc
    except RuntimeSessionNotRegistered as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "SESSION_NOT_FOUND", "message": "Runtime session not found"},
        ) from exc
    except Exception as exc:
        logger.exception("runtime session history failed: session_id={} user_id={}", session_id, user["id"])
        payload = unexpected_error_payload(message="Session history is temporarily unavailable")
        payload["code"] = "HISTORY_ERROR"
        raise HTTPException(status_code=500, detail=payload) from exc


def _items_to_messages(items: list[dict]) -> list[dict]:
    """把 SQLAlchemySession 的 SDK items 转成前端 blocks 格式。

    SDK item 格式（ChatCompletions 模式）：
      - user: {"content": "hi", "role": "user"}
      - assistant text: {"content": [{"text": "...", "type": "output_text"}], "role": "assistant", ...}
      - reasoning: {"summary": [{"text": "...", "type": "summary_text"}], "type": "reasoning"}
      - tool_call: {"id": "call_xxx", "function": {"arguments": "...", "name": "..."}, "type": "function"}
      - tool_result: {"content": "...", "role": "tool", "tool_call_id": "call_xxx"}
    """
    messages: list[dict] = []
    current_assistant: dict | None = None
    tool_calls: dict[str, dict] = {}

    def flush_assistant():
        nonlocal current_assistant
        if current_assistant and current_assistant.get("content_json", {}).get("blocks"):
            messages.append(current_assistant)
        current_assistant = None

    for item in items:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        item_type = item.get("type")

        # user 消息
        if role == "user":
            flush_assistant()
            content = item.get("content", "")
            if isinstance(content, list):
                # ChatCompletions 偶尔会包成 [{"text": "...", "type": "text"}]
                content = " ".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
            messages.append({
                "role": "user",
                "content_json": {"blocks": [{"type": "text", "content": str(content), "text": str(content)}]},
            })

        # assistant 消息
        elif role == "assistant":
            # 累积到当前 assistant（reasoning 可能先于 assistant text 到达）
            if current_assistant is None:
                current_assistant = {"role": "assistant", "content_json": {"blocks": []}}
            blocks = current_assistant["content_json"]["blocks"]
            content = item.get("content")
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    ptype = part.get("type")
                    if ptype in ("output_text", "text"):
                        text = str(part.get("text", ""))
                        blocks.append({"type": "text", "content": text, "text": text})
            # tool_calls 在 assistant item 上
            tool_calls_list = item.get("tool_calls") or []
            for tc in tool_calls_list:
                if not isinstance(tc, dict):
                    continue
                tc_id = tc.get("id", "")
                fn = tc.get("function", {}) if isinstance(tc.get("function"), dict) else {}
                tool_name = fn.get("name", "tool")
                args_raw = fn.get("arguments", "{}")
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                except Exception:
                    args = {"raw": args_raw}
                block = {
                    "type": "tool_call",
                    "toolCallId": tc_id,
                    "tool": tool_name,
                    "args": args,
                    "status": "completed",
                }
                blocks.append(block)
                tool_calls[tc_id] = block

        # reasoning（独立 item，合并到当前 assistant）
        elif item_type == "reasoning":
            if current_assistant is None:
                current_assistant = {"role": "assistant", "content_json": {"blocks": []}}
            summary = item.get("summary") or []
            texts = []
            for entry in summary:
                if isinstance(entry, dict):
                    t = entry.get("text")
                    if t:
                        texts.append(str(t))
            thinking_text = "\n\n".join(texts).strip()
            if thinking_text:
                thinking_block = {
                    "type": "thinking",
                    "summary": thinking_text[:120] + ("..." if len(thinking_text) > 120 else ""),
                    "collapsed": True,
                    "content": thinking_text,
                    "thinking": thinking_text,
                }
                # 只在没有 thinking block 时 insert，避免多轮 reasoning 重复
                if not any(b.get("type") == "thinking" for b in current_assistant["content_json"]["blocks"]):
                    current_assistant["content_json"]["blocks"].insert(0, thinking_block)
                else:
                    # 已有 thinking，追加到现有 thinking 后面
                    for b in current_assistant["content_json"]["blocks"]:
                        if b.get("type") == "thinking":
                            b["content"] = (b.get("content", "") + "\n\n" + thinking_text).strip()
                            b["thinking"] = b["content"]
                            b["summary"] = b["content"][:120] + ("..." if len(b["content"]) > 120 else "")
                            break

        # tool 结果（旧格式 role=tool）
        elif role == "tool":
            tc_id = item.get("tool_call_id", "")
            result_content = item.get("content", "")
            block = tool_calls.get(tc_id)
            if block:
                block["result"] = result_content

        # function_call（SDK ChatCompletions 独立 item）
        elif item_type == "function_call":
            if current_assistant is None:
                current_assistant = {"role": "assistant", "content_json": {"blocks": []}}
            blocks = current_assistant["content_json"]["blocks"]
            tc_id = item.get("call_id", "")
            tool_name = item.get("name", "tool")
            args_raw = item.get("arguments", "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except Exception:
                args = {"raw": args_raw}
            block = {
                "type": "tool_call",
                "toolCallId": tc_id,
                "tool": tool_name,
                "args": args,
                "status": "running",
            }
            blocks.append(block)
            tool_calls[tc_id] = block

        # function_call_output（SDK ChatCompletions 独立 item）
        elif item_type == "function_call_output":
            tc_id = item.get("call_id", "")
            output = item.get("output", "")
            block = tool_calls.get(tc_id)
            if block:
                block["status"] = "completed"
                block["result"] = output

    flush_assistant()
    return messages

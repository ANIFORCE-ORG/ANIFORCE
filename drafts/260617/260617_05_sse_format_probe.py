"""单点看 SSE 实际响应格式"""
import os, sys, json, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "aniforce-agent"))
import httpx
from app.core.auth import create_access_token

token = create_access_token({"sub": "probe_user", "email": "p@e.com", "name": "Probe"})
thread_id = str(uuid.uuid4())
print(f"threadId: {thread_id}")
print("=== SSE 原始响应 ===")

with httpx.stream("POST",
    "http://localhost:8020/api/agent/copilotkit/agent/default/run",
    json={"messages": [{"role": "user", "content": "你好，回复收到"}], "threadId": thread_id},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    timeout=60,
) as r:
    print(f"status: {r.status_code}")
    n = 0
    for line in r.iter_lines():
        if line:
            n += 1
            print(f"[{n}] {line!r}")
            if n > 200:
                print("... (截断)")
                break

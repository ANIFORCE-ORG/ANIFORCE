"""验证工具调用场景的 AG-UI 事件（ActionExecution*）"""
import os, sys, json, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "aniforce-agent"))
import httpx
from app.core.auth import create_access_token

token = create_access_token({"sub": "probe_user", "email": "p@e.com", "name": "Probe"})
thread_id = str(uuid.uuid4())
print(f"threadId: {thread_id}")
# 用一个需要工具的 prompt（Read 当前目录文件）
print("=== 工具调用场景 SSE ===")

with httpx.stream("POST",
    "http://localhost:8020/api/agent/copilotkit/agent/default/run",
    json={"messages": [{"role": "user", "content": "请读取当前目录下的 README.md 文件并一句话总结"}], "threadId": thread_id},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    timeout=120,
) as r:
    print(f"status: {r.status_code}")
    n = 0
    text_total = ""
    for line in r.iter_lines():
        if line:
            n += 1
            print(f"[{n}] {line!r}")
            # 提取文本内容汇总
            if line.startswith("data: "):
                try:
                    d = json.loads(line[6:])
                    if d.get("content"):
                        text_total += d["content"]
                except Exception:
                    pass
            if n > 200:
                print("... (截断)")
                break
    print(f"\n=== 文本汇总 ===\n{text_total}")

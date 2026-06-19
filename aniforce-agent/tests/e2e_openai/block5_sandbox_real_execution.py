#!/usr/bin/env python3
"""
Block 5 重测：验证 Agent 的真实执行能力

测试：
1. Agent 能否在 sandbox 里写文件
2. Agent 能否执行 shell 命令
3. 文件是否真的存在
4. SSE 事件流是否有 tool_called
"""

import json
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.auth import create_access_token


BASE_URL = "http://localhost:8020"
SANDBOX_DIR = Path(__file__).parent.parent.parent / "runtime/agent/sandbox"


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def print_result(passed: bool, message: str) -> bool:
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


def send_agent_run_sync(prompt: str, session_id: str, token: str, timeout: int = 120):
    """同步运行 agent，收集所有 SSE 事件和 tool_calls"""
    url = f"{BASE_URL}/api/agent/runs"
    payload = {"prompt": prompt, "session_id": session_id, "task_type": "conversation"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    events = []
    tool_calls = []
    current_event = None
    text_content = ""

    with httpx.stream("POST", url, json=payload, headers=headers, timeout=timeout) as response:
        print(f"状态码: {response.status_code}")
        if response.status_code != 200:
            return None, [], []

        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    data = {}
                events.append({"event": current_event, "data": data})

                if current_event == "message.updated":
                    text_content += data.get("delta", "")
                elif current_event == "message.completed":
                    text_content = data.get("content", text_content)
                elif current_event == "tool_call.started":
                    tool_calls.append({
                        "tool_name": data.get("tool_name"),
                        "arguments": data.get("arguments"),
                    })

    return text_content, events, tool_calls


def session_workspace(session_id: str) -> Path:
    """返回 session 级 sandbox 目录。"""
    return SANDBOX_DIR / session_id


def check_file_exists(session_id: str, filename: str) -> bool:
    """检查文件是否存在于当前 session 的 sandbox 目录"""
    p = session_workspace(session_id) / filename
    if p.exists():
        print(f"找到文件: {p}")
        return True
    print(f"未找到文件: {p}")
    return False


def check_sandbox_has_session_dirs() -> list[Path]:
    """检查 sandbox 目录下是否有 session 相关子目录"""
    dirs = [p for p in SANDBOX_DIR.iterdir() if p.is_dir() and p.name != ".agents"]
    print(f"sandbox 子目录: {[d.name for d in dirs]}")
    return dirs


def test_block_5_real_execution() -> bool:
    print_section("Block 5: Agent 真实执行能力验证")

    user_id = f"user_block5_real_{int(time.time())}"
    token = create_access_token({"sub": user_id, "email": f"{user_id}@example.com", "name": "Block5"})
    session_id = f"session_block5_real_{uuid.uuid4().hex[:12]}"
    results = []

    print_section("Step 5.1: 检查 sandbox 目录结构")
    print(f"SANDBOX_DIR: {SANDBOX_DIR}")
    dirs = check_sandbox_has_session_dirs()
    results.append(print_result(SANDBOX_DIR.exists(), "sandbox 目录存在"))

    print_section("Step 5.2: 让 Agent 创建文件")
    prompt_create = (
        "请在 sandbox 工作目录里创建一个名为 'block5_test_hello.txt' 的文件，"
        "内容写上 'Hello from Block5 sandbox test!'。"
        "使用 filesystem 工具或 shell 命令来完成。"
    )
    print(f"提示词: {prompt_create}")

    text1, events1, tools1 = send_agent_run_sync(prompt_create, session_id, token, timeout=120)
    print(f"Agent 回复: {text1[:200]}")
    print(f"事件数: {len(events1)}")
    print(f"工具调用: {tools1}")

    tool_names1 = [t["tool_name"] for t in tools1 if t.get("tool_name")]
    print(f"调用的工具名: {tool_names1}")

    # Sandbox 工具包括：apply_patch（Filesystem）、exec_command（Shell）
    has_sandbox_tool = any(
        name in ["apply_patch", "exec_command", "read_file", "write_file", "list_directory"]
        for name in tool_names1
    )

    results.append(print_result(has_sandbox_tool, "Agent 调用了 sandbox 工具（apply_patch/exec_command）"))

    print_section("Step 5.3: 检查文件是否真的存在")
    file_exists = check_file_exists(session_id, "block5_test_hello.txt")
    results.append(print_result(file_exists, "文件真实存在于当前 session sandbox"))
    if file_exists:
        p = session_workspace(session_id) / "block5_test_hello.txt"
        content = p.read_text()
        print(f"文件内容: {content}")
        results.append(print_result("Hello" in content or "Block5" in content, "文件内容正确"))
    else:
        results.append(print_result(False, "文件真实存在于 sandbox"))

    print_section("Step 5.4: 让 Agent 执行命令查看文件")
    prompt_cmd = "请执行命令 'ls -la' 或 'cat block5_test_hello.txt'，告诉我你看到了什么。"
    print(f"提示词: {prompt_cmd}")

    text2, events2, tools2 = send_agent_run_sync(prompt_cmd, session_id, token, timeout=120)
    print(f"Agent 回复: {text2[:300]}")

    tool_names2 = [t["tool_name"] for t in tools2 if t.get("tool_name")]
    has_sandbox_tool2 = any(name in ["apply_patch", "exec_command", "read_file", "cat", "ls"] for name in tool_names2)
    results.append(print_result(has_sandbox_tool2, "Agent 调用了 sandbox 工具执行命令"))

    # Agent 回复里应该提到看到了文件或内容
    saw_file = "block5_test_hello" in text2 or "Hello" in text2 or "ls" in text2.lower()
    results.append(print_result(saw_file, "Agent 在命令输出里看到了文件"))

    print_section("Step 5.5: Session 隔离验证")
    # 用另一个 session，看是否能看到上一个 session 的文件
    session_id2 = f"session_block5_isolation_{uuid.uuid4().hex[:12]}"
    prompt_isolation = "请执行 'ls -la' 命令，列出当前目录的文件。"
    text3, events3, tools3 = send_agent_run_sync(prompt_isolation, session_id2, token, timeout=60)
    print(f"Session 2 回复: {text3[:200]}")

    sees_other_file = "block5_test_hello" in text3
    print(f"Session 1 workspace: {session_workspace(session_id)}")
    print(f"Session 2 workspace: {session_workspace(session_id2)}")
    print(f"Session 2 看到 Session 1 的文件: {sees_other_file}")

    results.append(print_result(session_workspace(session_id).exists(), "Session 1 sandbox 目录存在"))
    results.append(print_result(session_workspace(session_id2).exists(), "Session 2 sandbox 目录存在"))
    results.append(print_result(session_workspace(session_id) != session_workspace(session_id2), "不同 session 使用不同 sandbox 目录"))
    results.append(print_result(not sees_other_file, "Session 隔离生效"))

    print_section("Block 5 汇总")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")

    print("\n" + "=" * 70)
    print("📊 分析结果:")
    print("=" * 70)
    if has_sandbox_tool:
        print("✅ Agent 已启用执行能力（apply_patch/exec_command 等 sandbox 工具）")
    else:
        print("❌ Agent 未调用 sandbox 工具，可能：")
        print("   1. 模型没有选择使用工具")
        print("   2. sandbox 配置有问题")
        print("   3. 工具没有正确暴露给 Agent")

    if file_exists:
        print("✅ 文件真实存在于 sandbox，执行能力生效")
    else:
        print("❌ 文件不存在，Agent 可能只是口头答应，没有真的执行")

    if sees_other_file:
        print("❌ Session 未隔离：不同 session 可以看到彼此的文件")
        print("   原因：UnixLocalSandboxClient 使用自定义 manifest.root")
        print("   修复：不传 manifest.root，让 SDK 用 tempfile.mkdtemp() 创建独立目录")
    else:
        print("✅ Session 已隔离")

    return passed == total


if __name__ == "__main__":
    success = test_block_5_real_execution()
    sys.exit(0 if success else 1)
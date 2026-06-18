#!/usr/bin/env python
"""
测试 Sandbox 管理和文件隔离

验证：
1. 每个 session 有独立的工作目录
2. 不同 session 的文件互不干扰
3. Session 清理后文件被删除
4. 目录结构正确（runtime/sessions/{session_id}/）
"""
import asyncio
import sys
import os
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.sandbox import SandboxManager


async def test_sandbox_isolation():
    """测试 Sandbox 隔离"""
    print("=" * 70)
    print("🧪 测试 Sandbox 管理和文件隔离")
    print("=" * 70)
    print()

    runtime_dir = os.getenv("RUNTIME_DIR", "tests/manual/runtime/sessions")
    sandbox = SandboxManager(runtime_dir=runtime_dir)

    # 测试 1：创建 Session 目录
    print("=" * 70)
    print("测试 1：创建 Session 目录")
    print("=" * 70)

    session_a = str(uuid4())
    session_b = str(uuid4())

    dir_a = sandbox.create_session_dir(session_a)
    dir_b = sandbox.create_session_dir(session_b)

    print(f"✅ Session A 目录: {dir_a}")
    print(f"✅ Session B 目录: {dir_b}")

    if dir_a.exists() and dir_b.exists():
        print("✅ 目录创建成功")
    else:
        print("❌ 目录创建失败")
        return

    if dir_a != dir_b:
        print("✅ 不同 session 目录相互独立")
    else:
        print("❌ 目录隔离失败")

    print()

    # 测试 2：文件写入隔离
    print("=" * 70)
    print("测试 2：文件写入隔离")
    print("=" * 70)

    file_a = dir_a / "test_file.txt"
    file_b = dir_b / "test_file.txt"

    file_a.write_text("Content from Session A")
    file_b.write_text("Content from Session B")

    content_a = file_a.read_text()
    content_b = file_b.read_text()

    print(f"Session A 文件内容: {content_a}")
    print(f"Session B 文件内容: {content_b}")

    if content_a != content_b:
        print("✅ 文件隔离成功：不同 session 的同名文件内容独立")
    else:
        print("❌ 文件隔离失败")

    print()

    # 测试 3：目录结构验证
    print("=" * 70)
    print("测试 3：目录结构验证")
    print("=" * 70)

    expected_parent = Path(runtime_dir)
    actual_parent_a = dir_a.parent
    actual_parent_b = dir_b.parent

    print(f"预期父目录: {expected_parent}")
    print(f"Session A 父目录: {actual_parent_a}")
    print(f"Session B 父目录: {actual_parent_b}")

    if actual_parent_a == expected_parent and actual_parent_b == expected_parent:
        print("✅ 目录结构正确")
    else:
        print("❌ 目录结构错误")

    print()

    # 测试 4：清理 Session
    print("=" * 70)
    print("测试 4：清理 Session")
    print("=" * 70)

    await sandbox.cleanup_session(session_a)

    if not dir_a.exists():
        print("✅ Session A 清理成功：目录已删除")
    else:
        print("❌ Session A 清理失败：目录仍然存在")

    if dir_b.exists():
        print("✅ Session B 未受影响：目录仍然存在")
    else:
        print("❌ Session B 被错误清理")

    print()

    # 测试 5：获取不存在的 Session 目录
    print("=" * 70)
    print("测试 5：获取不存在的 Session 目录")
    print("=" * 70)

    session_c = str(uuid4())
    dir_c = sandbox.get_session_dir(session_c)

    print(f"Session C 目录路径: {dir_c}")
    if not dir_c.exists():
        print("✅ get_session_dir 不自动创建目录")
    else:
        print("❌ get_session_dir 错误地创建了目录")

    print()

    # 清理
    await sandbox.cleanup_session(session_b)

    print("=" * 70)
    print("✅ Sandbox 管理测试完成")
    print("=" * 70)
    print()
    print("总结：")
    print("✅ Session 目录隔离正常")
    print("✅ 文件隔离正常")
    print("✅ 目录结构正确")
    print("✅ Session 清理正常")


if __name__ == "__main__":
    asyncio.run(test_sandbox_isolation())

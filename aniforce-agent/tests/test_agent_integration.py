"""
Phase 2 集成测试 - Agent Runtime + Task Service

测试内容：
1. SQLiteSessionStore 基本操作
2. SkillManager 基本操作
3. SandboxManager 基本操作
4. AgentRuntime 初始化（不实际调用 SDK）
5. TaskService 创建任务
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

from app.agent.session_store import SQLiteSessionStore
from app.agent.skill_manager import SkillManager
from app.agent.sandbox import SandboxManager
from app.agent.runtime import AgentRuntime
from app.models.task import AgentTask, TaskStatus
from app.repositories.task_repo import TaskRepository
from app.repositories.event_repo import EventRepository
from app.services.task_service import TaskService

# 导入共享的 test_db fixture
from tests.conftest import test_db


@pytest.fixture
async def temp_dirs():
    """创建临时目录"""
    temp_dir = Path(tempfile.mkdtemp())
    session_db = temp_dir / "sessions.db"
    runtime_dir = temp_dir / "runtime"
    skills_dir = temp_dir / "skills"

    runtime_dir.mkdir()
    skills_dir.mkdir()

    yield {
        "session_db": str(session_db),
        "runtime_dir": str(runtime_dir),
        "skills_dir": str(skills_dir),
    }

    # 清理
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_session_store_basic(temp_dirs):
    """测试 SessionStore 基本操作"""
    store = SQLiteSessionStore(temp_dirs["session_db"])

    key = {
        "project_key": "test_project",
        "session_id": "session_001",
    }

    # 追加条目
    entries = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    await store.append(key, entries)

    # 加载条目
    loaded = await store.load(key)
    assert loaded is not None
    assert len(loaded) == 2
    assert loaded[0]["role"] == "user"
    assert loaded[1]["role"] == "assistant"

    # 追加更多条目
    more_entries = [{"role": "user", "content": "How are you?"}]
    await store.append(key, more_entries)

    loaded = await store.load(key)
    assert len(loaded) == 3

    # 列出 sessions
    sessions = await store.list_sessions("test_project")
    assert "session_001" in sessions

    # 删除 session
    await store.delete(key)
    loaded = await store.load(key)
    assert loaded is None


@pytest.mark.asyncio
async def test_skill_manager_basic(temp_dirs):
    """测试 SkillManager 基本操作"""
    # 创建测试 Skill
    skill_dir = Path(temp_dirs["skills_dir"]) / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill\n\nThis is a test skill.")

    manager = SkillManager(
        source_dir=temp_dirs["skills_dir"],
        runtime_dir=temp_dirs["runtime_dir"],
    )

    # 列出可用 Skills
    skills = manager.list_available_skills()
    assert "test-skill" in skills

    # 初始化会话 Skills
    session_id = "session_test"
    skills_dir = manager.init_session_skills(session_id)
    assert skills_dir.exists()

    # 检查 Skill 是否复制成功
    skill_path = manager.get_skill_path(session_id, "test-skill")
    assert skill_path is not None
    assert skill_path.exists()

    # 清理
    manager.cleanup_session_skills(session_id)
    assert not manager.get_session_skills_dir(session_id).exists()


@pytest.mark.asyncio
async def test_sandbox_manager_basic(temp_dirs):
    """测试 SandboxManager 基本操作"""
    manager = SandboxManager(runtime_dir=temp_dirs["runtime_dir"])

    session_id = "session_sandbox"

    # 创建会话目录
    session_dir = manager.create_session_dir(session_id)
    assert session_dir.exists()
    assert (session_dir / ".claude").exists()
    assert (session_dir / "workspace").exists()
    assert (session_dir / "logs").exists()

    # 注册进程（模拟）
    fake_pid = 99999
    manager.register_process(session_id, fake_pid)
    assert manager.get_process_id(session_id) == fake_pid

    # 注销进程
    manager.unregister_process(session_id)
    assert manager.get_process_id(session_id) is None

    # 列出会话
    sessions = manager.list_sessions()
    assert session_id in sessions

    # 清理
    manager.cleanup_session_dir(session_id)
    assert not session_dir.exists()


@pytest.mark.asyncio
async def test_agent_runtime_init(temp_dirs):
    """测试 AgentRuntime 初始化"""
    # 修改配置（临时）
    import app.config.settings as settings_module
    original_session_db = settings_module.settings.SESSION_DB_PATH
    original_runtime_dir = settings_module.settings.RUNTIME_DIR
    original_skills_dir = settings_module.settings.SKILLS_SOURCE_DIR

    settings_module.settings.SESSION_DB_PATH = temp_dirs["session_db"]
    settings_module.settings.RUNTIME_DIR = temp_dirs["runtime_dir"]
    settings_module.settings.SKILLS_SOURCE_DIR = temp_dirs["skills_dir"]

    try:
        runtime = AgentRuntime()

        # 检查组件初始化
        assert runtime.session_store is not None
        assert runtime.skill_manager is not None
        assert runtime.sandbox_manager is not None

        # 测试会话信息获取
        session_id = "session_info_test"
        runtime.sandbox_manager.create_session_dir(session_id)

        info = runtime.get_session_info(session_id)
        assert info["session_id"] == session_id
        assert "session_dir" in info
        assert "is_running" in info

        # 清理
        await runtime.cleanup_session(session_id)

    finally:
        # 恢复配置
        settings_module.settings.SESSION_DB_PATH = original_session_db
        settings_module.settings.RUNTIME_DIR = original_runtime_dir
        settings_module.settings.SKILLS_SOURCE_DIR = original_skills_dir


@pytest.mark.asyncio
async def test_task_service_create(test_db):
    """测试 TaskService 创建任务"""
    task_repo = TaskRepository(test_db)
    event_repo = EventRepository(test_db)

    # AgentRuntime 传 None（不实际调用）
    task_service = TaskService(
        task_repo=task_repo,
        event_repo=event_repo,
        agent_runtime=None,  # 仅测试任务创建，不测试执行
    )

    # 创建任务
    task = await task_service.create_task(
        user_id="user123",
        task_type="conversation",
        title="Test Task",
        input_data={"prompt": "Hello"},
    )

    assert task.task_id.startswith("task_")
    assert task.user_id == "user123"
    assert task.status == TaskStatus.PENDING

    # 获取任务
    fetched = await task_service.get_task(task.task_id, "user123")
    assert fetched is not None
    assert fetched.task_id == task.task_id

    # 列出任务
    tasks = await task_service.list_tasks("user123")
    assert len(tasks) == 1
    assert tasks[0].task_id == task.task_id

    # 权限过滤测试
    fetched_wrong = await task_service.get_task(task.task_id, "user456")
    assert fetched_wrong is None

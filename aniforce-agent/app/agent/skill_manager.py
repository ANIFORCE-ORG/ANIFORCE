"""
Skill 动态注入管理器

核心设计：
- Skills 源文件：app/skills/{skill-name}/SKILL.md（Git 管理）
- 运行时注入：runtime/sessions/{session_id}/.claude/skills/（每个会话独立）
- 启动时复制：从源目录复制到会话目录
- 多租户隔离：每个 session 有独立 skill 副本
- 版本管理：通过 Git 管理 app/skills/
"""

import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SkillManager:
    """Skill 动态注入管理器"""

    def __init__(self, source_dir: str | Path, runtime_dir: str | Path):
        """
        Args:
            source_dir: Skills 源目录（app/skills/）
            runtime_dir: 运行时会话根目录（runtime/sessions/）
        """
        self.source_dir = Path(source_dir)
        self.runtime_dir = Path(runtime_dir)

    def init_session_skills(self, session_id: str) -> Path:
        """
        为会话初始化 Skills（动态注入）

        Args:
            session_id: 会话 ID

        Returns:
            Skills 目标目录路径
        """
        target_dir = self.runtime_dir / session_id / ".claude" / "skills"
        target_dir.mkdir(parents=True, exist_ok=True)

        if not self.source_dir.exists():
            logger.warning(f"Skills source directory not found: {self.source_dir}")
            return target_dir

        # 复制所有 Skill 目录
        copied_count = 0
        for skill_dir in self.source_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                target_skill_dir = target_dir / skill_dir.name
                if target_skill_dir.exists():
                    # 已存在则跳过（避免覆盖用户修改）
                    logger.debug(f"Skill already exists, skipping: {skill_dir.name}")
                    continue

                shutil.copytree(skill_dir, target_skill_dir, dirs_exist_ok=True)
                copied_count += 1
                logger.info(f"Copied skill: {skill_dir.name} -> {target_skill_dir}")

        logger.info(f"Initialized {copied_count} skills for session {session_id}")
        return target_dir

    def get_session_skills_dir(self, session_id: str) -> Path:
        """获取会话 Skills 目录路径（不创建）"""
        return self.runtime_dir / session_id / ".claude" / "skills"

    def cleanup_session_skills(self, session_id: str):
        """清理会话 Skills（删除整个会话目录）"""
        session_dir = self.runtime_dir / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
            logger.info(f"Cleaned up session directory: {session_id}")

    def list_available_skills(self) -> list[str]:
        """列出所有可用的 Skill 名称"""
        if not self.source_dir.exists():
            return []

        skills = []
        for skill_dir in self.source_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append(skill_dir.name)

        return sorted(skills)

    def get_skill_path(self, session_id: str, skill_name: str) -> Optional[Path]:
        """获取会话中特定 Skill 的路径"""
        skill_path = self.get_session_skills_dir(session_id) / skill_name / "SKILL.md"
        return skill_path if skill_path.exists() else None

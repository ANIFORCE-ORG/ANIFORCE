"""
AG-UI Tool Registry

可扩展的工具注册中心，用于向 AG-UI 协议适配器注册工具的展示配置和结果提取逻辑。

设计原则:
  - 不硬编码工具名或文案
  - Skills / 配置可通过 registry.register() 动态注册新工具
  - 适配器只消费 registry，不关心工具来源

Usage:
    from app.agent_platform.adapters.agui_registry import ToolRegistry, ToolPresentation

    registry = ToolRegistry()
    registry.register("my_tool", ToolPresentation(
        running_title="正在执行我的工具",
        completed_title="我的工具执行完成",
        extract_result=my_custom_extractor,
    ))
"""

import re
from typing import Optional, Callable


class ToolPresentation:
    """工具的 AG-UI 展示配置"""

    def __init__(
        self,
        running_title: str,
        completed_title: str,
        error_title: str = "工具调用异常",
        extract_result: Callable = None,
    ):
        """
        Args:
            running_title:   工具执行中的 Activity 标题
            completed_title: 工具执行完成后的 Activity 标题
            error_title:     工具执行失败时的 Activity 标题
            extract_result:  可选的结果提取函数 (result: any) -> dict | None
                             用于从工具原始结果中提取结构化数据写入 StateSnapshot
        """
        self.running_title = running_title
        self.completed_title = completed_title
        self.error_title = error_title
        self.extract_result = extract_result

    def title(self, status: str) -> str:
        return getattr(self, f"{status}_title", f"工具调用{status}")


class ToolRegistry:
    """可扩展的工具注册中心"""

    def __init__(self):
        self._tools: dict[str, ToolPresentation] = {}

    def register(self, tool_name: str, presentation: ToolPresentation):
        """注册单个工具"""
        self._tools[tool_name] = presentation

    def register_batch(self, tools: dict[str, ToolPresentation]):
        """批量注册工具"""
        self._tools.update(tools)

    def get(self, tool_name: str) -> Optional[ToolPresentation]:
        return self._tools.get(tool_name)

    def has(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def all(self) -> dict[str, ToolPresentation]:
        return dict(self._tools)


# ============================================================
# 内置 result extractors (可被 Skills 覆盖)
# ============================================================

def extract_projects_from_text(result) -> Optional[list[dict]]:
    """从 list_projects 文本结果提取结构化项目列表"""
    if not isinstance(result, str):
        return None
    projects = []
    for chunk in re.split(r'\n(?=\d+\.\s+\*\*)', result):
        chunk = chunk.strip()
        if not chunk:
            continue
        name_match = re.search(r'\d+\.\s+\*\*(.+?)\*\*', chunk)
        if not name_match:
            continue
        name = name_match.group(1).strip()
        id_match = re.search(r'ID:\s*(.+)', chunk)
        budget_match = re.search(r'预算:\s*[¥￥]?([\d,]+)', chunk)
        status_match = re.search(r'状态:\s*(.+)', chunk)
        projects.append({
            "name": name,
            "id": id_match.group(1).strip() if id_match else "",
            "total_budget": int(budget_match.group(1).replace(",", "")) if budget_match else 0,
            "status": status_match.group(1).strip() if status_match else "active",
        })
    return projects if projects else None


# ============================================================
# 默认注册表
# ============================================================

def create_default_tool_registry() -> ToolRegistry:
    """
    创建默认工具注册表。
    Skills 模块可从此获取 registry 并扩展：
        from app.api.v1.copilotkit import get_tool_registry
        get_tool_registry().register("my_new_tool", ToolPresentation(...))
    """
    registry = ToolRegistry()
    registry.register_batch({
        "list_projects": ToolPresentation(
            running_title="正在查询项目列表",
            completed_title="项目列表查询完成",
            error_title="项目列表查询失败",
            extract_result=extract_projects_from_text,
        ),
        "get_project_detail": ToolPresentation(
            running_title="正在读取项目详情",
            completed_title="项目详情读取完成",
            error_title="项目详情读取失败",
        ),
        "create_project": ToolPresentation(
            running_title="正在创建项目",
            completed_title="项目创建完成",
            error_title="项目创建失败",
        ),
        "list_campaigns": ToolPresentation(
            running_title="正在查询投放计划",
            completed_title="投放计划查询完成",
            error_title="投放计划查询失败",
        ),
        "create_campaign": ToolPresentation(
            running_title="正在创建投放计划",
            completed_title="投放计划创建完成",
            error_title="投放计划创建失败",
        ),
    })
    return registry

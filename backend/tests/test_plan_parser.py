"""测试 Plan Parser"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agent_platform.plan_parser import PlanParser


def test_json_format():
    """测试 JSON 格式"""
    text = """
好的，我来为您制定执行计划：

```json
{
  "todos": [
    {"id": "todo_1", "title": "查询项目列表", "description": "调用 list_projects"},
    {"id": "todo_2", "title": "创建新项目", "description": "调用 create_project", "dependencies": ["todo_1"]},
    {"id": "todo_3", "title": "查看项目详情", "description": "调用 get_project_detail", "dependencies": ["todo_2"]}
  ]
}
```

开始执行...
    """
    
    plan = PlanParser.extract_plan_from_text(text, "task_123")
    assert plan is not None, "应该提取到 JSON 格式的 Plan"
    assert len(plan.todos) == 3, f"应该有 3 个 Todo，实际: {len(plan.todos)}"
    assert plan.todos[0].title == "查询项目列表"
    assert plan.todos[2].dependencies == ["todo_2"]
    print("✅ JSON 格式测试通过")


def test_markdown_format():
    """测试 Markdown 格式"""
    text = """
好的，我来帮您分析。

## 执行计划

1. 查询所有项目
2. 分析每个项目的预算使用情况
3. 生成分析报告
4. 给出优化建议

现在开始执行第一步...
    """
    
    plan = PlanParser.extract_plan_from_text(text, "task_456")
    assert plan is not None, "应该提取到 Markdown 格式的 Plan"
    assert len(plan.todos) == 4, f"应该有 4 个 Todo，实际: {len(plan.todos)}"
    assert plan.todos[0].title == "查询所有项目"
    assert plan.todos[3].title == "给出优化建议"
    print("✅ Markdown 格式测试通过")


def test_chinese_steps_format():
    """测试中文步骤格式"""
    text = """
我的分析步骤如下：

第一步：获取项目数据
第二步：计算预算使用率
第三步：生成可视化图表
第四步：输出结论

让我开始执行...
    """
    
    plan = PlanParser.extract_plan_from_text(text, "task_789")
    assert plan is not None, "应该提取到中文步骤格式的 Plan"
    assert len(plan.todos) >= 2, f"应该至少有 2 个 Todo"
    print(f"✅ 中文步骤格式测试通过（提取到 {len(plan.todos)} 个 Todo）")


def test_no_plan():
    """测试没有计划的情况"""
    text = """
您好！我可以帮您查询项目信息。请问您需要查询哪个项目？
    """
    
    plan = PlanParser.extract_plan_from_text(text, "task_000")
    assert plan is None, "简单回复不应该提取出 Plan"
    print("✅ 无计划文本测试通过")


def test_emoji_list_format():
    """测试带 emoji 的列表格式"""
    text = """
📋 执行计划：

1. ✅ 查询用户的所有项目
2. ⏳ 筛选预算超支的项目
3. ⏳ 生成预警报告
4. ⏳ 发送通知

开始执行...
    """
    
    plan = PlanParser.extract_plan_from_text(text, "task_emoji")
    assert plan is not None, "应该提取到 emoji 列表格式的 Plan"
    assert len(plan.todos) >= 3, f"应该至少有 3 个 Todo"
    print(f"✅ Emoji 列表格式测试通过（提取到 {len(plan.todos)} 个 Todo）")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 Plan Parser")
    print("=" * 60)
    print()
    
    test_json_format()
    test_markdown_format()
    test_chinese_steps_format()
    test_emoji_list_format()
    test_no_plan()
    
    print()
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

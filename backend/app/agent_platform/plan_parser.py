"""
Plan Parser - 从 Agent 输出中提取执行计划

支持多种格式：
1. JSON 格式（最标准）
2. Markdown 列表格式
3. 纯文本列表格式
"""

import json
import re
from typing import Optional
from loguru import logger

from .models import ExecutionPlan, TodoItem, TodoStatus


class PlanParser:
    """执行计划解析器"""
    
    @staticmethod
    def extract_plan_from_text(text: str, task_id: str) -> Optional[ExecutionPlan]:
        """
        从 Agent 输出文本中提取执行计划
        
        Args:
            text: Agent 输出文本
            task_id: 任务 ID
        
        Returns:
            ExecutionPlan 或 None
        """
        
        # 尝试 JSON 格式
        plan = PlanParser._extract_json_plan(text, task_id)
        if plan:
            logger.info(f"[PlanParser] 提取到 JSON 格式的 Plan，包含 {len(plan.todos)} 个 Todo")
            return plan
        
        # 尝试 Markdown 列表格式
        plan = PlanParser._extract_markdown_plan(text, task_id)
        if plan:
            logger.info(f"[PlanParser] 提取到 Markdown 格式的 Plan，包含 {len(plan.todos)} 个 Todo")
            return plan
        
        # 尝试纯文本格式
        plan = PlanParser._extract_text_plan(text, task_id)
        if plan:
            logger.info(f"[PlanParser] 提取到纯文本格式的 Plan，包含 {len(plan.todos)} 个 Todo")
            return plan
        
        logger.debug(f"[PlanParser] 未能从文本中提取 Plan")
        return None
    
    @staticmethod
    def _extract_json_plan(text: str, task_id: str) -> Optional[ExecutionPlan]:
        """提取 JSON 格式的计划"""
        # 查找 JSON 代码块
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, text, re.DOTALL)
        
        if not match:
            # 尝试不带代码块的 JSON
            json_pattern2 = r'\{[\s\S]*?"todos"[\s\S]*?\}'
            match = re.search(json_pattern2, text)
        
        if not match:
            return None
        
        try:
            plan_data = json.loads(match.group(1) if match.lastindex else match.group(0))
            todos = []
            
            for i, todo_data in enumerate(plan_data.get("todos", [])):
                todos.append(TodoItem(
                    id=todo_data.get("id", f"todo_{i+1}"),
                    title=todo_data.get("title", ""),
                    description=todo_data.get("description"),
                    dependencies=todo_data.get("dependencies", []),
                    status=TodoStatus.PENDING,
                ))
            
            if len(todos) == 0:
                return None
            
            return ExecutionPlan(
                plan_id=f"plan_{task_id}_{len(todos)}",
                task_id=task_id,
                todos=todos
            )
        
        except Exception as e:
            logger.warning(f"[PlanParser] JSON 解析失败: {e}")
            return None
    
    @staticmethod
    def _extract_markdown_plan(text: str, task_id: str) -> Optional[ExecutionPlan]:
        """提取 Markdown 列表格式的计划"""
        # 查找 "执行计划" 或 "Todo" 或 "Plan" 后面的列表
        lines = text.split('\n')
        todos = []
        in_plan = False
        
        # 触发词
        plan_triggers = ['执行计划', 'todo list', 'todo', '📋', 'plan:', 'steps:', '步骤']
        
        for line in lines:
            # 判断是否进入计划区域
            if not in_plan:
                if any(trigger in line.lower() for trigger in plan_triggers):
                    in_plan = True
                    continue
            
            # 提取列表项
            if in_plan:
                # 匹配 "1. xxx" 或 "- xxx" 或 "• xxx" 或 "✅ xxx" 或 "⏳ xxx"
                match = re.match(r'^\s*[\d\.\-•]\s*[✅⏳❌☐□▪]?\s*(.+)$', line)
                if match:
                    title = match.group(1).strip()
                    # 移除开头的点号和空格
                    title = re.sub(r'^[\.\s]+', '', title)
                    # 移除可能的描述部分
                    title = re.sub(r'\s*[-:：]\s*.*$', '', title)
                    if title:  # 确保不是空字符串
                        todos.append(TodoItem(
                            id=f"todo_{len(todos)+1}",
                            title=title,
                            status=TodoStatus.PENDING,
                        ))
                elif line.strip() == '':
                    # 空行，可能结束
                    if len(todos) > 2:  # 至少有 2 个 todo 才算有效
                        break
                elif not line.strip().startswith('#') and len(todos) > 0:
                    # 非标题行且已有 todos，可能是结束
                    break
        
        if len(todos) >= 2:  # 至少 2 个才算有效的计划
            return ExecutionPlan(
                plan_id=f"plan_{task_id}_{len(todos)}",
                task_id=task_id,
                todos=todos
            )
        
        return None
    
    @staticmethod
    def _extract_text_plan(text: str, task_id: str) -> Optional[ExecutionPlan]:
        """
        提取纯文本格式的计划（最宽松）
        
        识别类似：
        "第一步...，第二步...，第三步..."
        "首先...，然后...，最后..."
        """
        # 匹配 "第X步" 或 "步骤X" 或 "首先/然后/接着/最后"
        step_patterns = [
            r'第[一二三四五六七八九十\d]+步[：:]\s*(.+?)(?=第[一二三四五六七八九十\d]+步|$)',
            r'步骤\s*\d+[：:]\s*(.+?)(?=步骤\s*\d+|$)',
            r'(首先|然后|接着|其次|再次|最后)[：:,，]\s*(.+?)(?=首先|然后|接着|其次|再次|最后|$)',
        ]
        
        todos = []
        
        for pattern in step_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for i, match in enumerate(matches):
                title = match.group(1) if match.lastindex == 1 else match.group(2)
                title = title.strip()
                # 限制长度
                if len(title) > 100:
                    title = title[:100] + "..."
                # 移除换行
                title = title.replace('\n', ' ').strip()
                if title:
                    todos.append(TodoItem(
                        id=f"todo_{len(todos)+1}",
                        title=title,
                        status=TodoStatus.PENDING,
                    ))
            
            if len(todos) >= 2:
                break
        
        if len(todos) >= 2:
            return ExecutionPlan(
                plan_id=f"plan_{task_id}_{len(todos)}",
                task_id=task_id,
                todos=todos
            )
        
        return None

"""Versioned first-party ANIFORCE business skills."""

from app.agent.business_skills.models import BusinessSkill


SAFE_BUSINESS_MUTATION = BusinessSkill(
    name="safe_business_mutation",
    version="1.0",
    description="安全创建、修改、删除、状态变更或关联业务对象，并验证真实结果。",
    trigger_examples=("把预算改成2万", "暂停这个计划", "创建项目", "关联这个素材"),
    required_slots=("operation", "target_type", "target_id_or_create_fields"),
    clarification_rules=(
        "对象、目标值、删除范围或创建必填字段不唯一时必须澄清，禁止猜测。",
        "用户未提供的可选业务字段保持为空或 Backend 默认值，不擅自补写日期、预算、市场或状态。",
        "用户意图和参数完整后直接调用写工具触发 Workspace HITL，不在聊天区重复确认。",
    ),
    evidence_contract=(
        "写前读取目标对象或关联状态，确认当前值、权限范围和预期变化。",
        "只把 Backend/MCP 返回结果视为执行事实。",
    ),
    workflow=(
        "解析唯一对象、操作和关键参数。",
        "读取当前事实并调用写工具触发 HITL。",
        "批准执行后调用对应读取工具做 read-after-write 验证。",
    ),
    allowed_tools=frozenset({
        "list_projects", "get_project_detail", "create_project", "update_project", "delete_project",
        "list_campaigns", "get_campaign_detail", "create_campaign", "update_campaign",
        "update_campaign_status", "delete_campaign", "get_campaign_materials",
        "list_materials", "get_material_detail", "create_material", "update_material", "delete_material",
        "add_material_to_campaign", "remove_material_from_campaign",
        "add_material_to_project", "remove_material_from_project",
    }),
    response_contract=(
        "审批前只说明将由 Workspace 展示待确认变更。",
        "执行后说明对象、实际变化和验证状态。",
        "失败、部分成功或状态未知时不得表述为已完成。",
    ),
    write_verification=(
        "create 后读取新对象并核对关键字段。",
        "update/status 后读取对象并逐项比对变更字段。",
        "association 后重新查询关联列表。",
        "delete 后确认对象不存在；若无法确认则报告状态未知。",
    ),
)

BUSINESS_SKILLS = (SAFE_BUSINESS_MUTATION,)

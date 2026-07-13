"""Versioned first-party ANIFORCE business skills."""

from app.agent.business_skills.models import BusinessSkill


CAMPAIGN_DIAGNOSIS = BusinessSkill(
    name="campaign_diagnosis",
    version="1.0",
    description="诊断广告计划效果下降、消耗或转化异常，并给出有证据的行动建议。",
    trigger_examples=("这个计划怎么突然掉了", "分析这个 Campaign 最近表现", "为什么转化变差"),
    required_slots=("campaign_id", "time_range_hours"),
    clarification_rules=(
        "必须确认唯一 Campaign；同名或多选时提供候选并等待用户选择，禁止猜测。",
        "时间范围未指定时使用最近 7 天（168 小时），并在回答中明确说明。",
    ),
    evidence_contract=(
        "至少读取 Campaign 详情和指定窗口的 performance 证据。",
        "data_available=false、样本不足或数据过旧时，只能说明不足以判断。",
        "严格区分工具事实、可能原因和建议，不把推断写成已发生事实。",
    ),
    workflow=(
        "解析唯一 Campaign 和时间范围。",
        "调用 get_campaign_detail 与 get_campaign_performance。",
        "识别主要变化和证据限制，再按影响与成本排序建议。",
    ),
    allowed_tools=frozenset({"list_campaigns", "get_campaign_detail", "get_campaign_performance"}),
    response_contract=(
        "先给一句结论，再列关键证据。",
        "将事实、可能原因和建议分开表达。",
        "给出最多三项有优先级的下一步，不罗列泛化常识。",
    ),
)

PROJECT_REVIEW = BusinessSkill(
    name="project_review",
    version="1.0",
    description="复盘项目整体表现，定位重点计划、预算和素材问题。",
    trigger_examples=("哪个项目不太行", "复盘这个项目", "哪些计划还值得继续投"),
    required_slots=("project_id", "time_range_hours"),
    clarification_rules=(
        "必须确认唯一项目；无法从显式 ID、Workspace 或任务状态唯一确定时再追问。",
        "时间范围未指定时使用最近 7 天（168 小时），并在回答中明确说明。",
    ),
    evidence_contract=(
        "至少读取项目详情和项目 performance 汇总。",
        "比较 Campaign 必须使用相同时间窗口和统一指标口径。",
        "没有数据的 Campaign 单独标记，禁止按零表现参与排名。",
    ),
    workflow=(
        "解析项目和时间范围。",
        "调用 get_project_detail、get_project_performance，必要时补充计划或素材关联查询。",
        "聚焦整体结论、重点问题和优先行动，不逐条复述所有对象。",
    ),
    allowed_tools=frozenset({
        "list_projects", "get_project_detail", "get_project_performance",
        "list_campaigns", "get_campaign_detail", "get_campaign_performance",
        "list_materials", "get_campaign_materials",
    }),
    response_contract=(
        "先给项目整体判断和数据覆盖情况。",
        "突出最多三个重点 Campaign 或问题。",
        "建议必须映射到已取得的业务证据。",
    ),
)

SAFE_BUSINESS_MUTATION = BusinessSkill(
    name="safe_business_mutation",
    version="1.0",
    description="安全创建、修改、删除、状态变更或关联业务对象，并验证真实结果。",
    trigger_examples=("把预算改成2万", "暂停这个计划", "创建项目", "关联这个素材"),
    required_slots=("operation", "target_type", "target_id_or_create_fields"),
    clarification_rules=(
        "对象、目标值、删除范围或创建必填字段不唯一时必须澄清，禁止猜测。",
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

BUSINESS_SKILLS = (CAMPAIGN_DIAGNOSIS, PROJECT_REVIEW, SAFE_BUSINESS_MUTATION)

from types import SimpleNamespace

from app.agent.business_skills.loader_tool import load_skill_into_context
from app.agent.business_skills.tool_filter import BASE_READ_TOOLS, allowed_mcp_tools, business_skill_tool_filter
from app.agent.prompts import workspace_instructions
from app.agent.workspace_context import WorkspaceRunContext


def context(run_id):
    return WorkspaceRunContext(user_id="u1", session_id=f"s-{run_id}", run_id=run_id)


def filter_tool(value, tool_name):
    filter_context = SimpleNamespace(run_context=SimpleNamespace(context=value))
    return business_skill_tool_filter(filter_context, SimpleNamespace(name=tool_name))


def test_unloaded_run_hides_write_tools_but_keeps_reads():
    value = context("base")
    assert allowed_mcp_tools(value) == BASE_READ_TOOLS
    assert filter_tool(value, "get_campaign_detail") is True
    assert filter_tool(value, "update_campaign") is False
    prompt = workspace_instructions(SimpleNamespace(context=value), SimpleNamespace())
    tool_section = prompt.split("# 核心规则", 1)[0]
    assert "get_campaign_detail" in tool_section
    assert "update_campaign" not in tool_section


def test_safe_mutation_exposes_write_and_verification_reads():
    value = context("mutation")
    load_skill_into_context(value, "safe_business_mutation", "matched_user_intent")
    allowed = allowed_mcp_tools(value)
    assert "update_campaign" in allowed
    assert "get_campaign_detail" in allowed
    assert "add_material_to_campaign" in allowed
    assert filter_tool(value, "update_campaign") is True


def test_analysis_skill_does_not_expose_writes():
    value = context("diagnosis")
    load_skill_into_context(value, "campaign_diagnosis", "matched_user_intent")
    allowed = allowed_mcp_tools(value)
    assert "get_campaign_performance" in allowed
    assert "update_campaign" not in allowed


def test_concurrent_run_contexts_do_not_share_tool_visibility():
    diagnosis = context("diagnosis")
    mutation = context("mutation")
    load_skill_into_context(diagnosis, "campaign_diagnosis", "matched_user_intent")
    load_skill_into_context(mutation, "safe_business_mutation", "matched_user_intent")

    assert filter_tool(diagnosis, "delete_campaign") is False
    assert filter_tool(mutation, "delete_campaign") is True
    assert diagnosis.selected_skill_ids == ["campaign_diagnosis"]
    assert mutation.selected_skill_ids == ["safe_business_mutation"]


def test_version_mismatch_fails_closed_to_base_reads():
    value = context("old")
    value.selected_skill_ids = ["safe_business_mutation"]
    value.selected_skill_versions = {"safe_business_mutation": "0.9"}
    assert allowed_mcp_tools(value) == BASE_READ_TOOLS
    assert filter_tool(value, "update_project") is False

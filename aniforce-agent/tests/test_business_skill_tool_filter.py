from types import SimpleNamespace

from app.agent.business_skills.loader_tool import load_skill_into_context
from app.agent.business_skills.tool_filter import allowed_mcp_tools, business_skill_tool_filter
from app.agent.prompts import workspace_instructions
from app.agent.workspace_context import WorkspaceRunContext


def context(run_id):
    return WorkspaceRunContext(user_id="u1", session_id=f"s-{run_id}", run_id=run_id)


def filter_tool(value, tool_name):
    filter_context = SimpleNamespace(run_context=SimpleNamespace(context=value))
    return business_skill_tool_filter(filter_context, SimpleNamespace(name=tool_name))


def test_unloaded_run_exposes_read_and_write_tools():
    value = context("base")
    assert allowed_mcp_tools(value) is None
    assert filter_tool(value, "get_campaign_detail") is True
    assert filter_tool(value, "update_campaign") is True
    prompt = workspace_instructions(SimpleNamespace(context=value), SimpleNamespace())
    tool_section = prompt.split("# 核心规则", 1)[0]
    assert "get_campaign_detail" in tool_section
    assert "update_campaign" in tool_section


def test_skills_do_not_change_tool_visibility():
    diagnosis = context("diagnosis")
    mutation = context("mutation")
    load_skill_into_context(diagnosis, "campaign_diagnosis", "matched_user_intent")
    load_skill_into_context(mutation, "safe_business_mutation", "matched_user_intent")

    for value in (diagnosis, mutation):
        assert allowed_mcp_tools(value) is None
        assert filter_tool(value, "get_campaign_performance") is True
        assert filter_tool(value, "remove_material_from_campaign") is True
        assert filter_tool(value, "delete_campaign") is True


def test_version_mismatch_does_not_hide_tools():
    value = context("old")
    value.selected_skill_ids = ["safe_business_mutation"]
    value.selected_skill_versions = {"safe_business_mutation": "0.9"}
    assert allowed_mcp_tools(value) is None
    assert filter_tool(value, "update_project") is True

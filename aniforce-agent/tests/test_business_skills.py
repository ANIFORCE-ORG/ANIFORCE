from types import SimpleNamespace

import pytest

from app.agent.business_skills.loader_tool import load_skill_into_context
from app.agent.business_skills.models import BusinessSkill
from app.agent.business_skills.registry import BusinessSkillRegistry, business_skill_registry
from app.agent.prompts import workspace_instructions
from app.agent.workspace_context import WorkspaceRunContext


def context():
    return WorkspaceRunContext(user_id="u1", session_id="s1", run_id="r1")


def prompt_for(value):
    return workspace_instructions(SimpleNamespace(context=value), SimpleNamespace())


def test_registry_contains_three_versioned_skills():
    assert [skill.name for skill in business_skill_registry.list()] == [
        "campaign_diagnosis",
        "project_review",
        "safe_business_mutation",
    ]
    assert all(skill.version == "1.0" for skill in business_skill_registry.list())


def test_registry_rejects_duplicate_names_and_unknown_tools():
    valid = business_skill_registry.require("campaign_diagnosis")
    with pytest.raises(ValueError, match="Duplicate"):
        BusinessSkillRegistry([valid, valid])

    invalid = BusinessSkill(
        name="invalid",
        version="1",
        description="invalid",
        trigger_examples=(),
        required_slots=(),
        clarification_rules=(),
        evidence_contract=(),
        workflow=("step",),
        allowed_tools=frozenset({"execute_arbitrary_sql"}),
        response_contract=("answer",),
    )
    with pytest.raises(ValueError, match="unknown tools"):
        BusinessSkillRegistry([invalid])


def test_prompt_only_injects_full_contract_after_loading():
    value = context()
    initial = prompt_for(value)
    assert "# Business Skill Index" in initial
    assert "`campaign_diagnosis` v1.0" in initial
    assert "# Business Skill: campaign_diagnosis" not in initial
    assert "## 证据合同" not in initial

    result = load_skill_into_context(value, "campaign_diagnosis", "matched_user_intent")
    loaded = prompt_for(value)
    assert result["loaded"] is True
    assert "# Business Skill: campaign_diagnosis" in loaded
    assert "## 证据合同" in loaded
    assert "# Business Skill: project_review" not in loaded


def test_loader_is_idempotent_and_limits_selected_skills():
    value = context()
    first = load_skill_into_context(value, "campaign_diagnosis", "matched_user_intent")
    repeated = load_skill_into_context(value, "campaign_diagnosis", "matched_user_intent")
    second = load_skill_into_context(value, "project_review", "matched_user_intent")
    blocked = load_skill_into_context(value, "safe_business_mutation", "matched_user_intent")

    assert first["already_loaded"] is False
    assert repeated["already_loaded"] is True
    assert second["loaded"] is True
    assert blocked["code"] == "BUSINESS_SKILL_LIMIT"
    assert value.selected_skill_ids == ["campaign_diagnosis", "project_review"]


def test_unknown_skill_does_not_mutate_context():
    value = context()
    result = load_skill_into_context(value, "missing", "matched_user_intent")
    assert result["code"] == "UNKNOWN_BUSINESS_SKILL"
    assert value.selected_skill_ids == []

import pytest

from app.agent.business_skills.selector import preselect_business_skill
from app.agent.workspace_context import WorkspaceRunContext


def context():
    return WorkspaceRunContext(user_id="u1", session_id="s1", run_id="r1")


@pytest.mark.parametrize("text", [
    "请创建一个美国市场项目，预算2万",
    "把这个项目预算改成2万",
    "暂停这个广告计划",
    "把素材关联到这个计划",
])
def test_explicit_mutations_are_preselected(text):
    value = context()
    assert preselect_business_skill(value, text) == "safe_business_mutation"
    assert value.selected_skill_ids == ["safe_business_mutation"]
    assert value.skill_load_reason == "deterministic_intent_match"


@pytest.mark.parametrize(("text", "expected"), [
    ("这个计划怎么突然掉了？", "campaign_diagnosis"),
    ("帮我复盘一下这个项目", "project_review"),
    ("美国市场哪些计划还值得继续投", "project_review"),
])
def test_clear_analysis_intents_are_preselected(text, expected):
    value = context()
    assert preselect_business_skill(value, text) == expected


@pytest.mark.parametrize("text", [
    "你好",
    "列出我的项目",
    "这个怎么看",
    "ROI 是什么意思",
    "能不能建议一下预算",
])
def test_ambiguous_or_simple_requests_keep_progressive_loading(text):
    value = context()
    assert preselect_business_skill(value, text) is None
    assert value.selected_skill_ids == []


def test_explicit_new_intent_replaces_restored_unfinished_skill():
    value = context()
    value.selected_skill_ids = ["campaign_diagnosis"]
    value.selected_skill_versions = {"campaign_diagnosis": "1.0"}
    assert preselect_business_skill(value, "删除这个项目") == "safe_business_mutation"
    assert value.selected_skill_ids == ["safe_business_mutation"]

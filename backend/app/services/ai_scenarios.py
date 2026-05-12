"""AI Gateway scenario controls."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AIScenarioConfig:
    scenario: str
    input_token_limit: int
    output_token_limit: int
    default_model_tier: str
    output_status: str
    requires_human_confirm: bool = True


AI_SCENARIOS: dict[str, AIScenarioConfig] = {
    "project_draft": AIScenarioConfig("project_draft", 4000, 1200, "small", "draft"),
    "plan_extract": AIScenarioConfig("plan_extract", 4000, 1200, "small", "draft"),
    "material_recommend": AIScenarioConfig("material_recommend", 8000, 1500, "medium", "suggested"),
    "material_copy": AIScenarioConfig("material_copy", 3000, 1000, "small", "draft"),
    "plan_review": AIScenarioConfig("plan_review", 4000, 1200, "small", "suggested"),
    "campaign_diagnosis": AIScenarioConfig("campaign_diagnosis", 8000, 1500, "medium", "suggested"),
    "report_summary": AIScenarioConfig("report_summary", 12000, 2000, "medium", "draft"),
    "chat_general": AIScenarioConfig("chat_general", 4000, 800, "small", "draft"),
}


def get_scenario_config(scenario: str) -> AIScenarioConfig:
    if scenario not in AI_SCENARIOS:
        raise ValueError(f"Unsupported AI scenario: {scenario}")
    return AI_SCENARIOS[scenario]


def mock_output_for_scenario(scenario: str, context: dict[str, Any]) -> dict[str, Any]:
    if scenario == "plan_extract":
        return {
            "project_match": {"project_id": context.get("project_id"), "confidence": 0.8 if context.get("project_id") else 0.0},
            "fields": {},
            "missing_fields": [],
            "blocking_issues": [],
            "next_question": None,
        }
    if scenario == "material_copy":
        return {
            "material_id": context.get("material_id"),
            "candidates": [
                {
                    "title": "高转化素材标题候选",
                    "description": "突出目标市场、核心卖点和首屏冲突的投放描述。",
                    "risk_flags": [],
                }
            ],
        }
    if scenario == "campaign_diagnosis":
        return {
            "facts": context.get("metrics", {}),
            "findings": [],
            "recommendations": [
                {
                    "action_type": "keep_observing",
                    "summary": "当前数据不足，建议继续观察并补充近 24 小时结果。",
                    "requires_human_confirm": True,
                }
            ],
        }
    return {
        "summary": "AI Gateway mock response",
        "scenario": scenario,
        "requires_human_confirm": True,
    }


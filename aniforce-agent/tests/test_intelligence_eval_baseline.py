import json
import re
from pathlib import Path


BASELINE_PATH = Path(__file__).parents[1] / "evals" / "intelligence_baseline.json"
UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


def load_baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def test_core_journeys_represent_natural_page_based_work() -> None:
    baseline = load_baseline()
    journeys = baseline["core_journeys"]

    assert len(journeys) == 10
    assert sum(baseline["score_dimensions"].values()) == 100
    assert {journey["journey"] for journey in journeys} >= {
        "日常巡检",
        "异常诊断",
        "预算取舍",
        "素材迭代",
        "周复盘",
        "新计划搭建",
        "止损执行",
    }

    for journey in journeys:
        context = journey["entry_context"]
        assert context["page"] == "home"
        assert context["fixture"]
        assert journey["expected_user_value"]
        assert journey["expected_behavior"]
        assert journey["forbidden_behavior"]

        user_text = "\n".join(
            turn["content"]
            for turn in journey["conversation"]
            if turn["role"] == "user"
        )
        assert user_text
        assert not UUID_RE.search(user_text)
        assert not re.search(r"(?:项目|计划|素材)\s*ID", user_text, re.IGNORECASE)


def test_protocol_failures_stay_out_of_core_journey_weighting() -> None:
    baseline = load_baseline()
    core_ids = {journey["id"] for journey in baseline["core_journeys"]}
    edge_ids = {case["id"] for case in baseline["edge_regressions"]}

    assert core_ids.isdisjoint(edge_ids)
    assert {"duplicate_name_resolution", "permission_failure"} <= edge_ids

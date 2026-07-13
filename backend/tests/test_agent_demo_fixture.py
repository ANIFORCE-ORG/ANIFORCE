from pathlib import Path

from scripts.seed_agent_demo_account import (
    AD_SETS,
    CAMPAIGNS,
    MATERIALS,
    MATERIAL_ASSIGNMENTS,
    daily_profile,
    rates,
)


def test_demo_fixture_represents_one_operator_workspace() -> None:
    campaign_ids = {item["id"] for item in CAMPAIGNS}
    ad_set_ids = {item[0] for item in AD_SETS}
    material_ids = {item[0] for item in MATERIALS}

    assert len(CAMPAIGNS) == 5
    assert len(AD_SETS) == 10
    assert len(MATERIALS) == 8
    assert {item[1] for item in AD_SETS} <= campaign_ids
    assert {item[0] for item in MATERIAL_ASSIGNMENTS} <= material_ids
    assert {item[1] for item in MATERIAL_ASSIGNMENTS} <= ad_set_ids


def test_demo_fixture_material_previews_exist() -> None:
    creative_dir = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "packages"
        / "main-app"
        / "public"
        / "images"
        / "creatives"
    )

    assert all((creative_dir / item[6]).is_file() for item in MATERIALS)
    assert len({item[6] for item in MATERIALS}) == len(MATERIALS)


def test_demo_fixture_contains_decision_quality_contrasts() -> None:
    latest = {}
    for ad_set_id, _, _, budget, _, _, kind, base_roi, cpi, ctr in AD_SETS:
        if kind == "no_data":
            latest[ad_set_id] = None
            continue
        spend, roi = daily_profile(kind, 13, budget, base_roi)
        latest[ad_set_id] = rates(spend, roi, cpi, ctr)

    assert latest["demo-adset-ios-broad"]["roi"] > 0.6
    assert latest["demo-adset-android-gamer"]["roi"] < 0
    assert latest["demo-adset-tiktok-interest"]["roi"] > 1
    assert latest["demo-adset-tiktok-interest"]["spend"] < latest["demo-adset-ios-broad"]["spend"] / 4
    assert latest["demo-adset-preheat-broad"] is None

    fatigued = [item for item in MATERIAL_ASSIGNMENTS if item[0] == "demo-material-reversal"]
    assert len(fatigued) == 2
    assert all(item[3] < 0 and item[4] >= 5 for item in fatigued)

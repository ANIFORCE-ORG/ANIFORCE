from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.meta_fact import MetaFact
from app.repositories.impl.sqlite_meta_fact_repo import IDENTITY_COLUMNS
from app.services.meta_fact_normalizer import normalize_account_id, normalize_meta_fact


def test_normalizes_sparse_campaign_fact_without_turning_missing_into_zero():
    raw = {
        "account_id": "act_123",
        "account_name": "Example",
        "campaign_id": "456",
        "campaign_name": "Lead Campaign",
        "date_start": "2026-08-10",
        "date_stop": "2026-08-10",
        "spend": "12.340000",
        "impressions": "1000",
        "actions": [{"action_type": "lead", "value": "3"}],
    }

    fact = normalize_meta_fact(raw, connection_id="connection-1", level="campaign")

    assert fact["account_id"] == "123"
    assert fact["entity_id"] == "456"
    assert fact["parent_entity_id"] == "123"
    assert fact["metric_date"] == date(2026, 8, 10)
    assert fact["spend"] == Decimal("12.340000")
    assert fact["clicks"] is None
    assert fact["actions_json"] == raw["actions"]
    assert fact["raw_payload_json"] == raw
    assert fact["attribution_setting"] == "default"


def test_level_controls_entity_and_parent_identity():
    raw = {
        "account_id": "123",
        "campaign_id": "456",
        "campaign_name": "Campaign",
        "adset_id": "789",
        "adset_name": "Ad Set",
        "ad_id": "999",
        "ad_name": "Ad",
        "date_start": "2026-08-10",
    }

    adset = normalize_meta_fact(raw, connection_id="c1", level="adset")
    ad = normalize_meta_fact(raw, connection_id="c1", level="ad")

    assert (adset["entity_id"], adset["parent_entity_id"]) == ("789", "456")
    assert (ad["entity_id"], ad["parent_entity_id"]) == ("999", "789")


def test_account_normalization_and_validation():
    assert normalize_account_id("act_123") == "123"
    assert normalize_account_id("123") == "123"
    with pytest.raises(ValueError):
        normalize_account_id("")
    with pytest.raises(ValueError):
        normalize_meta_fact({"account_id": "123"}, connection_id="c1", level="creative")


def test_database_identity_matches_daily_upsert_contract():
    unique = next(
        constraint for constraint in MetaFact.__table__.constraints
        if constraint.name == "uq_meta_facts_identity"
    )
    assert tuple(column.name for column in unique.columns) == IDENTITY_COLUMNS

    statement = sqlite_insert(MetaFact).values(
        connection_id="c1",
        level="campaign",
        account_id="123",
        entity_id="456",
        metric_date=date(2026, 8, 10),
        attribution_setting="default",
        status="accessible_with_rows",
    )
    statement = statement.on_conflict_do_update(
        index_elements=list(IDENTITY_COLUMNS),
        set_={"status": statement.excluded.status},
    )
    sql = str(statement.compile(dialect=sqlite_dialect()))
    assert "ON CONFLICT" in sql
    assert "DO UPDATE" in sql

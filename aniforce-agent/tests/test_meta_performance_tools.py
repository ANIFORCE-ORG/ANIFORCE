from datetime import date

import pytest

from app.mcp.tools.performance import _objective, _window


def test_objective_aliases_are_normalized_to_backend_contract():
    assert _objective("Sales") == "OUTCOME_SALES"
    assert _objective("purchase") == "OUTCOME_SALES"
    assert _objective("Leads") == "OUTCOME_LEADS"
    assert _objective("OUTCOME_LEADS") == "OUTCOME_LEADS"
    assert _objective("") is None


def test_window_defaults_to_seven_days(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 25)

    monkeypatch.setattr("app.mcp.tools.performance.date", FixedDate)
    assert _window("", "") == ("2026-08-19", "2026-08-25")


def test_window_rejects_invalid_order_and_more_than_ninety_days():
    with pytest.raises(ValueError, match="before"):
        _window("2026-08-02", "2026-08-01")
    with pytest.raises(ValueError, match="90 days"):
        _window("2026-01-01", "2026-04-01")

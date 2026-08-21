"""Small, whitelist-bound Meta Insights collector for meta_facts."""

from __future__ import annotations

from typing import Any, Iterable

from app.services.meta_fact_normalizer import normalize_account_id, normalize_meta_fact


class MetaInsightsCollector:
    LEVELS = ("campaign", "adset", "ad")

    def __init__(self, adapter: Any, repository: Any, allowed_account_ids: Iterable[str]):
        self.adapter = adapter
        self.repository = repository
        self.allowed_account_ids = {
            normalize_account_id(account_id) for account_id in allowed_account_ids
        }

    async def collect_account(
        self,
        *,
        connection_id: str,
        account_id: str,
        since: str,
        until: str,
        business_manager_id: str | None = None,
        account_timezone: str | None = None,
        sync_run_id: str | None = None,
        max_pages: int = 10,
    ) -> dict[str, int]:
        normalized_account_id = normalize_account_id(account_id)
        if normalized_account_id not in self.allowed_account_ids:
            raise PermissionError(f"Meta account {normalized_account_id} is not whitelisted")
        if since > until:
            raise ValueError("since must not be after until")

        counts: dict[str, int] = {}
        for level in self.LEVELS:
            payloads = await self.adapter.get_account_daily_insights(
                normalized_account_id,
                {"since": since, "until": until},
                level,
                max_pages=max_pages,
            )
            rows = [
                normalize_meta_fact(
                    payload,
                    connection_id=connection_id,
                    level=level,
                    business_manager_id=business_manager_id,
                    account_timezone=account_timezone,
                    sync_run_id=sync_run_id,
                )
                for payload in payloads
            ]
            counts[level] = await self.repository.upsert_many(rows)
        return counts

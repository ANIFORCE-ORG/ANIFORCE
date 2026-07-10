"""Dry-run or apply historical Agent state reconciliation."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.agent.reconciliation import AgentStateReconciler
from app.config.database import get_session_maker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stale-minutes",
        type=int,
        default=30,
        help="Treat queued/running runs older than this as interrupted (default: 30)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit repairs. Without this flag the command is read-only.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.stale_minutes < 1:
        raise SystemExit("--stale-minutes must be at least 1")
    cutoff = datetime.utcnow() - timedelta(minutes=args.stale_minutes)
    session_maker = get_session_maker()
    async with session_maker() as session:
        report = await AgentStateReconciler(session).reconcile(cutoff=cutoff, apply=args.apply)
        if args.apply:
            await session.commit()
        else:
            await session.rollback()
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

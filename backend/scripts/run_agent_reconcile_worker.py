"""Start the periodic Agent reconciliation worker."""

import asyncio
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.agent.reconcile_worker import AgentReconcileWorker


if __name__ == "__main__":
    asyncio.run(AgentReconcileWorker().run_forever())

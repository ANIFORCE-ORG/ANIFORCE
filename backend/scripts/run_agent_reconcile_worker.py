"""Start the periodic Agent reconciliation worker."""

import asyncio
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.agent.execution.reconcile_worker import AgentReconcileWorker
from app.config.logging import setup_logging
from app.config.settings import get_settings


if __name__ == "__main__":
    settings = get_settings()
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE or None,
        json_logs=settings.LOG_FORMAT.lower() == "json",
        console=settings.LOG_OUTPUT.lower() in {"console", "both"},
        service=settings.LOG_SERVICE,
        role=settings.LOG_ROLE,
        environment=settings.APP_ENV,
    )
    asyncio.run(AgentReconcileWorker().run_forever())

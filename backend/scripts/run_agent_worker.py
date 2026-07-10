"""Start the database-backed Agent run worker."""

import asyncio
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.agent.run_worker import AgentRunWorker


if __name__ == "__main__":
    asyncio.run(AgentRunWorker().run_forever())

"""Project normalized Workspace requests into durable Artifact facts."""

from app.repositories.impl.sqlite_agent_fact_repo import SqliteAgentArtifactRepository


class WorkspaceArtifactProjection:
    def __init__(self, repository: SqliteAgentArtifactRepository) -> None:
        self._repository = repository

    async def project(
        self,
        *,
        run_id: str,
        session_id: str,
        events: list[tuple[str, dict]],
    ) -> None:
        for event_name, request in events:
            if event_name != "workspace.projection" or not isinstance(request, dict):
                continue
            await self._repository.create_projection(
                session_id=session_id,
                run_id=run_id,
                source_tool_call_id=request.get("tool_call_id"),
                surface=str(request.get("surface") or "unknown"),
                payload=request,
            )

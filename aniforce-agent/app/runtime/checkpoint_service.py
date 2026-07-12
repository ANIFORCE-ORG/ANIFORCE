"""Coordinate SDK RunState checkpoint persistence for Runtime execution."""

from app.agent.checkpoints import (
    RuntimeCheckpointStore,
    interruption_to_dict,
    serialize_workspace_context_for_checkpoint,
)


class RuntimeCheckpointService:
    def __init__(self, engine) -> None:
        self.store = RuntimeCheckpointStore(engine)

    async def create(
        self,
        *,
        result,
        workspace_context,
        session_id: str,
        user_id: str,
        run_id: str,
    ) -> dict:
        state = result.to_state()
        run_state = state.to_json(
            context_serializer=serialize_workspace_context_for_checkpoint,
            strict_context=True,
        )
        interruptions = [
            interruption_to_dict(item)
            for item in (getattr(result, "interruptions", []) or [])
        ]
        return await self.store.create(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            interruptions=interruptions,
            run_state=run_state,
        )

    async def claim(
        self,
        checkpoint_id: str,
        user_id: str,
        *,
        edited_arguments: dict | None = None,
        argument_diff: list | None = None,
        claimed_by: str | None = None,
    ) -> dict:
        return await self.store.claim_or_raise(
            checkpoint_id,
            user_id,
            approved_arguments=edited_arguments,
            argument_diff=argument_diff,
            claimed_by=claimed_by,
        )

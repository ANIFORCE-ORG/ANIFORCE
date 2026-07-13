import asyncio

from app.backend_client import BackendResponseError, BackendUnavailableError
from app.mcp.verification import verify_absent, verify_collection_membership, verify_fields


def test_field_verification_passes_and_reports_mismatch():
    async def scenario():
        async def matching():
            return {"id": "c1", "budget": 20000.0, "status": "paused"}

        async def mismatching():
            return {"id": "c1", "budget": 10000.0, "status": "running"}

        passed = await verify_fields(
            {"id": "c1"}, matching, {"budget": 20000.0, "status": "paused"}, entity_id="c1"
        )
        failed = await verify_fields(
            {"id": "c1"}, mismatching, {"budget": 20000.0, "status": "paused"}, entity_id="c1"
        )
        assert passed["operation_status"] == "executed_and_verified"
        assert passed["verification"]["status"] == "passed"
        assert failed["operation_status"] == "executed_verification_failed"
        assert set(failed["verification"]["mismatches"]) == {"budget", "status"}

    asyncio.run(scenario())


def test_verification_unavailable_is_status_unknown_not_success():
    async def scenario():
        async def unavailable():
            raise BackendUnavailableError("BACKEND_TIMEOUT", "timeout", status=504, retryable=True)

        result = await verify_fields({"id": "p1"}, unavailable, {"name": "项目"}, entity_id="p1")
        assert result["operation_status"] == "status_unknown"
        assert result["verification"]["status"] == "unknown"

    asyncio.run(scenario())


def test_delete_requires_not_found_to_verify():
    async def scenario():
        async def missing():
            raise BackendResponseError("BACKEND_NOT_FOUND", "not found", status=404)

        async def still_exists():
            return {"id": "m1"}

        passed = await verify_absent({"deleted": True}, missing, entity_id="m1")
        failed = await verify_absent({"deleted": True}, still_exists, entity_id="m1")
        assert passed["operation_status"] == "executed_and_verified"
        assert failed["operation_status"] == "executed_verification_failed"

    asyncio.run(scenario())


def test_association_verification_handles_dicts_and_ids():
    async def scenario():
        async def campaign_materials():
            return {"materials": [{"id": "m1"}, {"id": "m2"}]}

        async def material_projects():
            return {"project_ids": ["p1"]}

        added = await verify_collection_membership(
            {"success": True}, campaign_materials, collection_key="materials", entity_id="m2", should_exist=True
        )
        removed = await verify_collection_membership(
            {"success": True}, material_projects, collection_key="project_ids", entity_id="p2", should_exist=False
        )
        assert added["verification"]["status"] == "passed"
        assert removed["verification"]["status"] == "passed"

    asyncio.run(scenario())

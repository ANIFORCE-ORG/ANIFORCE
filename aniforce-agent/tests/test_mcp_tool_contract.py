import asyncio

from app.mcp_server import mcp


EXPECTED_TOOLS = {
    "list_projects": ("limit",),
    "get_project_detail": ("project_id",),
    "get_project_performance": ("hours", "project_id"),
    "create_project": ("description", "end_date", "game_type", "manager", "name", "product", "start_date", "status", "tags", "target_market", "total_budget"),
    "update_project": ("description", "end_date", "name", "product", "project_id", "start_date", "status", "target_market", "total_budget"),
    "delete_project": ("project_id",),
    "list_campaigns": ("limit", "project_id", "status"),
    "get_campaign_detail": ("campaign_id",),
    "get_campaign_performance": ("campaign_id", "hours"),
    "create_campaign": ("ab_test", "account_id", "bid_strategy", "budget", "budget_schedule_specs", "budget_type", "buying_type", "campaign_budget_optimization", "end_date", "material_ids", "name", "objective", "pacing_type", "platform", "project_id", "promoted_object", "special_ad_categories", "special_ad_category_country", "spend_limit", "start_date", "status"),
    "update_campaign": ("ab_test", "account_id", "bid_strategy", "budget", "budget_schedule_specs", "budget_type", "buying_type", "campaign_budget_optimization", "campaign_id", "end_date", "material_ids", "name", "objective", "pacing_type", "platform", "promoted_object", "special_ad_categories", "special_ad_category_country", "spend_limit", "start_date", "status"),
    "update_campaign_status": ("campaign_id", "status"),
    "get_campaign_materials": ("campaign_id",),
    "add_material_to_campaign": ("campaign_id", "material_id"),
    "remove_material_from_campaign": ("campaign_id", "material_id"),
    "delete_campaign": ("campaign_id",),
    "list_materials": ("campaign_id", "limit", "project_id", "type"),
    "create_material": ("campaign_ids", "ctr_estimate", "name", "project_ids", "tags", "thumbnail_url", "type", "url"),
    "get_material_detail": ("material_id",),
    "get_material_image": ("material_id", "thumbnail"),
    "list_available_images": (),
    "update_material": ("creator", "ctr_estimate", "duration", "fatigue", "file_size", "format", "height", "material_id", "media_kind", "name", "placements", "platforms", "poster_url", "preview_url", "ratio", "review_status", "rights", "score", "source", "source_account", "status", "tags", "thumbnail_url", "width"),
    "add_material_to_project": ("material_id", "project_id"),
    "remove_material_from_project": ("material_id", "project_id"),
    "delete_material": ("material_id",),
}

EXPECTED_REQUIRED = {
    "get_project_detail": ("project_id",), "get_project_performance": ("project_id",), "create_project": ("name",), "update_project": ("project_id",), "delete_project": ("project_id",),
    "get_campaign_detail": ("campaign_id",), "get_campaign_performance": ("campaign_id",), "create_campaign": ("project_id", "name", "budget", "platform"), "update_campaign": ("campaign_id",),
    "update_campaign_status": ("campaign_id", "status"), "get_campaign_materials": ("campaign_id",), "add_material_to_campaign": ("campaign_id", "material_id"),
    "remove_material_from_campaign": ("campaign_id", "material_id"), "delete_campaign": ("campaign_id",), "create_material": ("name", "type", "url"),
    "get_material_detail": ("material_id",), "get_material_image": ("material_id",), "update_material": ("material_id",),
    "add_material_to_project": ("material_id", "project_id"), "remove_material_from_project": ("material_id", "project_id"), "delete_material": ("material_id",),
}


def test_mcp_tool_names_and_input_schema_are_stable() -> None:
    async def scenario() -> None:
        tools = await mcp.list_tools()
        actual = {tool.name: tuple(sorted(tool.inputSchema.get("properties", {}))) for tool in tools}
        required = {tool.name: tuple(tool.inputSchema.get("required", [])) for tool in tools if tool.inputSchema.get("required")}
        assert actual == EXPECTED_TOOLS
        assert required == EXPECTED_REQUIRED

    asyncio.run(scenario())

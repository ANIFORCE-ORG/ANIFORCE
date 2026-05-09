"""Schemas for Agent Ads OS GEO diagnosis."""
from pydantic import BaseModel, Field


class GeoAuditRequest(BaseModel):
    project_id: str | None = Field(default=None, max_length=64)
    brand: str | None = Field(default=None, max_length=120)
    url: str = Field(..., min_length=3, max_length=300)
    category: str | None = Field(default=None, max_length=160)
    competitors: list[str] = Field(default_factory=list, max_length=8)
    market: str = Field(default="", max_length=180)


class GeoCrawlerItem(BaseModel):
    name: str
    purpose: str
    hits: int


class GeoPageItem(BaseModel):
    path: str
    page_type: str
    agent_visits: int
    diagnosis: str
    status: str = "ok"


class PromptVisibilityItem(BaseModel):
    prompt: str
    mentioned: bool
    cited: bool
    leading_competitor: str


class FixRecommendation(BaseModel):
    title: str
    body: str
    priority: int


class GeoCrawlSummary(BaseModel):
    requested_url: str
    final_url: str
    sitemap_url: str | None = None
    robots_status: str
    pages_requested: int
    pages_analyzed: int
    pages_failed: int
    ai_assets: dict[str, str] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class GeoExtractedSignal(BaseModel):
    name: str
    value: str
    status: str


class GeoAuditScores(BaseModel):
    mention_rate: int
    citation_rate: int
    geo_readiness: int
    agent_hits: int
    fact_correctness: int
    shortlist_win_rate: int


class GeoAuditReport(BaseModel):
    id: str
    project_id: str | None = None
    input: GeoAuditRequest
    domain: str
    scores: GeoAuditScores
    competitor_leader: str
    agents: list[GeoCrawlerItem]
    pages: list[GeoPageItem]
    crawl_summary: GeoCrawlSummary
    extracted_signals: list[GeoExtractedSignal]
    prompts: list[PromptVisibilityItem]
    fixes: list[FixRecommendation]
    offer_json: dict
    created_at: str


class GeoAuditListResponse(BaseModel):
    audits: list[GeoAuditReport]

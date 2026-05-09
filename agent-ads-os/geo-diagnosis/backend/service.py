"""Website-backed GEO diagnosis generator."""
from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .schemas import (
    FixRecommendation,
    GeoAuditReport,
    GeoAuditRequest,
    GeoAuditScores,
    GeoCrawlSummary,
    GeoCrawlerItem,
    GeoExtractedSignal,
    GeoPageItem,
    PromptVisibilityItem,
)

MAX_PAGES = 10
USER_AGENT = "AgentAdsOS-GEO-Diagnosis/0.1 (+https://agent-ads-os.local)"


@dataclass
class PageSnapshot:
    url: str
    final_url: str = ""
    status_code: int = 0
    title: str = ""
    description: str = ""
    h1: str = ""
    headings: list[str] = field(default_factory=list)
    text: str = ""
    links: list[str] = field(default_factory=list)
    json_ld_count: int = 0
    canonical: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400 and not self.error


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _normalise_url(value: str) -> str:
    value = value.strip()
    if not re.match(r"^https?://", value, re.I):
        value = f"https://{value}"
    return value


def _domain(url: str) -> str:
    parsed = urlparse(_normalise_url(url))
    return (parsed.netloc or parsed.path.split("/")[0] or "example.com").removeprefix("www.")


def _same_domain(url: str, domain: str) -> bool:
    host = urlparse(url).netloc.removeprefix("www.")
    return host == domain or host.endswith(f".{domain}")


def _path(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path or "/"


def _page_type(url: str, page: PageSnapshot) -> str:
    haystack = f"{url} {page.title} {' '.join(page.headings[:4])}".lower()
    if _path(url) == "/":
        return "Homepage"
    if any(term in haystack for term in ("pricing", "price", "plans", "套餐", "价格")):
        return "Pricing"
    if any(term in haystack for term in ("customer", "case", "stories", "clients", "案例", "客户")):
        return "Case Studies"
    if any(term in haystack for term in ("compare", "alternative", "vs", "竞品", "对比")):
        return "Comparison"
    if any(term in haystack for term in ("faq", "help", "docs", "support", "文档", "帮助")):
        return "FAQ / Docs"
    if any(term in haystack for term in ("blog", "article", "guide", "resources", "博客", "指南")):
        return "Content"
    return "Landing Page"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def _has_term(text: str, term: str) -> bool:
    if re.match(r"^[a-z0-9 ]+$", term):
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
    return term in text


def _extract_page(url: str, html: str, domain: str) -> PageSnapshot:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = _clean_text(soup.title.string if soup.title else "")
    description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = _clean_text(description_tag.get("content", "") if description_tag else "")
    canonical_tag = soup.find("link", attrs={"rel": lambda value: value and "canonical" in value})
    canonical = canonical_tag.get("href", "") if canonical_tag else ""
    headings = [_clean_text(tag.get_text(" ")) for tag in soup.find_all(["h1", "h2", "h3"]) if _clean_text(tag.get_text(" "))]
    text = _clean_text(soup.get_text(" "))[:12000]

    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(url, anchor["href"]).split("#")[0]
        if absolute.startswith(("http://", "https://")) and _same_domain(absolute, domain):
            links.append(absolute)

    return PageSnapshot(
        url=url,
        title=title,
        description=description,
        h1=headings[0] if headings else "",
        headings=headings[:20],
        text=text,
        links=list(dict.fromkeys(links))[:80],
        json_ld_count=len(soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)})),
        canonical=canonical,
    )


class WebsiteCrawler:
    async def crawl(self, start_url: str) -> tuple[list[PageSnapshot], GeoCrawlSummary]:
        requested_url = _normalise_url(start_url)
        domain = _domain(requested_url)
        errors: list[str] = []
        robots_status = "not_checked"
        sitemap_url: str | None = None
        ai_assets: dict[str, str] = {}

        timeout = httpx.Timeout(12.0, connect=8.0)
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
        async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
            robots_status, sitemap_url = await self._discover_sitemap(client, requested_url, errors)
            ai_assets = await self._probe_ai_assets(client, requested_url)
            urls = [requested_url]
            urls.extend(await self._read_sitemap(client, sitemap_url, domain, errors) if sitemap_url else [])
            pages = await self._fetch_pages(client, urls, domain, errors)

            if pages:
                extra_links = []
                for link in pages[0].links:
                    if link not in urls:
                        extra_links.append(link)
                if len(pages) < MAX_PAGES and extra_links:
                    pages.extend(await self._fetch_pages(client, extra_links[: MAX_PAGES - len(pages)], domain, errors))

        analyzed = [page for page in pages if page.ok]
        summary = GeoCrawlSummary(
            requested_url=requested_url,
            final_url=analyzed[0].final_url if analyzed else requested_url,
            sitemap_url=sitemap_url,
            robots_status=robots_status,
            pages_requested=min(MAX_PAGES, len(list(dict.fromkeys([requested_url] + [page.url for page in pages])))),
            pages_analyzed=len(analyzed),
            pages_failed=len([page for page in pages if not page.ok]),
            ai_assets=ai_assets,
            errors=errors[:8],
        )
        return pages, summary

    async def _discover_sitemap(self, client: httpx.AsyncClient, start_url: str, errors: list[str]) -> tuple[str, str | None]:
        robots_url = urljoin(start_url, "/robots.txt")
        try:
            response = await client.get(robots_url)
            if response.status_code >= 400:
                return f"missing_{response.status_code}", urljoin(start_url, "/sitemap.xml")
            for line in response.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    return "found", line.split(":", 1)[1].strip()
            return "found_no_sitemap", urljoin(start_url, "/sitemap.xml")
        except httpx.HTTPError as exc:
            errors.append(f"robots fetch failed: {exc.__class__.__name__}")
            return "fetch_failed", urljoin(start_url, "/sitemap.xml")

    async def _read_sitemap(self, client: httpx.AsyncClient, sitemap_url: str, domain: str, errors: list[str]) -> list[str]:
        try:
            response = await client.get(sitemap_url)
            if response.status_code >= 400:
                errors.append(f"sitemap returned {response.status_code}: {sitemap_url}")
                return []
            root = ET.fromstring(response.text.encode("utf-8"))
        except (httpx.HTTPError, ET.ParseError) as exc:
            errors.append(f"sitemap parse failed: {exc.__class__.__name__}")
            return []

        locs: list[str] = []
        for element in root.iter():
            if element.tag.endswith("loc") and element.text:
                url = element.text.strip()
                if url.startswith(("http://", "https://")) and _same_domain(url, domain):
                    locs.append(url)

        locs = list(dict.fromkeys(locs))
        if root.tag.endswith("sitemapindex"):
            nested_urls: list[str] = []
            for nested_sitemap in locs[:5]:
                nested_urls.extend(await self._read_sitemap(client, nested_sitemap, domain, errors))
                if len(nested_urls) >= MAX_PAGES - 1:
                    break
            return self._prioritise_urls(list(dict.fromkeys(nested_urls)), domain)[: MAX_PAGES - 1]

        return self._prioritise_urls(locs, domain)[: MAX_PAGES - 1]

    async def _probe_ai_assets(self, client: httpx.AsyncClient, start_url: str) -> dict[str, str]:
        assets = {
            "llms.txt": "/llms.txt",
            "agent-offer.json": "/agent-offer.json",
            "ai-plugin.json": "/.well-known/ai-plugin.json",
        }
        result: dict[str, str] = {}
        for name, path in assets.items():
            try:
                response = await client.get(urljoin(start_url, path))
                content_type = response.headers.get("content-type", "")
                if 200 <= response.status_code < 300:
                    result[name] = f"found:{content_type or 'unknown'}"
                elif response.status_code in {401, 403}:
                    result[name] = f"blocked:{response.status_code}"
                else:
                    result[name] = f"missing:{response.status_code}"
            except httpx.HTTPError as exc:
                result[name] = f"error:{exc.__class__.__name__}"
        return result

    async def _fetch_pages(self, client: httpx.AsyncClient, urls: list[str], domain: str, errors: list[str]) -> list[PageSnapshot]:
        pages: list[PageSnapshot] = []
        for url in list(dict.fromkeys(urls))[:MAX_PAGES]:
            try:
                response = await client.get(url)
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    pages.append(PageSnapshot(url=url, final_url=str(response.url), status_code=response.status_code, error="not_html"))
                    continue
                page = _extract_page(str(response.url), response.text, domain)
                page.url = url
                page.final_url = str(response.url)
                page.status_code = response.status_code
                pages.append(page)
            except httpx.HTTPError as exc:
                errors.append(f"page fetch failed: {url} ({exc.__class__.__name__})")
                pages.append(PageSnapshot(url=url, error=exc.__class__.__name__))
        return pages[:MAX_PAGES]

    def _prioritise_urls(self, urls: list[str], domain: str) -> list[str]:
        weights = {
            "pricing": 0,
            "price": 0,
            "customers": 1,
            "case": 1,
            "compare": 2,
            "alternative": 2,
            "faq": 3,
            "docs": 3,
            "about": 4,
            "blog": 5,
        }

        def score(url: str) -> tuple[int, int, str]:
            path = _path(url).lower()
            match = min([weight for term, weight in weights.items() if term in path] or [6])
            return (match, len(path), url)

        return [url for url in sorted([url for url in urls if _same_domain(url, domain)], key=score)]


class GeoDiagnosisService:
    def __init__(self):
        self.crawler = WebsiteCrawler()

    async def generate(self, request: GeoAuditRequest) -> GeoAuditReport:
        pages, crawl_summary = await self.crawler.crawl(request.url)
        analyzed = [page for page in pages if page.ok]
        if not analyzed:
            detail = "; ".join(crawl_summary.errors) or "The URL did not return analyzable HTML"
            raise ValueError(f"No analyzable HTML pages were found for this URL: {detail}")

        domain = _domain(crawl_summary.final_url)
        combined_text = " ".join(page.text for page in analyzed).lower()
        brand = request.brand or self._infer_brand(analyzed[0], domain)
        category = request.category or self._infer_category(analyzed)
        competitors = [item.strip() for item in request.competitors if item.strip()][:6]
        competitor_leader = competitors[0] if competitors else "Top search competitor"

        signal_flags = self._signal_flags(analyzed, combined_text)
        signal_flags["llms_txt"] = int(crawl_summary.ai_assets.get("llms.txt", "").startswith("found"))
        signal_flags["offer"] = max(signal_flags["offer"], int(crawl_summary.ai_assets.get("agent-offer.json", "").startswith("found")))
        page_depth_score = min(12, max(0, len(analyzed) - 1) * 2)
        crawl_score = 6 if crawl_summary.robots_status.startswith("found") else 0
        metadata_score = signal_flags["metadata"] * 8
        ai_asset_score = signal_flags["llms_txt"] * 16 + signal_flags["offer"] * 18
        structure_score = signal_flags["structured_data"] * 16 + signal_flags["faq"] * 6
        proof_score = signal_flags["proof"] * 12 + signal_flags["case_study"] * 8
        comparison_score = signal_flags["comparison"] * 10
        penalty = 0
        penalty += 10 if len(analyzed) <= 1 else 0
        penalty += 8 if crawl_summary.pages_failed else 0
        penalty += 8 if not signal_flags["structured_data"] else 0
        penalty += 12 if not signal_flags["llms_txt"] else 0
        penalty += 14 if not signal_flags["offer"] else 0
        readiness = _clamp(
            10
            + page_depth_score
            + crawl_score
            + metadata_score
            + ai_asset_score
            + structure_score
            + proof_score
            + comparison_score
            - penalty,
            3,
            96,
        )
        citation = _clamp(6 + proof_score + signal_flags["structured_data"] * 18 + signal_flags["case_study"] * 10 + page_depth_score - (6 if not signal_flags["proof"] else 0), 3, 92)
        mention = _clamp(12 + metadata_score + comparison_score + signal_flags["brand_repetition"] * 10 + page_depth_score - (4 if len(analyzed) <= 1 else 0), 5, 90)
        correctness = _clamp(24 + metadata_score + signal_flags["structured_data"] * 14 + signal_flags["contact"] * 8 + proof_score - (8 if not signal_flags["offer"] else 0), 8, 94)
        win_rate = _clamp(5 + comparison_score + proof_score + signal_flags["offer"] * 12 + signal_flags["llms_txt"] * 6, 3, 76)
        agent_hits = _clamp(len(combined_text) // 38 + len(analyzed) * 28 + signal_flags["structured_data"] * 70, 30, 1200)

        return GeoAuditReport(
            id=f"audit_{uuid.uuid4().hex[:12]}",
            project_id=request.project_id,
            input=GeoAuditRequest(
                project_id=request.project_id,
                brand=brand,
                url=request.url,
                category=category,
                competitors=competitors,
                market=request.market,
            ),
            domain=domain,
            scores=GeoAuditScores(
                mention_rate=mention,
                citation_rate=citation,
                geo_readiness=readiness,
                agent_hits=agent_hits,
                fact_correctness=correctness,
                shortlist_win_rate=win_rate,
            ),
            competitor_leader=competitor_leader,
            agents=self._agent_items(agent_hits, crawl_summary.robots_status),
            pages=self._page_items(pages),
            crawl_summary=crawl_summary,
            extracted_signals=self._signals(analyzed, signal_flags, category),
            prompts=self._prompts(brand, category, request.market, competitor_leader, mention, citation, signal_flags),
            fixes=self._fixes(signal_flags, competitor_leader),
            offer_json=self._offer_json(brand, domain, category, request.market, competitors, analyzed, signal_flags),
            created_at=datetime.utcnow().isoformat() + "Z",
        )

    def _infer_brand(self, homepage: PageSnapshot, domain: str) -> str:
        candidates = [homepage.title, homepage.h1, domain.split(".")[0]]
        for candidate in candidates:
            candidate = re.split(r"[|-]", candidate or "")[0].strip()
            if candidate:
                return candidate[:80]
        return domain

    def _infer_category(self, pages: list[PageSnapshot]) -> str:
        text = " ".join([pages[0].description, pages[0].h1, pages[0].title]).lower()
        categories = [
            ("AI / Agent product", ("ai", "agent", "automation", "copilot")),
            ("Ecommerce product", ("shop", "commerce", "cart", "store")),
            ("SaaS platform", ("platform", "software", "dashboard", "workflow")),
            ("Mobile app", ("app", "ios", "android", "mobile")),
            ("Game", ("game", "gaming", "player")),
        ]
        for label, terms in categories:
            if any(_has_term(text, term) for term in terms):
                return label
        return "Website / Product"

    def _signal_flags(self, pages: list[PageSnapshot], text: str) -> dict[str, int]:
        page_types = {_page_type(page.final_url or page.url, page).lower() for page in pages}
        return {
            "metadata": int(bool(pages[0].title and pages[0].description and pages[0].h1)),
            "structured_data": int(any(page.json_ld_count for page in pages)),
            "faq": int("faq" in page_types or any(term in text for term in ("frequently asked", "常见问题", "faq"))),
            "offer": int(any("agent-offer.json" in page.text.lower() or "offer" in _path(page.final_url or page.url).lower() for page in pages)),
            "proof": int(any(term in text for term in ("customer", "testimonial", "case study", "review", "客户", "案例", "评价", "证据"))),
            "case_study": int(any("case" in page_type or "customer" in page_type for page_type in page_types)),
            "comparison": int(any("comparison" in page_type for page_type in page_types) or any(term in text for term in ("compare", "alternative", " vs ", "对比", "竞品"))),
            "brand_repetition": int(len(re.findall(re.escape((pages[0].h1 or pages[0].title)[:20].lower()), text)) >= 2 if pages[0].h1 or pages[0].title else False),
            "contact": int(any(term in text for term in ("contact", "book a demo", "get started", "sign up", "联系我们", "预约"))),
        }

    def _agent_items(self, agent_hits: int, robots_status: str) -> list[GeoCrawlerItem]:
        robots_factor = 1.0 if robots_status.startswith("found") else 0.72
        return [
            GeoCrawlerItem(name="OAI-SearchBot", purpose="ChatGPT search / retrieval readiness", hits=round(agent_hits * 0.28 * robots_factor)),
            GeoCrawlerItem(name="GPTBot", purpose="OpenAI crawler policy visibility", hits=round(agent_hits * 0.17 * robots_factor)),
            GeoCrawlerItem(name="PerplexityBot", purpose="Answer engine crawler readiness", hits=round(agent_hits * 0.18 * robots_factor)),
            GeoCrawlerItem(name="ClaudeBot", purpose="Anthropic crawler readiness", hits=round(agent_hits * 0.12 * robots_factor)),
            GeoCrawlerItem(name="Bingbot", purpose="Bing / Copilot search index", hits=round(agent_hits * 0.18)),
            GeoCrawlerItem(name="Googlebot", purpose="Google Search / AI features", hits=round(agent_hits * 0.07)),
        ]

    def _page_items(self, pages: list[PageSnapshot]) -> list[GeoPageItem]:
        items: list[GeoPageItem] = []
        for page in pages:
            if not page.ok:
                items.append(
                    GeoPageItem(
                        path=_path(page.final_url or page.url),
                        page_type="Fetch Error",
                        agent_visits=0,
                        diagnosis=page.error or f"HTTP {page.status_code}",
                        status="error",
                    )
                )
                continue
            page_type = _page_type(page.final_url or page.url, page)
            text_len = len(page.text)
            diagnosis = "可被 AI 摘取"
            if not page.description:
                diagnosis = "缺少 meta description"
            if not page.h1:
                diagnosis = "缺少清晰 H1"
            if page.json_ld_count == 0 and page_type in {"Homepage", "Pricing", "Case Studies", "Comparison"}:
                diagnosis = "建议补结构化数据"
            items.append(
                GeoPageItem(
                    path=_path(page.final_url or page.url),
                    page_type=page_type,
                    agent_visits=_clamp(text_len // 90 + page.json_ld_count * 18 + len(page.headings) * 2, 3, 180),
                    diagnosis=diagnosis,
                    status="ok",
                )
            )
        return items

    def _signals(self, pages: list[PageSnapshot], flags: dict[str, int], category: str) -> list[GeoExtractedSignal]:
        homepage = pages[0]
        return [
            GeoExtractedSignal(name="Title", value=homepage.title or "未发现", status="ok" if homepage.title else "missing"),
            GeoExtractedSignal(name="Description", value=homepage.description or "未发现", status="ok" if homepage.description else "missing"),
            GeoExtractedSignal(name="Primary H1", value=homepage.h1 or "未发现", status="ok" if homepage.h1 else "missing"),
            GeoExtractedSignal(name="Category", value=category, status="inferred"),
            GeoExtractedSignal(name="Structured Data", value=f"{sum(page.json_ld_count for page in pages)} JSON-LD blocks", status="ok" if flags["structured_data"] else "missing"),
            GeoExtractedSignal(name="llms.txt", value="已发布" if flags["llms_txt"] else "未发现", status="ok" if flags["llms_txt"] else "missing"),
            GeoExtractedSignal(name="agent-offer.json", value="已发布" if flags["offer"] else "未发现", status="ok" if flags["offer"] else "missing"),
            GeoExtractedSignal(name="Proof Assets", value="发现案例/客户/评价信号" if flags["proof"] else "未发现明确证据信号", status="ok" if flags["proof"] else "weak"),
            GeoExtractedSignal(name="Comparison Assets", value="发现对比/替代方案信号" if flags["comparison"] else "未发现竞品对比信号", status="ok" if flags["comparison"] else "missing"),
        ]

    def _prompts(self, brand: str, category: str, market: str, competitor: str, mention: int, citation: int, flags: dict[str, int]) -> list[PromptVisibilityItem]:
        buyer = market or "buyers"
        return [
            PromptVisibilityItem(prompt=f"Best {category} for {buyer}", mentioned=mention >= 55, cited=citation >= 45, leading_competitor=competitor),
            PromptVisibilityItem(prompt=f"{brand} reviews and proof", mentioned=flags["proof"] == 1, cited=citation >= 50, leading_competitor=competitor),
            PromptVisibilityItem(prompt=f"Compare {brand} vs {competitor}", mentioned=flags["comparison"] == 1, cited=citation >= 55, leading_competitor=competitor),
        ]

    def _fixes(self, flags: dict[str, int], competitor: str) -> list[FixRecommendation]:
        fixes: list[FixRecommendation] = []
        if not flags["offer"]:
            fixes.append(FixRecommendation(priority=1, title="发布 agent-offer.json", body="把产品定位、目标客户、价格、证据、CTA、集成和限制整理成机器可读 Offer。"))
        if not flags["llms_txt"]:
            fixes.append(FixRecommendation(priority=2, title="发布 llms.txt", body="为 AI agent 提供站点摘要、关键页面、产品事实、禁止误读项和可引用资料入口。"))
        if not flags["structured_data"]:
            fixes.append(FixRecommendation(priority=3, title="补齐 JSON-LD 结构化数据", body="为首页、价格页、FAQ 和案例页添加 Organization、Product、FAQPage、Review 或 SoftwareApplication schema。"))
        if not flags["comparison"]:
            fixes.append(FixRecommendation(priority=4, title=f"补齐 {competitor} 对比页", body="明确适用场景、差异点、迁移成本和证据，让 AI 能回答替代方案问题。"))
        if not flags["proof"]:
            fixes.append(FixRecommendation(priority=5, title="把 claim 绑定到 proof", body="将核心卖点绑定客户案例、截图、数据页、评价或第三方引用，提升 AI 引用概率。"))
        if not fixes:
            fixes.append(FixRecommendation(priority=1, title="增强机器可读证据链", body="现有基础较完整，下一步应把页面 claim、proof 和 CTA 以 JSON-LD 与 offer 文件统一发布。"))
        return fixes

    def _offer_json(self, brand: str, domain: str, category: str, market: str, competitors: list[str], pages: list[PageSnapshot], flags: dict[str, int]) -> dict:
        actions = [{"type": "visit_site", "url": f"https://{domain}/"}]
        for page in pages:
            path = _path(page.final_url or page.url).lower()
            if any(term in path for term in ("demo", "contact", "pricing", "signup")):
                actions.append({"type": "conversion", "url": page.final_url or page.url})
                break
        return {
            "brand": brand,
            "domain": domain,
            "category": category,
            "target_market": market,
            "competitors": competitors,
            "detected_assets": {
                    "structured_data": bool(flags["structured_data"]),
                    "llms_txt": bool(flags["llms_txt"]),
                    "proof": bool(flags["proof"]),
                "comparison": bool(flags["comparison"]),
                "faq": bool(flags["faq"]),
            },
            "recommended_assets": [
                asset
                for asset, present in {
                    "agent-offer.json": flags["offer"],
                    "llms.txt": flags["llms_txt"],
                    "comparison_page": flags["comparison"],
                    "faq_page": flags["faq"],
                    "proof_page": flags["proof"],
                    "json_ld_schema": flags["structured_data"],
                }.items()
                if not present
            ],
            "actions": actions,
        }

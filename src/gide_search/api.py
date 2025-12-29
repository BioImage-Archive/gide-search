"""FastAPI application for gide-search."""

import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .indexer import DatasetIndexer

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="gide-search",
    description="Unified search API for biological imaging databases",
    version="0.1.0",
)

# Initialize indexer from environment or defaults
ES_URL = os.environ.get("ES_URL", "http://localhost:9200")
ES_API_KEY = os.environ.get("ES_API_KEY")
indexer = DatasetIndexer(es_url=ES_URL, api_key=ES_API_KEY)


class FacetBucket(BaseModel):
    """A single facet bucket with key and count."""

    key: str
    count: int


class Facets(BaseModel):
    """Facet aggregations for filtering."""

    sources: list[FacetBucket]
    organisms: list[FacetBucket]
    imaging_methods: list[FacetBucket]
    years: list[FacetBucket]


class StudyHit(BaseModel):
    """A single search result."""

    id: str
    score: float
    source: str
    source_url: str
    title: str
    description: str
    organisms: list[str]
    imaging_methods: list[str]
    release_date: str | None


class SearchResponse(BaseModel):
    """Search response with results and facets."""

    total: int
    hits: list[StudyHit]
    facets: Facets


def parse_es_response(es_response: dict) -> SearchResponse:
    """Parse ElasticSearch response into API response."""
    # Parse hits
    hits = []
    for hit in es_response.get("hits", {}).get("hits", []):
        src = hit["_source"]
        organisms = [
            o.get("scientific_name", "Unknown")
            for bs in src.get("biosamples", [])
            for o in bs.get("organism", [])
        ]
        methods = [
            m.get("name", "Unknown")
            for iap in src.get("image_acquisition_protocols", [])
            for m in iap.get("methods", [])
        ]
        hits.append(
            StudyHit(
                id=src["id"],
                score=hit["_score"] or 0.0,
                source=src["source"],
                source_url=src["source_url"],
                title=src["title"],
                description=src.get("description", "")[:500],
                organisms=organisms,
                imaging_methods=methods,
                release_date=src.get("release_date"),
            )
        )

    # Parse aggregations
    aggs = es_response.get("aggregations", {})

    sources = [
        FacetBucket(key=b["key"], count=b["doc_count"])
        for b in aggs.get("sources", {}).get("buckets", [])
    ]

    organisms = [
        FacetBucket(key=b["key"], count=b["doc_count"])
        for b in aggs.get("organisms", {}).get("names", {}).get("buckets", [])
    ]

    imaging_methods = [
        FacetBucket(key=b["key"], count=b["doc_count"])
        for b in aggs.get("imaging_methods", {}).get("names", {}).get("buckets", [])
    ]

    years = [
        FacetBucket(key=b["key_as_string"], count=b["doc_count"])
        for b in aggs.get("release_dates", {}).get("buckets", [])
        if b["doc_count"] > 0
    ]

    return SearchResponse(
        total=es_response["hits"]["total"]["value"],
        hits=hits,
        facets=Facets(
            sources=sources,
            organisms=organisms,
            imaging_methods=imaging_methods,
            years=years,
        ),
    )


@app.get("/health")
def health_check() -> dict:
    """Check API and ElasticSearch health."""
    es_ok = indexer.ping()
    return {
        "status": "healthy" if es_ok else "degraded",
        "elasticsearch": "connected" if es_ok else "disconnected",
    }


@app.get("/search", response_model=SearchResponse)
def search(
    q: Annotated[str, Query(description="Search query")] = "",
    source: Annotated[
        list[str] | None, Query(description="Filter by source (IDR, SSBD, BIA)")
    ] = None,
    organism: Annotated[
        list[str] | None, Query(description="Filter by organism name")
    ] = None,
    imaging_method: Annotated[
        list[str] | None, Query(description="Filter by imaging method")
    ] = None,
    year_from: Annotated[
        int | None, Query(description="Filter by release year (from)")
    ] = None,
    year_to: Annotated[
        int | None, Query(description="Filter by release year (to)")
    ] = None,
    size: Annotated[int, Query(ge=1, le=100, description="Results per page")] = 20,
    offset: Annotated[int, Query(ge=0, description="Result offset")] = 0,
) -> SearchResponse:
    """
    Search studies with optional filters.

    Returns matching studies along with facet counts for filtering.
    """
    # Convert year to date string
    date_from = f"{year_from}-01-01" if year_from else None
    date_to = f"{year_to}-12-31" if year_to else None

    es_response = indexer.faceted_search(
        query=q,
        sources=source,
        organisms=organism,
        imaging_methods=imaging_method,
        date_from=date_from,
        date_to=date_to,
        size=size,
        from_=offset,
    )

    return parse_es_response(es_response)


@app.get("/api/study/{study_id:path}")
def get_study(study_id: str) -> dict:
    """Get a single study by ID."""
    result = indexer.es.get(index=indexer.index_name, id=study_id)
    return result["_source"]


# Serve index.html at root
@app.get("/")
def serve_index() -> FileResponse:
    """Serve the frontend index page."""
    return FileResponse(STATIC_DIR / "index.html")


# Serve index.html for study detail pages (client-side routing)
@app.get("/study/{study_id:path}")
def serve_study_page(study_id: str) -> FileResponse:
    """Serve the frontend for study detail pages."""
    # The study_id in the path is for the frontend router
    # The actual data is fetched via /study/{study_id} API endpoint
    # We need to distinguish between the API call and the page request
    return FileResponse(STATIC_DIR / "index.html")


# Mount static files (must be after API routes to not shadow them)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

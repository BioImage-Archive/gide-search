import logging
import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query
from pydantic import BaseModel, ValidationError

from .indexer import DatabaseEntryIndexer
from .schema_search_object import Dataset

logger = logging.getLogger()

app = FastAPI(
    title="gide-search",
    description="Unified search API for biological imaging databases",
    version="0.1.0",
)

# Initialize indexer from environment or defaults
ES_URL = os.environ.get("ES_URL", "http://localhost:9200")
ES_API_KEY = os.environ.get("ES_API_KEY")
indexer = DatabaseEntryIndexer(es_url=ES_URL, api_key=ES_API_KEY)


class FacetBucket(BaseModel):
    """A single facet bucket with key and count."""

    key: str
    count: int


class Facets(BaseModel):
    """Facet aggregations for filtering."""

    publishers: list[FacetBucket]
    organisms: list[FacetBucket]
    imaging_methods: list[FacetBucket]
    years: list[FacetBucket]


class Highlights(BaseModel):
    """Highlighted text fragments from search matches."""

    title: str | None = None
    description: list[str] | None = None
    keywords: list[str] | None = None


class EntryHit(BaseModel):
    id: str
    entry: Dataset
    score: float
    highlights: Highlights | None = None


class SearchResponse(BaseModel):
    """Search response with Dataset results and metadata."""

    total: int
    hits: list[EntryHit]
    facets: Facets | None = None


def parse_aggregate(aggregations: dict, source_key: str) -> list[FacetBucket]:
    return [
        FacetBucket(key=bucket["key"], count=bucket["doc_count"])
        for bucket in aggregations.get(source_key, {}).get("buckets", [])
    ]


def parse_es_response(es_response: dict) -> SearchResponse:
    """Parse ElasticSearch response into API response, returning Dataset objects with score."""
    # Parse hits - return the source document (Dataset) plus the score
    hits = []
    for hit in es_response.get("hits", {}).get("hits", []):
        entry_hit = {}
        entry_hit["id"] = hit["_id"]
        entry_hit["entry"] = hit["_source"]
        entry_hit["score"] = hit["_score"] or 0.0

        if "_highlight" in hit:
            entry_hit["highlights"] = hit["_highlight"]

        try:
            valid_hit = EntryHit.model_validate(entry_hit, by_name=True, by_alias=False)
        except ValidationError as e:
            logging.getLogger().error(entry_hit)
            raise e
        hits.append(valid_hit)

    # Parse aggregations for facets
    aggregations = es_response.get("aggregations", {})

    organisms = parse_aggregate(aggregations, "organisms")
    imaging_methods = parse_aggregate(aggregations, "imaging_methods")
    publishers = parse_aggregate(aggregations, "publisher")

    facets = (
        Facets(
            publishers=publishers,
            organisms=organisms,
            imaging_methods=imaging_methods,
            years=[],
        )
        if aggregations
        else None
    )

    return SearchResponse(
        total=es_response["hits"]["total"]["value"],
        hits=hits,
        facets=facets,
    )


SEARCH_QUERY_DESCRIPTION = """
Search query string. Supports two modes:

**Simple search** (default): Just type words to search across all fields including
title, description, authors, organisms, and imaging methods.

**Advanced Lucene syntax**: Use field names, boolean operators, and special syntax
for precise queries. Automatically detected when you use operators like AND, OR,
field:value, quotes, or wildcards.

## Searchable Fields

| Field | Description | Example |
|-------|-------------|---------|
| `title` | entry title (boosted 3x) | `title:fluorescence` |
| `description` | entry description (boosted 2x) | `description:cancer` |
| `keywords` | entry keywords (boosted 2x) | `keywords:microscopy` |
| `source` | Data source | `source:BIA` |
| `authors.name` | Author names | `authors.name:Smith` |
| `biosamples.organism.scientific_name` | Scientific organism name | `biosamples.organism.scientific_name:"Mus musculus"` |
| `image_acquisition_protocols.methods.name` | Imaging method | `image_acquisition_protocols.methods.name:confocal` |

## Lucene Query Syntax

| Syntax | Description | Example |
|--------|-------------|---------|
| `AND` | Both terms required | `mouse AND brain` |
| `OR` | Either term | `mouse OR human` |
| `NOT` | Exclude term | `mouse NOT liver` |
| `"..."` | Exact phrase | `"confocal microscopy"` |
| `*` | Wildcard (any chars) | `fluor*` |
| `?` | Single char wildcard | `m?use` |
| `~` | Fuzzy search | `flourescence~` |
| `^N` | Boost term | `cancer^2 tumor` |
| `[a TO b]` | Range query | `release_date:[2020-01-01 TO 2024-12-31]` |
| `+` | Must include | `+mouse brain` |
| `-` | Must exclude | `mouse -liver` |
| `(...)` | Grouping | `(mouse OR human) AND brain` |

## Examples

- `fluorescence` - Simple search across all fields
- `title:cancer AND authors.name:Smith` - Studies about cancer by Smith
- `"Mus musculus" AND confocal` - Mouse studies using confocal
- `source:BIA AND fluor*` - BIA studies with fluorescence-related terms
- `description:(brain OR neuron) AND NOT liver` - Brain/neuron studies, excluding liver
"""


@app.get("/search", response_model=SearchResponse, response_model_by_alias=False)
def search(
    q: Annotated[str, Query(description=SEARCH_QUERY_DESCRIPTION)] = "",
    publisher: Annotated[
        list[str] | None, Query(description="Filter by publisher (IDR, SSBD, BIA)")
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
    Supports both simple text search and advanced Lucene query syntax.
    """
    # Convert year to date string
    date_from = f"{year_from}-01-01" if year_from else None
    date_to = f"{year_to}-12-31" if year_to else None

    es_response = indexer.faceted_search(
        query=q,
        publishers=publisher,
        organisms=organism,
        imaging_methods=imaging_method,
        date_from=date_from,
        date_to=date_to,
        size=size,
        from_=offset,
    )

    return parse_es_response(es_response)


@app.get("/api/entry/{entry_id:path}")
def get_entry(entry_id: str) -> dict:
    """Get a single entry by ID."""
    result = indexer.es.get(index=indexer.index_name, id=entry_id)
    return result["_source"]


@app.get("/health")
def health_check() -> dict:
    """Check API and ElasticSearch health."""
    es_ok = indexer.ping()
    return {
        "status": "healthy" if es_ok else "degraded",
        "elasticsearch": "connected" if es_ok else "disconnected",
    }

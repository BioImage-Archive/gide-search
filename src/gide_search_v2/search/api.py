import logging
import os
import re
from collections.abc import Callable
from typing import Annotated
from urllib.parse import urlparse

import bidict
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from .indexer import DatabaseEntryIndexer
from .schema_search_object import Dataset

logger = logging.getLogger()

FAST_API_PATH = os.environ.get("FAST_API_PATH", "")

app = FastAPI(
    title="gide-search",
    description="Unified search API for biological imaging databases",
    version="0.1.0",
    root_path=FAST_API_PATH
)

# Initialize indexer from environment or defaults
ES_URL = os.environ.get("ES_URL", "http://localhost:9200")
ES_API_KEY = os.environ.get("ES_API_KEY")
ES_CA_CERT = os.environ.get("ES_CA_CERT")
indexer = DatabaseEntryIndexer(es_url=ES_URL, api_key=ES_API_KEY, ca_certs=ES_CA_CERT)


class FacetBucket(BaseModel):
    """A single facet bucket with key and count."""

    key: str
    count: int
    label: str | None = None


class Facets(BaseModel):
    """Facet aggregations for filtering."""

    publisher: list[FacetBucket]
    organism: list[FacetBucket]
    imaging_method: list[FacetBucket]
    year_published: list[FacetBucket]
    license: list[FacetBucket]


class EntryHit(BaseModel):
    id: str
    entry: Dataset
    score: float


class SearchResponse(BaseModel):
    """Search response with Dataset results and metadata."""

    total: int
    hits: list[EntryHit]
    facets: Facets | None = None


def map_publisher(input: str, to_url: bool) -> str | None:
    publisher_lookup = bidict.bidict(
        {
            "BioImage-Archive": "https://www.ebi.ac.uk/bioimage-archive/",
            "SSBD:repository": "https://ssbd.riken.jp/repository/",
            "SSBD:database": "https://ssbd.riken.jp/database/",
            "IDR": "https://idr.openmicroscopy.org/",
        }
    )

    if to_url:
        return publisher_lookup.get(input)
    else:
        return publisher_lookup.inverse.get(input)


def map_licence(input: str, to_url: bool) -> str | None:
    creative_commons = "https://creativecommons.org/licenses/{code}/{version}/"

    if to_url:
        if input == "CC0":
            return creative_commons.format(code="zero", version="1.0")
        elif input.startswith("CC-"):
            split_input = input.removeprefix("CC-").split("-")
            version = split_input[-1]
            code = "-".join(split_input[:-1]).lower()
            return creative_commons.format(code=code, version=version)

    else:
        # <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
        url = urlparse(input)
        if url.netloc == "creativecommons.org":
            if url.path == "/publicdomain/zero/1.0/":
                return "CC0"
            else:
                licence_path = url.path.split("/")
                licence_code = licence_path[2]
                licence_version = licence_path[3]
                return f"CC {licence_code.replace('-', ' ').upper()} {licence_version}"


def parse_aggregate(
    aggregations: dict,
    source_key: str,
    nested_source_key: str | None = None,
    label_mapping_function: Callable[[str], str | None] | None = None,
) -> list[FacetBucket]:
    aggs = []
    if nested_source_key:
        buckets = (
            aggregations.get(source_key, {})
            .get(nested_source_key, {})
            .get("buckets", [])
        )
    else:
        buckets = aggregations.get(source_key, {}).get("buckets", [])

    for bucket in buckets:
        key_label = None

        if bucket.get("name"):
            first_name_hit = next(
                iter(bucket.get("name", {}).get("hits", {}).get("hits", [])), None
            )
            if first_name_hit:
                key_label = first_name_hit.get("_source", {}).get("name")

        if label_mapping_function:
            key_label = label_mapping_function(bucket["key"])

        if key_label:
            aggs.append(
                FacetBucket(
                    key=bucket.get("key_as_string", bucket["key"]),
                    count=bucket["doc_count"],
                    label=key_label,
                )
            )

        else:
            aggs.append(
                FacetBucket(
                    key=bucket.get("key_as_string", bucket["key"]),
                    count=bucket["doc_count"],
                )
            )
    return aggs


def parse_es_response(es_response: dict) -> SearchResponse:
    """Parse ElasticSearch response into API response, returning Dataset objects with score."""
    # Parse hits - return the source document (Dataset) plus the score
    hits = []
    for hit in es_response.get("hits", {}).get("hits", []):
        entry_hit = {}
        entry_hit["id"] = hit["_id"]
        entry_hit["entry"] = hit["_source"]
        entry_hit["score"] = hit["_score"] or 0.0

        # TODO: parse highlight usefully

        try:
            valid_hit = EntryHit.model_validate(entry_hit, by_name=True, by_alias=False)
        except ValidationError as e:
            logging.getLogger().error(entry_hit)
            raise e
        hits.append(valid_hit)

    # Parse aggregations for facets
    aggregations = es_response.get("aggregations", {})

    organisms = parse_aggregate(aggregations, "organisms", "taxon_ids")
    imaging_methods = parse_aggregate(
        aggregations, "imaging_methods", "imaging_method_ids"
    )
    publishers = parse_aggregate(
        aggregations,
        "publishers",
        label_mapping_function=lambda agg_key: map_publisher(agg_key, False),
    )
    years = parse_aggregate(aggregations, "year_published")
    license = parse_aggregate(
        aggregations,
        "license",
        label_mapping_function=lambda agg_key: map_licence(agg_key, False),
    )

    facets = (
        Facets(
            publisher=publishers,
            organism=organisms,
            imaging_method=imaging_methods,
            year_published=years,
            license=license,
        )
        if aggregations
        else None
    )

    return SearchResponse(
        total=es_response["hits"]["total"]["value"],
        hits=hits,
        facets=facets,
    )


def expand_short_identifier(identifiers: list[str]) -> list[str]:
    full_indentitifers = []
    for identifier in identifiers:
        if identifier.startswith("http"):
            full_indentitifers.append(identifier)
            continue

        match_fbbi = re.match(r"^fbbi\w*?(\d+)$", identifier, re.IGNORECASE)
        if match_fbbi:
            full_indentitifers.append(
                f"http://purl.obolibrary.org/obo/FBbi_{match_fbbi.group(1)}"
            )
            continue

        match_ncbi = re.match(r"^ncbi\w*?(\d+)$", identifier, re.IGNORECASE)
        if match_ncbi:
            full_indentitifers.append(
                f"http://purl.obolibrary.org/obo/NCBITaxon_{int(match_ncbi.group(1))}"
            )
            continue

        full_indentitifers.append(identifier)

    return full_indentitifers


SEARCH_QUERY_DESCRIPTION = """
Search query string.

Supports simple search: Just type words to search across all fields including title, description, authors, organisms, and imaging methods.

"""


@app.get("/search", response_model=SearchResponse, response_model_by_alias=False)
def search(
    q: Annotated[str, Query(description=SEARCH_QUERY_DESCRIPTION)] = "",
    publisher: Annotated[
        list[str] | None, Query(description="Filter by publisher (IDR, SSBD, BIA)")
    ] = None,
    organism: Annotated[
        list[str] | None, Query(description="Filter by organism id")
    ] = None,
    imaging_method: Annotated[
        list[str] | None, Query(description="Filter by imaging method id")
    ] = None,
    license: Annotated[list[str] | None, Query(description="Filter by license")] = None,
    year_from: Annotated[
        int | None, Query(description="Filter by release year (from)")
    ] = None,
    year_to: Annotated[
        int | None, Query(description="Filter by release year (to)")
    ] = None,
    size: Annotated[int, Query(ge=1, le=100, description="Results per page")] = 20,
    offset: Annotated[int, Query(ge=0, description="Result offset")] = 0,
    require_thumbnail: Annotated[
        bool, Query(description="Filter by whether any thumbnails are present.")
    ] = False,
) -> SearchResponse:
    """
    Search studies with optional filters.

    Returns matching studies along with facet counts for filtering.
    Supports both simple text search and advanced Lucene query syntax.
    """
    # Convert year to date string
    date_from = f"{year_from}-01-01" if year_from else None
    date_to = f"{year_to}-12-31" if year_to else None

    publisher_urls = None
    if publisher:
        publisher_urls = [map_publisher(p, to_url=True) or p for p in publisher]

    license_urls = None
    if license:
        license_urls = [map_licence(l, to_url=True) or l for l in license]

    es_response = indexer.faceted_search(
        query=q,
        publishers=publisher_urls,
        organisms=expand_short_identifier(organism) if organism else None,
        imaging_methods=(
            expand_short_identifier(imaging_method) if imaging_method else None
        ),
        licenses=license_urls,
        date_from=date_from,
        date_to=date_to,
        require_thumbnail=require_thumbnail,
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

    response = {
        "status": "healthy" if es_ok else "degraded",
        "elasticsearch": "connected" if es_ok else "disconnected",
    }

    # ! k8s readiness probe only checks status code
    status_code = 200 if es_ok else 500
    return JSONResponse(content=response, status_code=status_code)

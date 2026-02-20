"""CLI for gide-search data transformation pipeline."""

import json
import logging
from pathlib import Path

import httpx
import typer
from pydantic import ValidationError
from tqdm import tqdm

from gide_search_v2.search.indexer import DatabaseEntryIndexer

from .transformers import BIAROCrateTransformer, ROCrateIndexTransformer
from .utils.ontology_term_finder import OntologyTermFinder

logger = logging.getLogger()


app = typer.Typer(
    name="gide-search",
    help="Unified search system for biological imaging databases",
)
data = typer.Typer(
    name="data",
)
app.add_typer(data)


BASE_OUTPUT_DIRECTORY = Path(__file__).parents[2] / "output"
DEFAULT_INDEX_FILE = "index.json"
DEFAULT_INDEX_DIRECTORY = BASE_OUTPUT_DIRECTORY / "index"


def write_rocrate(
    ro_crate_metadata: dict, output_path: Path, detached_ro_crate_id: str | None
) -> None:
    """Write datasets to JSON file."""
    output_path.mkdir(parents=True, exist_ok=True)
    ro_metadata_file_name = (
        f"{detached_ro_crate_id}-ro-crate-metadata.json"
        if detached_ro_crate_id
        else "ro-crate-metadata.json"
    )
    metadata_path = output_path / ro_metadata_file_name
    with open(metadata_path, "w") as f:
        json.dump(ro_crate_metadata, f, indent=2, ensure_ascii=False)


@data.command(
    help="Take detached RO-crates and turn into a single json document for indexing."
)
def transform_to_index(
    input_path: Path = typer.Argument(
        BASE_OUTPUT_DIRECTORY,
        help="Path to ro-crate-metadata.json file or directory to search recursively.",
    ),
    output_path: Path = typer.Option(
        DEFAULT_INDEX_DIRECTORY,
        "--output-path",
        "-o",
        help="Path to write a json file to later index.",
    ),
):
    path = Path(input_path)

    metadata_files = []

    if path.is_dir():
        metadata_files = list(path.glob("**/*-ro-crate-metadata.json"))
    else:
        raise ValueError(
            f"Path must be a ro-crate-metadata.json file or directory: {path}"
        )

    if not metadata_files:
        raise ValueError(f"No ro-crate-metadata.json files found in {path}")

    transformer = ROCrateIndexTransformer()
    results = []
    for metadata_file in tqdm(sorted(metadata_files), desc="Transforming RO-Crates"):
        try:
            with open(metadata_file) as f:
                document = json.load(f)
            try:
                transformed = transformer.transform(document)
            except ValidationError as e:
                logger.error(e)
                continue

            results.append(transformed)
        except Exception as e:
            typer.echo(f"Error transforming {metadata_file}: {e}", err=True)

    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path / DEFAULT_INDEX_FILE, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    typer.echo(
        f"Created indexable document containing {len(results)} datasets from {len(metadata_files)} ro-crates."
    )


@data.command(
    help="Generate detached ro-crate documents from results in the BIA search API."
)
def generate_bia_rocrate(
    output_path: Path = typer.Option(
        BASE_OUTPUT_DIRECTORY / "ro-crate",
        "--output-path",
        "-o",
        help="Path to write a json file to later index.",
    ),
):
    bia_api_url = "https://alpha.bioimagearchive.org/search/search/fts"

    query = ""
    page_size = 50
    params = {
        "query": query,
        "pagination.page_size": page_size,
    }

    response = httpx.get(bia_api_url, params=params, timeout=30.0)
    response.raise_for_status()

    data = response.json().get("hits", {}).get("hits", [])
    transformer = BIAROCrateTransformer(OntologyTermFinder())
    for hit in tqdm(data, desc="Generating BIA RO-Crates"):
        source = hit["_source"]
        if not source["dataset"]:
            continue
        detached_metadata = transformer.transform(source)

        write_rocrate(detached_metadata, output_path, source["accession_id"])


def main() -> None:
    app()


if __name__ == "__main__":
    main()


@data.command()
def index(
    input_path: Path = typer.Argument(
        DEFAULT_INDEX_DIRECTORY / DEFAULT_INDEX_FILE,
        help="Path to JSON file or directory containing JSON files",
        exists=True,
    ),
    es_url: str = typer.Option(
        "http://localhost:9200",
        "--es-url",
        help="ElasticSearch URL",
    ),
    api_key: str = typer.Option(
        None,
        "--api-key",
        help="ElasticSearch API key",
    ),
    recreate: bool = typer.Option(
        False,
        "--recreate",
        help="Delete and recreate the index before indexing",
    ),
) -> None:
    """Index study data into ElasticSearch."""
    indexer = DatabaseEntryIndexer(es_url=es_url, api_key=api_key)

    if not indexer.ping():
        typer.echo("Error: Cannot connect to ElasticSearch", err=True)
        raise typer.Exit(1)

    indexer.create_index(delete_existing=recreate)

    if input_path.is_dir():
        success, errors = indexer.index_from_directory(input_path)
    else:
        success, errors = indexer.index_from_file(input_path)

    typer.echo(f"Indexed {success} studies ({errors} errors)")
    typer.echo(f"Total documents in index: {indexer.get_count()}")


@app.command(help="Search indexed studies directly from elasticsearch.")
def search(
    query: str = typer.Argument(..., help="Search query"),
    es_url: str = typer.Option(
        "http://localhost:9200",
        "--es-url",
        help="ElasticSearch URL",
    ),
    api_key: str = typer.Option(
        None,
        "--api-key",
        help="ElasticSearch API key",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of results",
    ),
    raw: bool = typer.Option(False, "--raw", "-r"),
    faceted: bool = typer.Option(
        False,
        "--faceted",
        "-f",
        help="Use faceted search with aggregations from the indexer",
    ),
    organisms: list[str] | None = typer.Option(
        None,
        "--organism",
        "-o",
        help="Organism taxon id to filter by (repeatable)",
    ),
    imaging_methods: list[str] | None = typer.Option(
        None,
        "--imaging-method",
        "-m",
        help="Imaging method id to filter by (repeatable)",
    ),
    licenses: list[str] | None = typer.Option(
        None,
        "--license",
        "-l",
        help="Lincenses to filter by by (repeatable)",
    ),
    publishers: list[str] | None = typer.Option(
        None,
        "--publisher",
        "-p",
        help="Dataset publishers to filter by by (repeatable)",
    ),
    date_from: str | None = typer.Option(
        None,
        "--date-from",
        help="Start date (YYYY-MM-DD) to filter `datePublished`",
    ),
    date_to: str | None = typer.Option(
        None,
        "--date-to",
        help="End date (YYYY-MM-DD) to filter `datePublished`",
    ),
    require_thumbnail: bool = typer.Option(
        False,
        "--require-thumbnail",
        help="End year to filter `datePublished`",
    ),
) -> None:
    indexer = DatabaseEntryIndexer(es_url=es_url, api_key=api_key)

    if not indexer.ping():
        typer.echo("Error: Cannot connect to ElasticSearch", err=True)
        raise typer.Exit(1)

    if faceted:
        results = indexer.faceted_search(
            query=query,
            organisms=organisms,
            imaging_methods=imaging_methods,
            licenses=licenses,
            publishers=publishers,
            date_from=date_from,
            date_to=date_to,
            size=limit,
            require_thumbnail=require_thumbnail,
        )
    else:
        results = indexer.search(query, size=limit)

    hits = results.get("hits", {}).get("hits", [])

    total_info = results.get("hits", {}).get("total", 0)
    if isinstance(total_info, dict):
        total = total_info.get("value", 0)
    else:
        total = total_info

    typer.echo(f"Found {total} results\n")

    if raw:
        typer.echo(json.dumps(results.raw, indent=2))
        if faceted:
            typer.echo(json.dumps(results.get("aggregations"), indent=2))
        return

    for hit in hits:
        fancy_format_hit(hit, "_source", "_score")

    if faceted:
        aggregations = results.get("aggregations", {}) or {}
        if aggregations:
            fancy_format_aggregations(aggregations, "doc_count")


@app.command(
    help="Search studies via the HTTP API. Must have run the serve command previously."
)
def search_api(
    query: str = typer.Argument(..., help="Search query"),
    api_url: str = typer.Option(
        "http://localhost:8000",
        "--api-url",
        help="Search API base URL",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of results",
    ),
    raw: bool = typer.Option(False, "--raw", "-r"),
    organisms: list[str] | None = typer.Option(
        None,
        "--organism",
        "-o",
        help="Organism taxon id to filter by (repeatable)",
    ),
    imaging_methods: list[str] | None = typer.Option(
        None,
        "--imaging-method",
        "-m",
        help="Imaging method id to filter by (repeatable)",
    ),
    licenses: list[str] | None = typer.Option(
        None,
        "--license",
        "-l",
        help="Lincenses to filter by by (repeatable)",
    ),
    publishers: list[str] | None = typer.Option(
        None,
        "--publisher",
        "-p",
        help="Dataset publishers to filter by by (repeatable)",
    ),
    year_from: str | None = typer.Option(
        None,
        "--date-from",
        help="Start year to filter `datePublished`",
    ),
    year_to: str | None = typer.Option(
        None,
        "--date-to",
        help="End year to filter `datePublished`",
    ),
    require_thumbnail: bool = typer.Option(
        False,
        "--require-thumbnail",
        help="End year to filter `datePublished`",
    ),
) -> None:

    url = f"{api_url.rstrip('/')}/search"
    params = {"q": query, "size": limit, "offset": 0}

    # Forward CLI filter options to the API using the API's expected param names
    if organisms:
        params["organism"] = organisms
    if imaging_methods:
        params["imaging_method"] = imaging_methods
    if licenses:
        params["license"] = licenses
    if publishers:
        params["publishers"] = licenses
    if require_thumbnail:
        params["require_thumbnail"] = True

    # API expects year_from/year_to as integers; extract year if full dates provided
    if year_from:
        try:
            params["year_from"] = int(str(year_from)[:4])
        except Exception:
            pass
    if year_to:
        try:
            params["year_to"] = int(str(year_to)[:4])
        except Exception:
            pass

    try:
        resp = httpx.get(url, params=params, timeout=30.0)
        resp.raise_for_status()
    except Exception as e:
        typer.echo(f"Error contacting API at {url}: {e}", err=True)
        raise typer.Exit(1)

    data = resp.json()

    total = data.get("total") or data.get("total", 0)
    typer.echo(f"Found {total} results\n")

    if raw:
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    hits = data.get("hits", [])
    for hit in hits:
        fancy_format_hit(hit, "entry", "score")

    fancy_format_aggregations(data.get("facets"), "count")


def fancy_format_hit(hit: dict, source_field: str, score_field: str):
    source = hit.get(source_field, {})
    score = hit.get(score_field, 0.0)
    name = source.get("name", "Unknown")
    entry_id = source.get("id") or source.get("identifier") or "unknown"
    typer.echo(f"[{score:.2f}] {entry_id}")
    typer.echo(f"  {name[:80]}")
    if source.get("description"):
        typer.echo(f"  {source['description'][:80]}...")
    typer.echo()


def fancy_format_aggregations(facet_aggregataions: dict, count_field: str):
    typer.echo("Facets:")
    print_facet_list(facet_aggregataions, "organisms", "Organisms", count_field)
    print_facet_list(
        facet_aggregataions, "imaging_methods", "Imaging methods", count_field
    )
    print_facet_list(facet_aggregataions, "publishers", "Publisher", count_field)
    print_facet_list(
        facet_aggregataions, "year_published", "Year Published", count_field
    )
    print_facet_list(facet_aggregataions, "license", "License", count_field)


def print_facet_list(
    facet_aggs: dict, field_name: str, title: str, count_field: str, limit: int = 20
) -> None:
    facets = facet_aggs.get(field_name, [])
    if isinstance(facets, dict) and "buckets" in facets:
        facets = facets["buckets"]
    if len(facets) > 0:
        typer.echo(f"  {title}:")
        for facet in facets[:limit]:
            if facet.get(count_field) > 0:
                typer.echo(
                    f"    {facet.get('key_as_string') or facet.get('key')}: {facet.get(count_field)}"
                )


@app.command(help="Run the api.")
def serve(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Host to bind to",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port to bind to",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload for development",
    ),
) -> None:
    import uvicorn

    typer.echo(f"Starting server at http://{host}:{port}")
    typer.echo(f"API docs available at http://{host}:{port}/docs")
    uvicorn.run(
        "gide_search_v2.search.api:app",
        host=host,
        port=port,
        reload=reload,
    )

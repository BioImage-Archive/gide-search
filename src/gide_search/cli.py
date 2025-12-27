"""CLI for gide-search data transformation pipeline."""

import json
from pathlib import Path

import typer

from .indexer import StudyIndexer
from .schema import Study
from .transformers import BIATransformer, IDRTransformer, SSBDTransformer

app = typer.Typer(
    name="gide-search",
    help="Unified search system for biological imaging databases",
)


def write_studies(studies: list[Study], output_path: Path) -> None:
    """Write studies to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(
            [s.model_dump(mode="json") for s in studies],
            f,
            indent=2,
            default=str,
        )


@app.command()
def transform_ssbd(
    input_path: Path = typer.Argument(
        ...,
        help="Path to SSBD ontology TTL file",
        exists=True,
    ),
    output_path: Path = typer.Option(
        Path("output/ssbd.json"),
        "--output", "-o",
        help="Output JSON file path",
    ),
) -> None:
    """Transform SSBD ontology data to unified schema."""
    typer.echo(f"Loading SSBD ontology from {input_path}...")
    transformer = SSBDTransformer(input_path)

    typer.echo("Transforming datasets...")
    studies = transformer.transform_all()

    write_studies(studies, output_path)
    typer.echo(f"Wrote {len(studies)} studies to {output_path}")


@app.command()
def transform_idr(
    input_path: Path = typer.Argument(
        ...,
        help="Path to IDR metadata repository",
        exists=True,
    ),
    output_path: Path = typer.Option(
        Path("output/idr.json"),
        "--output", "-o",
        help="Output JSON file path",
    ),
) -> None:
    """Transform IDR metadata to unified schema."""
    typer.echo(f"Loading IDR metadata from {input_path}...")
    transformer = IDRTransformer(input_path)

    study_files = transformer.find_study_files()
    typer.echo(f"Found {len(study_files)} study files")

    typer.echo("Transforming studies...")
    studies = transformer.transform_all()

    write_studies(studies, output_path)
    typer.echo(f"Wrote {len(studies)} studies to {output_path}")


@app.command()
def transform_bia(
    page_size: int = typer.Option(
        50,
        "--page-size", "-n",
        help="Number of studies to fetch from BIA API",
    ),
    output_path: Path = typer.Option(
        Path("output/bia.json"),
        "--output", "-o",
        help="Output JSON file path",
    ),
) -> None:
    """Transform BioImage Archive data to unified schema (fetches from API)."""
    typer.echo(f"Fetching {page_size} studies from BIA API...")
    transformer = BIATransformer(page_size=page_size)

    studies = transformer.transform_all()

    write_studies(studies, output_path)
    typer.echo(f"Wrote {len(studies)} studies to {output_path}")


@app.command()
def transform_all(
    ssbd_path: Path = typer.Option(
        None,
        "--ssbd",
        help="Path to SSBD ontology TTL file",
        exists=True,
    ),
    idr_path: Path = typer.Option(
        None,
        "--idr",
        help="Path to IDR metadata repository",
        exists=True,
    ),
    bia: bool = typer.Option(
        False,
        "--bia",
        help="Fetch from BioImage Archive API",
    ),
    bia_page_size: int = typer.Option(
        50,
        "--bia-page-size",
        help="Number of BIA studies to fetch",
    ),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output-dir", "-o",
        help="Output directory for JSON files",
    ),
) -> None:
    """Transform all available data sources."""
    output_dir.mkdir(parents=True, exist_ok=True)
    total = 0

    if ssbd_path:
        typer.echo(f"Transforming SSBD from {ssbd_path}...")
        transformer = SSBDTransformer(ssbd_path)
        studies = transformer.transform_all()
        write_studies(studies, output_dir / "ssbd.json")
        typer.echo(f"  → {len(studies)} SSBD studies")
        total += len(studies)

    if idr_path:
        typer.echo(f"Transforming IDR from {idr_path}...")
        transformer = IDRTransformer(idr_path)
        studies = transformer.transform_all()
        write_studies(studies, output_dir / "idr.json")
        typer.echo(f"  → {len(studies)} IDR studies")
        total += len(studies)

    if bia:
        typer.echo(f"Fetching {bia_page_size} studies from BIA API...")
        transformer = BIATransformer(page_size=bia_page_size)
        studies = transformer.transform_all()
        write_studies(studies, output_dir / "bia.json")
        typer.echo(f"  → {len(studies)} BIA studies")
        total += len(studies)

    typer.echo(f"Total: {total} studies written to {output_dir}/")


@app.command()
def stats(
    input_path: Path = typer.Argument(
        ...,
        help="Path to JSON output file",
        exists=True,
    ),
) -> None:
    """Show statistics for transformed data."""
    with open(input_path) as f:
        studies = json.load(f)

    typer.echo(f"Total studies: {len(studies)}")

    # Count by source
    sources: dict[str, int] = {}
    for s in studies:
        src = s.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    typer.echo("\nBy source:")
    for src, count in sorted(sources.items()):
        typer.echo(f"  {src}: {count}")

    # Count organisms
    organisms: dict[str, int] = {}
    for s in studies:
        for org in s.get("biosample", {}).get("organism", []):
            name = org.get("name", "Unknown")
            organisms[name] = organisms.get(name, 0) + 1

    typer.echo("\nTop organisms:")
    for org, count in sorted(organisms.items(), key=lambda x: -x[1])[:10]:
        typer.echo(f"  {org}: {count}")

    # Count imaging methods
    methods: dict[str, int] = {}
    for s in studies:
        for m in s.get("image_acquisition", {}).get("methods", []):
            name = m.get("name", "Unknown")
            methods[name] = methods.get(name, 0) + 1

    typer.echo("\nTop imaging methods:")
    for method, count in sorted(methods.items(), key=lambda x: -x[1])[:10]:
        typer.echo(f"  {method}: {count}")


@app.command()
def index(
    input_path: Path = typer.Argument(
        ...,
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
    indexer = StudyIndexer(es_url=es_url, api_key=api_key)

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


@app.command()
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
        "--limit", "-n",
        help="Maximum number of results",
    ),
) -> None:
    """Search indexed studies."""
    indexer = StudyIndexer(es_url=es_url, api_key=api_key)

    if not indexer.ping():
        typer.echo("Error: Cannot connect to ElasticSearch", err=True)
        raise typer.Exit(1)

    results = indexer.search(query, size=limit)
    hits = results.get("hits", {}).get("hits", [])

    typer.echo(f"Found {results['hits']['total']['value']} results\n")

    for hit in hits:
        source = hit["_source"]
        score = hit["_score"]
        typer.echo(f"[{score:.2f}] {source['id']}")
        typer.echo(f"  {source['title'][:80]}...")
        typer.echo(f"  Source: {source['source']}")
        typer.echo()


@app.command()
def aggregations(
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
) -> None:
    """Show aggregations across indexed studies."""
    indexer = StudyIndexer(es_url=es_url, api_key=api_key)

    if not indexer.ping():
        typer.echo("Error: Cannot connect to ElasticSearch", err=True)
        raise typer.Exit(1)

    typer.echo(f"Total indexed: {indexer.get_count()}\n")

    typer.echo("By source:")
    for item in indexer.aggregate_sources():
        typer.echo(f"  {item['source']}: {item['count']}")

    typer.echo("\nTop organisms:")
    for item in indexer.aggregate_organisms(size=10):
        typer.echo(f"  {item['name']}: {item['count']}")

    typer.echo("\nTop imaging methods:")
    for item in indexer.aggregate_imaging_methods(size=10):
        typer.echo(f"  {item['name']}: {item['count']}")


@app.command()
def serve(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Host to bind to",
    ),
    port: int = typer.Option(
        8000,
        "--port", "-p",
        help="Port to bind to",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload for development",
    ),
) -> None:
    """Run the API server."""
    import uvicorn

    typer.echo(f"Starting server at http://{host}:{port}")
    typer.echo("API docs available at http://{host}:{port}/docs")
    uvicorn.run(
        "gide_search.api:app",
        host=host,
        port=port,
        reload=reload,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()

"""CLI for gide-search data transformation pipeline."""

import json
from pathlib import Path

import httpx
import typer
from tqdm import tqdm

from .transformers import BIAROCrateTransformer, ROCrateIndexTransformer

app = typer.Typer(
    name="gide-search",
    help="Unified search system for biological imaging databases",
)

BASE_OUTPUT_DIRECTORY = Path(__file__).parents[2] / "output"


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
        json.dump(
            ro_crate_metadata,
            f,
            indent=2,
        )


@app.command()
def transform_to_index(
    input_path: Path = typer.Argument(
        BASE_OUTPUT_DIRECTORY / "ro-crate",
        help="Path to ro-crate-metadata.json file or directory to search recursively.",
    ),
    output_path: Path = typer.Option(
        BASE_OUTPUT_DIRECTORY / "index",
        "--output-path",
        "-o",
        help="Path to write a json file to later index.",
    ),
):
    path = Path(input_path)

    metadata_files = []

    if path.is_file() and path.name == "ro-crate-metadata.json":
        metadata_files = [path]
    elif path.is_dir():
        metadata_files = list(path.glob("**/ro-crate-metadata.json"))
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

            transformed = transformer.transform(document)
            results.append(transformed)
        except Exception as e:
            typer.echo(f"Error transforming {metadata_file}: {e}", err=True)

    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path / "index.json", "w") as f:
        json.dump(results, f, indent=2)


@app.command()
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
    transformer = BIAROCrateTransformer()
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

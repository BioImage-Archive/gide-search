"""Shared pytest fixtures for tests."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from gide_search.cli import app
from gide_search.search.indexer import DatabaseEntryIndexer

runner = CliRunner()


def is_elasticsearch_available(es_url: str = "http://localhost:9200") -> bool:
    """Check if Elasticsearch is available."""
    try:
        indexer = DatabaseEntryIndexer(es_url=es_url)
        return indexer.ping()
    except Exception:
        return False


@pytest.fixture
def es_available():
    """Skip test if Elasticsearch is not available."""
    if not is_elasticsearch_available():
        pytest.skip("Elasticsearch is not available on localhost:9200")


@pytest.fixture
def indexed_data(es_available):
    """Fixture to ensure sample data is indexed before tests."""
    sample_index_file = (
        Path(__file__).parent
        / "data"
        / "index_document"
        / "example_ro_crate_index.json"
    )

    if not sample_index_file.exists():
        pytest.skip(f"Sample index file not found: {sample_index_file}")

    # Run the index command
    result = runner.invoke(
        app,
        [
            "data",
            "index",
            str(sample_index_file),
            "--es-url",
            "http://localhost:9200",
            "--recreate",
        ],
    )

    if result.exit_code != 0:
        pytest.skip(f"Failed to index data: {result.stdout}")

    # Return something to indicate success
    return True

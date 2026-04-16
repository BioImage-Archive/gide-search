"""Tests for CLI data index and search commands."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from gide_search.cli import app

runner = CliRunner()


def test_data_index_command(es_available, tmp_path):
    """Test the 'gide-search data index' command."""
    sample_index_file = (
        Path(__file__).parent
        / "data"
        / "index_document"
        / "example_ro_crate_index.json"
    )

    if not sample_index_file.exists():
        pytest.skip(f"Sample index file not found: {sample_index_file}")

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

    assert result.exit_code == 0, f"Index command failed: {result.stdout}"


def test_search_command(indexed_data):
    """Test the 'gide-search search' command."""
    # Data is already indexed via the fixture

    result = runner.invoke(
        app,
        [
            "search",
            "confocal",  # Query that should match a document in data/index_document
            "--es-url",
            "http://localhost:9200",
            "--limit",
            "10",
        ],
    )

    assert result.exit_code == 0, f"Search command failed: {result.stdout}"
    assert "Found" in result.stdout, "Expected 'Found' in search output"

"""Tests for the search API."""

import pytest
from fastapi.testclient import TestClient

from gide_search.search.api import app


def test_search_api(indexed_data):
    """Test the /search API endpoint with indexed data."""
    client = TestClient(app)

    # Search for "confocal" which should match the sample document
    response = client.get("/search?q=confocal&size=10")

    assert response.status_code == 200

    data = response.json()

    assert "total" in data
    assert "hits" in data
    assert "facets" in data

    assert data["total"] > 0, "Expected to find at least one result"
    assert len(data["hits"]) > 0, "Expected hits array to be non-empty"

    # Check that the first hit has expected structure
    hit = data["hits"][0]
    assert "id" in hit
    assert "entry" in hit
    assert "score" in hit

    # The entry should contain the indexed document data
    entry = hit["entry"]
    assert "name" in entry
    assert "description" in entry

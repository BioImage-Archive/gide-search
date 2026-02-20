"""ElasticSearch indexer for imaging dataset data."""

import json
from pathlib import Path

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk


# Index name
GIDE_DATASETS_INDEX = "gide-datasets"

# ElasticSearch mapping for ImagingDatasetSummary documents
INDEX_MAPPING = {
    "mappings": {
        "dynamic": "false",
        "properties": {
            "id": {"type": "keyword"},
            "identifier": {"type": "keyword"},
            "name": {
                "type": "text",
                "analyzer": "english",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "description": {"type": "text", "analyzer": "english"},
            "datePublished": {"type": "date"},
            "license": {"type": "keyword"},
            "keywords": {"type": "keyword"},
            "publisher": {
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "url": {"type": "keyword"},
                    "address": {"type": "text"},
                }
            },
            # Authors
            "author": {
                "type": "nested",
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "email": {"type": "keyword"},
                    "affiliation": {
                        "type": "nested",
                        "properties": {
                            "@id": {"type": "keyword"},
                            "name": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "url": {"type": "keyword"},
                            "address": {"type": "text"},
                        },
                    },
                },
            },
            # Funders / Grants
            "funder": {
                "type": "nested",
                "properties": {
                    "@id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "identifier": {"type": "keyword"},
                },
            },
            # Publications
            "citation": {
                "type": "nested",
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "text"},
                },
            },
            # Subject
            "about": {
                "type": "nested",
                "properties": {
                    "id": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "description": {"type": "text"},
                    "scientificName": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "vernacularName": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                },
            },
            # Measurement methods
            "measurementMethod": {
                "type": "nested",
                "properties": {
                    "id": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "description": {"type": "text"},
                },
            },
            # Pre-computed facet IDs for faster filtering and aggregation
            "taxon_ids": {"type": "keyword"},
            "imaging_method_ids": {"type": "keyword"},
            # No need to index the urls for search, but used for field exist queries
            "thumbnailUrl": {"type": "keyword", "index": False, "doc_values": True},
        },
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "english": {
                    "type": "english",
                },
            },
        },
    },
}


class DatabaseEntryIndexer:
    """Index imaging dataset entry documents into ElasticSearch."""

    def __init__(
        self,
        es_url: str = "http://localhost:9200",
        index_name: str = GIDE_DATASETS_INDEX,
        api_key: str | None = None,
    ):
        if api_key:
            self.es = Elasticsearch(es_url, api_key=api_key)
        else:
            self.es = Elasticsearch(es_url)
        self.index_name = index_name

    def ping(self) -> bool:
        """Check if ElasticSearch is available."""
        return self.es.ping()

    def create_index(self, delete_existing: bool = False) -> None:
        """Create the studies index with proper mapping."""
        if self.es.indices.exists(index=self.index_name):
            if delete_existing:
                self.es.indices.delete(index=self.index_name)
            else:
                return

        self.es.indices.create(index=self.index_name, body=INDEX_MAPPING)

    def delete_index(self) -> None:
        """Delete the studies index."""
        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)

    def index_entry(self, study: dict) -> None:
        """Index a single database entry."""
        self.es.index(
            index=self.index_name,
            id=study["id"],
            document=study,
        )

    def index_entries(self, studies: list[dict]) -> tuple[int, int]:
        """Bulk index multiple documents. Returns (success_count, error_count)."""

        def generate_actions():
            for study in studies:
                yield {
                    "_index": self.index_name,
                    "_id": study["id"],
                    "_source": study,
                }

        success, errors = bulk(self.es, generate_actions(), raise_on_error=False)
        error_count = len(errors) if isinstance(errors, list) else 0
        return success, error_count

    def index_from_file(self, json_path: Path) -> tuple[int, int]:
        """Load studies from JSON file and index them."""
        with open(json_path) as f:
            studies = json.load(f)
        return self.index_entries(studies)

    def index_from_directory(self, output_dir: Path) -> tuple[int, int]:
        """Index all JSON files in output directory."""
        total_success = 0
        total_errors = 0

        for json_file in output_dir.glob("*.json"):
            success, errors = self.index_from_file(json_file)
            total_success += success
            total_errors += errors

        return total_success, total_errors

    def get_count(self) -> int:
        """Get the number of documents in the index."""
        self.es.indices.refresh(index=self.index_name)
        result = self.es.count(index=self.index_name)
        return result["count"]

    def _build_simple_query(self, query: str) -> dict:
        """Build a simple text query that searches nested fields."""
        return {
            "bool": {
                "should": [
                    # Non-nested fields
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "name^3",
                                "description^2",
                                "keywords^2",
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                        },
                    },
                    # Nested: authors
                    {
                        "nested": {
                            "path": "author",
                            "query": {
                                "match": {
                                    "author.name": {
                                        "query": query,
                                        "fuzziness": "AUTO",
                                    },
                                },
                            },
                        },
                    },
                    # Nested: biolocal data
                    {
                        "nested": {
                            "path": "about",
                            "query": {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "about.id",
                                        "about.name",
                                        "about.description",
                                    ],
                                    "fuzziness": "AUTO",
                                },
                            },
                        },
                    },
                    # Nested: measurement methods
                    {
                        "nested": {
                            "path": "measurementMethod",
                            "query": {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "measurementMethod.name",
                                        "measurementMethod.description",
                                        "measurementMethod.id",
                                    ],
                                    "fuzziness": "AUTO",
                                },
                            },
                        },
                    },
                ],
                "minimum_should_match": 1,
            },
        }

    def _build_text_query(self, query: str) -> dict:
        return self._build_simple_query(query)

    def search(
        self,
        query: str,
        size: int = 10,
        from_: int = 0,
    ):
        """Simple full-text search across studies."""
        body = {
            "query": self._build_text_query(query),
            "size": size,
            "from": from_,
            "highlight": {"fields": {"*": {}}},
        }

        return self.es.search(index=self.index_name, body=body)

    def faceted_search(
        self,
        query: str = "",
        publishers: list[str] | None = None,
        organisms: list[str] | None = None,
        imaging_methods: list[str] | None = None,
        licenses: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        require_thumbnail: bool = False,
        size: int = 10,
        from_: int = 0,
    ) -> dict:
        """Search with filters and return facet aggregations."""
        # Build query
        must = []
        filter_clauses = []

        if licenses:
            filter_clauses.append({"terms": {"license": licenses}})

        if publishers:
            filter_clauses.append({"terms": {"publisher.id": publishers}})

        # Text query
        if query:
            must.append(self._build_text_query(query))

        # Organism filter - filter by pre-computed taxon_ids
        if organisms:
            filter_clauses.append({"terms": {"taxon_ids": organisms}})

        # Imaging method filter - filter by pre-computed imaging_method_ids
        if imaging_methods:
            filter_clauses.append({"terms": {"imaging_method_ids": imaging_methods}})

        # Date range filter
        if date_from or date_to:
            date_range = {}
            if date_from:
                date_range["gte"] = date_from
            if date_to:
                date_range["lte"] = date_to
            filter_clauses.append({"range": {"datePublished": date_range}})

        if require_thumbnail:
            filter_clauses.append({"exists": {"field": "thumbnailUrl"}})

        # Build final query
        if must or filter_clauses:
            bool_query: dict = {}
            if must:
                bool_query["must"] = must
            if filter_clauses:
                bool_query["filter"] = filter_clauses
            main_query = {"bool": bool_query}
        else:
            main_query = {"match_all": {}}

        body = {
            "query": main_query,
            "size": size,
            "from": from_,
            "aggs": {
                "license": {
                    "terms": {
                        "field": "license",
                        "size": 50,
                    }
                },
                "organisms": {
                    "terms": {
                        "field": "taxon_ids",
                        "size": 50,
                    },
                },
                "imaging_methods": {
                    "terms": {
                        "field": "imaging_method_ids",
                        "size": 50,
                    },
                },
                "publishers": {
                    "terms": {
                        "field": "publisher.id",
                        "size": 10,
                    },
                },
                "year_published": {
                    "date_histogram": {
                        "field": "datePublished",
                        "calendar_interval": "year",
                        "format": "yyyy",
                    },
                },
            },
            "highlight": {"fields": {"*": {}}},
        }

        return self.es.search(index=self.index_name, body=body)

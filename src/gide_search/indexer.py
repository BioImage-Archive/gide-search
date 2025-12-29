"""ElasticSearch indexer for imaging dataset data."""

import json
from pathlib import Path

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# Index name
INDEX_NAME = "gide-datasets"

# ElasticSearch mapping for ImagingDatasetSummary documents
INDEX_MAPPING = {
    "mappings": {
        "properties": {
            # Core identification
            "id": {"type": "keyword"},
            "source": {"type": "keyword"},
            "source_url": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "english",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "description": {"type": "text", "analyzer": "english"},
            "license": {"type": "keyword"},
            "release_date": {"type": "date"},
            # Biosamples - nested array for complex queries
            "biosamples": {
                "type": "nested",
                "properties": {
                    "organism": {
                        "type": "nested",
                        "properties": {
                            "scientific_name": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "common_name": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "ncbi_taxon_id": {"type": "integer"},
                        },
                    },
                    "sample_type": {"type": "keyword"},
                    "biological_entity_description": {"type": "text"},
                    "strain": {"type": "keyword"},
                    "cell_line": {"type": "keyword"},
                },
            },
            # Image acquisition protocols - nested array
            "image_acquisition_protocols": {
                "type": "nested",
                "properties": {
                    "methods": {
                        "type": "nested",
                        "properties": {
                            "name": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "fbbi_id": {"type": "keyword"},
                        },
                    },
                    "protocol_description": {"type": "text"},
                    "imaging_instrument_description": {"type": "text"},
                },
            },
            # Publications
            "publications": {
                "type": "nested",
                "properties": {
                    "doi": {"type": "keyword"},
                    "pubmed_id": {"type": "keyword"},
                    "pmc_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "year": {"type": "integer"},
                },
            },
            # Authors
            "authors": {
                "type": "nested",
                "properties": {
                    "name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "orcid": {"type": "keyword"},
                    "email": {"type": "keyword"},
                    "affiliations": {
                        "type": "nested",
                        "properties": {
                            "name": {"type": "text"},
                            "ror_id": {"type": "keyword"},
                            "country": {"type": "keyword"},
                        },
                    },
                },
            },
            # Funding
            "funding": {
                "type": "nested",
                "properties": {
                    "funder": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "grant_id": {"type": "keyword"},
                },
            },
            # Additional metadata
            "data_doi": {"type": "keyword"},
            "keywords": {"type": "keyword"},
            "study_type": {"type": "keyword"},
            "file_count": {"type": "integer"},
            "total_size_bytes": {"type": "long"},
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


class DatasetIndexer:
    """Index imaging dataset documents into ElasticSearch."""

    def __init__(
        self,
        es_url: str = "http://localhost:9200",
        index_name: str = INDEX_NAME,
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

    def index_study(self, study: dict) -> None:
        """Index a single study document."""
        self.es.index(
            index=self.index_name,
            id=study["id"],
            document=study,
        )

    def index_studies(self, studies: list[dict]) -> tuple[int, int]:
        """Bulk index multiple study documents. Returns (success_count, error_count)."""

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
        return self.index_studies(studies)

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

    def search(
        self,
        query: str,
        size: int = 10,
        from_: int = 0,
    ) -> dict:
        """Simple full-text search across studies."""
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^3",
                        "description^2",
                        "keywords^2",
                        "biosamples.organism.scientific_name",
                        "image_acquisition_protocols.methods.name",
                        "authors.name",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                },
            },
            "size": size,
            "from": from_,
        }

        return self.es.search(index=self.index_name, body=body)

    def faceted_search(
        self,
        query: str = "",
        sources: list[str] | None = None,
        organisms: list[str] | None = None,
        imaging_methods: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        size: int = 10,
        from_: int = 0,
    ) -> dict:
        """Search with filters and return facet aggregations."""
        # Build query
        must = []
        filter_clauses = []

        # Text query
        if query:
            must.append({
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^3",
                        "description^2",
                        "keywords^2",
                        "biosamples.organism.scientific_name",
                        "image_acquisition_protocols.methods.name",
                        "authors.name",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                },
            })

        # Source filter
        if sources:
            filter_clauses.append({"terms": {"source": sources}})

        # Organism filter (nested)
        if organisms:
            filter_clauses.append({
                "nested": {
                    "path": "biosamples.organism",
                    "query": {
                        "terms": {"biosamples.organism.scientific_name.keyword": organisms},
                    },
                },
            })

        # Imaging method filter (nested)
        if imaging_methods:
            filter_clauses.append({
                "nested": {
                    "path": "image_acquisition_protocols.methods",
                    "query": {
                        "terms": {"image_acquisition_protocols.methods.name.keyword": imaging_methods},
                    },
                },
            })

        # Date range filter
        if date_from or date_to:
            date_range = {}
            if date_from:
                date_range["gte"] = date_from
            if date_to:
                date_range["lte"] = date_to
            filter_clauses.append({"range": {"release_date": date_range}})

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
                "sources": {
                    "terms": {"field": "source", "size": 10},
                },
                "organisms": {
                    "nested": {"path": "biosamples.organism"},
                    "aggs": {
                        "names": {
                            "terms": {"field": "biosamples.organism.scientific_name.keyword", "size": 20},
                        },
                    },
                },
                "imaging_methods": {
                    "nested": {"path": "image_acquisition_protocols.methods"},
                    "aggs": {
                        "names": {
                            "terms": {"field": "image_acquisition_protocols.methods.name.keyword", "size": 20},
                        },
                    },
                },
                "release_dates": {
                    "date_histogram": {
                        "field": "release_date",
                        "calendar_interval": "year",
                        "format": "yyyy",
                    },
                },
            },
        }

        return self.es.search(index=self.index_name, body=body)

    def search_by_organism(self, organism: str, size: int = 10) -> dict:
        """Search studies by organism name."""
        body = {
            "query": {
                "nested": {
                    "path": "biosamples.organism",
                    "query": {
                        "match": {"biosamples.organism.scientific_name": organism},
                    },
                },
            },
            "size": size,
        }

        return self.es.search(index=self.index_name, body=body)

    def search_by_imaging_method(self, method: str, size: int = 10) -> dict:
        """Search studies by imaging method."""
        body = {
            "query": {
                "nested": {
                    "path": "image_acquisition_protocols.methods",
                    "query": {
                        "match": {"image_acquisition_protocols.methods.name": method},
                    },
                },
            },
            "size": size,
        }

        return self.es.search(index=self.index_name, body=body)

    def aggregate_organisms(self, size: int = 20) -> list[dict]:
        """Get aggregation of organisms across all studies."""
        body = {
            "size": 0,
            "aggs": {
                "organisms": {
                    "nested": {"path": "biosamples.organism"},
                    "aggs": {
                        "names": {
                            "terms": {
                                "field": "biosamples.organism.scientific_name.keyword",
                                "size": size,
                            },
                        },
                    },
                },
            },
        }

        result = self.es.search(index=self.index_name, body=body)
        buckets = result["aggregations"]["organisms"]["names"]["buckets"]
        return [{"name": b["key"], "count": b["doc_count"]} for b in buckets]

    def aggregate_imaging_methods(self, size: int = 20) -> list[dict]:
        """Get aggregation of imaging methods across all studies."""
        body = {
            "size": 0,
            "aggs": {
                "methods": {
                    "nested": {"path": "image_acquisition_protocols.methods"},
                    "aggs": {
                        "names": {
                            "terms": {
                                "field": "image_acquisition_protocols.methods.name.keyword",
                                "size": size,
                            },
                        },
                    },
                },
            },
        }

        result = self.es.search(index=self.index_name, body=body)
        buckets = result["aggregations"]["methods"]["names"]["buckets"]
        return [{"name": b["key"], "count": b["doc_count"]} for b in buckets]

    def aggregate_sources(self) -> list[dict]:
        """Get aggregation of data sources."""
        body = {
            "size": 0,
            "aggs": {
                "sources": {
                    "terms": {"field": "source", "size": 10},
                },
            },
        }

        result = self.es.search(index=self.index_name, body=body)
        buckets = result["aggregations"]["sources"]["buckets"]
        return [{"source": b["key"], "count": b["doc_count"]} for b in buckets]

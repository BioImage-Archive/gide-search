# gide-search

A unified search system for biological imaging databases. Aggregates study-level metadata from multiple sources into a single searchable index.

## Supported Data Sources

| Source | Description | Data Format |
|--------|-------------|-------------|
| **IDR** | Image Data Resource - curated reference datasets | Local TSV files (from [idr-metadata](https://github.com/IDR/idr-metadata)) |
| **SSBD** | Systems Science of Biological Dynamics | RDF/TTL ontology files |
| **BIA** | BioImage Archive | REST API |

## Installation

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Quick Start

```bash
# Transform data from all sources
uv run gide-search transform-all \
  --ssbd resources/ssbd/ssbd_instances.ttl \
  --idr resources/idr \
  --bia

# Index into ElasticSearch (requires ES on localhost:9200)
uv run gide-search index output/

# Search
uv run gide-search search "fluorescence microscopy"
```

## CLI Commands

### Data Transformation

Transform source data into the unified JSON schema:

```bash
# SSBD - from ontology TTL file
uv run gide-search transform-ssbd resources/ssbd/ssbd_instances.ttl

# IDR - from metadata repository
uv run gide-search transform-idr resources/idr

# BIA - fetches from API (default 50 studies)
uv run gide-search transform-bia -n 100

# All sources at once
uv run gide-search transform-all --ssbd <path> --idr <path> --bia

# View statistics for transformed data
uv run gide-search stats output/ssbd.json
```

Output is written to `output/*.json` by default.

### ElasticSearch Indexing

Index transformed JSON into ElasticSearch:

```bash
# Index all JSON files in a directory
uv run gide-search index output/

# Index a single file
uv run gide-search index output/ssbd.json

# Recreate index from scratch
uv run gide-search index output/ --recreate

# Use remote ES with API key
uv run gide-search index output/ --es-url https://... --api-key <key>
```

### Search & Aggregations

```bash
# Full-text search
uv run gide-search search "HeLa cells"
uv run gide-search search "confocal" -n 20

# View aggregations (counts by source, organism, imaging method)
uv run gide-search aggregations
```

## Architecture

```
+-------------------------------------------------------------------+
|                        Data Sources                               |
+------------------+------------------+-----------------------------+
|   SSBD (TTL)     |   IDR (TSV)      |   BIA (REST API)            |
+--------+---------+--------+---------+-------------+---------------+
         |                  |                       |
         v                  v                       v
+-------------------------------------------------------------------+
|                     Transformers                                  |
|  SSBDTransformer  |  IDRTransformer  |  BIATransformer            |
|    (rdflib)       |   (TSV parsing)  |     (httpx)                |
+--------+---------------------+------------------------+-----------+
         |                     |                        |
         v                     v                        v
+-------------------------------------------------------------------+
|                    Unified Schema (Pydantic)                      |
|                                                                   |
|  Study                                                            |
|  +-- id, source, source_url, title, description                   |
|  +-- license, release_date                                        |
|  +-- BioSample                                                    |
|  |   +-- Organism[] (name, ncbi_taxon_id)                         |
|  |   +-- sample_type, biological_entity, strain, cell_line        |
|  +-- ImageAcquisition                                             |
|  |   +-- ImagingMethod[] (name, fbbi_id)                          |
|  |   +-- instruments, magnification, channels                     |
|  +-- Publication[] (doi, pubmed_id, pmc_id, title, year)          |
|  +-- Author[] (name, orcid, email, Affiliation[])                 |
|  +-- Funding[] (funder, grant_id)                                 |
+-----------------------------+-------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
|                      JSON Files                                   |
|              output/ssbd.json, idr.json, bia.json                 |
+-----------------------------+-------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
|                    ElasticSearch Index                            |
|                                                                   |
|  - Full-text search on title, description, keywords               |
|  - Nested queries for organisms, imaging methods, authors         |
|  - Aggregations for faceted browsing                              |
+-----------------------------+-------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
|                    FastAPI (/search)                              |
|                                                                   |
|  - Free-text search with filters                                  |
|  - Facets: source, organism, imaging method, year                 |
|  - OpenAPI docs at /docs                                          |
+-------------------------------------------------------------------+
```

## Unified Schema

The schema normalizes metadata across sources while preserving source-specific details:

### Core Fields (all sources)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Prefixed identifier (e.g., `idr:idr0164`, `ssbd:000479`, `bia:S-BIAD2455`) |
| `source` | enum | `IDR`, `SSBD`, `BIA` |
| `source_url` | string | Link to original study page |
| `title` | string | Study title |
| `description` | string | Study description |
| `license` | string | Data license |
| `release_date` | date | Publication date |
| `biosample` | object | Organism, sample type, biological entity |
| `image_acquisition` | object | Imaging methods, instruments |

### Extended Fields (some sources)

| Field | Sources | Description |
|-------|---------|-------------|
| `authors` | IDR, BIA | Authors with affiliations, ORCIDs |
| `publications` | All | DOIs, PubMed IDs, titles |
| `funding` | BIA | Funder and grant IDs |
| `keywords` | BIA, SSBD | Searchable keywords |
| `file_count` | BIA | Number of files |
| `total_size_bytes` | BIA | Dataset size |

### Ontology Support

Where available, ontology identifiers are preserved:

- **Organisms**: NCBI Taxonomy IDs (e.g., `9606` for Homo sapiens)
- **Imaging Methods**: FBbi IDs (e.g., `FBbi:00000246` for confocal microscopy)
- **Affiliations**: ROR IDs for research organizations

## Project Structure

```
src/gide_search/
    __init__.py
    schema.py           # Pydantic models for unified schema
    cli.py              # Typer CLI commands
    indexer.py          # ElasticSearch indexing
    api.py              # FastAPI search endpoint
    transformers/
        __init__.py
        ssbd.py         # SSBD TTL -> Study
        idr.py          # IDR TSV -> Study
        bia.py          # BIA API -> Study

resources/
    ssbd/               # SSBD ontology files
        ssbd_instances.ttl
        ssbd_meta.ttl
    idr/                # IDR metadata (git clone)

output/                 # Transformed JSON files
    ssbd.json
    idr.json
    bia.json
```

## API Server

Run the search API:

```bash
# Start the server
uv run gide-search serve

# With custom host/port
uv run gide-search serve --host 0.0.0.0 --port 8080

# Development mode with auto-reload
uv run gide-search serve --reload
```

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /search` | Search with facets |
| `GET /study/{id}` | Get single study |
| `GET /docs` | OpenAPI documentation |

### Search Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Free-text search query |
| `source` | string[] | Filter by source (IDR, SSBD, BIA) |
| `organism` | string[] | Filter by organism name |
| `imaging_method` | string[] | Filter by imaging method |
| `year_from` | int | Filter by release year (from) |
| `year_to` | int | Filter by release year (to) |
| `size` | int | Results per page (1-100, default 20) |
| `offset` | int | Result offset for pagination |

Example:
```bash
curl "http://localhost:8000/search?q=fluorescence&source=BIA&size=5"
```

## Local Infrastructure

Start ElasticSearch locally using colima (macOS):

```bash
# Start colima (container runtime)
colima start

# Run ElasticSearch
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# Verify it's running
curl http://localhost:9200/_cluster/health

# Stop when done
docker stop elasticsearch
colima stop
```

## Development

```bash
# Run with uv
uv run gide-search --help

# Run Python interactively
uv run python
```

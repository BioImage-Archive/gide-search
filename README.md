# gide-search

A unified search system for biological imaging databases. Aggregates study-level metadata from multiple sources into a single searchable index.


## Installation

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

To run, requires some local continer runtime with docker, e.g. colima. 

## Overview

There are two main areas of the package:
- A data transformation pipeline, to create ro-crates, produce a list of elastic search documents, and index them.
- Code to control an elasticsearch index, and an api to serve data from elasticsearch.

## Data transformation

There are three steps to get data into elastic search:
1. Transforming data from a source repository into a valid GIDE ro-crate.
2. Transforming a GIDE ro-crate into a list of indexable documents
3. Indexing these with elasticsearch

You can see the list of commands by running
```bash
uv run gide-search data --help
```

A typical sequence could look like:

```bash
uv run gide-search data generate-bia-rocrate
uv run gide-search data transform-to-index 
```
This should generate ro-crates under output/ro-crate/ and an index document under output/index/.

If elasticsearch is running (commands for that below) you can index this with:
```bash
uv run gide-search data index
```


## ElasticSearch

A local ElasticSearch instance is required for indexing and searching. 

**Quick start (macOS with colima):**

Start your local container runtime, e.g. for colima:
```bash
colima start
```

Then you can start elastisearch with:

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  -e "http.cors.enabled=true" \
  -e "http.cors.allow-origin=http://localhost:1358" \
  -e "http.cors.allow-headers=X-Requested-With,X-Auth-Token,Content-Type,Content-Length,Authorization" \
  -e "http.cors.allow-credentials=true" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

These settings are used so you can also start Dejavu with the following command. Dejava is a browser based elasticsearch inspector.
```bash
docker run -p 1358:1358 -d appbaseio/dejavu
```
You can connect to ES with url: http://elastic:test@localhost:9200 and index: *, though note this will fail if no data has been indexed. 
To index the data in output/index/index.json:
```bash
uv run gide-search data index
```

To search using elasticsearch directly (e.g. for debugging), you can use:
```bash
uv run gide-search search "mouse"
```


## API

To setup the api, run:

```bash
uv run gide-search serve
```

You can then search it with cli command:
```bash
uv run gide-search search-api "mouse"
```

or directly use the endpoints


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
| `publisher` | string[] | Filter by source (IDR, SSBD, BIA) |
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

  docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  -e "http.cors.enabled=true" \
  -e "http.cors.allow-origin=http://localhost:1358" \
  -e "http.cors.allow-headers=X-Requested-With,X-Auth-Token,Content-Type,Content-Length,Authorization" \
  -e "http.cors.allow-credentials=true" \
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

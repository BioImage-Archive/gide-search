# GIDE-Search Documentation

Documentation for the GIDE-Search unified biological imaging database search system.

## Documents

### [Setup Notes](setup-notes.md)
Complete setup guide from scratch, including:
- Installing dependencies
- Downloading data sources (IDR, BIA, SSBD)
- **ElasticSearch installation and configuration** (the tricky parts!)
- Data transformation
- Indexing
- API server setup

**Start here** if you're setting up GIDE-Search for the first time.

### [ElasticSearch Troubleshooting](elasticsearch-troubleshooting.md)
Detailed troubleshooting guide for ElasticSearch issues:
- Out of memory errors (exit code 137)
- Configuration conflicts
- Lock file issues
- Multiple process conflicts
- Complete reset procedures
- Performance tuning

**Use this** when ElasticSearch isn't behaving.

### [API Usage Guide](api-usage.md)
How to use the GIDE-Search REST API:
- Available endpoints
- Search parameters and filters
- Example queries
- Response formats
- Integration examples

**Read this** to integrate with the API.

## Quick Start

For a working system, you need:

1. **ElasticSearch** running on port 9200
2. **Data sources** transformed and indexed
3. **API server** running on port 8080

See [Setup Notes](setup-notes.md) for step-by-step instructions.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Sources                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │   IDR    │  │   BIA    │  │   SSBD   │                 │
│  │ (local)  │  │  (API)   │  │ (GitHub) │                 │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                 │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
        ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                  Transformers                               │
│     (Convert to unified ImagingDatasetSummary schema)      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
                ┌───────────────┐
                │  output/*.json │
                └───────┬────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   ElasticSearch                             │
│     (Full-text search with faceted queries)                │
│               Port: 9200                                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Server                            │
│        (REST API with OpenAPI documentation)               │
│               Port: 8080                                    │
└─────────────────────────────────────────────────────────────┘
```

## Current Data

- **Total studies**: 185
  - BIA: 100
  - SSBD: 67
  - IDR: 18
- **Top organisms**: Mus musculus (70), Homo sapiens (61)
- **Top methods**: fluorescence microscopy (57), confocal (48)

## Key Files

- `src/gide_search/transformers/` - Data source transformers
- `src/gide_search/indexer.py` - ElasticSearch indexing logic
- `src/gide_search/api.py` - FastAPI application
- `src/gide_search/cli.py` - Command-line interface
- `output/` - Transformed JSON data
- `resources/` - Source data files

## Common Tasks

### Search from CLI
```bash
uv run gide-search search "microscopy" -n 10
```

### View Statistics
```bash
uv run gide-search aggregations
```

### Re-index Data
```bash
uv run gide-search index output/
```

### Start API Server
```bash
uv run gide-search serve --host 0.0.0.0 --port 8080
```

### Check ElasticSearch Health
```bash
curl http://localhost:9200/_cluster/health
```

## Support

For issues related to:
- **Setup**: See [Setup Notes](setup-notes.md)
- **ElasticSearch**: See [ElasticSearch Troubleshooting](elasticsearch-troubleshooting.md)
- **API Usage**: See [API Usage Guide](api-usage.md)

## Checkpoints

If running on Sprite, checkpoints capture the entire working state:

```bash
# List checkpoints
sprite-env checkpoint list

# Restore to working state
sprite-env checkpoint restore v2
```

Checkpoint `v2` contains the fully configured system with all 3 data sources indexed.

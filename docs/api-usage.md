# GIDE-Search API Usage Guide

The GIDE-Search API provides RESTful access to search biological imaging datasets from BIA, IDR, and SSBD.

## Base URL

When running locally:
```
http://localhost:8080
```

When running on Sprite with HTTP routing:
```
https://<your-sprite-url>
```

## Interactive Documentation

The API includes auto-generated OpenAPI/Swagger documentation:

```
http://localhost:8080/docs
```

This provides an interactive interface to test all endpoints.

## Authentication

Currently, the API does not require authentication. ElasticSearch security is disabled for local development.

## Endpoints

### Health Check

**GET** `/health`

Check API and ElasticSearch connection status.

**Response:**
```json
{
  "status": "healthy",
  "elasticsearch": "connected"
}
```

**Example:**
```bash
curl http://localhost:8080/health
```

---

### Search Studies

**GET** `/search`

Full-text search across all imaging datasets with faceted filtering.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | "" | Search query (full-text) |
| `size` | integer | 20 | Number of results (max 100) |
| `from_` | integer | 0 | Pagination offset |
| `source` | string | null | Filter by source (BIA, IDR, SSBD) |
| `organism` | string | null | Filter by organism name |
| `imaging_method` | string | null | Filter by imaging method |
| `year_from` | integer | null | Filter by release year (from) |
| `year_to` | integer | null | Filter by release year (to) |

**Response:**
```json
{
  "total": 93,
  "hits": [
    {
      "id": "bia:S-BIAD2357",
      "score": 13.41787,
      "source": "BIA",
      "source_url": "https://www.ebi.ac.uk/biostudies/bioimages/studies/S-BIAD2357",
      "title": "pan-ASLM: a high-resolution and large field-of-view light sheet microscope...",
      "description": "Expansion microscopy, a super-resolution fluorescence microscopy...",
      "organisms": ["Unknown"],
      "imaging_methods": ["Unknown"],
      "release_date": "2025-10-25",
      "file_count": null,
      "total_size_bytes": null,
      "highlights": {
        "title": "pan-ASLM: a high-resolution and large field-of-view light sheet <mark>microscope</mark>...",
        "description": ["Expansion <mark>microscopy</mark>, a super-resolution..."],
        "keywords": null
      }
    }
  ],
  "facets": {
    "sources": [
      {"key": "BIA", "count": 77},
      {"key": "IDR", "count": 16}
    ],
    "organisms": [
      {"key": "Homo sapiens", "count": 46},
      {"key": "Mus musculus", "count": 19}
    ],
    "imaging_methods": [
      {"key": "fluorescence microscopy", "count": 41},
      {"key": "confocal microscopy", "count": 23}
    ],
    "years": [
      {"key": "2025", "count": 77},
      {"key": "2016", "count": 8}
    ]
  }
}
```

**Examples:**

```bash
# Simple text search
curl "http://localhost:8080/search?q=microscopy&size=10"

# Filter by source
curl "http://localhost:8080/search?q=cell&source=BIA"

# Filter by organism
curl "http://localhost:8080/search?q=imaging&organism=Homo+sapiens"

# Filter by imaging method
curl "http://localhost:8080/search?imaging_method=confocal+microscopy"

# Filter by year range
curl "http://localhost:8080/search?q=neuron&year_from=2020&year_to=2025"

# Combine multiple filters
curl "http://localhost:8080/search?q=fluorescence&source=SSBD&organism=Mus+musculus&size=20"

# Pagination
curl "http://localhost:8080/search?q=cell&size=20&from_=20"
```

---

### Get Study by ID

**GET** `/study/{id}`

Retrieve a specific study by its unique identifier.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Study ID (e.g., "bia:S-BIAD2357", "idr:idr0001") |

**Response:**
```json
{
  "id": "bia:S-BIAD2443",
  "source": "BIA",
  "source_url": "https://www.ebi.ac.uk/biostudies/bioimages/studies/S-BIAD2443",
  "title": "Cell-DINO: Self-Supervised Image-based Embeddings for Cell Fluorescent Microscopy",
  "description": "Reprocessed images from LINCS image dataset and Human Protein Atlas for training deep learning models.",
  "biosamples": [
    {
      "organism": [
        {
          "scientific_name": "Homo sapiens",
          "common_name": null,
          "ncbi_taxon_id": 9606
        }
      ],
      "sample_type": null,
      "biological_entity_description": null
    }
  ],
  "image_acquisition_protocols": [
    {
      "methods": [
        {"name": "fluorescence microscopy", "fbbi_id": null},
        {"name": "confocal microscopy", "fbbi_id": null}
      ]
    }
  ],
  "publications": [],
  "authors": [],
  "keywords": ["Microscopy"],
  "release_date": "2025-11-26",
  "file_count": 141,
  "total_size_bytes": 1425925481854
}
```

**Examples:**

```bash
# Get BIA study
curl "http://localhost:8080/study/bia:S-BIAD2443"

# Get IDR study
curl "http://localhost:8080/study/idr:idr0001"

# Get SSBD study
curl "http://localhost:8080/study/ssbd:ssbd-dataset-141-Fig1a_FIB-SEM_somatosensory"
```

---

### Aggregations

**GET** `/aggregations`

Get aggregated statistics across all indexed studies.

**Response:**
```json
{
  "total": 185,
  "by_source": {
    "BIA": 100,
    "SSBD": 67,
    "IDR": 18
  },
  "top_organisms": [
    {"name": "Mus musculus", "count": 70},
    {"name": "Homo sapiens", "count": 61}
  ],
  "top_imaging_methods": [
    {"name": "fluorescence microscopy", "count": 57},
    {"name": "confocal microscopy", "count": 48}
  ]
}
```

**Example:**
```bash
curl "http://localhost:8080/aggregations"
```

## Search Query Syntax

### Simple Queries

Just type what you're looking for:

```bash
curl "http://localhost:8080/search?q=neuron"
```

### Phrase Queries

Use quotes for exact phrases:

```bash
curl "http://localhost:8080/search?q=\"confocal+microscopy\""
```

### Boolean Operators

Combine terms with AND, OR, NOT:

```bash
# Both terms
curl "http://localhost:8080/search?q=cell+AND+microscopy"

# Either term
curl "http://localhost:8080/search?q=neuron+OR+brain"

# Exclude term
curl "http://localhost:8080/search?q=imaging+NOT+electron"
```

### Field-Specific Queries

Search in specific fields:

```bash
# Search in title only
curl "http://localhost:8080/search?q=title:fluorescence"

# Search by source
curl "http://localhost:8080/search?q=source:SSBD"

# Search by organism (in nested field)
curl "http://localhost:8080/search?q=Homo+sapiens"
```

### Wildcards

Use `*` for wildcard matching:

```bash
# All documents
curl "http://localhost:8080/search?q=*&size=100"

# Prefix match
curl "http://localhost:8080/search?q=micro*"
```

## Response Format

### Hit Object

Each search result (hit) contains:

- `id`: Unique identifier (prefixed with source)
- `score`: Relevance score
- `source`: Data source (BIA, IDR, SSBD)
- `source_url`: Link to original study
- `title`: Study title
- `description`: Study description
- `organisms`: List of organism names
- `imaging_methods`: List of imaging method names
- `release_date`: Publication/release date
- `file_count`: Number of files (if available)
- `total_size_bytes`: Total data size (if available)
- `highlights`: Matching text snippets with `<mark>` tags

### Facets Object

Aggregated counts for filtering:

- `sources`: Studies per source
- `organisms`: Studies per organism
- `imaging_methods`: Studies per method
- `years`: Studies per year

## Pagination

Use `size` and `from_` for pagination:

```bash
# Page 1 (results 0-19)
curl "http://localhost:8080/search?q=cell&size=20&from_=0"

# Page 2 (results 20-39)
curl "http://localhost:8080/search?q=cell&size=20&from_=20"

# Page 3 (results 40-59)
curl "http://localhost:8080/search?q=cell&size=20&from_=40"
```

Maximum `size` is 100 per request.

## Error Handling

### 404 Not Found

When a study ID doesn't exist:

```json
{
  "detail": "Study not found"
}
```

### 500 Internal Server Error

When ElasticSearch is unreachable:

```json
{
  "detail": "ElasticSearch connection error"
}
```

## Integration Examples

### Python

```python
import requests

# Search
response = requests.get(
    "http://localhost:8080/search",
    params={
        "q": "fluorescence microscopy",
        "source": "BIA",
        "size": 10
    }
)
results = response.json()

for hit in results["hits"]:
    print(f"{hit['id']}: {hit['title']}")

# Get specific study
study = requests.get("http://localhost:8080/study/bia:S-BIAD2443").json()
print(study["description"])
```

### JavaScript

```javascript
// Search
fetch('http://localhost:8080/search?q=microscopy&size=10')
  .then(response => response.json())
  .then(data => {
    console.log(`Total results: ${data.total}`);
    data.hits.forEach(hit => {
      console.log(`${hit.id}: ${hit.title}`);
    });
  });

// Get specific study
fetch('http://localhost:8080/study/idr:idr0001')
  .then(response => response.json())
  .then(study => {
    console.log(study.description);
  });
```

### curl with jq

```bash
# Pretty-print search results
curl -s "http://localhost:8080/search?q=cell&size=5" | jq '.hits[] | {id, title, score}'

# Extract just the IDs
curl -s "http://localhost:8080/search?q=microscopy" | jq -r '.hits[].id'

# Get facet counts
curl -s "http://localhost:8080/search?q=*" | jq '.facets.sources'
```

## Rate Limiting

Currently, there are no rate limits. For production use, consider implementing rate limiting based on your requirements.

## CORS

CORS is enabled by default for all origins. Modify `src/gide_search/api.py` to restrict origins if needed.

## Performance Tips

1. **Use filters instead of text search** when possible (faster)
2. **Limit result size** to what you actually need
3. **Use facets** to understand data distribution before searching
4. **Cache common queries** on the client side
5. **Use pagination** instead of requesting large result sets

## Support

For API issues, check:
1. ElasticSearch is running: `curl http://localhost:9200/_cluster/health`
2. API server logs: `tail /.sprite/logs/services/gide-api.log`
3. Test with simple query: `curl http://localhost:8080/health`

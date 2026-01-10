# GIDE-Search Setup Notes

## Overview

This document covers the complete setup process for the GIDE-Search biological imaging database search system, including all the tricky bits encountered during ElasticSearch configuration.

## Prerequisites

- Python 3.11+ with `uv` package manager
- ElasticSearch 8.x
- Sufficient memory (at least 1GB available for ElasticSearch)

## 1. Project Dependencies

```bash
uv sync
```

This installs all Python dependencies including:
- FastAPI for the API server
- ElasticSearch Python client
- Typer for CLI
- Data transformers for BIA, IDR, and SSBD

## 2. Data Source Resources

### IDR (Image Data Resource)

Clone the IDR metadata repository:

```bash
mkdir -p resources
git clone https://github.com/IDR/idr-metadata.git resources/idr
```

This provides 19 study files from the Image Data Resource.

### BIA (BioImage Archive)

No local files needed - data is fetched directly from the BIA API during transformation.

### SSBD (Systems Science of Biological Dynamics)

**Important:** The URLs in the original README are outdated (404 errors). Use the GitHub repository instead:

```bash
mkdir -p resources/ssbd
curl -L -o resources/ssbd/ssbd_instances.ttl \
  https://raw.githubusercontent.com/openssbd/ssbd-ontology/main/ontology/ssbd_instances.ttl
```

Source: https://github.com/openssbd/ssbd-ontology/tree/main/ontology

## 3. ElasticSearch Setup (The Fiddly Parts)

### Installation on Sprite/Ubuntu

```bash
# Add ElasticSearch GPG key
curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch | \
  sudo gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg

# Add repository
echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] \
  https://artifacts.elastic.co/packages/8.x/apt stable main" | \
  sudo tee /etc/apt/sources.list.d/elastic-8.x.list

# Install
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y elasticsearch
```

### Critical Configuration Issues & Solutions

#### Issue 1: Memory Constraints

**Problem:** Default ElasticSearch heap size is ~4GB, which is too much for containerized environments.

**Solution:** Create custom heap configuration:

```bash
sudo mkdir -p /etc/elasticsearch/jvm.options.d
sudo tee /etc/elasticsearch/jvm.options.d/heap.options > /dev/null << 'EOF'
# Set heap size to 512MB
-Xms512m
-Xmx512m
EOF
```

#### Issue 2: Configuration Conflicts

**Problem:** The default elasticsearch.yml contains `cluster.initial_master_nodes` which conflicts with `discovery.type: single-node`.

**Error:**
```
setting [cluster.initial_master_nodes] is not allowed when [discovery.type] is set to [single-node]
```

**Solution:** Comment out the conflicting setting:

```bash
# Find and comment out cluster.initial_master_nodes
sudo sed -i 's/^cluster.initial_master_nodes:/#cluster.initial_master_nodes:/' \
  /etc/elasticsearch/elasticsearch.yml
```

#### Issue 3: Security Configuration Conflict

**Problem:** Multiple `xpack.security.enabled` settings cause parsing errors.

**Solution:** Comment out the original setting and add our own:

```bash
# Comment out original xpack.security.enabled (usually around line 92)
sudo sed -i '92s/^/#/' /etc/elasticsearch/elasticsearch.yml

# Add configuration at the end
sudo tee -a /etc/elasticsearch/elasticsearch.yml > /dev/null << 'EOF'

# Sprite configuration
discovery.type: single-node
xpack.security.enabled: false
network.host: 0.0.0.0
http.port: 9200
EOF
```

#### Issue 4: Lock Files from Previous Runs

**Problem:** If ElasticSearch crashes or is killed improperly, lock files remain and prevent restart.

**Solution:** Clean lock files before starting:

```bash
sudo rm -f /var/lib/elasticsearch/node.lock
```

### Running ElasticSearch as a Sprite Service

Create a startup script:

```bash
cat > /tmp/start-elasticsearch.sh << 'EOF'
#!/bin/bash
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch
EOF
chmod +x /tmp/start-elasticsearch.sh
```

Start as a Sprite service (requires `jq`):

```bash
sudo apt-get install -y jq
sprite-env services create elasticsearch --cmd /tmp/start-elasticsearch.sh --duration 60s
```

### Verify ElasticSearch is Running

```bash
curl http://localhost:9200/_cluster/health
```

Expected response:
```json
{
  "cluster_name": "elasticsearch",
  "status": "green",
  "number_of_nodes": 1,
  ...
}
```

## 4. Data Transformation

Transform each data source to the unified schema:

```bash
# IDR - 19 studies
uv run gide-search transform-idr resources/idr

# BIA - 100 studies
uv run gide-search transform-bia -n 100

# SSBD - 67 studies
uv run gide-search transform-ssbd resources/ssbd/ssbd_instances.ttl
```

This creates JSON files in the `output/` directory.

## 5. Indexing into ElasticSearch

Index all transformed data:

```bash
uv run gide-search index output/
```

Expected output:
```
Indexed 186 studies (0 errors)
Total documents in index: 185
```

Note: The slight difference (186 indexed, 185 total) is due to duplicate handling.

### Verify Indexing

```bash
uv run gide-search aggregations
```

Should show:
- **Total indexed: 185**
- BIA: 100
- SSBD: 67
- IDR: 18

## 6. API Server Setup

### Create API Startup Script

```bash
cat > /tmp/start-gide-api.sh << 'EOF'
#!/bin/bash
cd /home/sprite/gide-search
uv run gide-search serve --host 0.0.0.0 --port 8080
EOF
chmod +x /tmp/start-gide-api.sh
```

### Start API as Sprite Service

```bash
sprite-env services create gide-api \
  --cmd /tmp/start-gide-api.sh \
  --http-port 8080 \
  --duration 30s
```

### Verify API

```bash
# Health check
curl http://localhost:8080/health

# Test search
curl "http://localhost:8080/search?q=microscopy&size=3"

# API documentation
# Open in browser: http://<your-sprite-url>/docs
```

## 7. Testing Search Functionality

### CLI Search

```bash
# Search by keyword
uv run gide-search search "cell" -n 10

# Search all documents (wildcard)
uv run gide-search search "*" -n 150

# Filter by source
uv run gide-search search "source:SSBD" -n 5
```

### API Search

```bash
# Basic search
curl "http://localhost:8080/search?q=fluorescence&size=10"

# With filters
curl "http://localhost:8080/search?q=cell&source=BIA&organism=Homo+sapiens"

# Get specific study
curl "http://localhost:8080/study/bia:S-BIAD2443"
```

## Common Issues & Solutions

### ElasticSearch Won't Start

1. **Check logs:**
   ```bash
   tail -100 /.sprite/logs/services/elasticsearch.log
   ```

2. **Common causes:**
   - Memory issues: Reduce heap size further if needed
   - Configuration conflicts: Review `/etc/elasticsearch/elasticsearch.yml`
   - Lock files: Remove `/var/lib/elasticsearch/node.lock`
   - Port conflict: Check if something else is on port 9200

### Search Returns 0 Results

1. **Verify index exists:**
   ```bash
   curl http://localhost:9200/gide-datasets/_count
   ```

2. **Check ElasticSearch health:**
   ```bash
   curl http://localhost:9200/_cluster/health
   ```

3. **Re-index if needed:**
   ```bash
   uv run gide-search index output/
   ```

### API Server Not Accessible

1. **Check service status:**
   ```bash
   sprite-env services list
   ```

2. **View API logs:**
   ```bash
   tail -50 /.sprite/logs/services/gide-api.log
   ```

3. **Verify port binding:**
   ```bash
   curl http://localhost:8080/health
   ```

## Final System Status

After successful setup:

- **ElasticSearch:** Running on port 9200, green status
- **API Server:** Running on port 8080, accessible via Sprite URL
- **Total Documents:** 185 studies
  - BIA: 100 studies
  - SSBD: 67 studies
  - IDR: 18 studies
- **Search:** Fully functional with faceted search, highlighting, and aggregations

## Checkpoint

If using Sprite, create a checkpoint to save this working state:

```bash
sprite-env checkpoint create "SSBD data added, all 3 sources indexed and searchable via API"
```

This allows you to restore to this exact state later if needed.

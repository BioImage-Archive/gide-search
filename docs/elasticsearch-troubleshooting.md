# ElasticSearch Troubleshooting Guide

This guide covers the specific issues encountered during GIDE-Search ElasticSearch setup and their solutions.

## Quick Diagnostics

### Check ElasticSearch Status

```bash
# Service status
sprite-env services list

# Cluster health
curl http://localhost:9200/_cluster/health

# Check recent logs
tail -50 /.sprite/logs/services/elasticsearch.log
```

## Issue #1: Out of Memory (Exit Code 137)

### Symptoms
- ElasticSearch process dies immediately
- Log shows: `exit_code: 137` or `killed`
- System logs show OOM killer activity

### Root Cause
Default ElasticSearch heap size (~4GB) exceeds available container memory.

### Solution

Create custom JVM heap configuration:

```bash
sudo mkdir -p /etc/elasticsearch/jvm.options.d
sudo tee /etc/elasticsearch/jvm.options.d/heap.options > /dev/null << 'EOF'
# Set heap size to 512MB
-Xms512m
-Xmx512m
EOF
```

Then restart ElasticSearch.

### Verification

Check logs for heap size confirmation:

```bash
tail /.sprite/logs/services/elasticsearch.log | grep -i "xms\|xmx"
```

Should show: `-Xms512m, -Xmx512m`

## Issue #2: Configuration Conflict (cluster.initial_master_nodes)

### Symptoms
- Error: `setting [cluster.initial_master_nodes] is not allowed when [discovery.type] is set to [single-node]`
- ElasticSearch exits immediately with code 1

### Root Cause
The default `elasticsearch.yml` contains both:
- `discovery.type: single-node` (for our single-node setup)
- `cluster.initial_master_nodes: ["node-1"]` (for multi-node clusters)

These settings are mutually exclusive.

### Solution

Comment out the conflicting setting:

```bash
# Find the line with cluster.initial_master_nodes
sudo grep -n "cluster.initial_master_nodes" /etc/elasticsearch/elasticsearch.yml

# Comment it out (adjust line number as needed)
sudo sed -i 's/^cluster.initial_master_nodes:/#cluster.initial_master_nodes:/' \
  /etc/elasticsearch/elasticsearch.yml
```

### Verification

```bash
sudo grep "cluster.initial_master_nodes" /etc/elasticsearch/elasticsearch.yml
```

All occurrences should be commented out (start with `#`).

## Issue #3: Duplicate xpack.security.enabled Settings

### Symptoms
- Error: duplicate key `xpack.security.enabled`
- Configuration parse failure

### Root Cause
The default config already has `xpack.security.enabled: true`, and we're trying to add our own setting.

### Solution

Comment out the original setting before adding ours:

```bash
# Find the original setting (usually around line 92)
sudo grep -n "xpack.security.enabled" /etc/elasticsearch/elasticsearch.yml

# Comment out the original (example for line 92)
sudo sed -i '92s/^/#/' /etc/elasticsearch/elasticsearch.yml

# Now add our configuration at the end
sudo tee -a /etc/elasticsearch/elasticsearch.yml > /dev/null << 'EOF'

# Sprite configuration
discovery.type: single-node
xpack.security.enabled: false
network.host: 0.0.0.0
http.port: 9200
EOF
```

### Verification

```bash
sudo cat /etc/elasticsearch/elasticsearch.yml | grep -n "xpack.security.enabled"
```

Should show the original commented out and only one active setting.

## Issue #4: Node Lock Files

### Symptoms
- Error: `Lock held by another program: /var/lib/elasticsearch/node.lock`
- `LockObtainFailedException`
- Can't start even though no other instance is running

### Root Cause
Previous ElasticSearch process was killed without clean shutdown, leaving lock files.

### Solution

Remove stale lock files:

```bash
# Remove main lock file
sudo rm -f /var/lib/elasticsearch/node.lock

# Remove node-specific locks if they exist
sudo rm -f /var/lib/elasticsearch/nodes/*/node.lock
```

For a complete clean start:

```bash
# Stop service
sprite-env services delete elasticsearch

# Kill any lingering processes
sudo pkill -9 -f elasticsearch

# Clean data and locks
sudo rm -rf /var/lib/elasticsearch/nodes

# Restart
sprite-env services create elasticsearch --cmd /tmp/start-elasticsearch.sh --duration 60s
```

## Issue #5: Multiple ElasticSearch Processes

### Symptoms
- Multiple elasticsearch processes in `ps aux`
- Port already in use errors
- Conflicting lock attempts

### Root Cause
Previous instances not properly terminated before starting new ones.

### Solution

Kill all ElasticSearch processes and start fresh:

```bash
# Stop sprite service
sprite-env services delete elasticsearch

# Force kill all elasticsearch processes
sudo pkill -9 -f elasticsearch

# Wait a moment
sleep 2

# Verify none are running
ps aux | grep elasticsearch | grep -v grep

# Clean locks
sudo rm -f /var/lib/elasticsearch/node.lock

# Start fresh
sprite-env services create elasticsearch --cmd /tmp/start-elasticsearch.sh --duration 60s
```

## Issue #6: Sprite Service Already Running Error

### Symptoms
- `Service already running with that command` when trying to create service
- Service shows as running but isn't responding

### Root Cause
Sprite's service registry thinks the service is running, but it may have crashed.

### Solution

Force delete and recreate:

```bash
# Stop via API
curl -X POST --unix-socket /.sprite/api.sock \
  http://localhost/v1/services/elasticsearch/stop

# Delete via API
curl -X DELETE --unix-socket /.sprite/api.sock \
  http://localhost/v1/services/elasticsearch

# Wait and recreate
sleep 2
sprite-env services create elasticsearch --cmd /tmp/start-elasticsearch.sh --duration 60s
```

## Complete Reset Procedure

If all else fails, here's a complete reset:

```bash
#!/bin/bash

# 1. Stop and delete service
curl -X DELETE --unix-socket /.sprite/api.sock http://localhost/v1/services/elasticsearch 2>/dev/null || true
sprite-env services delete elasticsearch 2>/dev/null || true

# 2. Kill all processes
sudo pkill -9 -f elasticsearch

# 3. Clean data directories
sudo rm -rf /var/lib/elasticsearch/nodes
sudo rm -f /var/lib/elasticsearch/node.lock
sudo rm -rf /var/log/elasticsearch/*

# 4. Verify configuration
echo "Checking configuration..."
sudo cat /etc/elasticsearch/elasticsearch.yml | grep -E "discovery.type|xpack.security.enabled|cluster.initial_master_nodes"

# 5. Wait
sleep 3

# 6. Start fresh
sprite-env services create elasticsearch --cmd /tmp/start-elasticsearch.sh --duration 60s

# 7. Wait for startup
sleep 15

# 8. Test
curl http://localhost:9200/_cluster/health
```

## Monitoring ElasticSearch

### Watch Startup Logs

```bash
tail -f /.sprite/logs/services/elasticsearch.log
```

### Key Log Indicators

**Successful startup:**
- `node name [sprite]`
- `started`
- No ERROR lines

**Common errors to watch for:**
- `IllegalArgumentException` → configuration conflict
- `LockObtainFailedException` → lock file issue
- `OutOfMemoryError` → heap size too large
- `exit code 137` → OOM killer

### Health Check Loop

Wait for ElasticSearch to become healthy:

```bash
until curl -s http://localhost:9200/_cluster/health | grep -q '"status":"green"'; do
  echo "Waiting for ElasticSearch..."
  sleep 2
done
echo "ElasticSearch is healthy!"
```

## Performance Tuning

### For Larger Datasets

If indexing more than 1000 documents:

```bash
# Increase heap (if memory available)
sudo tee /etc/elasticsearch/jvm.options.d/heap.options > /dev/null << 'EOF'
-Xms1g
-Xmx1g
EOF
```

### For Faster Indexing

Temporarily disable refresh:

```bash
curl -X PUT "localhost:9200/gide-datasets/_settings" -H 'Content-Type: application/json' -d'
{
  "index": {
    "refresh_interval": "-1"
  }
}'

# Do your indexing...

# Re-enable after indexing
curl -X PUT "localhost:9200/gide-datasets/_settings" -H 'Content-Type: application/json' -d'
{
  "index": {
    "refresh_interval": "1s"
  }
}'
```

## Useful Commands Reference

```bash
# Check index stats
curl http://localhost:9200/gide-datasets/_stats?pretty

# Count documents
curl http://localhost:9200/gide-datasets/_count

# View index mapping
curl http://localhost:9200/gide-datasets/_mapping?pretty

# Delete index (careful!)
curl -X DELETE http://localhost:9200/gide-datasets

# Check all indices
curl http://localhost:9200/_cat/indices?v

# Node stats
curl http://localhost:9200/_nodes/stats?pretty
```

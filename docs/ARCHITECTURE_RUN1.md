# Run 1: Infrastructure & Architecture Design

**Status**: ✅ Complete  
**Date**: December 18, 2024

## Executive Summary

Unity will use a **flexible database architecture** supporting PostgreSQL (with TimescaleDB), MySQL, and SQLite. Redis/Valkey caching is optional but recommended. Design prioritizes homelab preferences while maintaining performance and AI-readiness.

## Database Strategy

### Primary: PostgreSQL + TimescaleDB

**Why PostgreSQL?**
- Most popular in homelabs (Docker, Nextcloud, Gitea all use it)
- Mature, reliable, well-documented
- Excellent JSON support for flexible plugin data
- Strong community and tooling

**Why TimescaleDB?**
- PostgreSQL extension (no separate database)
- Optimized for time-series data (metrics, logs)
- Automatic partitioning and compression
- Native PostgreSQL compatibility
- Query existing data with SQL

**Installation**:
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### Alternative: MySQL/MariaDB

**Support Level**: Full SQLAlchemy adapter support

**When to Use**:
- Existing MySQL infrastructure
- MariaDB preference
- Resource-constrained environments

**Trade-offs**:
- No TimescaleDB equivalent
- Use standard tables with indexes
- Slightly less efficient for time-series

### Development: SQLite

**Use Case**: Development and single-user deployments

**Limitations**:
- No concurrent writes
- Limited for production at scale
- Perfect for testing and dev

## Data Storage Architecture

### Schema Design

```sql
-- Plugin Registry
CREATE TABLE plugins (
    id UUID PRIMARY KEY,
    plugin_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    enabled BOOLEAN DEFAULT false,
    config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Plugin Metrics (TimescaleDB Hypertable)
CREATE TABLE plugin_metrics (
    time TIMESTAMPTZ NOT NULL,
    plugin_id VARCHAR(100) NOT NULL,
    metric_name VARCHAR(200) NOT NULL,
    value JSONB NOT NULL,
    tags JSONB,
    FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id)
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('plugin_metrics', 'time');

-- Plugin Status
CREATE TABLE plugin_status (
    plugin_id VARCHAR(100) PRIMARY KEY,
    last_run TIMESTAMPTZ,
    last_success TIMESTAMPTZ,
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    health_status VARCHAR(20),
    FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id)
);

-- Alerts Configuration
CREATE TABLE alerts (
    id UUID PRIMARY KEY,
    plugin_id VARCHAR(100),
    name VARCHAR(200) NOT NULL,
    condition JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id)
);

-- Alert History
CREATE TABLE alert_history (
    time TIMESTAMPTZ NOT NULL,
    alert_id UUID NOT NULL,
    triggered BOOLEAN NOT NULL,
    value JSONB,
    FOREIGN KEY (alert_id) REFERENCES alerts(id)
);

SELECT create_hypertable('alert_history', 'time');
```

### Indexes Strategy

```sql
-- Optimize common queries
CREATE INDEX idx_metrics_plugin_time ON plugin_metrics (plugin_id, time DESC);
CREATE INDEX idx_metrics_name ON plugin_metrics (metric_name);
CREATE INDEX idx_metrics_tags ON plugin_metrics USING GIN (tags);
CREATE INDEX idx_plugins_enabled ON plugins (enabled) WHERE enabled = true;
```

## Caching Architecture

### Redis/Valkey Strategy

**What to Cache**:
- Latest metric per plugin (5min TTL)
- Dashboard aggregations (1min TTL)
- Plugin status (30s TTL)
- Hot queries (configurable TTL)

**Cache Keys Pattern**:
```
unity:plugin:{plugin_id}:latest
unity:plugin:{plugin_id}:status
unity:dashboard:summary
unity:metrics:{plugin_id}:{metric}:{timestamp}
```

**Graceful Degradation**:
- Cache miss = query database
- Cache unavailable = direct database queries
- No performance critical dependencies

**Configuration**:
```yaml
cache:
  enabled: true
  type: redis  # or valkey
  host: localhost
  port: 6379
  db: 0
  ttl:
    latest_metrics: 300  # 5 minutes
    dashboard: 60        # 1 minute
    status: 30           # 30 seconds
```

## Data Collection Pipeline

### Collection Flow

```
┌──────────────┐
│   Scheduler  │
│  (APScheduler)│
└──────┬───────┘
       │
       v
┌──────────────────────┐
│  PluginManager       │
│  - Load enabled      │
│  - Schedule collect  │
└──────┬───────────────┘
       │
       v (async)
┌──────────────────────┐
│  Plugin.collect_data │
│  - Gather metrics    │
│  - Return JSON       │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  DataProcessor       │
│  - Validate          │
│  - Transform         │
│  - Enrich            │
└──────┬───────────────┘
       │
       ├─────────────────┐
       v                 v
┌─────────────┐  ┌─────────────┐
│   Cache     │  │  Database   │
│ (Optional)  │  │ (Required)  │
└─────────────┘  └─────────────┘
```

### Scheduling Strategy

**Per-Plugin Configuration**:
```python
{
    "interval": 60,  # seconds
    "timeout": 30,   # collection timeout
    "retry_count": 3,
    "retry_delay": 10
}
```

**Smart Scheduling**:
- Spread plugin collections across intervals
- Avoid thundering herd (randomize start times)
- Adaptive intervals based on error rate
- Pause on repeated failures

### Data Processing

**Validation**:
- JSON schema validation
- Required fields check
- Data type verification
- Range validation (if applicable)

**Transformation**:
- Timestamp normalization (UTC)
- Unit standardization
- NULL handling
- Data type casting

**Enrichment**:
- Add collection metadata
- Calculate derived metrics
- Tag with context (host, env, etc.)

## Data Retention

### Retention Policies

```sql
-- TimescaleDB retention policies
SELECT add_retention_policy('plugin_metrics', INTERVAL '30 days');
SELECT add_retention_policy('alert_history', INTERVAL '90 days');

-- Continuous aggregates for long-term storage
CREATE MATERIALIZED VIEW plugin_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS hour,
    plugin_id,
    metric_name,
    avg((value->>'numeric_value')::numeric) as avg_value,
    max((value->>'numeric_value')::numeric) as max_value,
    min((value->>'numeric_value')::numeric) as min_value,
    count(*) as sample_count
FROM plugin_metrics
WHERE value ? 'numeric_value'
GROUP BY hour, plugin_id, metric_name;

-- Keep hourly aggregates for 1 year
SELECT add_retention_policy('plugin_metrics_hourly', INTERVAL '1 year');
```

**User Configuration**:
```yaml
retention:
  raw_metrics: 30d
  hourly_aggregates: 1y
  daily_aggregates: 5y
  alert_history: 90d
```

## AI Ingestion Format

### Structured Data Format

**Metric JSON**:
```json
{
  "timestamp": "2024-12-18T03:52:00Z",
  "plugin_id": "docker-monitor",
  "plugin_name": "Docker Monitor",
  "metric_name": "container_stats",
  "value": {
    "containers_running": 12,
    "containers_stopped": 3,
    "images_total": 45,
    "memory_used_gb": 8.2,
    "cpu_percent": 23.5
  },
  "tags": {
    "host": "homelab-01",
    "environment": "production"
  },
  "summary": "12 containers running, 3 stopped",
  "metadata": {
    "collection_duration_ms": 145,
    "collector_version": "1.0.0"
  }
}
```

### LLM-Friendly Context

**Query Format**:
```json
{
  "query": "What's the status of my docker containers?",
  "context": {
    "timeframe": "last 1 hour",
    "plugins": ["docker-monitor"],
    "relevant_metrics": [
      {
        "time": "2024-12-18T03:52:00Z",
        "summary": "12 containers running, 3 stopped",
        "details": {...}
      }
    ]
  }
}
```

**Alert Analysis Format**:
```json
{
  "alert": "High CPU on docker host",
  "triggered_at": "2024-12-18T03:52:00Z",
  "context": {
    "current_value": 87.5,
    "threshold": 80,
    "historical_baseline": 45.2,
    "recent_trend": "increasing",
    "related_metrics": [...]
  },
  "suggestion": "Docker CPU usage is above normal..."
}
```

## Configuration System

### database.yaml
```yaml
database:
  # Type: postgresql, mysql, sqlite
  type: postgresql
  
  # TimescaleDB (PostgreSQL only)
  timeseries:
    enabled: true
    compression: true
    retention_days: 30
  
  # Connection
  host: localhost
  port: 5432
  database: unity
  username: unity_user
  password: ${UNITY_DB_PASSWORD}
  
  # Pool settings
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  
cache:
  # Type: redis, valkey, none
  type: redis
  enabled: true
  host: localhost
  port: 6379
  db: 0
  password: ${UNITY_CACHE_PASSWORD}
  
  # TTL settings
  ttl:
    latest: 300
    dashboard: 60
    status: 30

collection:
  # Default collection interval (seconds)
  default_interval: 60
  
  # Batch settings
  batch_size: 100
  batch_timeout: 5
  
  # Retry policy
  retry_count: 3
  retry_delay: 10
  retry_backoff: 2
  
  # Resource limits
  max_concurrent: 10
  collection_timeout: 30
```

## Homelab Compatibility Matrix

| Database | Support | Performance | Notes |
|----------|---------|-------------|-------|
| PostgreSQL + TimescaleDB | ⭐⭐⭐⭐⭐ | Excellent | Recommended |
| PostgreSQL (plain) | ⭐⭐⭐⭐ | Good | Works well |
| MySQL/MariaDB | ⭐⭐⭐⭐ | Good | Full support |
| SQLite | ⭐⭐⭐ | Limited | Dev only |

| Cache | Support | Performance | Notes |
|-------|---------|-------------|-------|
| Redis | ⭐⭐⭐⭐⭐ | Excellent | Default |
| Valkey | ⭐⭐⭐⭐⭐ | Excellent | Drop-in |
| None | ⭐⭐⭐ | Good | Fallback |

## Migration Path

### From SQLite to PostgreSQL
```bash
# Export data
unity export --format json --output unity_data.json

# Setup PostgreSQL + TimescaleDB
createdb unity
psql unity -c "CREATE EXTENSION timescaledb;"

# Update config
# Edit config/database.yaml

# Import data
unity import --input unity_data.json
```

### From MySQL to PostgreSQL
```bash
# Use pgloader
pgloader mysql://user:pass@localhost/unity \
         postgresql://user:pass@localhost/unity
```

## Performance Targets

- **Collection Rate**: 500 metrics/minute
- **Query Response**: <100ms (p95) with cache
- **Query Response**: <500ms (p95) without cache
- **Write Latency**: <50ms (p95)
- **Concurrent Users**: 50+
- **Data Volume**: 1M+ metrics/day

## Next Steps (Run 2)

1. Implement SQLAlchemy models
2. Create Alembic migrations
3. Add TimescaleDB detection and setup
4. Build database adapters for MySQL/SQLite
5. Implement caching layer
6. Create data processor module

---

*Infrastructure design by Matthew and Warp AI*  
*Co-Authored-By: Warp <agent@warp.dev>*

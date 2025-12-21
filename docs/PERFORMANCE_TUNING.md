# Unity Performance Tuning Guide

**Last Updated**: December 21, 2024

## Current Performance Baseline

From Run 5 testing:
- Health endpoint: ~25ms average
- Plugins list: ~35ms average
- Metrics query: ~45ms average
- Throughput: ~120 req/s
- WebSocket latency: <10ms

## Quick Wins

### 1. Adjust Plugin Collection Intervals

Reduce scheduler frequency for non-critical plugins:

```python
# In plugin registration or via API
{
    "plugin_id": "less_critical_plugin",
    "config": {
        "collection_interval": 300  # 5 minutes instead of 60s
    }
}
```

### 2. Database Connection Pooling

In `.env`:
```bash
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### 3. Enable Redis Caching

When Redis is available:
```bash
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_METRICS=300
CACHE_TTL_STATUS=60
```

### 4. Use PostgreSQL Over SQLite

For production:
```bash
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db
```

Benefits:
- Better concurrent access
- Faster queries on large datasets
- Native JSON support (JSONB)

## API Optimization

### Response Caching

The cache service (`backend/app/services/cache.py`) provides:
- Latest metrics: 5min TTL
- Dashboard data: 1min TTL
- Plugin status: 30s TTL

Configure TTL in `.env`:
```bash
CACHE_TTL_METRICS=300
CACHE_TTL_DASHBOARD=60
CACHE_TTL_STATUS=30
```

### Query Optimization

**Limit result sets**:
```bash
# Default limits already applied
GET /api/plugins/{id}/metrics?limit=100  # Max 1000
GET /api/plugins/{id}/executions?limit=50  # Max 500
```

**Use time windows**:
```bash
GET /api/plugins/{id}/metrics/history?hours=1  # Instead of 24
```

## Database Optimization

### Indexes

Current indexes (automatically created):
- `plugins.plugin_id` - Primary lookup
- `plugin_metrics.time` - Time-series queries
- `plugin_metrics.plugin_id` - Per-plugin queries
- `plugin_executions.plugin_id, started_at` - Execution history

### Data Retention

Limit historical data:

```bash
# In .env
RETENTION_DAYS=30  # Keep only last 30 days
```

**Manual cleanup**:
```sql
DELETE FROM plugin_metrics WHERE time < NOW() - INTERVAL '30 days';
DELETE FROM plugin_executions WHERE started_at < NOW() - INTERVAL '30 days';
VACUUM FULL;  # Reclaim space
```

### TimescaleDB (Optional)

For large-scale deployments:
```sql
-- Convert metrics table to hypertable
SELECT create_hypertable('plugin_metrics', 'time');

-- Add compression
ALTER TABLE plugin_metrics SET (
  timescaledb.compress,
  timescaledb.compress_orderby = 'time DESC'
);

-- Create compression policy
SELECT add_compression_policy('plugin_metrics', INTERVAL '7 days');
```

## Scheduler Optimization

### Spread Execution

Scheduler automatically spreads plugin execution:
- Plugins execute at staggered intervals
- Prevents thundering herd problem

### Disable Unused Plugins

```bash
curl -X POST http://localhost:8000/api/plugins/{id}/enable \
  -d '{"enabled": false}'
```

### Adjust Intervals

```bash
# In .env
INFRASTRUCTURE_COLLECTION_MINUTES=15  # Default: 5
CONTAINER_SCAN_INTERVAL_HOURS=12      # Default: 6
```

## Resource Limits

### Docker Compose

```yaml
services:
  backend:
    cpus: '2.0'
    mem_limit: 2g
    mem_reservation: 512m
  
  db:
    cpus: '2.0'
    mem_limit: 1g
    mem_reservation: 256m
```

### Python Worker Processes

For high load (requires gunicorn):
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## Monitoring Performance

### Enable Metrics

```bash
# In .env
ENABLE_PERFORMANCE_METRICS=true
```

### Check Slow Queries

```bash
# PostgreSQL slow query log
docker-compose exec db psql -U homelab_user homelab_db -c "
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;"
```

### Monitor API Response Times

```bash
# Run performance tests
cd backend
pytest tests/test_performance.py -v -s
```

## Scaling Strategies

### Horizontal Scaling

**Load Balancer + Multiple Backends**:
```yaml
# docker-compose.yml
services:
  backend-1:
    <<: *backend-common
    container_name: homelab-backend-1
  
  backend-2:
    <<: *backend-common
    container_name: homelab-backend-2
  
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "8000:80"
```

**nginx.conf**:
```nginx
upstream backend {
    least_conn;
    server backend-1:8000;
    server backend-2:8000;
}

server {
    location / {
        proxy_pass http://backend;
    }
}
```

### Database Scaling

**Read Replicas**:
- Primary for writes
- Replicas for read queries
- Route /metrics/ queries to replicas

**Connection Pooling**:
```python
# In backend/app/core/database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Check connection health
    pool_recycle=3600    # Recycle every hour
)
```

## Performance Testing

### Load Testing

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Test API
hey -n 1000 -c 50 http://localhost:8000/api/plugins

# Test WebSocket
# Use custom script or tool like artillery
```

### Profiling

```python
# Add to specific endpoints for profiling
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# ... endpoint logic ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumtime')
stats.print_stats(10)
```

## Troubleshooting Slow Performance

### Symptoms & Solutions

**Slow API responses (>500ms)**:
- Check database connection pool exhaustion
- Enable caching
- Reduce metrics query result limits
- Check for slow database queries

**High memory usage**:
- Reduce plugin collection frequency
- Implement data retention policy
- Check for memory leaks in custom plugins
- Increase container memory limits

**High CPU usage**:
- Reduce number of active plugins
- Increase collection intervals
- Check for inefficient plugin code
- Scale horizontally

**Database growing too large**:
- Implement retention policy
- Enable compression (TimescaleDB)
- Run VACUUM regularly
- Archive old data

## Best Practices

1. **Start with defaults** - Only optimize if needed
2. **Measure first** - Use performance tests before/after
3. **One change at a time** - Isolate performance improvements
4. **Monitor continuously** - Track metrics over time
5. **Document changes** - Note what worked and what didn't

## Performance Checklist

- [ ] PostgreSQL instead of SQLite
- [ ] Database connection pooling configured
- [ ] Redis caching enabled (optional)
- [ ] Plugin collection intervals optimized
- [ ] Data retention policy implemented
- [ ] Unused plugins disabled
- [ ] Resource limits set in docker-compose
- [ ] Slow query monitoring enabled
- [ ] Performance tests passing
- [ ] API response times <200ms P95

---

**Current Status**: Excellent baseline performance (Run 5 results)  
**Optimization**: Only needed for >100 plugins or >1000 req/min

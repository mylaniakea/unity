# Dashboard & Visualization System

Comprehensive real-time monitoring dashboard for Unity homelab platform.

## Overview

The Dashboard system provides unified visualization of metrics, alerts, plugin health, and infrastructure status through a modern, responsive UI with automatic refresh capabilities.

### Features

- **Real-time Metrics**: Live CPU, memory, disk, and network statistics
- **Alert Status**: Visual indicators for active alerts by severity
- **Plugin Health**: Grid view of all monitoring plugins with status indicators
- **Infrastructure Overview**: Servers, storage, and database health
- **Historical Charts**: Time-series visualization with configurable time ranges (1h, 6h, 24h, 7d)
- **Per-Plugin Metrics**: Detailed metric views for individual plugins
- **Auto-refresh**: Configurable polling intervals (default 30s)
- **Dark Mode**: Full dark mode support for all visualizations

## Architecture

### Backend Components

#### Metrics Service (`app/services/monitoring/metrics_service.py`)

Core aggregation service providing unified access to metrics:

**Functions:**
- `get_dashboard_metrics()` - Aggregate latest CPU, memory, disk, network metrics
- `get_plugin_metrics_summary()` - Plugin execution status and freshness
- `get_alert_summary()` - Alert counts by severity + recent alerts
- `get_infrastructure_health()` - Server/storage/database health
- `get_metric_history()` - Time-series data for specific metrics
- `get_multi_metric_history()` - Batch fetch multiple metric histories

#### Dashboard Router (`app/routers/monitoring/dashboard.py`)

REST API endpoints for dashboard data:

**Endpoints:**
1. `GET /api/v1/monitoring/dashboard/overview` - Complete dashboard data
2. `GET /api/v1/monitoring/dashboard/metrics/history?time_range={1h|6h|24h|7d}` - Historical metrics
3. `GET /api/v1/monitoring/dashboard/plugins/health?category={category}` - Plugin health status
4. `GET /api/v1/monitoring/dashboard/metrics/{plugin_id}/{metric_name}/history` - Single metric history

### Frontend Components

#### Core Components (`frontend/src/components/dashboard/`)

1. **MetricChart** - Reusable Chart.js line/bar chart
   - Props: title, data, color, unit, chartType, height
   - Features: Dark mode, tooltips, auto-scaling, empty states

2. **AlertStatusCard** - Alert summary with severity breakdown
   - Shows counts by severity (critical/warning/info)
   - Lists recent unresolved alerts (last 5)
   - Click to navigate to alerts page

3. **PluginHealthGrid** - Grid of plugin status cards
   - Color-coded status: healthy (green), stale (yellow), error (red), disabled (gray)
   - Category grouping
   - Hover tooltips with last execution time

4. **InfrastructureOverview** - Infrastructure health cards
   - Servers, storage, databases
   - Healthy/unhealthy counts
   - Links to detailed views

5. **MetricsDashboard** - Historical metrics charts
   - 4 charts: CPU, Memory, Disk, Network
   - Time range selector
   - Auto-refresh support

#### Pages

1. **Dashboard** (`frontend/src/pages/Dashboard.tsx`)
   - Main dashboard page
   - Integrates all components
   - Auto-refresh every 30s

2. **PluginMetrics** (`frontend/src/pages/PluginMetrics.tsx`)
   - Per-plugin detailed metrics view
   - Dynamic metric discovery
   - Time range filtering
   - Metrics summary table

## API Reference

### Dashboard Overview

**Endpoint:** `GET /api/v1/monitoring/dashboard/overview`

**Response:**
```json
{
  "timestamp": "2025-12-22T17:00:00Z",
  "metrics": {
    "cpu": {"value": 45.2, "timestamp": "2025-12-22T17:00:00Z"},
    "memory": {"value": 62.5, "timestamp": "2025-12-22T17:00:00Z"},
    "disk": {"value": 78.3, "timestamp": "2025-12-22T17:00:00Z"},
    "network": {"value": 1024000, "timestamp": "2025-12-22T17:00:00Z"}
  },
  "alerts": {
    "total": 10,
    "unresolved": 3,
    "by_severity": {"critical": 1, "warning": 2, "info": 0},
    "recent_alerts": [...]
  },
  "infrastructure": {
    "servers": {"total": 5, "healthy": 4, "unhealthy": 1},
    "storage": {"total": 10, "devices": 10, "pools": 0},
    "databases": {"total": 3, "online": 3, "offline": 0}
  },
  "plugins": {
    "total": 39,
    "enabled": 35,
    "healthy": 32,
    "stale": 3,
    "items": [...]
  }
}
```

### Metrics History

**Endpoint:** `GET /api/v1/monitoring/dashboard/metrics/history?time_range=1h`

**Parameters:**
- `time_range` (optional): `1h`, `6h`, `24h`, `7d` (default: `1h`)

**Response:**
```json
{
  "time_range": "1h",
  "metrics": {
    "system_info.cpu_percent": [
      {"timestamp": "2025-12-22T16:00:00Z", "value": 45.0},
      {"timestamp": "2025-12-22T16:01:00Z", "value": 47.2}
    ],
    "system_info.memory_percent": [...]
  },
  "fetched_at": "2025-12-22T17:00:00Z"
}
```

### Plugin Health

**Endpoint:** `GET /api/v1/monitoring/dashboard/plugins/health?category=system`

**Parameters:**
- `category` (optional): Filter by plugin category

**Response:**
```json
{
  "total": 39,
  "summary": {
    "healthy": 32,
    "stale": 3,
    "failed": 1,
    "unknown": 3
  },
  "plugins": [
    {
      "plugin_id": "system_info",
      "name": "System Info",
      "category": "system",
      "enabled": true,
      "last_execution": "2025-12-22T16:59:30Z",
      "status": "success",
      "is_stale": false
    }
  ],
  "fetched_at": "2025-12-22T17:00:00Z"
}
```

### Single Metric History

**Endpoint:** `GET /api/v1/monitoring/dashboard/metrics/{plugin_id}/{metric_name}/history?time_range=1h`

**Example:** `/api/v1/monitoring/dashboard/metrics/system_info/cpu_percent/history?time_range=6h`

**Response:**
```json
{
  "plugin_id": "system_info",
  "metric_name": "cpu_percent",
  "time_range": "6h",
  "data": [
    {"timestamp": "2025-12-22T11:00:00Z", "value": 45.0}
  ],
  "count": 360,
  "fetched_at": "2025-12-22T17:00:00Z"
}
```

## Usage Examples

### Fetching Dashboard Data (Frontend)

```typescript
import dashboardApi from '../api/dashboard';

// Get complete overview
const overview = await dashboardApi.getOverview();
console.log(overview.metrics.cpu.value);

// Get historical metrics
const history = await dashboardApi.getMetricsHistory('24h');
const cpuData = history.metrics['system_info.cpu_percent'];

// Get plugin health
const health = await dashboardApi.getPluginHealth();
console.log(`${health.summary.healthy} healthy plugins`);

// Get single metric
const metric = await dashboardApi.getSingleMetricHistory(
  'system_info',
  'cpu_percent',
  '7d'
);
```

### Creating Custom Charts

```tsx
import MetricChart from '../components/dashboard/MetricChart';

function CustomDashboard() {
  const [data, setData] = useState([]);

  return (
    <MetricChart
      title="Custom Metric"
      data={data}
      color="#3b82f6"
      unit="%"
      chartType="line"
      height={300}
    />
  );
}
```

## Customization Guide

### Adding New Metrics

1. **Backend**: Update `get_dashboard_metrics()` in `metrics_service.py`
```python
async def get_dashboard_metrics(db: Session) -> Dict[str, Any]:
    metrics = {
        # ... existing metrics
        "custom_metric": None
    }
    
    # Query custom metric
    custom = db.execute(
        select(PluginMetric)
        .where(...)
    ).scalar_one_or_none()
    
    if custom:
        metrics["custom_metric"] = {
            "value": custom.value,
            "timestamp": custom.time.isoformat()
        }
    
    return metrics
```

2. **Frontend**: Add to Dashboard.tsx
```tsx
<StatCard
  title="Custom Metric"
  value={formatValue(metrics?.custom_metric?.value, ' units')}
  icon={CustomIcon}
  color="text-indigo-600"
/>
```

### Changing Refresh Intervals

**Dashboard Overview:**
```tsx
// In Dashboard.tsx
const [refreshInterval, setRefreshInterval] = useState(30000); // 30s
```

**Historical Charts:**
```tsx
<MetricsDashboard 
  autoRefresh={true} 
  refreshInterval={60000}  // 60s
/>
```

### Custom Time Ranges

Edit `metrics_service.py`:
```python
range_map = {
    "1h": timedelta(hours=1),
    "12h": timedelta(hours=12),  # Add new range
    "30d": timedelta(days=30)    # Add new range
}
```

Update frontend TimeRange type:
```typescript
type TimeRange = '1h' | '6h' | '12h' | '24h' | '7d' | '30d';
```

## Troubleshooting

### Dashboard Not Loading

**Symptom:** Dashboard shows "Failed to load dashboard data"

**Solutions:**
1. Check backend is running: `curl http://localhost:8000/api/v1/monitoring/dashboard/overview`
2. Verify database connection
3. Check browser console for CORS errors
4. Ensure plugins are enabled and collecting metrics

### No Historical Data

**Symptom:** Charts show "No data available"

**Causes:**
- Plugins haven't run yet (wait for first execution cycle)
- Time range too narrow (try 24h or 7d)
- Plugin metrics not being stored

**Debug:**
```sql
-- Check if metrics exist
SELECT plugin_id, metric_name, COUNT(*) 
FROM plugin_metrics 
GROUP BY plugin_id, metric_name;
```

### Stale Plugin Status

**Symptom:** Plugins showing as "stale" (yellow)

**Cause:** No execution in last 10 minutes

**Fix:**
- Check plugin scheduler is running
- Verify plugin configuration
- Check plugin logs for errors

### Chart Performance Issues

**Symptom:** Slow rendering with large datasets

**Solutions:**
1. Reduce data points:
```typescript
// Limit points for longer ranges
const maxPoints = timeRange === '7d' ? 168 : 360;
```

2. Disable point rendering:
```typescript
pointRadius: data.length > 100 ? 0 : 3
```

## Performance Considerations

### Backend

- **Caching**: Consider Redis for dashboard overview (30s TTL)
- **Database Indexes**: Ensure indexes on `plugin_metrics(time, plugin_id, metric_name)`
- **Pagination**: Limit query results (e.g., last 1000 metrics)

### Frontend

- **Debouncing**: Debounce time range changes
- **Lazy Loading**: Load charts on viewport entry
- **Memoization**: Use React.memo for expensive components

## Testing

Run backend tests:
```bash
cd backend
pytest tests/test_dashboard_api.py -v
```

Run frontend type checking:
```bash
cd frontend
npm run typecheck
```

## Related Documentation

- [Alerting System](ALERTING_SYSTEM.md)
- [Plugin Development Guide](PLUGIN_DEVELOPMENT_GUIDE.md)
- [Builtin Plugins](BUILTIN_PLUGINS.md)
- [API Documentation](API.md)

## Version History

- **v1.0.0** (2025-12-22): Initial release
  - 4 backend endpoints
  - 6 frontend components
  - 39 plugin support
  - Historical metrics with 4 time ranges

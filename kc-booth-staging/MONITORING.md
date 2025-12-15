# Monitoring and Observability

## Prometheus Metrics
Metrics endpoint: `http://localhost:8001/metrics` (no auth required)

### Available Metrics
- `http_requests_total{method, endpoint, status}` - Total HTTP requests
- `http_request_duration_seconds{method, endpoint}` - Request duration
- `auth_attempts_total{status}` - Auth attempts (success/failed/expired)
- `api_key_usage_total{api_key_name}` - API key usage
- `certificates_issued_total{status}` - Certificates issued
- `certificates_rotated_total` - Auto-rotated certificates
- `certificate_rotation_errors` - Rotation failures
- `db_queries_total{operation}` - Database queries
- `db_query_duration_seconds{operation}` - Query duration
- `active_servers_total` - Active servers count
- `active_ssh_keys_total` - SSH keys count
- `active_certificates_total` - Certificates count

### Prometheus Config
```yaml
scrape_configs:
  - job_name: 'kc-booth'
    scrape_interval: 15s
    static_configs:
      - targets: ['app:8000']
```

## Correlation IDs
Every request gets a unique correlation ID for tracing:
- Auto-generated or from `X-Correlation-ID` header
- Included in all logs
- Returned in response headers

### Trace Request
```bash
curl -H "X-Correlation-ID: trace-123" http://localhost:8001/servers/
docker compose logs app | grep "trace-123"
```

## Structured Logging
Set `JSON_LOGS=true` for production (JSON format)
Default: human-readable with correlation IDs

## Sample Alerts (alerts.yml)
```yaml
groups:
  - name: kc-booth
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
      
      - alert: CertRotationFailures
        expr: certificate_rotation_errors > 0
        for: 1m
```

## Grafana Dashboards
Key panels:
- Request rate: `rate(http_requests_total[5m])`
- Error rate: `rate(http_requests_total{status=~"5.."}[5m])`
- P95 latency: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- Active resources: `active_servers_total`, `active_ssh_keys_total`

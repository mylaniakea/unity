"""Prometheus metrics for monitoring."""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Authentication metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['status']  # success, failed, expired
)

api_key_usage_total = Counter(
    'api_key_usage_total',
    'Total API key usages',
    ['api_key_name']
)

# Certificate metrics
certificates_issued_total = Counter(
    'certificates_issued_total',
    'Total certificates issued',
    ['status']  # success, failed
)

certificates_rotated_total = Counter(
    'certificates_rotated_total',
    'Total certificates rotated automatically'
)

certificate_rotation_errors = Counter(
    'certificate_rotation_errors',
    'Certificate rotation errors'
)

# Database metrics
db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['operation']  # create, read, update, delete
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation']
)

# Active resources
active_servers = Gauge(
    'active_servers_total',
    'Total number of active servers'
)

active_ssh_keys = Gauge(
    'active_ssh_keys_total',
    'Total number of active SSH keys'
)

active_certificates = Gauge(
    'active_certificates_total',
    'Total number of active certificates'
)


def metrics_endpoint() -> Response:
    """Generate Prometheus metrics endpoint response."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


class MetricsMiddleware:
    """Middleware to track HTTP request metrics."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        method = scope["method"]
        path = scope["path"]
        
        # Skip metrics endpoint itself
        if path == "/metrics":
            return await self.app(scope, receive, send)
        
        start_time = time.time()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration = time.time() - start_time
                
                # Record metrics
                http_requests_total.labels(
                    method=method,
                    endpoint=path,
                    status=status_code
                ).inc()
                
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=path
                ).observe(duration)
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)

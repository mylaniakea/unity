"""
Web Service Monitor Plugin

Monitors HTTP/HTTPS endpoints - health checks, response times, SSL certificates.
Essential for monitoring web applications and APIs.
"""

import requests
import ssl
import socket
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class WebServiceMonitorPlugin(PluginBase):
    """Monitors web service endpoints and APIs"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="web-service-monitor",
            name="Web Service Monitor",
            version="1.0.0",
            description="Monitors HTTP/HTTPS endpoints including health checks, response times, and SSL certificate expiration",
            author="Unity Team",
            category=PluginCategory.APPLICATION,
            tags=["http", "https", "web", "api", "ssl", "health-check"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["requests"],
            config_schema={
                "type": "object",
                "properties": {
                    "endpoints": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "url": {"type": "string"},
                                "method": {"type": "string", "default": "GET"},
                                "expected_status": {"type": "integer", "default": 200},
                                "timeout": {"type": "number", "default": 10.0},
                                "verify_ssl": {"type": "boolean", "default": True},
                                "headers": {"type": "object", "default": {}},
                                "check_content": {"type": "string", "default": None}
                            },
                            "required": ["name", "url"]
                        },
                        "default": [],
                        "description": "List of endpoints to monitor"
                    },
                    "ssl_warning_days": {
                        "type": "integer",
                        "default": 30,
                        "description": "Days before SSL expiration to warn"
                    },
                    "user_agent": {
                        "type": "string",
                        "default": "Unity-WebServiceMonitor/1.0",
                        "description": "User agent string"
                    }
                },
                "required": []
            }
        )
    
    def _check_ssl_certificate(self, hostname: str, port: int = 443) -> Dict[str, Any]:
        """Check SSL certificate expiration"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Parse expiration date
                    not_after = cert.get('notAfter')
                    if not_after:
                        # Parse date: 'Dec 17 03:40:40 2025 GMT'
                        expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                        days_until_expiry = (expiry_date - datetime.utcnow()).days
                        
                        warning_days = self.config.get("ssl_warning_days", 30)
                        
                        return {
                            "valid": True,
                            "issuer": dict(x[0] for x in cert.get('issuer', [])),
                            "subject": dict(x[0] for x in cert.get('subject', [])),
                            "expiry_date": expiry_date.isoformat(),
                            "days_until_expiry": days_until_expiry,
                            "expires_soon": days_until_expiry <= warning_days,
                            "expired": days_until_expiry < 0
                        }
            
            return {"valid": False, "error": "Could not retrieve certificate"}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def _check_endpoint(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Check a single endpoint"""
        name = endpoint.get("name", "Unknown")
        url = endpoint.get("url")
        method = endpoint.get("method", "GET").upper()
        expected_status = endpoint.get("expected_status", 200)
        timeout = endpoint.get("timeout", 10.0)
        verify_ssl = endpoint.get("verify_ssl", True)
        custom_headers = endpoint.get("headers", {})
        check_content = endpoint.get("check_content")
        
        result = {
            "name": name,
            "url": url,
            "method": method,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Prepare headers
            headers = {"User-Agent": self.config.get("user_agent", "Unity-WebServiceMonitor/1.0")}
            headers.update(custom_headers)
            
            # Make request
            start_time = datetime.utcnow()
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=timeout,
                verify=verify_ssl,
                allow_redirects=True
            )
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Basic response info
            result.update({
                "status": "success",
                "status_code": response.status_code,
                "response_time_ms": round(response_time_ms, 2),
                "content_length": len(response.content),
                "headers": dict(response.headers),
                "redirects": len(response.history)
            })
            
            # Check if status matches expected
            if response.status_code != expected_status:
                result["status"] = "warning"
                result["message"] = f"Status {response.status_code} != expected {expected_status}"
            
            # Check content if specified
            if check_content:
                if check_content in response.text:
                    result["content_check"] = "passed"
                else:
                    result["status"] = "warning"
                    result["content_check"] = "failed"
                    result["message"] = f"Content check failed: '{check_content}' not found"
            
            # Check SSL certificate if HTTPS
            parsed_url = urlparse(url)
            if parsed_url.scheme == "https":
                hostname = parsed_url.hostname
                port = parsed_url.port or 443
                result["ssl"] = self._check_ssl_certificate(hostname, port)
            
        except requests.exceptions.SSLError as e:
            result.update({
                "status": "error",
                "error": "SSL Error",
                "message": str(e)
            })
        except requests.exceptions.Timeout:
            result.update({
                "status": "error",
                "error": "Timeout",
                "message": f"Request timed out after {timeout}s"
            })
        except requests.exceptions.ConnectionError as e:
            result.update({
                "status": "error",
                "error": "Connection Error",
                "message": str(e)
            })
        except requests.exceptions.RequestException as e:
            result.update({
                "status": "error",
                "error": "Request Error",
                "message": str(e)
            })
        except Exception as e:
            result.update({
                "status": "error",
                "error": "Unexpected Error",
                "message": str(e)
            })
        
        return result
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect web service metrics"""
        
        endpoints = self.config.get("endpoints", [])
        
        if not endpoints:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "No endpoints configured",
                "message": "Please configure endpoints in plugin config"
            }
        
        results = []
        success_count = 0
        warning_count = 0
        error_count = 0
        total_response_time = 0.0
        ssl_expiring_soon = 0
        
        for endpoint in endpoints:
            result = self._check_endpoint(endpoint)
            results.append(result)
            
            if result.get("status") == "success":
                success_count += 1
                if "response_time_ms" in result:
                    total_response_time += result["response_time_ms"]
            elif result.get("status") == "warning":
                warning_count += 1
            elif result.get("status") == "error":
                error_count += 1
            
            # Check SSL expiration warnings
            if "ssl" in result and result["ssl"].get("expires_soon"):
                ssl_expiring_soon += 1
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_endpoints": len(endpoints),
                "success": success_count,
                "warnings": warning_count,
                "errors": error_count,
                "avg_response_time_ms": round(total_response_time / max(success_count, 1), 2) if success_count > 0 else None,
                "ssl_expiring_soon": ssl_expiring_soon
            },
            "endpoints": results
        }
        
        return data
    
    async def health_check(self) -> Dict[str, Any]:
        """Check web service monitor health"""
        
        endpoints = self.config.get("endpoints", [])
        
        if not endpoints:
            return {
                "healthy": False,
                "message": "No endpoints configured",
                "details": {
                    "suggestion": "Configure endpoints in plugin config"
                }
            }
        
        return {
            "healthy": True,
            "message": "Web service monitor is configured",
            "details": {
                "endpoint_count": len(endpoints),
                "endpoints": [e.get("name") for e in endpoints]
            }
        }

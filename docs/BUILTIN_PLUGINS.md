# Built-in Plugins Catalog

This catalog documents all built-in monitoring plugins included with Unity. Each plugin is production-ready and follows best practices for monitoring and observability.

## Quick Reference

| Plugin | Category | Description | Key Metrics |
|--------|----------|-------------|-------------|
| [System Info](#system-info) | System | Basic system information | CPU, Memory, Disk, Network |
| [Process Monitor](#process-monitor) | System | Process tracking and analysis | Top processes, counts, resource usage |
| [Thermal Monitor](#thermal-monitor) | Thermal | Temperature monitoring | CPU/GPU temps, fan speeds |
| [Network Monitor](#network-monitor) | Network | Network interface statistics | Throughput, errors, connections |
| [Disk Monitor](#disk-monitor) | Storage | Disk usage and I/O stats | Usage %, I/O counters, partitions |
| [Docker Monitor](#docker-monitor) | Container | Docker container monitoring | Container stats, health, networks |
| [PostgreSQL Monitor](#postgresql-monitor) | Database | PostgreSQL metrics | Connections, queries, cache hits |
| [MySQL Monitor](#mysql-monitor) | Database | MySQL/MariaDB metrics | Threads, queries, buffer pool |
| [MongoDB Monitor](#mongodb-monitor) | Database | MongoDB metrics | Operations, connections, replica status |
| [Redis Monitor](#redis-monitor) | Database | Redis metrics | Memory, commands, keyspace |
| [InfluxDB Monitor](#influxdb-monitor) | Database | InfluxDB metrics | Writes, queries, measurements |
| [SQLite Monitor](#sqlite-monitor) | Database | SQLite database stats | Size, queries, cache, integrity |
| [Web Service Monitor](#web-service-monitor) | Application | HTTP endpoint monitoring | Response time, status, availability |
| [Log Monitor](#log-monitor) | Application | Log file analysis | Error counts, patterns, rates |

## System Monitoring

### System Info

**Plugin ID:** `system-info`  
**Version:** 1.0.0  
**Dependencies:** `psutil`

Collects comprehensive system information including CPU, memory, disk, and network statistics.

#### Metrics

- **CPU**: Usage percentage, core count, frequency
- **Memory**: Total, used, available (GB), usage percentage
- **Swap**: Total, used, percentage
- **Disk**: Total, used, free (GB), usage percentage
- **Platform**: OS type, release, architecture
- **Network** (optional): Bytes/packets sent/received

#### Configuration

```json
{
  "collect_network": true
}
```

#### Example Output

```json
{
  "cpu": {
    "usage_percent": 23.5,
    "count": 8,
    "frequency_mhz": 2400.0
  },
  "memory": {
    "total_gb": 16.0,
    "used_gb": 8.2,
    "available_gb": 7.8,
    "percent": 51.3
  },
  "disk": {
    "total_gb": 500.0,
    "used_gb": 320.5,
    "free_gb": 179.5,
    "percent": 64.1
  }
}
```

### Process Monitor

**Plugin ID:** `process-monitor`  
**Version:** 1.0.0  
**Dependencies:** `psutil`

Monitors running processes, tracks resource consumption, and identifies top consumers.

#### Metrics

- **Process Counts**: Total, running, sleeping, zombie processes
- **Top Processes**: By CPU or memory usage
- **System Load**: 1min, 5min, 15min averages

#### Configuration

```json
{
  "top_n": 10,
  "sort_by": "cpu"
}
```

Options:
- `top_n`: Number of top processes to return (default: 10)
- `sort_by`: "cpu" or "memory" (default: "cpu")

#### Use Cases

- Identify resource-hungry processes
- Track process lifecycle
- Detect zombie processes
- Monitor system load trends

## Best Practices

### Configuration Management

1. **Secrets**: Never hardcode passwords in configuration
   - Use environment variables: `${ENV_VAR_NAME}`
   - Use secret management tools
   - Consider HashiCorp Vault integration

2. **Validation**: Always validate configuration before enabling
   ```bash
   curl -X POST http://localhost:8000/api/v1/plugins/system-info/validate \
     -H "Content-Type: application/json" \
     -d '{"collect_network": true}'
   ```

3. **Testing**: Test plugins in dev environment first
   ```bash
   curl http://localhost:8000/api/v1/plugins/system-info/health
   ```

## Related Documentation

- [Plugin Development Guide](PLUGIN_DEVELOPMENT.md) - Build custom plugins
- [API Documentation](API.md) - REST API reference  
- [Architecture Overview](../ARCHITECTURE.md) - System architecture


# Unity Built-in Plugins - Complete Reference

**Last Updated**: December 22, 2025  
**Total Plugins**: 39  
**Categories**: System (5), Network (7), Database (6), Application (9), Storage (4), Security (4), Container (2), Hardware (1), IoT (1)

## Quick Reference

| Plugin ID | Category | Purpose |
|-----------|----------|---------|
| system-info | System | CPU, memory, disk metrics |
| process-monitor | System | Process counts and top processes |
| temperature-monitor | System | Hardware temperature sensors |
| network-monitor | Network | Network interface statistics |
| disk-monitor | Storage | Disk usage and I/O statistics |
| docker-monitor | Container | Docker container metrics |
| kubernetes-monitor | Container | Kubernetes cluster health |
| postgres-monitor | Database | PostgreSQL metrics |
| mysql-monitor | Database | MySQL/MariaDB metrics |
| mongodb-monitor | Database | MongoDB metrics |
| redis-monitor | Database | Redis metrics |
| influxdb-monitor | Database | InfluxDB metrics |
| sqlite-monitor | Database | SQLite database health |
| auth-monitor | Security | Authentication attempts |
| firewall-monitor | Security | Firewall rules and blocks |
| certificate-monitor | Security | SSL certificate expiration |
| bitwarden-monitor | Security | Bitwarden/Vaultwarden health |
| backup-monitor | Storage | Backup job status |
| zfs-btrfs-monitor | Storage | ZFS/Btrfs filesystem health |
| smart-monitor | Storage | SMART disk health |
| dns-monitor | Network | Pi-hole/AdGuard DNS stats |
| vpn-monitor | Network | VPN tunnel health |
| vpn-mesh-monitor | Network | Tailscale/Nebula mesh |
| network-switch-monitor | Network | SNMP switch monitoring |
| reverse-proxy-monitor | Network | Reverse proxy health |
| nginx-proxy-manager-monitor | Network | NPM proxy hosts |
| email-server-monitor | Network | Mail server health |
| home-assistant-monitor | IoT | Home Assistant health |
| media-server-monitor | Application | Plex/Jellyfin/Emby stats |
| download-manager-monitor | Application | qBittorrent/Transmission |
| git-server-monitor | Application | Gitea/GitLab health |
| nextcloud-monitor | Application | Nextcloud stats |
| game-server-monitor | Application | Game server monitoring |
| photo-manager-monitor | Application | PhotoPrism/Immich |
| log-monitor | Application | Log file parsing |
| web-service-monitor | Application | HTTP endpoint health |
| ipmi-monitor | Hardware | IPMI/BMC monitoring |
| ups-monitor | Hardware | UPS battery status |
| syncthing-monitor | Application | Syncthing sync health |

---

## System Plugins

### system-info
**ID**: `system-info`  
**Version**: 1.0.0  
**Category**: System

Collects fundamental system metrics including CPU usage, memory utilization, swap usage, disk space, and platform information.

**Dependencies**: `psutil`

**Configuration**:
```json
{
  "collect_network": true,
  "collect_disk_io": false
}
```

**Metrics**:
- `cpu.usage_percent` - Current CPU usage percentage
- `cpu.count` - Number of CPU cores
- `cpu.frequency_mhz` - Current CPU frequency
- `memory.total_gb` - Total RAM in GB
- `memory.used_gb` - Used RAM in GB
- `memory.percent` - Memory usage percentage
- `swap.total_gb` - Total swap space
- `swap.used_gb` - Used swap space
- `disk.total_gb` - Total disk space
- `disk.used_gb` - Used disk space
- `disk.percent` - Disk usage percentage

**Example Output**:
```json
{
  "cpu": {"usage_percent": 45.2, "count": 8, "frequency_mhz": 3400},
  "memory": {"total_gb": 32.0, "used_gb": 18.5, "percent": 57.8},
  "disk": {"total_gb": 500, "used_gb": 320, "percent": 64.0}
}
```

---

### process-monitor
**ID**: `process-monitor`  
**Version**: 1.0.0  
**Category**: System

Monitors running processes including process counts, top resource consumers, and system load.

**Dependencies**: `psutil`

**Configuration**:
```json
{
  "top_n": 10,
  "sort_by": "cpu",
  "include_cmdline": false
}
```

**Metrics**:
- `process_count` - Total number of processes
- `thread_count` - Total number of threads
- `top_processes` - List of top N processes
- `load_average` - 1/5/15 minute load averages

---

### temperature-monitor
**ID**: `temperature-monitor`  
**Version**: 1.0.0  
**Category**: System

Monitors hardware temperature sensors for CPU, GPU, and other components.

**Dependencies**: `psutil`

**Configuration**:
```json
{
  "temp_unit": "celsius",
  "alert_threshold": 85.0
}
```

**Metrics**:
- `temperatures` - Dict of sensor names and temperatures
- `critical_temp` - Highest temperature detected
- `alerts` - List of sensors exceeding threshold

---

## Network Plugins

### network-monitor
**ID**: `network-monitor`  
**Version**: 1.0.0  
**Category**: Network

Monitors network interfaces including throughput, packet counts, errors, and active connections.

**Dependencies**: `psutil`

**Configuration**:
```json
{
  "interfaces": ["eth0", "wlan0"],
  "collect_connections": true
}
```

**Metrics**:
- `interfaces` - Per-interface statistics
- `bytes_sent` - Total bytes sent
- `bytes_recv` - Total bytes received
- `packets_sent` - Total packets sent
- `packets_recv` - Total packets received
- `errors_in` - Inbound errors
- `errors_out` - Outbound errors
- `connections` - Active network connections

---

### dns-monitor
**ID**: `dns-monitor`  
**Version**: 1.0.0  
**Category**: Network

Monitors DNS servers including Pi-hole, AdGuard Home, and Unbound. Tracks query statistics, block rates, and performance.

**Dependencies**: `requests`

**Configuration**:
```json
{
  "server_type": "pihole",
  "api_url": "http://pihole.local/admin/api.php",
  "api_token": "your_token_here"
}
```

**Metrics**:
- `queries_today` - Total DNS queries today
- `blocked_today` - Queries blocked today
- `percent_blocked` - Block percentage
- `domains_blocked` - Number of blocked domains
- `clients_ever_seen` - Total clients
- `queries_forwarded` - Forwarded queries
- `queries_cached` - Cached queries

---

### vpn-monitor
**ID**: `vpn-monitor`  
**Version**: 1.0.0  
**Category**: Network

Monitors VPN tunnel health including connection status, throughput, and connected clients.

**Dependencies**: None (uses system commands)

**Configuration**:
```json
{
  "vpn_type": "wireguard",
  "interface": "wg0",
  "config_file": "/etc/wireguard/wg0.conf"
}
```

**Metrics**:
- `tunnel_status` - Up/Down status
- `connected_peers` - Number of active peers
- `bytes_sent` - Bytes sent through tunnel
- `bytes_recv` - Bytes received
- `last_handshake` - Timestamp of last handshake

---

## Database Plugins

### postgres-monitor
**ID**: `postgres-monitor`  
**Version**: 1.0.0  
**Category**: Database

Monitors PostgreSQL server including connections, transactions, cache hits, and replication status.

**Dependencies**: `psycopg2`

**Configuration**:
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "postgres",
  "user": "monitor_user",
  "password": "secure_password"
}
```

**Metrics**:
- `connections.active` - Active connections
- `connections.idle` - Idle connections
- `connections.max` - Max connections allowed
- `transactions.commits` - Transaction commits
- `transactions.rollbacks` - Transaction rollbacks
- `cache_hit_ratio` - Buffer cache hit ratio
- `database_size_mb` - Database size in MB

---

### mysql-monitor
**ID**: `mysql-monitor`  
**Version**: 1.0.0  
**Category**: Database

Monitors MySQL and MariaDB servers including connections, queries, and replication.

**Dependencies**: `pymysql`

**Configuration**:
```json
{
  "host": "localhost",
  "port": 3306,
  "user": "monitor_user",
  "password": "secure_password"
}
```

**Metrics**:
- `connections` - Current connections
- `max_connections` - Maximum allowed
- `queries_per_second` - QPS rate
- `slow_queries` - Slow query count
- `replication_status` - Master/slave status
- `uptime_seconds` - Server uptime

---

## Application Plugins

### docker-monitor
**ID**: `docker-monitor`  
**Version**: 1.0.0  
**Category**: Container

Monitors Docker containers, images, and resource usage including CPU, memory, and network per container.

**Dependencies**: `docker`

**Configuration**:
```json
{
  "docker_host": "unix:///var/run/docker.sock",
  "include_stopped": false
}
```

**Metrics**:
- `containers.total` - Total containers
- `containers.running` - Running containers
- `containers.stopped` - Stopped containers
- `images.total` - Total images
- `per_container` - Per-container CPU/memory/network

---

### media-server-monitor
**ID**: `media-server-monitor`  
**Version**: 1.0.0  
**Category**: Application

Monitors Plex, Jellyfin, and Emby media servers including active streams, transcodes, library statistics, and user activity.

**Dependencies**: `requests`

**Configuration**:
```json
{
  "server_type": "plex",
  "api_url": "http://plex.local:32400",
  "api_token": "your_plex_token"
}
```

**Metrics**:
- `active_sessions` - Current streams
- `transcode_sessions` - Active transcodes
- `library_count` - Number of libraries
- `movie_count` - Total movies
- `tv_show_count` - Total TV shows
- `user_count` - Total users

---

## Storage Plugins

### disk-monitor
**ID**: `disk-monitor`  
**Version**: 1.0.0  
**Category**: Storage

Monitors disk usage, I/O statistics, and mounted partitions across all filesystems.

**Dependencies**: `psutil`

**Configuration**:
```json
{
  "exclude_types": ["tmpfs", "devtmpfs"],
  "min_size_gb": 1.0
}
```

**Metrics**:
- `partitions` - List of mounted partitions
- `total_gb` - Total disk space per partition
- `used_gb` - Used space
- `free_gb` - Free space
- `percent` - Usage percentage
- `io_read_bytes` - Bytes read
- `io_write_bytes` - Bytes written

---

### backup-monitor
**ID**: `backup-monitor`  
**Version**: 1.0.0  
**Category**: Storage

Monitors backup job status for Restic, Borg, Duplicati, rsync, and custom scripts. Tracks last successful run and backup health.

**Dependencies**: None (uses system commands)

**Configuration**:
```json
{
  "backup_type": "restic",
  "repository": "/backup/repo",
  "password_file": "/etc/restic/password"
}
```

**Metrics**:
- `last_backup` - Timestamp of last backup
- `backup_size_gb` - Total backup size
- `snapshot_count` - Number of snapshots
- `status` - Success/Failed/Warning
- `duration_seconds` - Last backup duration

---

## Security Plugins

### auth-monitor
**ID**: `auth-monitor`  
**Version**: 1.0.0  
**Category**: Security

Monitors authentication attempts, failures, and suspicious patterns in system logs.

**Dependencies**: None (reads logs)

**Configuration**:
```json
{
  "log_file": "/var/log/auth.log",
  "alert_threshold": 5,
  "time_window_minutes": 10
}
```

**Metrics**:
- `successful_logins` - Count of successful logins
- `failed_attempts` - Failed login attempts
- `suspicious_ips` - IPs with multiple failures
- `locked_accounts` - Accounts that are locked

---

### certificate-monitor
**ID**: `certificate-monitor`  
**Version**: 1.0.0  
**Category**: Security

Monitors SSL/TLS certificate expiration dates, chain validation, and security status to prevent outages.

**Dependencies**: `cryptography`

**Configuration**:
```json
{
  "domains": ["example.com", "api.example.com"],
  "warning_days": 30,
  "critical_days": 7
}
```

**Metrics**:
- `certificates` - List of monitored certificates
- `days_until_expiry` - Days until expiration
- `is_valid` - Certificate validity
- `chain_valid` - Certificate chain status
- `alerts` - Expiring certificates

---

## Usage Examples

### Quick Start
```bash
# List all available plugins
curl http://localhost:8000/api/plugins/v2/available

# Enable system-info plugin
curl -X POST http://localhost:8000/api/plugins/v2/enable/system-info

# Configure plugin
curl -X PUT http://localhost:8000/api/plugins/v2/system-info/config \
  -H "Content-Type: application/json" \
  -d '{"collect_network": true}'

# Execute plugin
curl -X POST http://localhost:8000/api/plugins/v2/system-info/execute

# Get plugin metrics
curl http://localhost:8000/api/plugins/v2/system-info/metrics
```

### Common Configurations

#### Monitoring a Homelab Stack
```json
{
  "enabled_plugins": [
    "system-info",
    "docker-monitor",
    "postgres-monitor",
    "redis-monitor",
    "nginx-proxy-manager-monitor",
    "certificate-monitor",
    "backup-monitor"
  ]
}
```

#### Network Monitoring Setup
```json
{
  "enabled_plugins": [
    "network-monitor",
    "dns-monitor",
    "vpn-monitor",
    "firewall-monitor"
  ]
}
```

## Best Practices

1. **Start Simple** - Enable core plugins (system-info, disk-monitor) first
2. **Configure Credentials Securely** - Use environment variables or secrets management
3. **Set Appropriate Collection Intervals** - Balance freshness vs resource usage
4. **Monitor Plugin Performance** - Check execution times in plugin logs
5. **Test Configuration Changes** - Use `/execute` endpoint before enabling scheduled collection
6. **Handle Dependencies** - Install required Python packages for each plugin
7. **Use Tags** - Leverage plugin tags for filtering and organization

## Troubleshooting

### Plugin Not Collecting Data
1. Check plugin is enabled: `GET /api/plugins/v2/{plugin_id}/status`
2. Verify configuration: `GET /api/plugins/v2/{plugin_id}/config`
3. Check dependencies are installed
4. Review plugin logs for errors
5. Test manual execution: `POST /api/plugins/v2/{plugin_id}/execute`

### High Resource Usage
- Increase collection interval
- Disable unused plugins
- Reduce `top_n` values in process monitors
- Exclude unnecessary interfaces/disks

### Connection Failures
- Verify hostnames and ports
- Check credentials and permissions
- Ensure firewall rules allow connections
- Test connectivity from Unity server

## Related Documentation

- [Plugin Development Guide](PLUGIN_DEVELOPMENT.md) - Create custom plugins
- [Plugin API Reference](PLUGIN_API_EXAMPLES.md) - API documentation
- [Plugin Architecture](ARCHITECTURE.md) - System design
- [Testing Guide](TESTING-GUIDE.md) - Plugin testing

---

**Note**: This is a living document. New plugins are added regularly. Check the [GitHub repository](https://github.com/your-repo/unity) for the latest plugin additions.

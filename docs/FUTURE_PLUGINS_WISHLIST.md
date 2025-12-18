# Future Plugins Wishlist

**Last Updated**: December 17, 2025  
**Purpose**: Comprehensive plugin ideas ranked by homelab necessity and pain points

This document represents the collective struggles, joys, and needs of homelabbers at every experience level. Each plugin addresses real pain points in the homelab journey.

---

## 🔥 Tier 1: Essential Pain Points (The "Why didn't this exist sooner?" tier)

### 1. **Backup Monitor** ⭐⭐⭐⭐⭐
**Category**: Storage  
**Pain Point**: "Did my backup run? Is it working? When did it last succeed?"  
**What it monitors**:
- Backup job status (Restic, Borg, Duplicati, rsync)
- Last successful backup timestamp
- Backup size trends
- Failed backup alerts
- Restore test results
- Retention policy compliance

**Why homelabbers need this**: The #1 regret story in r/homelab starts with "I thought my backups were working..."

---

### 2. **UPS Monitor** ⭐⭐⭐⭐⭐
**Category**: Power  
**Pain Point**: "Is my UPS battery dying? Will my server survive a power outage?"  
**What it monitors**:
- Battery health and charge level
- Runtime estimates under current load
- Input/output voltage
- Load percentage
- UPS events (power failures, battery tests)
- Battery replacement indicators
- Integration with NUT (Network UPS Tools), APC PowerChute

**Why homelabbers need this**: Power outages at 3 AM shouldn't be a mystery. Battery deaths shouldn't be a surprise.

---

### 3. **Certificate Expiration Monitor** ⭐⭐⭐⭐⭐
**Category**: Security  
**Pain Point**: "My SSL cert expired and I didn't know until everything broke"  
**What it monitors**:
- SSL/TLS certificate expiration dates
- Certificate chain validation
- Domain validation status
- Let's Encrypt renewal tracking
- Self-signed cert warnings
- Certificate transparency logs

**Why homelabbers need this**: Nothing ruins a Saturday morning like expired certs breaking your entire stack.

---

### 4. **Reverse Proxy Monitor** ⭐⭐⭐⭐⭐
**Category**: Network  
**Pain Point**: "Which service is behind which domain? Is my proxy config correct?"  
**What it monitors**:
- Nginx Proxy Manager, Traefik, Caddy status
- Active routes and backends
- SSL termination status
- Proxy errors and 502s
- Rate limiting stats
- Response times per route

**Why homelabbers need this**: The reverse proxy is the front door. When it breaks, everything breaks.

---

### 5. **SMART Disk Health Monitor** ⭐⭐⭐⭐⭐
**Category**: Storage  
**Pain Point**: "My drive died and I had no warning"  
**What it monitors**:
- SMART attributes for all drives
- Reallocated sectors
- Pending sectors
- Temperature
- Power-on hours
- Predictive failure warnings
- RAID rebuild status

**Why homelabbers need this**: Drives fail. The question is: will you know before data loss?

---

## 🎯 Tier 2: Quality of Life Essentials

### 6. **DNS Monitor** ⭐⭐⭐⭐
**Category**: Network  
**What it monitors**:
- Pi-hole, AdGuard Home, Unbound stats
- Query counts and block rates
- Top domains and clients
- DNS query response times
- Upstream resolver status
- Blocklist updates

**Why homelabbers need this**: DNS is everything. When it's slow or broken, the entire internet "feels" broken.

---

### 7. **VPN Monitor** ⭐⭐⭐⭐
**Category**: Security  
**What it monitors**:
- WireGuard, OpenVPN connection status
- Active tunnels and peers
- Bandwidth usage per peer
- Connection uptime
- Failed authentication attempts
- Split tunneling status

**Why homelabbers need this**: Remote access is critical. Knowing your VPN is healthy means peace of mind.

---

### 8. **Media Server Monitor** ⭐⭐⭐⭐
**Category**: Application  
**What it monitors**:
- Plex, Jellyfin, Emby status
- Active streams and transcodes
- Library sizes and recent additions
- Transcode performance and load
- User activity
- Storage usage per library

**Why homelabbers need this**: "Why is Plex buffering?" - Every homelabber, constantly

---

### 9. **Download Manager Monitor** ⭐⭐⭐⭐
**Category**: Application  
**What it monitors**:
- qBittorrent, Transmission, SABnzbd, NZBGet
- Active downloads and queue
- Download/upload speeds
- Disk space warnings
- Ratio tracking
- Failed downloads

**Why homelabbers need this**: Automation is beautiful until you realize nothing downloaded all week.

---

### 10. **Home Assistant Monitor** ⭐⭐⭐⭐
**Category**: IoT  
**What it monitors**:
- Home Assistant instance health
- Entity counts and unavailable entities
- Automation execution stats
- Integration errors
- Database size
- Addon status

**Why homelabbers need this**: HA is the brain of smart homes. Brain health matters.

---

### 11. **Nextcloud Monitor** ⭐⭐⭐⭐
**Category**: Application  
**What it monitors**:
- Nextcloud instance status
- Active users and sessions
- File sync status
- Storage quota usage
- App status and updates
- Background job execution

**Why homelabbers need this**: Self-hosted cloud storage is the dream. Monitoring makes it reliable.

---

### 12. **Git Server Monitor** ⭐⭐⭐⭐
**Category**: Application  
**What it monitors**:
- Gitea, Gogs, GitLab status
- Repository counts and sizes
- Active webhooks
- CI/CD pipeline status
- User activity
- Storage usage

**Why homelabbers need this**: Code is precious. Git server health is non-negotiable.

---

## 🚀 Tier 3: Power User Sophistication

### 13. **ZFS/BTRFS Monitor** ⭐⭐⭐⭐
**Category**: Storage  
**What it monitors**:
- Pool health and status
- Scrub progress and results
- Compression ratios
- Deduplication stats
- Snapshot counts
- Free space per dataset/subvolume

**Why homelabbers need this**: Advanced filesystems require advanced monitoring.

---

### 14. **Kubernetes Monitor** ⭐⭐⭐⭐
**Category**: Container  
**What it monitors**:
- Cluster health (nodes, pods, services)
- Resource usage per namespace
- Pod restarts and crashloops
- Persistent volume claims
- Ingress status
- Helm releases

**Why homelabbers need this**: K8s at home is powerful but complex. Observability is survival.

---

### 15. **Temperature/Environmental Monitor** ⭐⭐⭐⭐
**Category**: System  
**What it monitors**:
- Server room temperature
- Humidity levels
- Rack temperature sensors
- External weather integration
- Alert on dangerous temps

**Why homelabbers need this**: Hardware + heat = bad time. Monitoring prevents meltdowns.

---

### 16. **Network Switch Monitor** ⭐⭐⭐⭐
**Category**: Network  
**What it monitors**:
- Port status and link speeds
- Traffic per port
- PoE usage and budget
- VLAN configurations
- Spanning tree status
- Switch CPU/memory

**Why homelabbers need this**: Network is infrastructure. Switch health = network health.

---

### 17. **Wireguard/Tailscale Monitor** ⭐⭐⭐⭐
**Category**: Network  
**What it monitors**:
- Active mesh connections
- Peer connectivity status
- Latency between nodes
- Exit node status
- Subnet router health

**Why homelabbers need this**: Modern VPNs are mesh networks. Visibility matters.

---

### 18. **Email Server Monitor** ⭐⭐⭐
**Category**: Application  
**What it monitors**:
- Postfix, Dovecot, Mail-in-a-Box status
- Queue size and stuck emails
- DKIM/SPF/DMARC status
- Spam filter effectiveness
- Mailbox sizes
- Delivery success rates

**Why homelabbers need this**: Email is hard. Self-hosting email is harder. Monitoring is essential.

---

### 19. **Minecraft/Game Server Monitor** ⭐⭐⭐
**Category**: Application  
**What it monitors**:
- Server online status
- Player counts
- TPS (ticks per second)
- Memory usage
- Mod/plugin status
- World backup status

**Why homelabbers need this**: Gaming is a legitimate homelab use case. Friends appreciate uptime.

---

### 20. **Photoprism/Immich Monitor** ⭐⭐⭐
**Category**: Application  
**What it monitors**:
- Instance status and health
- Photo library size
- Indexing progress
- Storage usage
- Face recognition stats
- Duplicate detection

**Why homelabbers need this**: Photos are memories. Monitoring protects them.

---

## 🔮 Tier 4: Advanced/Specialized Needs

### 21. **IPMI/iDRAC/iLO Monitor** ⭐⭐⭐⭐
**Category**: System  
**What it monitors**:
- Out-of-band management status
- Hardware health via BMC
- Fan speeds and power supply status
- Remote console availability
- Firmware versions

**Why homelabbers need this**: Enterprise hardware needs enterprise monitoring.

---

### 22. **Tor Relay Monitor** ⭐⭐
**Category**: Network  
**What it monitors**:
- Relay status and bandwidth
- Consensus health
- Exit policy compliance
- Guard/middle/exit designation

**Why homelabbers need this**: Supporting privacy infrastructure deserves monitoring.

---

### 23. **Mastodon/Fediverse Monitor** ⭐⭐⭐
**Category**: Application  
**What it monitors**:
- Instance health and federation status
- User counts and activity
- Media storage usage
- Sidekiq queue health
- Database performance

**Why homelabbers need this**: Self-hosted social media is growing. Reliability matters.

---

### 24. **Bitwarden/Vaultwarden Monitor** ⭐⭐⭐⭐
**Category**: Security  
**What it monitors**:
- Vault service status
- Active sessions
- Failed login attempts
- Database backup status
- 2FA usage stats

**Why homelabbers need this**: Password managers are critical infrastructure. Downtime is unacceptable.

---

### 25. **Syncthing Monitor** ⭐⭐⭐
**Category**: Storage  
**What it monitors**:
- Sync status across devices
- Folder sync states
- Conflict detection
- Bandwidth usage
- Device connectivity

**Why homelabbers need this**: P2P sync is elegant. Knowing it's working is peace of mind.

---

### 26. **Network Bandwidth Monitor** ⭐⭐⭐⭐
**Category**: Network  
**What it monitors**:
- WAN bandwidth usage
- Per-service bandwidth tracking
- ISP connection quality
- Data cap warnings
- Historical usage trends

**Why homelabbers need this**: Bandwidth caps are real. Knowing usage prevents overage fees.

---

### 27. **Prometheus/Grafana Monitor** ⭐⭐⭐
**Category**: Monitoring  
**What it monitors**:
- Prometheus scrape health
- Query performance
- Storage usage
- Retention policy status
- Grafana dashboard load times

**Why homelabbers need this**: Meta-monitoring. Monitoring the monitoring.

---

### 28. **IoT Device Monitor** ⭐⭐⭐
**Category**: IoT  
**What it monitors**:
- Zigbee/Z-Wave coordinator health
- Device battery levels
- Connectivity status
- Firmware versions
- Signal strength

**Why homelabbers need this**: IoT devices are everywhere. Knowing when batteries die = happy spouse.

---

### 29. **Paperless-ngx Monitor** ⭐⭐⭐
**Category**: Application  
**What it monitors**:
- Document ingestion status
- OCR queue length
- Storage usage
- Consumer health
- Search index status

**Why homelabbers need this**: Document management is liberation from paper chaos. Keep it running.

---

### 30. **Matrix/Synapse Monitor** ⭐⭐⭐
**Category**: Application  
**What it monitors**:
- Homeserver status
- Room counts and federation
- Database size
- Media storage usage
- Registration stats

**Why homelabbers need this**: Self-hosted chat is the dream. Monitoring makes it stable.

---

## 📊 Category Summary

| Category | Plugin Count | Priority Level |
|----------|-------------|----------------|
| Storage | 4 | Critical |
| Security | 4 | Critical |
| Network | 7 | High |
| Application | 11 | High |
| System | 3 | Medium |
| Container | 1 | Medium |
| IoT | 2 | Medium |
| Power | 1 | Critical |
| Monitoring | 1 | Meta |

---

## 🎯 Implementation Priority Order

### Phase 1: Absolute Essentials (Do These First)
1. UPS Monitor
2. Backup Monitor
3. Certificate Expiration Monitor
4. SMART Disk Health Monitor
5. Reverse Proxy Monitor

### Phase 2: Quality of Life
6. DNS Monitor
7. VPN Monitor
8. Media Server Monitor
9. Network Bandwidth Monitor
10. Bitwarden/Vaultwarden Monitor

### Phase 3: Power Users
11. ZFS/BTRFS Monitor
12. Kubernetes Monitor
13. IPMI/iDRAC Monitor
14. Network Switch Monitor
15. Temperature/Environmental Monitor

### Phase 4: Application-Specific
16. Home Assistant Monitor
17. Nextcloud Monitor
18. Git Server Monitor
19. Download Manager Monitor
20. Photoprism/Immich Monitor

### Phase 5: Specialized Use Cases
21-30: Based on individual homelab needs

---

## 💡 Plugin Development Notes

**For each new plugin, remember to**:
- Create the plugin file
- Add comprehensive metadata
- Write unit tests
- Document in BUILTIN_PLUGINS.md (one at a time!)
- Add to plugin showcase HTML
- Test with validator tool

**Dependencies to consider**:
- Most will need Python clients for the services they monitor
- Some may require system-level tools (smartctl, ipmitool, etc.)
- API access for cloud-connected services

---

## 🌟 Community Suggestions Welcome

This is a living document. If you're a homelabber and have plugin ideas, contribute them!

**GitHub Discussions**: [Unity Plugin Ideas](https://github.com/mylaniakea/unity/discussions)

---

*"A homelab without monitoring is just a collection of servers waiting to surprise you."*

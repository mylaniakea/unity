# VPN Mesh Monitor Plugin

## Overview
The **VPN Mesh Monitor** tracks WireGuard and Tailscale mesh networks. Peer-to-peer networking, professionally monitored!

## Features
- WireGuard peer tracking
- Tailscale device monitoring
- Handshake freshness detection
- Transfer statistics
- Online/offline peer tracking

## Configuration

### WireGuard
```yaml
plugins:
  vpn-mesh-monitor:
    enabled: true
    config:
      type: "wireguard"
      interface: "wg0"
```

### Tailscale
```yaml
plugins:
  vpn-mesh-monitor:
    enabled: true
    config:
      type: "tailscale"
```

## Requirements
- For WireGuard: `wg` command and active interface
- For Tailscale: `tailscale` CLI and running daemon
- Sudo access (may be required for WireGuard)

## Metrics Collected

### WireGuard
- Total/active/inactive peer counts
- Latest handshake times
- Transfer RX/TX bytes per peer
- Endpoint addresses

### Tailscale
- Total/online/offline peer counts
- Device hostnames and IPs
- Backend state
- Last seen timestamps

## Use Cases
- Mesh network health monitoring
- Peer connectivity tracking
- Tunnel failure detection
- Multi-site VPN monitoring

## Example Output

### WireGuard
```json
{
  "summary": {
    "total_peers": 5,
    "active_peers": 4,
    "inactive_peers": 1
  },
  "peers": [...]
}
```

### Tailscale
```json
{
  "summary": {
    "total_peers": 8,
    "online_peers": 7,
    "backend_state": "Running"
  }
}
```

## Tips
- WireGuard: peers active if handshake < 3min
- Monitor handshake times for connectivity issues
- Track peer churn for network stability
- Alert on critical peer disconnections

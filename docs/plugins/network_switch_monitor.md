# Network Switch Monitor Plugin

## Overview
The **Network Switch Monitor** tracks managed switches via SNMP. For the homelabber who VLANs everything!

## Features
- SNMP v1/v2c/v3 support
- Port status monitoring (up/down)
- Device uptime tracking
- System information collection
- Multi-switch support

## Configuration
```yaml
plugins:
  network-switch-monitor:
    enabled: true
    config:
      host: "192.168.1.1"
      community: "public"
      version: "2c"
      port: 161
```

## Requirements
- `snmpwalk` and `snmpget` commands (net-snmp package)
- SNMP enabled on switch
- Community string or credentials

## Metrics Collected
- Total/up/down port counts
- Interface names and statuses
- System description and hostname
- Device uptime
- Interface operational states

## Use Cases
- Port monitoring and alerting
- Network topology tracking
- Switch health verification
- Uptime monitoring

## Example Output
```json
{
  "summary": {
    "total_ports": 24,
    "up_ports": 18,
    "down_ports": 6
  },
  "hostname": "core-switch-01",
  "uptime_human": "45d 3h 22m",
  "interfaces": [...]
}
```

## Tips
- Use SNMPv3 for better security
- Monitor critical uplinks separately
- Track port flapping with time-series data
- Set alerts for unexpected port down events

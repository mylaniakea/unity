# IPMI/BMC Monitor Plugin

## Overview
The **IPMI/BMC Monitor** tracks server hardware via out-of-band management. Out-of-band monitoring for in-band peace of mind!

## Features
- Temperature sensor monitoring
- Fan speed tracking
- Voltage monitoring
- Power status verification
- System Event Log (SEL) tracking
- Works with iDRAC, iLO, and standard IPMI BMCs

## Configuration
```yaml
plugins:
  ipmi-monitor:
    enabled: true
    config:
      host: "192.168.1.100"
      username: "admin"
      password: "your-password"
      interface: "lanplus"  # or "lan"
```

## Requirements
- `ipmitool` installed
- BMC configured with network access
- IPMI credentials

## Metrics Collected
- All sensor readings (temperature, fan, voltage, power)
- Chassis power status
- System event log entry count
- Per-sensor health status
- Overall hardware health

## Use Cases
- Hardware failure detection
- Temperature alerts
- Fan failure monitoring
- Power state tracking
- Remote server monitoring

## Example Output
```json
{
  "summary": {
    "power_on": true,
    "temperature_sensors": 8,
    "fan_sensors": 6,
    "sel_entries": 42,
    "healthy": true
  },
  "sensors": [
    {"name": "CPU1 Temp", "value": "45", "units": "degrees C", "status": "ok"}
  ],
  "power": {"status": "on"}
}
```

## Tips
- Use lanplus for IPMI 2.0 features
- Keep BMC firmware updated
- Monitor SEL for hardware warnings
- Set temperature thresholds for alerts
- Store passwords securely

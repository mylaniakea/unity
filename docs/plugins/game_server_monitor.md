# Game Server Monitor Plugin

## Overview
The **Game Server Monitor** tracks game servers. Because homelabbing and gaming aren't mutually exclusive!

## Features
- Minecraft server monitoring
- Valheim server monitoring (Steam query)
- Generic TCP port checks
- Connection timeout detection
- Multi-game support

## Configuration

### Minecraft
```yaml
plugins:
  game-server-monitor:
    enabled: true
    config:
      game: "minecraft"
      host: "192.168.1.100"
      port: 25565
      timeout: 5
```

### Valheim
```yaml
plugins:
  game-server-monitor:
    enabled: true
    config:
      game: "valheim"
      host: "192.168.1.101"
      port: 2456
      timeout: 5
```

### Generic
```yaml
plugins:
  game-server-monitor:
    enabled: true
    config:
      game: "generic"
      host: "192.168.1.102"
      port: 7777
      timeout: 5
```

## Requirements
- Reachable game server
- No external dependencies

## Metrics Collected
- Server online/offline status
- Reachability checks
- Connection errors

## Use Cases
- Game night readiness checks
- Server uptime monitoring
- Quick status verification
- Multi-server tracking

## Example Output
```json
{
  "game": "minecraft",
  "host": "192.168.1.100",
  "port": 25565,
  "summary": {
    "online": true,
    "reachable": true
  }
}
```

## Tips
- Use generic mode for unsupported games
- Set reasonable timeouts for slow networks
- Monitor multiple game servers with separate configs
- Track server downtime for SLA monitoring
- Combine with container monitoring for hosted servers

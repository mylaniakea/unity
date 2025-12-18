# Kubernetes Monitor Plugin

## Overview
The **Kubernetes Monitor** tracks your Kubernetes cluster health, nodes, pods, and resource distribution. For those brave souls running K8s at home!

## Features
- Node status and readiness tracking
- Pod phase monitoring across all namespaces
- Namespace distribution analysis
- Multi-context support
- Custom kubeconfig support

## Configuration
```yaml
plugins:
  kubernetes-monitor:
    enabled: true
    config:
      kubeconfig: "/home/user/.kube/config"  # Optional: custom kubeconfig
      context: "home-cluster"                 # Optional: specific context
```

## Requirements
- `kubectl` installed and configured
- Access to Kubernetes cluster (kubeconfig)

## Metrics Collected
- Total nodes and ready nodes
- Pods by phase (Running, Pending, Failed, Succeeded)
- Pod distribution across namespaces
- Node capacity (CPU, memory)
- Kubernetes versions

## Use Cases
- Cluster health at-a-glance
- Pod restart detection
- Node availability monitoring
- Multi-cluster management

## Example Output
```json
{
  "summary": {
    "total_nodes": 3,
    "ready_nodes": 3,
    "total_pods": 42,
    "running_pods": 38,
    "pending_pods": 2,
    "failed_pods": 0,
    "namespaces": 8
  },
  "nodes": [...],
  "pod_stats": {...}
}
```

## Tips
- Use different contexts for multiple clusters
- Monitor failed pods for issues
- Track namespace growth over time
- Alert on node not ready conditions

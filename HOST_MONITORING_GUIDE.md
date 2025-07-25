# Host System Monitoring for Kubernetes AI Agent

## Overview

The Kubernetes AI Agent now has full capability to execute Linux commands on the host node and collect comprehensive system and GlusterFS statistics. This is achieved through a privileged container with extensive host access.

## Architecture

### Container Privileges
- **Privileged Mode**: Full privileged container execution
- **Host Network**: Direct access to host networking stack
- **Host PID**: Access to host process namespace
- **Capabilities**: SYS_ADMIN, SYS_PTRACE, NET_ADMIN, SYS_CHROOT, SETUID, SETGID, DAC_OVERRIDE, FOWNER, SYS_RESOURCE

### Host Access Methods

#### 1. Namespace Execution (Primary)
- Uses `nsenter` to execute commands in host namespaces
- Command: `nsenter -t 1 -m -u -i -n -p <command>`
- Provides full host system access

#### 2. Chroot Execution (Fallback)
- Uses `chroot /host <command>` for host filesystem access
- Fallback when nsenter is not available

#### 3. Direct Command Symlinks
- Creates symlinks to host commands in container
- Available commands: gluster, glusterd, df, lsblk, mount, ps, top, htop, iostat, sar, vmstat, free, lscpu, lsof, netstat, ss, iptables

## Host Volume Mounts

### System Access Volumes
```yaml
- /host -> /                    # Full host root filesystem
- /host/proc -> /proc          # Host process information
- /host/sys -> /sys            # Host system information
- /host/var/lib -> /var/lib    # Host libraries and data
- /host/usr/bin -> /usr/bin    # Host user binaries
- /host/usr/sbin -> /usr/sbin  # Host system binaries
- /host/etc -> /etc            # Host configuration files
- /host/run -> /run            # Host runtime data
- /host/tmp -> /tmp            # Host temporary files
```

### GlusterFS Specific Volumes
```yaml
- /var/log/glusterfs           # GlusterFS logs
- /var/lib/glusterd            # GlusterFS daemon data
```

## Command Execution Framework

### Helper Scripts

#### `/usr/local/bin/host-exec`
```bash
#!/bin/bash
# Execute commands in host namespaces
if [ -f "/usr/local/bin/nsenter" ]; then
    exec nsenter -t 1 -m -u -i -n -p "$@"
else
    exec chroot /host "$@"
fi
```

#### `/usr/local/bin/gluster-exec`
```bash
#!/bin/bash
# Execute GlusterFS commands with proper environment
export PATH="/usr/sbin:/usr/bin:/sbin:/bin"
if [ -f "/usr/local/bin/nsenter" ]; then
    exec nsenter -t 1 -m -u -i -n -p gluster "$@"
else
    exec chroot /host gluster "$@"
fi
```

## System Statistics Collection

### CPU Statistics
- **CPU Usage Percentage**: Calculated from /proc/stat
- **Load Average**: 1, 5, and 15-minute load averages
- **CPU Core Information**: From lscpu command

### Memory Statistics
- **Memory Usage**: Total, used, free, available, buffers, cached
- **Source**: /proc/meminfo (converted to bytes)
- **Swap Information**: Swap total, used, free

### Disk Statistics
- **Disk Usage**: Size, used, available, usage percentage per mount point
- **I/O Statistics**: Reads/writes completed, sectors read/written, I/O time
- **Source**: df command + /proc/diskstats

### Network Statistics
- **Interface Statistics**: RX/TX bytes, packets, errors, dropped
- **Source**: /proc/net/dev
- **Network Connections**: Active connections via netstat/ss

### Process Statistics
- **Process Count**: Total, running, sleeping processes
- **Top Processes**: CPU and memory usage by process
- **Source**: ps command

## GlusterFS Statistics Collection

### Volume Information
```python
{
    "volume_name": {
        "status": "Started|Stopped|Created",
        "brick_count": "number",
        "replica_count": "number",
        "type": "Distribute|Replicate|Stripe"
    }
}
```

### Peer Status
```python
{
    "hostname": {
        "state": "Peer in Cluster|Peer Rejected|Connected",
        "uuid": "peer_uuid"
    }
}
```

### Heal Information
- Self-heal status per volume
- Entries needing heal
- Heal completion status

### Brick Status
- Brick health per volume
- Disk usage per brick
- I/O statistics per brick

## Python API Usage

### Basic Usage
```python
from agent.host_system_monitor import HostSystemMonitor

# Initialize monitor
monitor = HostSystemMonitor()

# Collect all statistics
stats = monitor.collect_all_stats()

# Individual statistics
system_stats = monitor.get_system_stats()
gluster_stats = monitor.get_glusterfs_stats()
```

### Integration with Kubernetes Monitor
```python
from agent.monitor import KubernetesMonitor

# Initialize with host monitoring
k8s_monitor = KubernetesMonitor()

# Get comprehensive stats (K8s + Host)
comprehensive_stats = k8s_monitor.get_comprehensive_stats()

# Host-only stats
host_stats = k8s_monitor.get_host_system_stats()
```

## Security Considerations

### Privileges Required
- **Container**: Must run as privileged with root user
- **Capabilities**: Extensive system capabilities required
- **Host Access**: Full host filesystem and namespace access

### Risk Mitigation
- **RBAC**: Proper Kubernetes RBAC configuration
- **Service Account**: Dedicated service account with minimal required permissions
- **Audit Logging**: All host command executions are logged
- **User Switching**: Application can run as non-root user for normal operations

## Deployment Configuration

### Kubernetes Deployment
```yaml
securityContext:
  privileged: true
  runAsUser: 0
  capabilities:
    add: ["SYS_ADMIN", "SYS_PTRACE", "NET_ADMIN", "SYS_CHROOT", "SETUID", "SETGID"]
hostNetwork: true
hostPID: true
```

### Environment Variables
```yaml
env:
  - name: HOST_MONITORING_ENABLED
    value: "true"
  - name: GLUSTER_MONITORING_ENABLED
    value: "true"
```

## Monitoring Output Example

```json
{
  "timestamp": "2025-07-22T10:30:00Z",
  "system": {
    "cpu_usage_percent": 25.5,
    "memory": {
      "MemTotal": 8589934592,
      "MemFree": 2147483648,
      "MemAvailable": 6442450944
    },
    "disks": [
      {
        "device": "/dev/sda1",
        "filesystem": "ext4",
        "size": "100G",
        "used": "50G",
        "available": "45G",
        "usage_percent": "53%",
        "mount_point": "/"
      }
    ],
    "network": {
      "eth0": {
        "rx_bytes": 1073741824,
        "tx_bytes": 536870912,
        "rx_packets": 1000000,
        "tx_packets": 500000
      }
    },
    "load_average": [1.5, 1.2, 1.0]
  },
  "glusterfs": {
    "volumes": {
      "gv0": {
        "status": "Started",
        "brick_count": "4",
        "type": "Replicate"
      }
    },
    "peers": {
      "gluster-node-2": {
        "state": "Peer in Cluster"
      }
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Host commands not found**
   - Check host volume mounts
   - Verify nsenter availability
   - Check PATH environment in container

2. **Permission denied**
   - Ensure privileged mode is enabled
   - Verify required capabilities
   - Check RBAC permissions

3. **GlusterFS commands fail**
   - Check if GlusterFS is installed on host
   - Verify gluster daemon is running
   - Check GlusterFS service status

### Debug Commands
```bash
# Check host access
kubectl exec -it k8s-ai-agent -- /usr/local/bin/host-exec ps aux

# Test GlusterFS access
kubectl exec -it k8s-ai-agent -- /usr/local/bin/gluster-exec volume info

# Check mounted volumes
kubectl exec -it k8s-ai-agent -- ls -la /host/

# Verify capabilities
kubectl exec -it k8s-ai-agent -- capsh --print
```

## Performance Impact

### Resource Usage
- **CPU**: Minimal overhead for statistics collection
- **Memory**: ~50MB additional for host monitoring
- **Network**: Negligible impact
- **Storage**: Log files for command execution history

### Execution Frequency
- **System Stats**: Every 30 seconds
- **GlusterFS Stats**: Every 60 seconds
- **On-Demand**: Available via API calls

This comprehensive host system monitoring capability provides complete visibility into both the Kubernetes cluster and the underlying host infrastructure, enabling advanced analysis and remediation capabilities.

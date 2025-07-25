# GlusterFS Node Access and Cleanup Summary

## Changes Made for Node-Level File Access

### 1. Kubernetes Deployment Updates (`k8s/k8s-ai-agent.yaml`)

**Privileged Security Context:**
- Added `hostNetwork: true` and `hostPID: true` for host-level access
- Configured `securityContext` with `privileged: true` and `runAsUser: 0`
- Added `SYS_ADMIN`, `SYS_PTRACE`, `NET_ADMIN` capabilities

**Host Volume Mounts:**
- `/host/proc` - Access to host processes
- `/host/sys` - Access to host system information
- `/host/var/lib` - Access to host libraries and data
- `/host/usr/bin` and `/host/usr/sbin` - Access to host commands
- `/host/etc` - Access to host configuration
- `/var/log/glusterfs` - GlusterFS log directory
- `/var/lib/glusterd` - GlusterFS daemon data

### 2. RBAC Enhancements (`k8s/02-rbac.yaml`)

**Additional Permissions:**
- Node proxy, stats, log, spec, and metrics access
- OpenShift SecurityContextConstraints support for privileged containers

### 3. Docker Container Updates

**Dockerfile Changes:**
- Added GlusterFS client tools (`glusterfs-client`, `glusterfs-common`)
- Added system utilities (`procps`, `util-linux`)
- Added `su-exec` for user switching in privileged mode
- Created custom entrypoint script for privilege handling

**Entrypoint Script (`docker-entrypoint.sh`):**
- Detects privileged vs non-privileged mode
- Sets up host command paths when running as root
- Creates symlinks to host GlusterFS commands
- Supports running as k8s-agent user when needed

### 4. Application Code Updates

**GlusterFS Analyzer Enhancement:**
- Updated to check for host-mounted GlusterFS commands
- Priority order: `/usr/local/bin/gluster` → `/host/usr/bin/gluster` → `/host/usr/sbin/gluster` → `gluster`
- Improved logging for command detection

### 5. Requirements Updates

**Added Dependencies:**
- `lxml>=5.1.0` for XML parsing of GlusterFS output
- `psutil>=5.9.0` for enhanced system monitoring

## Cleanup Operations Performed

### 1. Temporary File Removal
- Removed all `__pycache__` directories from project (excluding .venv)
- Deleted all `.pyc` and `.pyo` compiled Python files
- Removed application log file (`k8s_ai_assistant.log`)

### 2. Cache Cleanup
- Cleared Python bytecode cache files
- Maintained virtual environment integrity

## Usage Modes

### Privileged Mode (Full GlusterFS Access)
```yaml
securityContext:
  privileged: true
  runAsUser: 0
```
- Full host filesystem access
- GlusterFS commands available via host mounts
- Can execute system-level operations

### Non-Privileged Mode (Limited Access)
```yaml
securityContext:
  runAsUser: 1000
```
- Standard container security
- Mock data when GlusterFS unavailable
- Graceful degradation

## Deployment Command

For privileged deployment with GlusterFS access:
```bash
kubectl apply -f k8s/02-rbac.yaml
kubectl apply -f k8s/k8s-ai-agent.yaml
```

The pod will automatically detect available GlusterFS commands and adapt accordingly.

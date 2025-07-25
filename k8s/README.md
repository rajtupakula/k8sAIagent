# K8s AI Agent Deployment

Simple Kubernetes deployment following etcd/kafka patterns.

## Files

- `k8s-ai-agent.yaml` - Main application manifest with ConfigMap, Service, PersistentVolumes, and Deployment
- `02-rbac.yaml` - ServiceAccount and RBAC configuration
- `deploy-simple.sh` - Simple deployment script

## Configuration

The ConfigMap includes runtime arguments needed by the application:
- **mode**: "interactive" (operational mode)
- **automation_level**: "semi_auto" (automation level)
- **confidence_threshold**: "80" (confidence threshold)
- **historical_learning**: "true" (enable historical learning)
- **predictive_analysis**: "true" (enable predictive analysis)
- **safety_checks**: "true" (enable safety checks)
- **ui_always_interactive**: "true" (UI behavior)

All configurations are available as both individual keys and a complete config.yaml file.

## Quick Deploy

```bash
./deploy-simple.sh
```

## Manual Deploy

```bash
# Apply RBAC
kubectl apply -f 02-rbac.yaml

# Deploy application
kubectl apply -f k8s-ai-agent.yaml

# Check status
kubectl get pods -l app=k8s-ai-agent
kubectl logs -l app=k8s-ai-agent -f
```

## Clean Up

```bash
kubectl delete -f k8s-ai-agent.yaml
kubectl delete -f 02-rbac.yaml
```

### Individual Component Files
- **`namespace.yaml`** - Namespace definitions
- **`rbac.yaml`** - Service accounts, roles, and bindings
- **`secrets.yaml`** - Docker registry secrets and API keys
- **`deployment.yaml`** - Main application deployment
- **`service-enhanced.yaml`** - Service definitions (ClusterIP, NodePort, Headless)
- **`pvc.yaml`** - Persistent volume claims for storage
- **`hpa.yaml`** - Horizontal Pod Autoscaler and Pod Disruption Budget
- **`ingress.yaml`** - Ingress and Network Policy
- **`monitoring.yaml`** - ServiceMonitor and PrometheusRule for monitoring
- **`jobs.yaml`** - Initialization and maintenance jobs

### Legacy Files
- **`pod.yaml`** - Simple pod deployment (development only)
- **`service.yaml`** - Basic service definition
- **`runtime-configmap.yaml`** - Runtime configuration

## 🚀 Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
# Make the deployment script executable
chmod +x k8s/deploy.sh

# Deploy with default settings
./k8s/deploy.sh

# Deploy with specific image tag
./k8s/deploy.sh --tag 1.0.0-52

# Production deployment with monitoring
./k8s/deploy.sh --tag 1.0.0-52 --deployment production

# Dry run to see what would be deployed
./k8s/deploy.sh --dry-run
```

### Option 2: Manual Deployment

```bash
# Deploy complete stack
kubectl apply -f k8s/k8s-ai-agent-complete.yaml

# Add production features (optional)
kubectl apply -f k8s/k8s-ai-agent-production.yaml
```

## 🏗️ Architecture

### Components Deployed

1. **Namespace**: `k8s-ai-system`
2. **ServiceAccount**: `k8s-ai-agent` with ClusterRole permissions
3. **Deployment**: Main AI Agent application
4. **Services**: 
   - ClusterIP for internal communication
   - NodePort for external access
5. **Storage**: PersistentVolumeClaims for models and data
6. **ConfigMap**: Runtime configuration
7. **Secrets**: Docker registry authentication
8. **HPA**: Auto-scaling based on CPU/memory
9. **Network Policy**: Security controls
10. **Monitoring**: Prometheus ServiceMonitor and alerting rules

### Resource Requirements

| Component | CPU Request | Memory Request | CPU Limit | Memory Limit |
|-----------|-------------|----------------|-----------|--------------|
| AI Agent  | 500m        | 2Gi           | 2000m     | 8Gi          |
| Init Job  | 250m        | 512Mi         | 1000m     | 2Gi          |

### Storage Requirements

| Volume | Size | Storage Class | Purpose |
|--------|------|---------------|---------|
| Models | 50Gi | fast-ssd      | AI models and embeddings |
| Data   | 20Gi | standard      | Training data and logs |
| Cache  | 5Gi  | emptyDir      | Temporary cache |

## 🔧 Configuration

### Environment Variables

The deployment uses the following key environment variables:

- `KUBERNETES_NAMESPACE`: Current namespace
- `POD_NAME`: Pod name
- `POD_IP`: Pod IP address  
- `NODE_NAME`: Node name
- `CONFIG_PATH`: Configuration path
- `LOG_LEVEL`: Logging level

### ConfigMap Settings

Key configuration options in `k8s-ai-runtime-config`:

```yaml
mode: "interactive"                    # Operation mode
automation_level: "semi_auto"         # Automation level
confidence_threshold: "80"            # Confidence threshold
historical_learning: "true"           # Enable learning
predictive_analysis: "true"           # Enable predictions
continuous_monitoring: "true"         # Enable monitoring
safety_checks: "true"                 # Enable safety checks
```

## 🌐 Access Methods

### 1. NodePort Access (Default)

```bash
# Get NodePort values
kubectl get svc k8s-ai-agent-nodeport -n k8s-ai-system

# Access URLs (replace <node-ip> with actual node IP)
# Dashboard: http://<node-ip>:30501
# API: http://<node-ip>:30080
# Health: http://<node-ip>:30000
```

### 2. Port Forward (Development)

```bash
# Dashboard
kubectl port-forward svc/k8s-ai-agent 8501:8501 -n k8s-ai-system

# API
kubectl port-forward svc/k8s-ai-agent 8080:8080 -n k8s-ai-system

# Access: http://localhost:8501 (dashboard) or http://localhost:8080 (api)
```

### 3. Ingress (Production)

When using the production deployment:

```bash
# Check Ingress status
kubectl get ingress k8s-ai-agent-ingress -n k8s-ai-system

# Access via configured domains:
# https://k8s-ai.cisco.com
# https://ai-agent.k8s.local
```

## 📊 Monitoring

### Prometheus Metrics

The AI Agent exposes metrics on port 9090 at `/metrics`. Key metrics include:

- Application health and performance
- Resource utilization
- AI model inference times
- Kubernetes API interactions

### Grafana Dashboard

A Grafana dashboard configuration is included in the monitoring manifests.

### Alerts

Pre-configured Prometheus alerts:

- **K8sAIAgentDown**: Agent is unavailable
- **K8sAIAgentHighMemory**: Memory usage > 90%
- **K8sAIAgentHighCPU**: CPU usage > 150%
- **K8sAIAgentRestartLoop**: Frequent restarts
- **K8sAIAgentPVCSpaceLow**: Storage < 10%

## 🔐 Security

### Security Features

1. **Non-root containers**: Runs as user 1000
2. **Read-only root filesystem**: Where possible
3. **Dropped capabilities**: All capabilities dropped
4. **Security contexts**: Applied at pod and container level
5. **Network policies**: Restrict network access
6. **RBAC**: Minimal required permissions
7. **Pod Security Standards**: Compatible with restricted policies

### RBAC Permissions

The AI Agent has permissions to:

- Read/write pods, nodes, deployments, services
- Access metrics and monitoring data
- Manage jobs and cronjobs
- Read storage and network resources

## 🔄 Updates and Maintenance

### Rolling Updates

The deployment supports rolling updates with zero downtime:

```bash
# Update image tag
kubectl set image deployment/k8s-ai-agent ai-agent=dockerhub.cisco.com/robot-dockerprod/k8s-ai-agent:1.0.0-53 -n k8s-ai-system

# Check rollout status
kubectl rollout status deployment/k8s-ai-agent -n k8s-ai-system
```

### Automatic Maintenance

A CronJob runs daily at 2 AM to:

- Clean up old logs (> 7 days)
- Clear temporary cache files
- Monitor storage usage

### Model Updates

Use the model initialization job to update AI models:

```bash
# Delete existing job (if any)
kubectl delete job k8s-ai-agent-init-models -n k8s-ai-system

# Reapply to run again
kubectl apply -f k8s/k8s-ai-agent-production.yaml
```

## 🐛 Troubleshooting

### Common Issues

1. **Pod not starting**
   ```bash
   kubectl describe pod -l app=k8s-ai-agent -n k8s-ai-system
   kubectl logs -l app=k8s-ai-agent -n k8s-ai-system
   ```

2. **Image pull errors**
   ```bash
   # Check secret
   kubectl get secret cisco-dockerhub-secret -n k8s-ai-system
   
   # Recreate secret with correct credentials
   kubectl create secret docker-registry cisco-dockerhub-secret \
     --docker-server=dockerhub.cisco.com \
     --docker-username=<username> \
     --docker-password=<password> \
     -n k8s-ai-system
   ```

3. **Storage issues**
   ```bash
   # Check PVCs
   kubectl get pvc -n k8s-ai-system
   
   # Check storage classes
   kubectl get storageclass
   ```

4. **Service not accessible**
   ```bash
   # Check services
   kubectl get svc -n k8s-ai-system
   
   # Check endpoints
   kubectl get endpoints -n k8s-ai-system
   ```

### Debugging Commands

```bash
# Get all resources
kubectl get all -n k8s-ai-system

# Check events
kubectl get events -n k8s-ai-system --sort-by='.lastTimestamp'

# Pod shell access
kubectl exec -it deployment/k8s-ai-agent -n k8s-ai-system -- /bin/bash

# Check logs
kubectl logs -f deployment/k8s-ai-agent -n k8s-ai-system

# Check resource usage
kubectl top pods -n k8s-ai-system
```

## 🗑️ Cleanup

### Remove Everything

```bash
# Delete all resources
kubectl delete -f k8s/k8s-ai-agent-complete.yaml
kubectl delete -f k8s/k8s-ai-agent-production.yaml

# Or delete the entire namespace
kubectl delete namespace k8s-ai-system
```

### Selective Cleanup

```bash
# Remove just the deployment
kubectl delete deployment k8s-ai-agent -n k8s-ai-system

# Remove storage (WARNING: This deletes all data)
kubectl delete pvc -l app=k8s-ai-agent -n k8s-ai-system
```

## 📝 Customization

### Image Tag

Update the image tag in the manifests:

```bash
# Using sed
sed -i 's|k8s-ai-agent:.*|k8s-ai-agent:1.0.0-53|g' k8s/k8s-ai-agent-complete.yaml

# Or use the deployment script
./k8s/deploy.sh --tag 1.0.0-53
```

### Resource Limits

Modify the `resources` section in the deployment:

```yaml
resources:
  requests:
    memory: "4Gi"    # Increase memory request
    cpu: "1000m"     # Increase CPU request
  limits:
    memory: "16Gi"   # Increase memory limit
    cpu: "4000m"     # Increase CPU limit
```

### Storage Size

Modify PVC sizes:

```yaml
resources:
  requests:
    storage: 100Gi   # Increase storage size
```

### Replicas

For high availability, increase replicas:

```yaml
spec:
  replicas: 3        # Run 3 instances
```

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review application logs: `kubectl logs -f deployment/k8s-ai-agent -n k8s-ai-system`
3. Check Kubernetes events: `kubectl get events -n k8s-ai-system`
4. Contact the platform team with deployment details

---

**Note**: Replace placeholder values (like `<username>`, `<password>`, `<node-ip>`) with actual values for your environment.

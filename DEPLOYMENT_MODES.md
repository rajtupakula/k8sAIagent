# Kubernetes AI Assistant - Multi-Mode Deployment Guide

## Overview

The Kubernetes AI Assistant now supports 5 distinct operational modes, each optimized for different use cases and deployment scenarios. This guide explains how to deploy and configure each mode.

## Operational Modes

### 1. 🔍 Debug Mode
**Purpose**: Root cause analysis and deep diagnostics without automatic remediation.

**Use Cases**:
- Troubleshooting complex issues
- Learning about system behavior
- Safe environment exploration
- Forensic analysis

**Configuration**:
```bash
# Environment Variables
K8S_AI_MODE=debug
K8S_AI_AUTOMATION_LEVEL=manual
K8S_AI_CONFIDENCE_THRESHOLD=95
K8S_AI_HISTORICAL_LEARNING=true
K8S_AI_PREDICTIVE_ANALYSIS=true
K8S_AI_CONTINUOUS_MONITORING=false
K8S_AI_AUTO_REMEDIATION=false
```

**Deployment Example**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-ai-debug
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: k8s-ai-assistant
        image: k8s-ai-assistant:latest
        env:
        - name: K8S_AI_MODE
          value: "debug"
        - name: K8S_AI_AUTOMATION_LEVEL
          value: "manual"
        ports:
        - containerPort: 8501
```

### 2. 🔧 Remediation Mode
**Purpose**: Automatic issue resolution with confidence-based decision making.

**Use Cases**:
- Production environments with trusted automation
- Automated incident response
- Self-healing clusters
- Proactive maintenance

**Configuration**:
```bash
# Environment Variables
K8S_AI_MODE=remediation
K8S_AI_AUTOMATION_LEVEL=full_auto
K8S_AI_CONFIDENCE_THRESHOLD=85
K8S_AI_HISTORICAL_LEARNING=true
K8S_AI_PREDICTIVE_ANALYSIS=true
K8S_AI_CONTINUOUS_MONITORING=true
K8S_AI_AUTO_REMEDIATION=true
```

**Deployment Example**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-ai-remediation
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: k8s-ai-assistant
        image: k8s-ai-assistant:latest
        env:
        - name: K8S_AI_MODE
          value: "remediation"
        - name: K8S_AI_AUTOMATION_LEVEL
          value: "full_auto"
        - name: K8S_AI_CONFIDENCE_THRESHOLD
          value: "85"
        - name: K8S_AI_AUTO_REMEDIATION
          value: "true"
```

### 3. 💬 Interactive Mode
**Purpose**: User-driven operations with confirmation for all actions.

**Use Cases**:
- Development environments
- Learning and training
- Manual oversight required
- Step-by-step guidance

**Configuration**:
```bash
# Environment Variables
K8S_AI_MODE=interactive
K8S_AI_AUTOMATION_LEVEL=semi_auto
K8S_AI_CONFIDENCE_THRESHOLD=75
K8S_AI_HISTORICAL_LEARNING=true
K8S_AI_PREDICTIVE_ANALYSIS=false
K8S_AI_CONTINUOUS_MONITORING=false
K8S_AI_AUTO_REMEDIATION=false
```

### 4. 📊 Monitoring Mode
**Purpose**: Continuous real-time monitoring with alerting and dashboard focus.

**Use Cases**:
- NOC (Network Operations Center) displays
- Real-time cluster monitoring
- Alert management
- Performance tracking

**Configuration**:
```bash
# Environment Variables
K8S_AI_MODE=monitoring
K8S_AI_AUTOMATION_LEVEL=semi_auto
K8S_AI_CONFIDENCE_THRESHOLD=80
K8S_AI_HISTORICAL_LEARNING=true
K8S_AI_PREDICTIVE_ANALYSIS=true
K8S_AI_CONTINUOUS_MONITORING=true
K8S_AI_AUTO_REMEDIATION=false
```

### 5. 🔄 Hybrid Mode
**Purpose**: Adaptive responses combining multiple operational approaches.

**Use Cases**:
- Complex environments
- Mixed automation needs
- Adaptive decision making
- Multi-team environments

**Configuration**:
```bash
# Environment Variables
K8S_AI_MODE=hybrid
K8S_AI_AUTOMATION_LEVEL=semi_auto
K8S_AI_CONFIDENCE_THRESHOLD=80
K8S_AI_HISTORICAL_LEARNING=true
K8S_AI_PREDICTIVE_ANALYSIS=true
K8S_AI_CONTINUOUS_MONITORING=true
K8S_AI_AUTO_REMEDIATION=true
```

## Command Line Usage

### Direct Mode Setting
```bash
# Start in debug mode
python3 agent/main.py --mode debug --automation-level manual

# Start in remediation mode with high confidence
python3 agent/main.py --mode remediation --confidence-threshold 90 --auto-remediation true

# Start in interactive mode
python3 agent/main.py --mode interactive --historical-learning true

# Start in monitoring mode with continuous monitoring
python3 agent/main.py --mode monitoring --continuous-monitoring true

# Start in hybrid mode with full features
python3 agent/main.py --mode hybrid --predictive-analysis true
```

### Docker Run Examples

#### Debug Mode Container
```bash
docker run -d \
  --name k8s-ai-debug \
  -p 8501:8501 \
  -e K8S_AI_MODE=debug \
  -e K8S_AI_AUTOMATION_LEVEL=manual \
  -e K8S_AI_CONFIDENCE_THRESHOLD=95 \
  k8s-ai-assistant:latest
```

#### Remediation Mode Container
```bash
docker run -d \
  --name k8s-ai-remediation \
  -p 8501:8501 \
  -e K8S_AI_MODE=remediation \
  -e K8S_AI_AUTOMATION_LEVEL=full_auto \
  -e K8S_AI_AUTO_REMEDIATION=true \
  -e K8S_AI_CONFIDENCE_THRESHOLD=85 \
  k8s-ai-assistant:latest
```

#### Monitoring Mode Container
```bash
docker run -d \
  --name k8s-ai-monitor \
  -p 8501:8501 \
  -e K8S_AI_MODE=monitoring \
  -e K8S_AI_CONTINUOUS_MONITORING=true \
  -e K8S_AI_PREDICTIVE_ANALYSIS=true \
  k8s-ai-assistant:latest
```

## Kubernetes Deployment Files

### Complete Deployment with ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: k8s-ai-config
data:
  mode: "interactive"
  automation_level: "semi_auto"
  confidence_threshold: "80"
  historical_learning: "true"
  predictive_analysis: "true"
  continuous_monitoring: "false"
  auto_remediation: "false"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-ai-assistant
  labels:
    app: k8s-ai-assistant
spec:
  replicas: 1
  selector:
    matchLabels:
      app: k8s-ai-assistant
  template:
    metadata:
      labels:
        app: k8s-ai-assistant
    spec:
      serviceAccountName: k8s-ai-assistant
      containers:
      - name: k8s-ai-assistant
        image: k8s-ai-assistant:latest
        ports:
        - containerPort: 8501
          name: dashboard
        - containerPort: 8000
          name: health
        envFrom:
        - configMapRef:
            name: k8s-ai-config
        env:
        - name: K8S_AI_MODE
          valueFrom:
            configMapKeyRef:
              name: k8s-ai-config
              key: mode
        - name: K8S_AI_AUTOMATION_LEVEL
          valueFrom:
            configMapKeyRef:
              name: k8s-ai-config
              key: automation_level
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: k8s-ai-assistant-service
spec:
  selector:
    app: k8s-ai-assistant
  ports:
  - name: dashboard
    port: 8501
    targetPort: 8501
  - name: health
    port: 8000
    targetPort: 8000
  type: ClusterIP
```

## Mode Switching

### Runtime Mode Switching
The assistant supports runtime mode switching through the dashboard interface:

1. **Dashboard Controls**: Use the sidebar mode selection controls
2. **API Endpoints**: Send mode change requests to the management API
3. **Environment Variables**: Update and restart the container

### Mode-Specific Features

| Feature | Debug | Remediation | Interactive | Monitoring | Hybrid |
|---------|--------|-------------|-------------|------------|--------|
| Root Cause Analysis | ✅ | ✅ | ✅ | ✅ | ✅ |
| Auto-Remediation | ❌ | ✅ | User Confirm | ❌ | ✅ |
| Historical Learning | ✅ | ✅ | ✅ | ✅ | ✅ |
| Predictive Analysis | ✅ | ✅ | Optional | ✅ | ✅ |
| Continuous Monitoring | ❌ | ✅ | ❌ | ✅ | ✅ |
| User Confirmations | N/A | ❌ | ✅ | N/A | Adaptive |
| Real-time Alerts | ❌ | ✅ | ❌ | ✅ | ✅ |

## Security Considerations

### Mode-Based RBAC
Different modes require different levels of cluster access:

- **Debug Mode**: Read-only access with extended logging permissions
- **Remediation Mode**: Full cluster management permissions
- **Interactive Mode**: Standard operational permissions
- **Monitoring Mode**: Read access with metrics collection
- **Hybrid Mode**: Adaptive permissions based on actions

### Example RBAC for Remediation Mode
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k8s-ai-remediation
rules:
- apiGroups: [""]
  resources: ["pods", "nodes", "services", "persistentvolumes", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets", "daemonsets", "statefulsets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["extensions", "networking.k8s.io"]
  resources: ["ingresses", "networkpolicies"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
```

## Monitoring and Observability

### Health Checks
Each mode provides specific health endpoints:
- `/health` - Basic health status
- `/ready` - Readiness for requests
- `/mode` - Current operational mode
- `/config` - Current configuration

### Metrics
Mode-specific metrics are exposed:
- `k8s_ai_mode_current` - Current operational mode
- `k8s_ai_actions_total` - Total actions taken by mode
- `k8s_ai_confidence_avg` - Average confidence scores
- `k8s_ai_learning_patterns` - Number of learned patterns

## Troubleshooting

### Common Issues

1. **Mode not switching**: Check RBAC permissions for the desired mode
2. **Auto-remediation not working**: Verify confidence thresholds and automation level
3. **Dashboard not reflecting mode**: Clear browser cache and refresh
4. **Historical learning disabled**: Check persistent storage configuration

### Logs and Debugging
```bash
# Check mode configuration
kubectl logs deployment/k8s-ai-assistant | grep "Mode:"

# Monitor mode switches
kubectl logs deployment/k8s-ai-assistant | grep "mode"

# Check configuration errors
kubectl logs deployment/k8s-ai-assistant | grep -i error
```

## Best Practices

1. **Start with Debug Mode** in new environments
2. **Use Interactive Mode** for learning and training
3. **Deploy Remediation Mode** only after thorough testing
4. **Use Monitoring Mode** for NOC displays
5. **Consider Hybrid Mode** for complex environments

## Migration Guide

### From Single Mode to Multi-Mode
1. Update your deployment YAML with environment variables
2. Test each mode in a non-production environment
3. Gradually migrate production workloads
4. Monitor behavior and adjust confidence thresholds

### Mode Selection Decision Tree
```
Is this a production environment?
├── Yes → Are you comfortable with automation?
│   ├── Yes → Remediation Mode
│   └── No → Interactive Mode
└── No → Are you learning/debugging?
    ├── Yes → Debug Mode
    └── No → Interactive Mode
```

## Support and Contact

For mode-specific issues or questions:
- Debug Mode: Focus on analysis capabilities
- Remediation Mode: Automation and confidence tuning
- Interactive Mode: User experience and confirmations
- Monitoring Mode: Real-time display and alerting
- Hybrid Mode: Complex configuration scenarios

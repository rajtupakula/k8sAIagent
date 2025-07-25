# 🔒 K8s AI Assistant - Complete Offline Deployment Guide

## 🎯 Overview

The K8s AI Assistant has been **completely updated for offline operation**. All dependencies are downloaded during Docker build, and the application works without internet access at runtime.

## ✅ Recent Updates (Completed)

### Docker Image Optimization
- ✅ **Multi-stage build** with comprehensive dependency installation
- ✅ **Pre-downloads ML models** during build (sentence-transformers, tokenizers)  
- ✅ **Offline environment variables** set for all AI/ML libraries
- ✅ **Complete requirements** in `requirements-complete.txt`

### Python Code Updates  
- ✅ **Graceful fallbacks** for missing AI/ML dependencies
- ✅ **Offline-first design** with proper error handling
- ✅ **No runtime downloads** - all models cached during build
- ✅ **Dependency checks** prevent internet calls

### Configuration Management
- ✅ **ConfigMap integration** preserved with runtime arguments
- ✅ **Environment variables** from K8s ConfigMap
- ✅ **Offline mode settings** in environment

## 🚀 Quick Offline Deployment

### Step 1: Prepare the Environment
```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd k8sAIagent

# Make scripts executable
chmod +x scripts/*.sh models/*.sh scripts/*.py

# Verify all files are present
ls -la
```

### Step 2: Build Docker Image (Offline)
```bash
# Build the image locally (includes all dependencies)
./scripts/build.sh build

# Tag for your local registry if needed
docker tag k8s-ai-assistant:latest your-registry.local/k8s-ai-assistant:latest

# Push to local/air-gapped registry
docker push your-registry.local/k8s-ai-assistant:latest
```

### Step 3: Deploy to Kubernetes
```bash
# Apply RBAC first
kubectl apply -f k8s/rbac.yaml

# Deploy the application with NodePort service
kubectl apply -f k8s/pod.yaml
kubectl apply -f k8s/service.yaml

# Verify deployment
kubectl get pods,services -l app=k8s-ai-assistant

# Wait for pod to be ready
kubectl wait --for=condition=Ready pod/k8s-ai-assistant --timeout=300s
```

### Step 4: Access the Dashboard
```bash
# Get node IPs
kubectl get nodes -o wide

# Access dashboard via NodePort
# Dashboard: http://<node-ip>:30501
# LLM API: http://<node-ip>:30080
# Health: http://<node-ip>:30000
```

## 🔧 Configuration

### Offline Mode Settings
The application is configured for offline operation by default:

```json
{
  "rag": {
    "offline_mode": true,
    "embedding_model": "all-MiniLM-L6-v2",
    "chroma_path": "/app/data/chroma_db"
  },
  "llama": {
    "auto_start": true,
    "default_model": "mistral-7b-instruct"
  }
}
```

### NodePort Configuration
Services are exposed via NodePort:

```yaml
spec:
  type: NodePort
  ports:
  - name: dashboard
    port: 8501
    nodePort: 30501  # Dashboard access
  - name: llama-api
    port: 8080
    nodePort: 30080  # LLM API
  - name: health
    port: 8000
    nodePort: 30000  # Health checks
```

## 🧪 Testing Offline Functionality

### Run Offline Tests
```bash
# Test all offline components
python3 scripts/test_offline.py

# Test specific components
python3 -c "
from agent.rag_agent import RAGAgent
rag = RAGAgent(offline_mode=True)
print('Response:', rag.query('How to restart a pod?'))
"
```

### Verify Chat Interface
1. Access dashboard: `http://<node-ip>:30501`
2. Go to "Chat Assistant" tab
3. Try these commands:
   - "restart failed pods"
   - "check cluster status"
   - "clean completed jobs"
   - "scale deployment <name> to 3 replicas"

### Test Action Execution
```bash
# Via the dashboard chat:
User: "restart failed pods"
Expected: ✅ Action Executed: Restarted X failed pods

User: "clean completed jobs"
Expected: ✅ Action Executed: Cleaned X completed jobs
```

## 🛠️ Troubleshooting

### Pod Not Starting
```bash
# Check pod status
kubectl describe pod/k8s-ai-assistant

# Check logs
kubectl logs k8s-ai-assistant -f

# Common issues:
# - Insufficient resources (increase memory/CPU limits)
# - Image pull issues (verify image is available)
# - RBAC problems (check service account permissions)
```

### Dashboard Not Accessible
```bash
# Verify service is running
kubectl get svc k8s-ai-assistant

# Check NodePort is open
kubectl get svc k8s-ai-assistant -o jsonpath='{.spec.ports[0].nodePort}'

# Test connectivity
curl http://<node-ip>:30501/health

# If using firewall, open ports:
# sudo ufw allow 30501  # Dashboard
# sudo ufw allow 30080  # LLM API  
# sudo ufw allow 30000  # Health
```

### LLM Not Responding
```bash
# Check if LLM server is running inside pod
kubectl exec k8s-ai-assistant -- ps aux | grep llama

# Check LLM server logs
kubectl exec k8s-ai-assistant -- cat /app/logs/llama_server.log

# Test LLM API directly
curl http://<node-ip>:30080/health

# Note: LLM may not be available initially - the app works in offline mode without it
```

### Chat Actions Not Working
```bash
# Verify remediation engine is working
kubectl logs k8s-ai-assistant | grep -i remediation

# Check RBAC permissions
kubectl auth can-i delete pods --as=system:serviceaccount:default:k8s-ai-assistant

# Test manual action
kubectl exec k8s-ai-assistant -- python3 -c "
from agent.remediate import RemediationEngine
engine = RemediationEngine()
print(engine.restart_failed_pods())
"
```

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Application health
curl http://<node-ip>:30000/health

# Component status
curl http://<node-ip>:30000/status

# Resource usage
kubectl top pod k8s-ai-assistant
```

### Log Management
```bash
# View application logs
kubectl logs k8s-ai-assistant -f

# View specific component logs
kubectl exec k8s-ai-assistant -- tail -f /app/logs/rag_agent.log
kubectl exec k8s-ai-assistant -- tail -f /app/logs/monitor.log

# Log rotation (if needed)
kubectl exec k8s-ai-assistant -- logrotate /app/config/logrotate.conf
```

### Storage Management
```bash
# Check storage usage
kubectl exec k8s-ai-assistant -- df -h

# Clean up old data (if needed)
kubectl exec k8s-ai-assistant -- find /app/data -name "*.log" -mtime +7 -delete

# Backup important data
kubectl cp k8s-ai-assistant:/app/data/chroma_db ./backup/chroma_db
```

## 🔐 Security Considerations

### Network Security
- NodePort services are accessible from any network interface
- Consider using NetworkPolicies to restrict access
- Use firewalls to limit NodePort access to trusted networks

### RBAC Security
- Service account has minimal required permissions
- Regularly audit RBAC permissions
- Monitor for privilege escalation attempts

### Data Security
- All data processing happens locally
- No external API calls or data transmission
- Vector database and models stored on persistent volumes

## 🚀 Performance Optimization

### Resource Tuning
```yaml
# Recommended resource limits
resources:
  requests:
    memory: "4Gi"
    cpu: "1000m"
  limits:
    memory: "12Gi"
    cpu: "4000m"
```

### Storage Optimization
```bash
# Use fast storage for better performance
kubectl annotate pvc ai-assistant-models-pvc volume.beta.kubernetes.io/storage-class=fast-ssd

# Increase storage if needed
kubectl patch pvc ai-assistant-models-pvc -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'
```

### Model Optimization
```bash
# Download optimized models for your hardware
./models/download_models.sh --recommend

# Use Q4_K_M quantization for best performance/quality balance
./models/download_models.sh --download mistral-7b-instruct --quantization Q4_K_M
```

## 📈 Scaling

### Horizontal Scaling
```bash
# Create deployment from pod
kubectl create deployment ai-assistant --image=k8s-ai-assistant:latest --replicas=3

# Scale deployment
kubectl scale deployment ai-assistant --replicas=5
```

### Load Balancing
```yaml
# Use LoadBalancer service for production
apiVersion: v1
kind: Service
metadata:
  name: ai-assistant-lb
spec:
  type: LoadBalancer
  ports:
  - port: 8501
    targetPort: 8501
  selector:
    app: k8s-ai-assistant
```

---

**⚠️ Important Notes:**
- This setup provides complete offline functionality
- External model downloads require initial internet access
- NodePort services expose the application on all cluster nodes
- Ensure firewall rules allow NodePort access if needed

**🎯 Next Steps:**
- Access dashboard via NodePort
- Test chat functionality and action execution
- Monitor cluster health and resource usage
- Customize configuration as needed

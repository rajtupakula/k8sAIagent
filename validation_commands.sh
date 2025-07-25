# 🚀 KUBERNETES AI AGENT DEPLOYMENT VALIDATION COMMANDS
# Run these commands individually to validate your deployment

# ========================================
# STEP 1: BASIC CLUSTER STATUS
# ========================================

# Check if the pod is running
kubectl get pods -l app=k8s-ai-agent -o wide

# Get detailed pod information
kubectl describe pod -l app=k8s-ai-agent

# Check pod status and restarts
kubectl get pods -l app=k8s-ai-agent -o jsonpath='{.items[0].status.phase}'

# Check container ready status
kubectl get pods -l app=k8s-ai-agent -o jsonpath='{.items[0].status.containerStatuses[0].ready}'

# ========================================
# STEP 2: SERVICE AND PORT VALIDATION
# ========================================

# Check service configuration
kubectl get svc k8s-ai-agent -o wide

# Verify NodePorts are assigned
kubectl get svc k8s-ai-agent -o jsonpath='{.spec.ports[*].nodePort}'

# Check if service has endpoints
kubectl get endpoints k8s-ai-agent

# Get service details in YAML format
kubectl get svc k8s-ai-agent -o yaml

# ========================================
# STEP 3: CONTAINER LOGS ANALYSIS
# ========================================

# Check recent container logs
kubectl logs -l app=k8s-ai-agent --tail=50

# Follow logs in real-time (run in separate terminal)
kubectl logs -l app=k8s-ai-agent -f

# Check for specific startup messages
kubectl logs -l app=k8s-ai-agent | grep -i "llama\|streamlit\|server\|running\|online"

# Check for errors in logs
kubectl logs -l app=k8s-ai-agent | grep -i "error\|failed\|exception\|traceback"

# Check for port binding messages
kubectl logs -l app=k8s-ai-agent | grep -i "port\|8080\|8501"

# ========================================
# STEP 4: PORT CONNECTIVITY TESTS
# ========================================

# Set up port forwarding for UI (run in background terminal)
kubectl port-forward svc/k8s-ai-agent 8501:8501 &

# Set up port forwarding for LLaMA API (run in background terminal)
kubectl port-forward svc/k8s-ai-agent 8080:8080 &

# Test Streamlit UI health
curl -f http://localhost:8501/_stcore/health

# Test LLaMA API health
curl -f http://localhost:8080/health

# Test LLaMA completion endpoint
curl -X POST http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?", "max_tokens": 20}' \
  -w "\nHTTP Status: %{http_code}\n"

# Test if main dashboard loads
curl -s http://localhost:8501 | head -20

# ========================================
# STEP 5: KUBERNETES RBAC VALIDATION
# ========================================

# Check if service account exists
kubectl get serviceaccount robot-app

# Check RBAC permissions
kubectl auth can-i get pods --as=system:serviceaccount:default:robot-app

# Check cluster role binding
kubectl get clusterrolebinding robot-app-binding

# Test API access from within pod
kubectl exec -l app=k8s-ai-agent -- kubectl get nodes

# Test if pod can list pods
kubectl exec -l app=k8s-ai-agent -- kubectl get pods

# ========================================
# STEP 6: RESOURCE USAGE CHECK
# ========================================

# Check CPU and memory usage
kubectl top pod -l app=k8s-ai-agent

# Check resource limits and requests
kubectl describe pod -l app=k8s-ai-agent | grep -A 10 "Limits:\|Requests:"

# Check if pod is hitting resource limits
kubectl describe pod -l app=k8s-ai-agent | grep -A 5 "Status:\|Conditions:"

# ========================================
# STEP 7: NETWORK AND DNS TESTS
# ========================================

# Test DNS resolution from pod
kubectl exec -l app=k8s-ai-agent -- nslookup kubernetes.default.svc.cluster.local

# Test external connectivity
kubectl exec -l app=k8s-ai-agent -- curl -I https://google.com

# Check pod IP and network details
kubectl get pod -l app=k8s-ai-agent -o jsonpath='{.items[0].status.podIP}'

# ========================================
# STEP 8: CONFIGURATION VALIDATION
# ========================================

# Check ConfigMap is mounted correctly
kubectl exec -l app=k8s-ai-agent -- ls -la /etc/config/

# Verify environment variables
kubectl exec -l app=k8s-ai-agent -- env | grep -E "STREAMLIT|LLAMA|K8S"

# Check volume mounts
kubectl describe pod -l app=k8s-ai-agent | grep -A 10 "Mounts:"

# ========================================
# STEP 9: LLAMA INTEGRATION VALIDATION
# ========================================

# Check if LLaMA server process is running in container
kubectl exec -l app=k8s-ai-agent -- ps aux | grep -i llama

# Check LLaMA server logs within container
kubectl exec -l app=k8s-ai-agent -- cat /app/llama_server.log 2>/dev/null || echo "LLaMA log not found"

# Test LLaMA server from within pod
kubectl exec -l app=k8s-ai-agent -- curl -f http://localhost:8080/health

# Check if models directory exists and has content
kubectl exec -l app=k8s-ai-agent -- ls -la /opt/models/

# ========================================
# STEP 10: DASHBOARD FUNCTIONALITY TEST
# ========================================

# Check if Streamlit process is running
kubectl exec -l app=k8s-ai-agent -- ps aux | grep -i streamlit

# Test dashboard health from within pod
kubectl exec -l app=k8s-ai-agent -- curl -f http://localhost:8501/_stcore/health

# Check dashboard files are present
kubectl exec -l app=k8s-ai-agent -- ls -la /app/ | grep -E "dashboard|runtime_fixed"

# ========================================
# STEP 11: END-TO-END VALIDATION
# ========================================

# Get NodePort for external access
export UI_NODEPORT=$(kubectl get svc k8s-ai-agent -o jsonpath='{.spec.ports[?(@.name=="streamlit-ui")].nodePort}')
export LLAMA_NODEPORT=$(kubectl get svc k8s-ai-agent -o jsonpath='{.spec.ports[?(@.name=="llama-api")].nodePort}')
export NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')

# If no external IP, use internal IP
if [ -z "$NODE_IP" ]; then
  export NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
fi

echo "Dashboard URL: http://$NODE_IP:$UI_NODEPORT"
echo "LLaMA API URL: http://$NODE_IP:$LLAMA_NODEPORT"

# Test external access to dashboard
curl -f "http://$NODE_IP:$UI_NODEPORT/_stcore/health"

# Test external access to LLaMA API
curl -f "http://$NODE_IP:$LLAMA_NODEPORT/health"

# ========================================
# STEP 12: TROUBLESHOOTING COMMANDS
# ========================================

# If pod is not running, check events
kubectl get events --sort-by='.metadata.creationTimestamp' | grep k8s-ai-agent

# Check image pull status
kubectl describe pod -l app=k8s-ai-agent | grep -A 5 "Events:"

# Check if volumes are mounted correctly
kubectl exec -l app=k8s-ai-agent -- df -h

# Check container startup command
kubectl get pod -l app=k8s-ai-agent -o jsonpath='{.items[0].spec.containers[0].command}'

# Check security context
kubectl get pod -l app=k8s-ai-agent -o jsonpath='{.items[0].spec.securityContext}'

# ========================================
# STEP 13: CLEANUP COMMANDS (if needed)
# ========================================

# Kill port-forward processes
pkill -f "kubectl port-forward"

# Restart the pod (if needed)
kubectl delete pod -l app=k8s-ai-agent

# Check new pod startup
kubectl get pods -l app=k8s-ai-agent -w

# ========================================
# SUCCESS VALIDATION CHECKLIST
# ========================================
# ✅ Pod status: Running
# ✅ Container ready: true
# ✅ Service has endpoints
# ✅ Port 8501 (UI) responding to health check
# ✅ Port 8080 (LLaMA) responding to health check
# ✅ LLaMA completion API working
# ✅ Kubernetes API accessible from pod
# ✅ No errors in container logs
# ✅ External access working via NodePort
# ✅ Dashboard loads in browser
# ✅ AI chat functionality working

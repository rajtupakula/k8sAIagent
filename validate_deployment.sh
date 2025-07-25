#!/bin/bash
"""
🚀 DEPLOYMENT VALIDATION COMMANDS
Comprehensive validation for the newly deployed K8s AI Agent with fixed LLaMA integration
"""

echo "🚀 KUBERNETES AI AGENT - DEPLOYMENT VALIDATION"
echo "=============================================="
echo "Date: $(date)"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}🔍 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 1: Check Pod Status
print_step "Step 1: Checking Pod Status"
echo "================================================"

kubectl get pods -l app=k8s-ai-agent -o wide

POD_NAME=$(kubectl get pods -l app=k8s-ai-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    print_error "No k8s-ai-agent pods found!"
    exit 1
else
    print_success "Found pod: $POD_NAME"
fi

# Check pod status
POD_STATUS=$(kubectl get pod $POD_NAME -o jsonpath='{.status.phase}')
echo "Pod Status: $POD_STATUS"

if [ "$POD_STATUS" = "Running" ]; then
    print_success "Pod is running"
else
    print_warning "Pod status: $POD_STATUS"
    print_step "Checking pod events..."
    kubectl describe pod $POD_NAME | tail -20
fi

echo ""

# Step 2: Check Services and Endpoints
print_step "Step 2: Checking Services and Port Configuration"
echo "================================================"

kubectl get svc k8s-ai-agent -o wide

# Get NodePort for UI (8501)
UI_NODEPORT=$(kubectl get svc k8s-ai-agent -o jsonpath='{.spec.ports[?(@.name=="streamlit-ui")].nodePort}' 2>/dev/null)
LLAMA_NODEPORT=$(kubectl get svc k8s-ai-agent -o jsonpath='{.spec.ports[?(@.name=="llama-api")].nodePort}' 2>/dev/null)

if [ ! -z "$UI_NODEPORT" ]; then
    print_success "Streamlit UI NodePort: $UI_NODEPORT"
else
    print_warning "Streamlit UI NodePort not found"
fi

if [ ! -z "$LLAMA_NODEPORT" ]; then
    print_success "LLaMA API NodePort: $LLAMA_NODEPORT"
else
    print_warning "LLaMA API NodePort not found"
fi

echo ""

# Step 3: Check Container Logs
print_step "Step 3: Checking Container Startup Logs"
echo "================================================"

echo "Last 20 lines of container logs:"
kubectl logs $POD_NAME --tail=20

echo ""
echo "Checking for specific startup messages:"

# Check for LLaMA server startup
if kubectl logs $POD_NAME | grep -i "llama.*server.*running\|llama.*online\|port.*8080" >/dev/null; then
    print_success "LLaMA server startup detected in logs"
else
    print_warning "LLaMA server startup not detected in logs"
fi

# Check for Streamlit startup
if kubectl logs $POD_NAME | grep -i "streamlit.*running\|streamlit.*8501\|dashboard.*running" >/dev/null; then
    print_success "Streamlit dashboard startup detected in logs"
else
    print_warning "Streamlit dashboard startup not detected in logs"
fi

echo ""

# Step 4: Port Forward and Test Services
print_step "Step 4: Testing Service Connectivity"
echo "================================================"

# Test if we can port-forward
print_step "Setting up port forwards for testing..."

# Port forward for UI (8501)
kubectl port-forward pod/$POD_NAME 8501:8501 >/dev/null 2>&1 &
PF_UI_PID=$!

# Port forward for LLaMA API (8080)  
kubectl port-forward pod/$POD_NAME 8080:8080 >/dev/null 2>&1 &
PF_LLAMA_PID=$!

# Wait for port forwards to establish
sleep 3

# Test Streamlit UI
print_step "Testing Streamlit UI (port 8501)..."
if curl -s -f http://localhost:8501/_stcore/health >/dev/null 2>&1; then
    print_success "Streamlit UI is responding on port 8501"
    UI_WORKING=true
else
    print_error "Streamlit UI not responding on port 8501"
    UI_WORKING=false
fi

# Test LLaMA API
print_step "Testing LLaMA API (port 8080)..."
if curl -s -f http://localhost:8080/health >/dev/null 2>&1; then
    print_success "LLaMA API is responding on port 8080"
    LLAMA_WORKING=true
    
    # Test actual completion
    print_step "Testing LLaMA completion API..."
    COMPLETION_RESPONSE=$(curl -s -X POST http://localhost:8080/completion \
        -H "Content-Type: application/json" \
        -d '{"prompt": "Hello", "max_tokens": 5}' 2>/dev/null)
    
    if echo "$COMPLETION_RESPONSE" | grep -q "content\|text"; then
        print_success "LLaMA completion API working"
        echo "Sample response: $(echo "$COMPLETION_RESPONSE" | head -c 100)..."
    else
        print_warning "LLaMA completion API may have issues"
        echo "Response: $COMPLETION_RESPONSE"
    fi
else
    print_error "LLaMA API not responding on port 8080"
    LLAMA_WORKING=false
fi

# Clean up port forwards
kill $PF_UI_PID $PF_LLAMA_PID 2>/dev/null

echo ""

# Step 5: Test Kubernetes Integration
print_step "Step 5: Testing Kubernetes API Integration"
echo "================================================"

# Test if pod can access Kubernetes API
print_step "Testing Kubernetes API access from within pod..."
KUBECTL_TEST=$(kubectl exec $POD_NAME -- kubectl get nodes 2>/dev/null | wc -l)

if [ "$KUBECTL_TEST" -gt "0" ]; then
    print_success "Pod can access Kubernetes API"
    NODE_COUNT=$((KUBECTL_TEST - 1))  # Subtract header
    echo "Detected $NODE_COUNT nodes from within pod"
else
    print_warning "Pod may not have Kubernetes API access"
fi

# Check RBAC
print_step "Checking RBAC configuration..."
kubectl auth can-i get pods --as=system:serviceaccount:default:robot-app >/dev/null 2>&1
if [ $? -eq 0 ]; then
    print_success "RBAC permissions look good"
else
    print_warning "RBAC permissions may need adjustment"
fi

echo ""

# Step 6: Real-time Dashboard Test
print_step "Step 6: Testing Real-time Dashboard Features"
echo "================================================"

if [ "$UI_WORKING" = true ]; then
    # Set up port forward again for testing
    kubectl port-forward pod/$POD_NAME 8501:8501 >/dev/null 2>&1 &
    PF_PID=$!
    sleep 2
    
    print_step "Testing dashboard endpoints..."
    
    # Test main dashboard
    if curl -s http://localhost:8501 | grep -q "Kubernetes AI Agent\|Expert.*Agent"; then
        print_success "Main dashboard page loading"
    else
        print_warning "Dashboard may not be fully loaded"
    fi
    
    kill $PF_PID 2>/dev/null
else
    print_warning "Skipping dashboard tests - UI not responding"
fi

echo ""

# Step 7: Performance and Resource Check
print_step "Step 7: Checking Resource Usage"
echo "================================================"

kubectl top pod $POD_NAME 2>/dev/null || print_warning "Metrics server not available"

# Check pod resources
print_step "Pod resource limits and requests:"
kubectl describe pod $POD_NAME | grep -A 10 "Limits:\|Requests:"

echo ""

# Step 8: Generate Access URLs
print_step "Step 8: Access Information"
echo "================================================"

# Get node IP
NODE_IP=$(kubectl get pod $POD_NAME -o jsonpath='{.status.hostIP}')

if [ ! -z "$NODE_IP" ] && [ ! -z "$UI_NODEPORT" ]; then
    print_success "🌐 Dashboard URL: http://$NODE_IP:$UI_NODEPORT"
    echo "   Alternative: http://localhost:$UI_NODEPORT (if port-forwarded)"
fi

if [ ! -z "$NODE_IP" ] && [ ! -z "$LLAMA_NODEPORT" ]; then
    print_success "🤖 LLaMA API URL: http://$NODE_IP:$LLAMA_NODEPORT"
    echo "   Health check: http://$NODE_IP:$LLAMA_NODEPORT/health"
    echo "   Alternative: http://localhost:$LLAMA_NODEPORT (if port-forwarded)"
fi

echo ""

# Final Summary
print_step "VALIDATION SUMMARY"
echo "================================================"

TOTAL_CHECKS=6
PASSED_CHECKS=0

if [ "$POD_STATUS" = "Running" ]; then
    print_success "✅ Pod Status: Running"
    ((PASSED_CHECKS++))
else
    print_error "❌ Pod Status: $POD_STATUS"
fi

if [ "$UI_WORKING" = true ]; then
    print_success "✅ Streamlit UI: Working"
    ((PASSED_CHECKS++))
else
    print_error "❌ Streamlit UI: Not responding"
fi

if [ "$LLAMA_WORKING" = true ]; then
    print_success "✅ LLaMA API: Working"
    ((PASSED_CHECKS++))
else
    print_error "❌ LLaMA API: Not responding"
fi

if [ "$KUBECTL_TEST" -gt "0" ]; then
    print_success "✅ Kubernetes Integration: Working"
    ((PASSED_CHECKS++))
else
    print_error "❌ Kubernetes Integration: Issues detected"
fi

if [ ! -z "$UI_NODEPORT" ] && [ ! -z "$LLAMA_NODEPORT" ]; then
    print_success "✅ Service Configuration: Correct"
    ((PASSED_CHECKS++))
else
    print_error "❌ Service Configuration: Issues detected"
fi

if kubectl logs $POD_NAME | grep -i "error\|failed\|exception" | grep -v "INFO\|DEBUG" >/dev/null; then
    print_error "❌ Application Logs: Errors detected"
else
    print_success "✅ Application Logs: Clean"
    ((PASSED_CHECKS++))
fi

echo ""
echo "SCORE: $PASSED_CHECKS/$TOTAL_CHECKS checks passed"

if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
    print_success "🎉 DEPLOYMENT VALIDATION PASSED!"
    print_success "Your K8s AI Agent is fully functional with LLaMA integration!"
elif [ $PASSED_CHECKS -ge 4 ]; then
    print_warning "⚠️ DEPLOYMENT PARTIALLY WORKING"
    print_warning "Most features working, minor issues detected"
else
    print_error "❌ DEPLOYMENT NEEDS ATTENTION"
    print_error "Multiple issues detected - check logs and configuration"
fi

echo ""
print_step "Next Steps:"
if [ "$UI_WORKING" = true ]; then
    echo "• Access dashboard and test AI chat functionality"
    echo "• Verify real-time Kubernetes data is displayed"
    echo "• Test auto-remediation features"
else
    echo "• Check pod logs: kubectl logs $POD_NAME"
    echo "• Verify container startup: kubectl describe pod $POD_NAME"
    echo "• Check service configuration: kubectl get svc k8s-ai-agent -o yaml"
fi

echo ""
echo "Validation completed at $(date)"

# 🧪 FIXED INTEGRATION VALIDATION - Test New LLaMA+Streamlit Separation

echo "🧪 Testing Fixed Integration (Port Separation)"
echo "=============================================="

# Get pod name
POD_NAME=$(kubectl get pods -l app=k8s-ai-agent -o jsonpath='{.items[0].metadata.name}')
echo "Pod: $POD_NAME"

# 1. VERIFY FIXED STARTUP SCRIPT IS USED
echo -e "\n1️⃣ Checking startup configuration..."
kubectl exec $POD_NAME -- ps aux | grep -E "fixed_container_startup|container_startup"

# 2. VERIFY PORT SEPARATION
echo -e "\n2️⃣ Checking port separation..."
kubectl exec $POD_NAME -- lsof -i :8080 | head -3  # Should show LLaMA
kubectl exec $POD_NAME -- lsof -i :8501 | head -3  # Should show Streamlit

# 3. VERIFY BOTH SERVICES RUNNING
echo -e "\n3️⃣ Checking service health from inside pod..."
kubectl exec $POD_NAME -- curl -s -f http://localhost:8080/health > /dev/null && echo "✅ LLaMA API (8080) OK" || echo "❌ LLaMA API (8080) FAILED"
kubectl exec $POD_NAME -- curl -s -f http://localhost:8501/_stcore/health > /dev/null && echo "✅ Streamlit UI (8501) OK" || echo "❌ Streamlit UI (8501) FAILED"

# 4. VERIFY INTEGRATION FILES EXIST
echo -e "\n4️⃣ Checking fixed integration files..."
kubectl exec $POD_NAME -- ls -la /app/fixed_container_startup.py && echo "✅ Fixed startup script" || echo "❌ Missing fixed startup"
kubectl exec $POD_NAME -- ls -la /app/runtime_fixed_dashboard.py && echo "✅ Fixed dashboard" || echo "❌ Missing fixed dashboard"
kubectl exec $POD_NAME -- ls -la /app/quick_fix_integration.sh && echo "✅ Fix script" || echo "❌ Missing fix script"

# 5. TEST LLAMA COMPLETION WITH PROPER API
echo -e "\n5️⃣ Testing LLaMA completion API..."
COMPLETION_TEST=$(kubectl exec $POD_NAME -- curl -s -X POST http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test", "max_tokens": 5}')

if echo "$COMPLETION_TEST" | grep -q "content\|text"; then
    echo "✅ LLaMA completion working"
    echo "Sample: $(echo "$COMPLETION_TEST" | head -c 100)..."
else
    echo "❌ LLaMA completion failed"
    echo "Response: $COMPLETION_TEST"
fi

# 6. VERIFY KUBERNETES INTEGRATION IN DASHBOARD
echo -e "\n6️⃣ Testing Kubernetes integration..."
kubectl exec $POD_NAME -- curl -s http://localhost:8501 | grep -q "Kubernetes\|K8s" && echo "✅ K8s integration in UI" || echo "❌ K8s integration missing"

# 7. CHECK FOR RUNTIME ERRORS
echo -e "\n7️⃣ Checking for runtime errors..."
ERROR_COUNT=$(kubectl logs $POD_NAME | grep -i "error\|exception\|failed" | grep -v "INFO\|DEBUG" | wc -l)
if [ "$ERROR_COUNT" -eq "0" ]; then
    echo "✅ No runtime errors detected"
else
    echo "⚠️ $ERROR_COUNT potential errors in logs"
    kubectl logs $POD_NAME | grep -i "error\|exception\|failed" | grep -v "INFO\|DEBUG" | tail -3
fi

# 8. EXTERNAL ACCESS TEST
echo -e "\n8️⃣ Testing external access..."
UI_NODEPORT=$(kubectl get svc k8s-ai-agent -o jsonpath='{.spec.ports[?(@.name=="streamlit-ui")].nodePort}')
LLAMA_NODEPORT=$(kubectl get svc k8s-ai-agent -o jsonpath='{.spec.ports[?(@.name=="llama-api")].nodePort}')
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

echo "Dashboard URL: http://$NODE_IP:$UI_NODEPORT"
echo "LLaMA API URL: http://$NODE_IP:$LLAMA_NODEPORT"

# Test external access (if accessible)
if curl -s -f "http://$NODE_IP:$UI_NODEPORT/_stcore/health" > /dev/null 2>&1; then
    echo "✅ External UI access working"
else
    echo "⚠️ External UI access may need port-forward"
fi

if curl -s -f "http://$NODE_IP:$LLAMA_NODEPORT/health" > /dev/null 2>&1; then
    echo "✅ External LLaMA access working"
else
    echo "⚠️ External LLaMA access may need port-forward"
fi

echo -e "\n🎯 INTEGRATION TEST COMPLETE"
echo "If all items show ✅, your fixed integration is working correctly!"

# 🔥 QUICK VALIDATION COMMANDS - Essential Checks Only

# 1. CHECK POD STATUS
kubectl get pods -l app=k8s-ai-agent

# 2. CHECK CONTAINER LOGS  
kubectl logs -l app=k8s-ai-agent --tail=20

# 3. GET ACCESS URLs
export UI_NODEPORT=$(kubectl get svc k8s-ai-agent -o jsonpath='{.spec.ports[?(@.name=="streamlit-ui")].nodePort}')
export LLAMA_NODEPORT=$(kubectl get svc k8s-ai-agent -o jsonpath='{.spec.ports[?(@.name=="llama-api")].nodePort}')
export NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

echo "🌐 Dashboard: http://$NODE_IP:$UI_NODEPORT"
echo "🤖 LLaMA API: http://$NODE_IP:$LLAMA_NODEPORT"

# 4. QUICK HEALTH CHECKS (port-forward first)
kubectl port-forward svc/k8s-ai-agent 8501:8501 &
kubectl port-forward svc/k8s-ai-agent 8080:8080 &

# Wait 3 seconds for port-forward to establish
sleep 3

# Test UI
curl -f http://localhost:8501/_stcore/health && echo "✅ UI Working" || echo "❌ UI Failed"

# Test LLaMA
curl -f http://localhost:8080/health && echo "✅ LLaMA Working" || echo "❌ LLaMA Failed"

# 5. TEST AI COMPLETION
curl -X POST http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "max_tokens": 10}' \
  && echo "✅ AI Working" || echo "❌ AI Failed"

# 6. CHECK KUBERNETES ACCESS
kubectl exec -l app=k8s-ai-agent -- kubectl get nodes > /dev/null 2>&1 \
  && echo "✅ K8s API Access" || echo "❌ K8s API Failed"

# 7. CLEANUP
pkill -f "kubectl port-forward"

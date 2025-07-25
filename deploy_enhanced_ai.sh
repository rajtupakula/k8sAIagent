#!/bin/bash
# Enhanced AI Agent Deployment Script

echo "🧠 Deploying Enhanced Kubernetes AI Expert Assistant"
echo "=================================================="

# Build the enhanced container
echo "📦 Building enhanced AI container..."
podman build -t k8s-ai-agent:latest . --no-cache

if [ $? -eq 0 ]; then
    echo "✅ Container built successfully"
else
    echo "❌ Container build failed"
    exit 1
fi

# Deploy to Kubernetes (if available)
echo "🚀 Deploying to Kubernetes..."
if command -v kubectl >/dev/null 2>&1; then
    kubectl apply -f k8s/k8s-ai-agent.yaml
    
    if [ $? -eq 0 ]; then
        echo "✅ Deployed to Kubernetes successfully"
        echo ""
        echo "📊 Checking deployment status..."
        kubectl get pods -l app=k8s-ai-agent
        kubectl get svc k8s-ai-agent
        
        echo ""
        echo "🌐 Access the Enhanced AI Expert Dashboard:"
        echo "   NodePort: http://<node-ip>:30180"
        echo "   Port Forward: kubectl port-forward svc/k8s-ai-agent 8080:8080"
        echo "   Then access: http://localhost:8080"
        
    else
        echo "⚠️ Kubernetes deployment failed or not available"
    fi
else
    echo "⚠️ kubectl not found - skipping Kubernetes deployment"
fi

echo ""
echo "🎯 Enhanced AI Features:"
echo "✅ Expert-level responses (no confidence filtering)"
echo "✅ Real-time cluster status integration"
echo "✅ Live pod and node monitoring"
echo "✅ Intelligent pattern matching"
echo "✅ Comprehensive troubleshooting guidance"
echo "✅ Auto-analysis of cluster issues"
echo ""
echo "🧠 The AI Agent now works like a human expert!"
echo "   Ask: 'check if all kubernetes pods are running'"
echo "   Ask: 'help me debug node issues'" 
echo "   Ask: 'what's wrong with my cluster?'"
echo ""
echo "🚀 Enhanced AI deployment complete!"

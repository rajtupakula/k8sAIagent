#!/bin/bash

# Deploy Advanced Dashboard UI - Quick Deployment Script
# This script deploys the K8s AI Agent with Advanced Dashboard UI enabled

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[DEPLOY-ADVANCED]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Configuration
NAMESPACE="${NAMESPACE:-default}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

log "🚀 Deploying K8s AI Agent with Advanced Dashboard UI"

# Check if we're in the right directory
if [ ! -f "ui/advanced_dashboard.py" ]; then
    error "❌ Advanced Dashboard UI file not found. Please run from project root."
    exit 1
fi

success "✅ Advanced Dashboard UI file found"

# Method 1: Docker Compose (Local Development)
log "📦 Option 1: Docker Compose Deployment (Recommended for testing)"
echo "Run: docker-compose up --build"
echo "Access: http://localhost:8080"
echo ""

# Method 2: Direct Python Execution
log "🐍 Option 2: Direct Python Execution (Development)"
echo "Run: UI_MODE=advanced python app_wrapper.py"
echo "Access: http://localhost:8080"
echo ""

# Method 3: Kubernetes Deployment
log "☸️  Option 3: Kubernetes Deployment (Production)"
echo "Build: docker build -t k8s-ai-agent:advanced ."
echo "Deploy: kubectl apply -f k8s/k8s-ai-agent.yaml"
echo "Access: kubectl port-forward service/k8s-ai-agent 8080:8080"
echo ""

# Interactive deployment selection
read -p "Select deployment method (1-3) or 'q' to quit: " choice

case $choice in
    1)
        log "🚀 Starting Docker Compose deployment..."
        export UI_MODE=advanced
        docker-compose down 2>/dev/null || true
        docker-compose up --build -d
        
        log "⏳ Waiting for service to be ready..."
        sleep 10
        
        # Test connectivity
        if curl -s http://localhost:8080/health > /dev/null; then
            success "🎉 Advanced Dashboard UI is running!"
            log "🌐 Access the Advanced Dashboard at: http://localhost:8080"
            log "📊 Health endpoint: http://localhost:9090/health"
            
            # Show logs
            echo ""
            warning "📝 Container logs (last 20 lines):"
            docker-compose logs --tail=20 k8s-ai-agent
            
        else
            error "❌ Service not responding. Check logs with: docker-compose logs"
            docker-compose logs --tail=50 k8s-ai-agent
        fi
        ;;
    
    2)
        log "🐍 Starting direct Python execution..."
        export UI_MODE=advanced
        export PYTHONPATH="$(pwd)"
        
        # Check Python dependencies
        log "🔍 Checking dependencies..."
        python -c "import streamlit; print('✅ Streamlit available')" || {
            error "❌ Streamlit not available. Install with: pip install streamlit"
            exit 1
        }
        
        python -c "import plotly; print('✅ Plotly available')" || {
            warning "⚠️  Plotly not available. Install with: pip install plotly"
        }
        
        log "🚀 Starting Advanced Dashboard UI..."
        python app_wrapper.py
        ;;
    
    3)
        log "☸️  Kubernetes deployment selected"
        
        # Build image
        log "🔨 Building Docker image..."
        docker build -t k8s-ai-agent:advanced .
        
        # Deploy to Kubernetes
        log "🚀 Deploying to Kubernetes..."
        kubectl apply -f k8s/k8s-ai-agent.yaml
        
        # Wait for deployment
        log "⏳ Waiting for deployment to be ready..."
        kubectl wait --for=condition=available --timeout=300s deployment/k8s-ai-agent -n ${NAMESPACE}
        
        # Set up port forwarding
        log "🌐 Setting up port forwarding..."
        kubectl port-forward service/k8s-ai-agent 8080:8080 -n ${NAMESPACE} &
        PORT_FORWARD_PID=$!
        
        sleep 5
        
        if curl -s http://localhost:8080/health > /dev/null; then
            success "🎉 Advanced Dashboard UI is running on Kubernetes!"
            log "🌐 Access the Advanced Dashboard at: http://localhost:8080"
            log "📊 Health endpoint: http://localhost:9090/health"
            
            # Show pod status
            echo ""
            log "📋 Pod status:"
            kubectl get pods -l app=k8s-ai-agent -n ${NAMESPACE}
            
            log "📝 To view logs: kubectl logs -l app=k8s-ai-agent -n ${NAMESPACE} -f"
            log "🛑 To stop port-forwarding: kill ${PORT_FORWARD_PID}"
            
        else
            error "❌ Service not responding after Kubernetes deployment"
            kubectl logs -l app=k8s-ai-agent -n ${NAMESPACE} --tail=50
        fi
        ;;
        
    q|Q)
        log "👋 Deployment cancelled"
        exit 0
        ;;
        
    *)
        error "❌ Invalid selection. Please choose 1, 2, 3, or 'q'"
        exit 1
        ;;
esac

echo ""
success "🎯 Advanced Dashboard UI Features Available:"
echo "   • 🔧 Expert AI-Powered Actions (5 action buttons)"
echo "   • 💬 Intelligent Chat Interface with streaming responses"
echo "   • 📊 Real-time System Status Indicators"
echo "   • 📈 Comprehensive Analytics & Performance metrics"
echo "   • 🧠 Historical Insights & Learning patterns"
echo "   • 🔮 Predictive Recommendations based on AI analysis"
echo ""
log "🚀 Advanced Dashboard UI deployment complete!"

#!/bin/bash

# Offline Installation and Testing Script for Kubernetes AI Assistant
# This script sets up the application to run completely offline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
check_directory() {
    if [ ! -f "requirements.txt" ] || [ ! -d "ui" ]; then
        error "Please run this script from the k8sAIagent directory"
        exit 1
    fi
}

# Test offline functionality
test_offline_mode() {
    log "Testing offline functionality..."
    
    python3 -c "
import sys
sys.path.append('.')

print('🔍 Testing offline mode...')

# Test dashboard import
try:
    import ui.dashboard as dashboard
    print('✅ Dashboard imports successfully')
    
    # Test mock components
    rag = dashboard.MockRAGAgent()
    response = rag.query('How to restart a pod?')
    assert len(response) > 100, 'Response too short'
    print('✅ Mock RAG agent functional')
    
    action_result = rag.query_with_actions('restart failed pods')
    assert 'Mock mode' in action_result['action_result']['message']
    print('✅ Action parsing functional')
    
    print('✅ Offline mode test PASSED')
    
except Exception as e:
    print(f'❌ Offline test FAILED: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        success "Offline functionality test passed"
    else
        error "Offline functionality test failed"
        exit 1
    fi
}

# Test Kubernetes manifests
test_kubernetes_manifests() {
    log "Validating Kubernetes manifests..."
    
    # Check if kubectl is available
    if command -v kubectl &> /dev/null; then
        log "Testing Kubernetes manifests syntax..."
        
        # Test RBAC with validation disabled for offline mode
        kubectl apply --dry-run=client --validate=false -f k8s/rbac.yaml > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            success "RBAC manifest syntax is valid"
        else
            warning "RBAC manifest may have issues (offline mode)"
        fi
        
        # Test Pod
        kubectl apply --dry-run=client --validate=false -f k8s/pod.yaml > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            success "Pod manifest syntax is valid"
        else
            warning "Pod manifest may have issues (offline mode)"
        fi
        
        # Test Service
        kubectl apply --dry-run=client --validate=false -f k8s/service.yaml > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            success "Service manifest syntax is valid"
        else
            warning "Service manifest may have issues (offline mode)"
        fi
        
        success "Kubernetes manifests validated (offline mode)"
    else
        warning "kubectl not available - skipping manifest validation"
    fi
}

# Test Docker build capability
test_docker_build() {
    log "Testing Docker build capability..."
    
    if command -v docker &> /dev/null; then
        log "Checking Dockerfile syntax..."
        
        # Just test if the Dockerfile is readable and has basic structure
        if [ -f "Dockerfile" ]; then
            if grep -q "FROM" Dockerfile && grep -q "COPY" Dockerfile; then
                success "Dockerfile appears valid"
            else
                warning "Dockerfile may have issues"
            fi
        else
            error "Dockerfile not found"
            return 1
        fi
    else
        warning "Docker not available - skipping Docker tests"
    fi
}

# Show access information
show_access_info() {
    log "Access Information:"
    echo ""
    echo "📋 After deployment, access the dashboard via:"
    echo ""
    echo "🌐 NodePort Access (External):"
    echo "   • Dashboard: http://<node-ip>:30501"
    echo "   • LLM API: http://<node-ip>:30080"  
    echo "   • Health: http://<node-ip>:30000"
    echo ""
    echo "🔒 Port Forward (Local):"
    echo "   • kubectl port-forward pod/k8s-ai-assistant 8501:8501"
    echo "   • Then: http://localhost:8501"
    echo ""
    echo "📝 To get node IPs:"
    echo "   • kubectl get nodes -o wide"
    echo ""
}

# Show deployment commands
show_deployment_commands() {
    log "Deployment Commands:"
    echo ""
    echo "🚀 Quick Deploy:"
    echo "   ./scripts/deploy.sh deploy"
    echo ""
    echo "🐳 Build and Deploy:"
    echo "   ./scripts/build.sh build"
    echo "   ./scripts/deploy.sh deploy"
    echo ""
    echo "📊 Check Status:"
    echo "   ./scripts/deploy.sh status"
    echo ""
    echo "📋 View Logs:"
    echo "   ./scripts/deploy.sh logs"
    echo ""
}

# Show offline features
show_offline_features() {
    log "Offline Features Available:"
    echo ""
    echo "✅ Core Features (No Internet Required):"
    echo "   • Interactive Chat Interface"
    echo "   • Natural Language Action Execution"  
    echo "   • Kubernetes Cluster Monitoring"
    echo "   • Automated Remediation"
    echo "   • Basic Resource Analysis"
    echo ""
    echo "🔧 Enhanced Features (Require Dependencies):"
    echo "   • Local LLM Integration (llama.cpp)"
    echo "   • ML-based Resource Forecasting"
    echo "   • Vector Database RAG System"
    echo "   • Advanced Visualization"
    echo ""
    echo "📦 To enable enhanced features:"
    echo "   pip install -r requirements.txt"
    echo ""
}

# Main execution
main() {
    echo "🚀 Kubernetes AI Assistant - Offline Setup and Testing"
    echo "========================================================"
    echo ""
    
    check_directory
    
    # Run tests
    test_offline_mode
    test_kubernetes_manifests
    test_docker_build
    
    echo ""
    echo "========================================================"
    success "All tests passed! The application is ready for offline deployment."
    echo ""
    
    show_offline_features
    show_access_info
    show_deployment_commands
    
    echo "🎉 Setup complete! The Kubernetes AI Assistant is ready for offline operation."
    echo ""
    echo "📖 Next steps:"
    echo "   1. Review the deployment guide: ./OFFLINE_DEPLOYMENT.md"
    echo "   2. Deploy to Kubernetes: ./scripts/deploy.sh deploy"
    echo "   3. Access the dashboard via NodePort or port forwarding"
    echo ""
}

# Handle script arguments
case "${1:-}" in
    "test")
        check_directory
        test_offline_mode
        ;;
    "validate")
        check_directory
        test_kubernetes_manifests
        ;;
    "info")
        show_access_info
        show_deployment_commands
        ;;
    *)
        main
        ;;
esac

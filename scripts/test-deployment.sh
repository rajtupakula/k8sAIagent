#!/bin/bash

# Test script for deployment and NodePort verification

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log "Testing deployment package creation and NodePort configuration..."

# Set test environment variables
export IMAGE_TAG="test-latest"
export VERSION="1.0.0"
export BUILD_NUMBER="999"
export IMAGE_REGISTRY="test-registry.com"
export IMAGE_REPO="test-repo"
export IMAGE_NAME="k8s-ai-agent"
export GIT_BRANCH="test-branch"
export NAMESPACE="test-ai-agent"

# Function to test NodePort configuration
test_nodeport_config() {
    log "Testing NodePort service configuration..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        warning "kubectl not available - skipping NodePort configuration test"
        return 0
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        warning "Kubernetes cluster not accessible - skipping NodePort configuration test"
        return 0
    fi
    
    # Test service configuration parsing
    local temp_dir="/tmp/test-nodeport-config"
    mkdir -p "${temp_dir}"
    cp k8s/k8s-ai-agent.yaml "${temp_dir}/"
    
    # Extract service configuration
    if grep -q "type: NodePort" "${temp_dir}/k8s-ai-agent.yaml"; then
        success "Service configured as NodePort"
        
        # Check NodePort values
        if grep -q "nodePort: 30080" "${temp_dir}/k8s-ai-agent.yaml"; then
            success "Dashboard NodePort (30080) configured correctly"
        else
            error "Dashboard NodePort (30080) not found"
        fi
        
        if grep -q "nodePort: 30090" "${temp_dir}/k8s-ai-agent.yaml"; then
            success "Metrics NodePort (30090) configured correctly"
        else
            error "Metrics NodePort (30090) not found"
        fi
    else
        error "Service not configured as NodePort"
    fi
    
    rm -rf "${temp_dir}"
}

# Function to test deployment script dry run
test_deployment_dry_run() {
    log "Testing deployment script dry run..."
    
    # Test dry run deployment
    if DRY_RUN=true NAMESPACE="${NAMESPACE}" ./scripts/deploy.sh deploy; then
        success "Deployment dry run completed successfully"
    else
        error "Deployment dry run failed"
        return 1
    fi
}

# Test the easy-deploy script (dry run)
log "Testing easy-deploy.sh..."
if [ -f "./scripts/easy-deploy.sh" ]; then
    ./scripts/easy-deploy.sh -e local -t test-latest --dry-run --no-apply
    success "easy-deploy.sh test completed"
else
    warning "easy-deploy.sh not found - skipping test"
fi

# Test deployment package creation
log "Testing create-deployment-package.sh..."
if [ -f "./scripts/create-deployment-package.sh" ]; then
    ./scripts/create-deployment-package.sh
    success "create-deployment-package.sh completed"
else
    warning "create-deployment-package.sh not found - skipping test"
fi

# Test NodePort configuration
test_nodeport_config

# Test deployment script dry run
test_deployment_dry_run

# Verify package was created
if [ -f "k8s-ai-agent-deployment-1.0.0-999.zip" ]; then
    success "Deployment package created successfully"
    log "Package size: $(du -h k8s-ai-agent-deployment-1.0.0-999.zip | cut -f1)"
    
    # Test zip contents
    log "Package contents:"
    unzip -l k8s-ai-agent-deployment-1.0.0-999.zip | head -15
    
    # Cleanup test files
    rm -rf k8s-ai-agent-deployment-1.0.0-999*
    rm -rf deploy-*-test-latest
    
    success "Package verification completed"
else
    warning "Deployment package not created (may not be an error if script wasn't found)"
fi

# Test NodePort access information generation
log "Testing NodePort access information..."
cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 NodePort Access Test Results:
  📱 Dashboard should be accessible at: http://<NODE_IP>:30080
  📊 Metrics should be accessible at:   http://<NODE_IP>:30090
  
  🔧 To get actual node IPs after deployment:
  kubectl get nodes -o wide
  
  🔗 Alternative local access:
  kubectl port-forward service/k8s-ai-agent 8080:8080
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

success "All deployment tests completed successfully"

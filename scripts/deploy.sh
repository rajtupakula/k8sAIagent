#!/bin/bash

# Deployment script for Kubernetes AI Assistant
# This script handles deployment to Kubernetes clusters

set -e

# Configuration
NAMESPACE="${NAMESPACE:-default}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REGISTRY="${REGISTRY:-}"
KUBE_CONFIG="${KUBE_CONFIG:-}"
DRY_RUN="${DRY_RUN:-false}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-300}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
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

# Show usage
usage() {
    echo "Usage: $0 [deploy|delete|status|logs|port-forward]"
    echo
    echo "Commands:"
    echo "  deploy        Deploy the AI assistant to Kubernetes"
    echo "  delete        Delete the AI assistant from Kubernetes"
    echo "  status        Show deployment status"
    echo "  logs          Show application logs"
    echo "  port-forward  Forward ports for local access"
    echo "  verify        Verify NodePort access and connectivity"
    echo
    echo "Environment variables:"
    echo "  NAMESPACE      Kubernetes namespace (default: default)"
    echo "  IMAGE_TAG      Docker image tag (default: latest)"
    echo "  REGISTRY       Docker registry URL"
    echo "  KUBE_CONFIG    Path to kubeconfig file"
    echo "  DRY_RUN        Run in dry-run mode (default: false)"
    echo "  WAIT_TIMEOUT   Timeout for deployment wait (default: 300)"
    echo
    echo "Examples:"
    echo "  ./scripts/deploy.sh deploy"
    echo "  NAMESPACE=ai-assistant ./scripts/deploy.sh deploy"
    echo "  REGISTRY=my-registry.com IMAGE_TAG=v1.0.0 ./scripts/deploy.sh deploy"
    echo "  DRY_RUN=true ./scripts/deploy.sh deploy"
}

# Check dependencies
check_dependencies() {
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check kubectl connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        error "Please check your kubeconfig and cluster connectivity"
        exit 1
    fi
    
    success "kubectl is available and connected to cluster"
}

# Prepare manifests with image updates
prepare_manifests() {
    local temp_dir="/tmp/k8s-ai-assistant-deploy"
    rm -rf "${temp_dir}"
    mkdir -p "${temp_dir}"
    
    log "Preparing Kubernetes manifests..."
    
    # Copy manifests to temp directory
    cp -r k8s/* "${temp_dir}/"
    
    # Update image in k8s-ai-agent.yaml if registry is specified
    if [ -n "${REGISTRY}" ]; then
        local full_image="${REGISTRY}/k8s-ai-agent:${IMAGE_TAG}"
        log "Updating image to: ${full_image}"
        
        # Use sed to replace the image line in the deployment
        sed -i.bak "s|image: dockerhub.cisco.com/robot-dockerprod/k8s-ai-agent:latest|image: ${full_image}|g" "${temp_dir}/k8s-ai-agent.yaml"
        rm "${temp_dir}/k8s-ai-agent.yaml.bak" 2>/dev/null || true
    fi
    
    # Update namespace in all files
    if [ "${NAMESPACE}" != "default" ]; then
        log "Updating namespace to: ${NAMESPACE}"
        sed -i.bak "s/namespace: default/namespace: ${NAMESPACE}/g" "${temp_dir}"/*.yaml
        rm "${temp_dir}"/*.yaml.bak
    fi
    
    echo "${temp_dir}"
}

# Deploy function
deploy() {
    log "Deploying Kubernetes AI Assistant to namespace: ${NAMESPACE}"
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        log "Creating namespace: ${NAMESPACE}"
        if [ "${DRY_RUN}" = "true" ]; then
            kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml
        else
            kubectl create namespace "${NAMESPACE}"
        fi
    fi
    
    # Prepare manifests
    local manifest_dir=$(prepare_manifests)
    
    # Apply manifests in order
    local manifests=("02-rbac.yaml" "k8s-ai-agent.yaml")
    
    for manifest in "${manifests[@]}"; do
        if [ -f "${manifest_dir}/${manifest}" ]; then
            log "Applying ${manifest}..."
            if [ "${DRY_RUN}" = "true" ]; then
                kubectl apply -f "${manifest_dir}/${manifest}" -n "${NAMESPACE}" --dry-run=client
            else
                kubectl apply -f "${manifest_dir}/${manifest}" -n "${NAMESPACE}"
            fi
        else
            warning "Manifest ${manifest} not found, skipping..."
        fi
    done
    
    # Clean up temp files
    rm -rf "${manifest_dir}"
    
    if [ "${DRY_RUN}" = "true" ]; then
        success "Dry-run completed successfully"
        return
    fi
    
    # Wait for deployment to be ready
    log "Waiting for deployment to be ready (timeout: ${WAIT_TIMEOUT}s)..."
    if kubectl wait --for=condition=Ready pod -l app=k8s-ai-agent -n "${NAMESPACE}" --timeout="${WAIT_TIMEOUT}s"; then
        success "Deployment completed successfully!"
        
        # Show status
        show_status
        
        # Get node IPs for NodePort access
        log "Getting cluster node information for external access..."
        EXTERNAL_IPS=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null || echo "")
        INTERNAL_IPS=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "")
        
        if [ -n "$EXTERNAL_IPS" ]; then
            NODE_IPS="$EXTERNAL_IPS"
            IP_TYPE="External"
        elif [ -n "$INTERNAL_IPS" ]; then
            NODE_IPS="$INTERNAL_IPS"
            IP_TYPE="Internal"
        else
            NODE_IPS="<NODE_IP>"
            IP_TYPE="Unknown"
        fi
        
        log "Access Information:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🌐 NodePort Access (External):"
        if [ "$NODE_IPS" != "<NODE_IP>" ]; then
            for ip in $NODE_IPS; do
                echo "  📱 Streamlit Dashboard: http://${ip}:30080"
                echo "  📊 Metrics Endpoint:    http://${ip}:30090"
            done
            echo "  💡 IP Type: ${IP_TYPE}"
        else
            echo "  📱 Streamlit Dashboard: http://<NODE_IP>:30080"
            echo "  📊 Metrics Endpoint:    http://<NODE_IP>:30090"
            echo "  💡 Get node IPs: kubectl get nodes -o wide"
        fi
        echo ""
        echo "🔗 Port Forwarding (Local Development):"
        echo "  kubectl port-forward service/k8s-ai-agent -n ${NAMESPACE} 8080:8080"
        echo "  Then access: http://localhost:8080"
        echo ""
        echo "🔧 Troubleshooting:"
        echo "  - Check service: kubectl get service k8s-ai-agent -n ${NAMESPACE}"
        echo "  - Check pods: kubectl get pods -l app=k8s-ai-agent -n ${NAMESPACE}"
        echo "  - View logs: kubectl logs -l app=k8s-ai-agent -n ${NAMESPACE}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
    else
        error "Deployment failed or timed out"
        error "Check deployment status with: kubectl describe deployment k8s-ai-agent -n ${NAMESPACE}"
        error "Check pod status with: kubectl get pods -l app=k8s-ai-agent -n ${NAMESPACE}"
        exit 1
    fi
}

# Delete function
delete() {
    log "Deleting Kubernetes AI Assistant from namespace: ${NAMESPACE}"
    
    if [ "${DRY_RUN}" = "true" ]; then
        log "DRY RUN - Would delete the following resources:"
        kubectl get all,pvc,ingress -l app=k8s-ai-assistant -n "${NAMESPACE}" 2>/dev/null || true
        return
    fi
    
    # Delete resources
    kubectl delete -f k8s/ -n "${NAMESPACE}" --ignore-not-found=true
    
    # Wait for resources to be deleted
    log "Waiting for resources to be deleted..."
    kubectl wait --for=delete pod -l app=k8s-ai-agent -n "${NAMESPACE}" --timeout=60s 2>/dev/null || true
    
    success "AI Assistant deleted successfully"
}

# Status function
show_status() {
    log "Kubernetes AI Agent Status in namespace: ${NAMESPACE}"
    echo
    
    # Deployment status
    echo "Deployment Status:"
    kubectl get deployment k8s-ai-agent -n "${NAMESPACE}" -o wide 2>/dev/null || echo "Deployment not found"
    echo
    
    # Pod status
    echo "Pod Status:"
    kubectl get pods -l app=k8s-ai-agent -n "${NAMESPACE}" -o wide 2>/dev/null || echo "Pods not found"
    echo
    
    # Service status
    echo "Service Status:"
    kubectl get svc k8s-ai-agent -n "${NAMESPACE}" -o wide 2>/dev/null || echo "Service not found"
    echo
    
    # Check NodePort access
    SERVICE_TYPE=$(kubectl get service k8s-ai-agent -n "${NAMESPACE}" -o jsonpath='{.spec.type}' 2>/dev/null || echo "")
    if [ "$SERVICE_TYPE" = "NodePort" ]; then
        HTTP_NODEPORT=$(kubectl get service k8s-ai-agent -n "${NAMESPACE}" -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}' 2>/dev/null || echo "")
        METRICS_NODEPORT=$(kubectl get service k8s-ai-agent -n "${NAMESPACE}" -o jsonpath='{.spec.ports[?(@.name=="metrics")].nodePort}' 2>/dev/null || echo "")
        echo "NodePort Configuration:"
        echo "  - Dashboard: ${HTTP_NODEPORT}"
        echo "  - Metrics: ${METRICS_NODEPORT}"
        echo
    fi
    
    # PVC status  
    echo "Storage Status:"
    kubectl get pvc -l app=k8s-ai-agent -n "${NAMESPACE}" 2>/dev/null || echo "No PVCs found"
    echo
    
    # Events
    echo "Recent Events:"
    kubectl get events --field-selector involvedObject.kind=Deployment --field-selector involvedObject.name=k8s-ai-agent -n "${NAMESPACE}" --sort-by='.lastTimestamp' | tail -10 2>/dev/null || echo "No deployment events found"
}

# Logs function
show_logs() {
    log "Showing logs for Kubernetes AI Agent in namespace: ${NAMESPACE}"
    
    if ! kubectl get pods -l app=k8s-ai-agent -n "${NAMESPACE}" &> /dev/null; then
        error "No pods found with label app=k8s-ai-agent in namespace ${NAMESPACE}"
        exit 1
    fi
    
    # Follow logs
    kubectl logs -l app=k8s-ai-agent -n "${NAMESPACE}" -f
}

# Port forward function
port_forward() {
    log "Setting up port forwarding for Kubernetes AI Agent"
    
    if ! kubectl get pods -l app=k8s-ai-agent -n "${NAMESPACE}" &> /dev/null; then
        error "No pods found with label app=k8s-ai-agent in namespace ${NAMESPACE}"
        exit 1
    fi
    
    # Get node IPs for NodePort reference
    EXTERNAL_IPS=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null || echo "")
    INTERNAL_IPS=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "")
    
    if [ -n "$EXTERNAL_IPS" ]; then
        NODE_IP=$(echo $EXTERNAL_IPS | cut -d' ' -f1)
    elif [ -n "$INTERNAL_IPS" ]; then
        NODE_IP=$(echo $INTERNAL_IPS | cut -d' ' -f1)
    else
        NODE_IP="<NODE_IP>"
    fi
    
    log "Port forwarding setup:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔗 Local Access (Port Forwarding):"
    echo "  📱 Dashboard: http://localhost:8080"
    echo "  📊 Metrics:   http://localhost:9090"
    echo ""
    echo "🌐 NodePort Access (Alternative):"
    echo "  📱 Dashboard: http://${NODE_IP}:30080"
    echo "  📊 Metrics:   http://${NODE_IP}:30090"
    echo ""
    echo "💡 Use Ctrl+C to stop port forwarding"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    kubectl port-forward service/k8s-ai-agent -n "${NAMESPACE}" 8080:8080 9090:9090
}

# NodePort verification function
verify_nodeport_access() {
    log "Verifying NodePort access for Kubernetes AI Agent"
    
    # Check if service exists and is NodePort
    if ! kubectl get service k8s-ai-agent -n "${NAMESPACE}" &> /dev/null; then
        error "Service k8s-ai-agent not found in namespace ${NAMESPACE}"
        exit 1
    fi
    
    SERVICE_TYPE=$(kubectl get service k8s-ai-agent -n "${NAMESPACE}" -o jsonpath='{.spec.type}')
    if [ "$SERVICE_TYPE" != "NodePort" ]; then
        warning "Service is not configured as NodePort (current type: ${SERVICE_TYPE})"
        echo "To enable NodePort access, the service needs to be configured with type: NodePort"
        exit 1
    fi
    
    success "Service is configured as NodePort"
    
    # Get NodePort values
    HTTP_NODEPORT=$(kubectl get service k8s-ai-agent -n "${NAMESPACE}" -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}' 2>/dev/null || echo "")
    METRICS_NODEPORT=$(kubectl get service k8s-ai-agent -n "${NAMESPACE}" -o jsonpath='{.spec.ports[?(@.name=="metrics")].nodePort}' 2>/dev/null || echo "")
    
    if [ -n "$HTTP_NODEPORT" ] && [ -n "$METRICS_NODEPORT" ]; then
        success "NodePort configuration found:"
        echo "  - Dashboard: ${HTTP_NODEPORT}"
        echo "  - Metrics: ${METRICS_NODEPORT}"
    else
        error "Could not retrieve NodePort configuration"
        exit 1
    fi
    
    # Get node IPs
    log "Getting cluster node information..."
    EXTERNAL_IPS=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null || echo "")
    INTERNAL_IPS=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "")
    
    if [ -n "$EXTERNAL_IPS" ]; then
        NODE_IPS="$EXTERNAL_IPS"
        IP_TYPE="External"
    elif [ -n "$INTERNAL_IPS" ]; then
        NODE_IPS="$INTERNAL_IPS"
        IP_TYPE="Internal"
    else
        error "Could not retrieve node IP addresses"
        exit 1
    fi
    
    success "Found ${IP_TYPE} Node IPs: ${NODE_IPS}"
    
    # Check pod status
    POD_STATUS=$(kubectl get pods -l app=k8s-ai-agent -n "${NAMESPACE}" -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
    if [ "$POD_STATUS" = "Running" ]; then
        success "Pod is running and ready"
    else
        warning "Pod status: ${POD_STATUS} (may affect connectivity)"
    fi
    
    # Test connectivity if curl is available
    log "Testing NodePort connectivity..."
    if command -v curl &> /dev/null; then
        for NODE_IP in $NODE_IPS; do
            DASHBOARD_URL="http://${NODE_IP}:${HTTP_NODEPORT}"
            echo "Testing ${DASHBOARD_URL}..."
            
            if curl -s --connect-timeout 5 "${DASHBOARD_URL}/health" &> /dev/null; then
                success "✅ Dashboard accessible at ${DASHBOARD_URL}"
            else
                warning "⚠️  Dashboard health check failed at ${DASHBOARD_URL} (may still be starting)"
            fi
        done
    else
        warning "curl not available - skipping connectivity test"
    fi
    
    # Summary
    echo
    log "NodePort Access Summary:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for NODE_IP in $NODE_IPS; do
        echo "🌐 Node IP: ${NODE_IP}"
        echo "  📱 Dashboard: http://${NODE_IP}:${HTTP_NODEPORT}"
        echo "  📊 Metrics:   http://${NODE_IP}:${METRICS_NODEPORT}"
        echo
    done
    echo "🔧 Troubleshooting:"
    echo "  - Check firewall: Ensure ports ${HTTP_NODEPORT} and ${METRICS_NODEPORT} are open"
    echo "  - Check pod: kubectl get pods -l app=k8s-ai-agent -n ${NAMESPACE}"
    echo "  - Check service: kubectl get service k8s-ai-agent -n ${NAMESPACE}"
    echo "  - View logs: kubectl logs -l app=k8s-ai-agent -n ${NAMESPACE}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main script logic
main() {
    local command="${1:-}"
    
    if [ -z "${command}" ]; then
        usage
        exit 1
    fi
    
    # Set kubeconfig if specified
    if [ -n "${KUBE_CONFIG}" ]; then
        export KUBECONFIG="${KUBE_CONFIG}"
    fi
    
    # Check dependencies for most commands
    if [ "${command}" != "help" ]; then
        check_dependencies
    fi
    
    case "${command}" in
        "deploy")
            deploy
            ;;
        "delete")
            delete
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "port-forward")
            port_forward
            ;;
        "verify")
            verify_nodeport_access
            ;;
        "help"|"-h"|"--help")
            usage
            ;;
        *)
            error "Unknown command: ${command}"
            usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"

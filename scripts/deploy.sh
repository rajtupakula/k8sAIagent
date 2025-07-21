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
    
    # Update image in pod.yaml if registry is specified
    if [ -n "${REGISTRY}" ]; then
        local full_image="${REGISTRY}/k8s-ai-assistant:${IMAGE_TAG}"
        log "Updating image to: ${full_image}"
        
        # Use sed to replace the image line
        sed -i.bak "s|image: k8s-ai-assistant:latest|image: ${full_image}|g" "${temp_dir}/pod.yaml"
        rm "${temp_dir}/pod.yaml.bak"
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
    local manifests=("rbac.yaml" "pod.yaml" "service.yaml")
    
    for manifest in "${manifests[@]}"; do
        log "Applying ${manifest}..."
        if [ "${DRY_RUN}" = "true" ]; then
            kubectl apply -f "${manifest_dir}/${manifest}" -n "${NAMESPACE}" --dry-run=client
        else
            kubectl apply -f "${manifest_dir}/${manifest}" -n "${NAMESPACE}"
        fi
    done
    
    # Clean up temp files
    rm -rf "${manifest_dir}"
    
    if [ "${DRY_RUN}" = "true" ]; then
        success "Dry-run completed successfully"
        return
    fi
    
    # Wait for deployment to be ready
    log "Waiting for pod to be ready (timeout: ${WAIT_TIMEOUT}s)..."
    if kubectl wait --for=condition=Ready pod/k8s-ai-assistant -n "${NAMESPACE}" --timeout="${WAIT_TIMEOUT}s"; then
        success "Deployment completed successfully!"
        
        # Show status
        show_status
        
        log "To access the dashboard:"
        echo "  External NodePort access:"
        echo "  - Dashboard: http://<node-ip>:30501"
        echo "  - LLaMA API: http://<node-ip>:30080"
        echo "  - Health: http://<node-ip>:30000"
        echo ""
        echo "  Or use port forwarding:"
        echo "  kubectl port-forward pod/k8s-ai-assistant -n ${NAMESPACE} 8501:8501"
        echo "  Then open: http://localhost:8501"
        echo ""
        echo "  To get node IPs: kubectl get nodes -o wide"
        
    else
        error "Deployment failed or timed out"
        error "Check pod status with: kubectl describe pod/k8s-ai-assistant -n ${NAMESPACE}"
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
    kubectl wait --for=delete pod/k8s-ai-assistant -n "${NAMESPACE}" --timeout=60s 2>/dev/null || true
    
    success "AI Assistant deleted successfully"
}

# Status function
show_status() {
    log "Kubernetes AI Assistant Status in namespace: ${NAMESPACE}"
    echo
    
    # Pod status
    echo "Pod Status:"
    kubectl get pod/k8s-ai-assistant -n "${NAMESPACE}" -o wide 2>/dev/null || echo "Pod not found"
    echo
    
    # Service status
    echo "Service Status:"
    kubectl get svc -l app=k8s-ai-assistant -n "${NAMESPACE}" 2>/dev/null || echo "No services found"
    echo
    
    # PVC status
    echo "Storage Status:"
    kubectl get pvc -l app=k8s-ai-assistant -n "${NAMESPACE}" 2>/dev/null || echo "No PVCs found"
    echo
    
    # Events
    echo "Recent Events:"
    kubectl get events --field-selector involvedObject.name=k8s-ai-assistant -n "${NAMESPACE}" --sort-by='.lastTimestamp' | tail -10 2>/dev/null || echo "No events found"
}

# Logs function
show_logs() {
    log "Showing logs for Kubernetes AI Assistant in namespace: ${NAMESPACE}"
    
    if ! kubectl get pod/k8s-ai-assistant -n "${NAMESPACE}" &> /dev/null; then
        error "Pod not found in namespace ${NAMESPACE}"
        exit 1
    fi
    
    # Follow logs
    kubectl logs pod/k8s-ai-assistant -n "${NAMESPACE}" -f
}

# Port forward function
port_forward() {
    log "Setting up port forwarding for Kubernetes AI Assistant"
    
    if ! kubectl get pod/k8s-ai-assistant -n "${NAMESPACE}" &> /dev/null; then
        error "Pod not found in namespace ${NAMESPACE}"
        exit 1
    fi
    
    log "Port forwarding setup:"
    echo "  Dashboard: http://localhost:8501"
    echo "  LLaMA API: http://localhost:8080"
    echo "  Health: http://localhost:8000"
    echo ""
    echo "  Note: NodePort services are also available:"
    echo "  - Dashboard: http://<node-ip>:30501"
    echo "  - LLaMA API: http://<node-ip>:30080"
    echo "  - Health: http://<node-ip>:30000"
    echo ""
    log "Press Ctrl+C to stop port forwarding"
    
    kubectl port-forward pod/k8s-ai-assistant -n "${NAMESPACE}" 8501:8501 8080:8080 8000:8000
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

#!/bin/bash

# Deployment script for K8s AI Agent
# Supports local, staging, and production deployments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"; }
info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"; }

# Default configuration
ENVIRONMENT="local"
IMAGE_TAG="latest"
NAMESPACE="default"
HELM_RELEASE_NAME="k8s-ai-agent"
DOCKER_REGISTRY="localhost:5000"
IMAGE_NAME="k8s-ai-agent"
DRY_RUN=false
WAIT_FOR_ROLLOUT=true

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy K8s AI Agent to various environments

OPTIONS:
    -e, --environment ENV     Target environment: local, staging, prod (default: local)
    -t, --tag TAG            Image tag to deploy (default: latest)
    -n, --namespace NS       Kubernetes namespace (default: default)
    -r, --registry REG       Docker registry (default: localhost:5000)
    -i, --image-name NAME    Image name (default: k8s-ai-agent)
    --release-name NAME      Helm release name (default: k8s-ai-agent)
    --dry-run               Perform a dry run without actual deployment
    --no-wait               Don't wait for rollout to complete
    -h, --help              Show this help

EXAMPLES:
    # Local deployment
    $0 --environment local

    # Staging deployment with specific tag
    $0 --environment staging --tag v1.2.3 --namespace ai-staging

    # Production deployment
    $0 --environment prod --tag v1.2.3 --namespace ai-production

    # Dry run
    $0 --environment prod --tag v1.2.3 --dry-run

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--registry)
                DOCKER_REGISTRY="$2"
                shift 2
                ;;
            -i|--image-name)
                IMAGE_NAME="$2"
                shift 2
                ;;
            --release-name)
                HELM_RELEASE_NAME="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-wait)
                WAIT_FOR_ROLLOUT=false
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Deploy Kubernetes manifests
deploy_kubernetes_manifests() {
    local image="$1"
    local is_production="${2:-false}"

    info "Deploying Kubernetes manifests..."
    info "Image: $image"
    info "Namespace: $NAMESPACE"

    # Apply existing Kubernetes manifests with image update
    if [[ "$DRY_RUN" == "false" ]]; then
        # Update deployment image
        kubectl set image deployment/k8s-ai-agent ai-agent="$image" -n "$NAMESPACE" || {
            # If deployment doesn't exist, apply manifests
            kubectl apply -f k8s/ -n "$NAMESPACE"
            kubectl set image deployment/k8s-ai-agent ai-agent="$image" -n "$NAMESPACE"
        }
        
        # Wait for rollout if requested
        if [[ "$WAIT_FOR_ROLLOUT" == "true" ]]; then
            info "Waiting for deployment rollout..."
            kubectl rollout status deployment/k8s-ai-agent -n "$NAMESPACE" --timeout=300s
        fi
    else
        info "DRY RUN - Would update image to: $image"
    fi
}

# Main execution
main() {
    log "K8s AI Agent Deployment Script"
    log "==============================="

    parse_args "$@"
    
    local full_image="${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    deploy_kubernetes_manifests "$full_image"

    log "Deployment completed!"
}

# Run main function
main "$@"

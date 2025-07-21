#!/bin/bash

# Build script for Kubernetes AI Assistant
# This script builds the Docker image and prepares for deployment

set -e

# Configuration
IMAGE_NAME="k8s-ai-assistant"
IMAGE_TAG="${1:-latest}"
REGISTRY="${REGISTRY:-}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
VERSION="${VERSION:-1.0.0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[BUILD]${NC} $1"
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

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if git is available for VCS ref
if ! command -v git &> /dev/null; then
    warning "Git is not available, using 'unknown' for VCS ref"
fi

log "Building Kubernetes AI Assistant Docker image"
log "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
log "Registry: ${REGISTRY:-"local"}"
log "Build Date: ${BUILD_DATE}"
log "VCS Ref: ${VCS_REF}"
log "Version: ${VERSION}"

# Build the Docker image
log "Starting Docker build..."

docker build \
    --build-arg BUILD_DATE="${BUILD_DATE}" \
    --build-arg VCS_REF="${VCS_REF}" \
    --build-arg VERSION="${VERSION}" \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    -f Dockerfile \
    .

if [ $? -eq 0 ]; then
    success "Docker image built successfully"
else
    error "Docker build failed"
    exit 1
fi

# Tag with registry if specified
if [ -n "${REGISTRY}" ]; then
    FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    log "Tagging image for registry: ${FULL_IMAGE}"
    docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${FULL_IMAGE}"
    
    # Also tag as latest if not already latest
    if [ "${IMAGE_TAG}" != "latest" ]; then
        docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${REGISTRY}/${IMAGE_NAME}:latest"
        log "Tagged as latest: ${REGISTRY}/${IMAGE_NAME}:latest"
    fi
fi

# Show image details
log "Image build complete. Details:"
docker images "${IMAGE_NAME}:${IMAGE_TAG}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Optional: Run basic tests on the image
if [ "${RUN_TESTS:-}" = "true" ]; then
    log "Running basic image tests..."
    
    # Test that the image starts
    CONTAINER_ID=$(docker run -d "${IMAGE_NAME}:${IMAGE_TAG}")
    sleep 10
    
    # Check if container is still running
    if docker ps -q --filter "id=${CONTAINER_ID}" | grep -q .; then
        success "Container started successfully"
        docker stop "${CONTAINER_ID}" > /dev/null
        docker rm "${CONTAINER_ID}" > /dev/null
    else
        error "Container failed to start"
        docker logs "${CONTAINER_ID}"
        docker rm "${CONTAINER_ID}" > /dev/null
        exit 1
    fi
fi

# Optional: Push to registry
if [ "${PUSH:-}" = "true" ] && [ -n "${REGISTRY}" ]; then
    log "Pushing to registry..."
    docker push "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    
    if [ "${IMAGE_TAG}" != "latest" ]; then
        docker push "${REGISTRY}/${IMAGE_NAME}:latest"
    fi
    
    success "Image pushed to registry"
fi

success "Build completed successfully!"

# Show usage instructions
echo
log "Usage instructions:"
echo "  Local run: docker run -p 8501:8501 -p 8080:8080 ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  Deploy to K8s: Update image in k8s/pod.yaml and apply"
echo "  Push to registry: PUSH=true REGISTRY=your-registry.com ./scripts/build.sh ${IMAGE_TAG}"

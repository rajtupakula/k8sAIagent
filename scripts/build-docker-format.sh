#!/bin/bash

# Optimized build script for Kubernetes AI Assistant
# Includes aggressive space optimization - uses /home directory for all storage
# Prevents "no space left on device" errors by redirecting container storage

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

# Configuration
VERSION=${VERSION:-"1.0.0"}
BUILD_NUMBER=${BUILD_NUMBER:-"local"}
BRANCH=${BRANCH:-$(git branch --show-current 2>/dev/null || echo "main")}
IMAGE_NAME=${IMAGE_NAME:-"k8s-ai-agent"}
REGISTRY=${REGISTRY:-""}

# Storage configuration for space optimization
BUILD_TEMP_DIR=${BUILD_TEMP_DIR:-"$HOME/k8s-ai-build"}
STORAGE_DRIVER=${STORAGE_DRIVER:-"overlay"}
CONTAINER_STORAGE_ROOT=${CONTAINER_STORAGE_ROOT:-"$HOME/.containers"}

# Create temporary build directory with more space in home
if [[ ! -d "${BUILD_TEMP_DIR}" ]]; then
    log "Creating temporary build directory: ${BUILD_TEMP_DIR}"
    mkdir -p "${BUILD_TEMP_DIR}"
fi

# Create container storage directory in home
if [[ ! -d "${CONTAINER_STORAGE_ROOT}" ]]; then
    log "Creating container storage directory: ${CONTAINER_STORAGE_ROOT}"
    mkdir -p "${CONTAINER_STORAGE_ROOT}"
fi

# Build metadata
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
IMAGE_TAG="${VERSION}-${BRANCH}-${BUILD_NUMBER}"

# If main/master branch, use simpler tag
if [[ "${BRANCH}" == "main" || "${BRANCH}" == "master" ]]; then
    IMAGE_TAG="${VERSION}-${BUILD_NUMBER}"
fi

# Use standard Dockerfile (already OCI compatible)
DOCKERFILE="Dockerfile"
log "Using standard Dockerfile (OCI compatible, no HEALTHCHECK)"

log "Build Configuration:"
log "  Image Name: ${IMAGE_NAME}"
log "  Image Tag: ${IMAGE_TAG}"
log "  Dockerfile: ${DOCKERFILE}"
log "  Build Date: ${BUILD_DATE}"
log "  VCS Ref: ${VCS_REF}"
log "  Version: ${VERSION}"
log "  Temp Directory: ${BUILD_TEMP_DIR}"
log "  Container Storage: ${CONTAINER_STORAGE_ROOT}"

# Check available space
AVAILABLE_SPACE=$(df -h "${BUILD_TEMP_DIR}" | awk 'NR==2 {print $4}')
AVAILABLE_SPACE_BYTES=$(df "${BUILD_TEMP_DIR}" | awk 'NR==2 {print $4}')
log "Available space at ${BUILD_TEMP_DIR}: ${AVAILABLE_SPACE}"

# Check if we have sufficient space (need at least 10GB for AI model builds)
MIN_SPACE_KB=$((10 * 1024 * 1024)) # 10GB in KB
if [ "${AVAILABLE_SPACE_BYTES}" -lt "${MIN_SPACE_KB}" ]; then
    warn "Low disk space detected: ${AVAILABLE_SPACE}"
    warn "Recommended: At least 10GB free space for AI model builds"
    warn "Consider running: ./scripts/emergency-space-cleanup.sh"
fi

# Build with appropriate tool and format
build_image() {
    local build_args=(
        --build-arg BUILD_DATE="${BUILD_DATE}"
        --build-arg VCS_REF="${VCS_REF}"
        --build-arg VERSION="${VERSION}"
        -t "${IMAGE_NAME}:${IMAGE_TAG}"
        -f "${DOCKERFILE}"
        .
    )

    # Set up comprehensive space optimization environment
    export TMPDIR="${BUILD_TEMP_DIR}"
    export DOCKER_TMPDIR="${BUILD_TEMP_DIR}"
    export DOCKER_CONFIG="${CONTAINER_STORAGE_ROOT}/docker"
    export BUILDAH_ISOLATION=chroot
    
    # Create docker config directory in home
    mkdir -p "${CONTAINER_STORAGE_ROOT}/docker"
    
    # Choose build tool based on availability
    if command -v buildah >/dev/null 2>&1; then
        log "Using buildah with space optimization"
        log "Storage root: ${CONTAINER_STORAGE_ROOT}"
        log "Temp directory: ${BUILD_TEMP_DIR}"
        
        # Use buildah with complete storage redirection
        buildah build \
            --storage-driver "${STORAGE_DRIVER}" \
            --root "${CONTAINER_STORAGE_ROOT}/storage" \
            --runroot "${CONTAINER_STORAGE_ROOT}/run" \
            --format docker \
            --layers \
            --squash \
            --isolation chroot \
            --network=host \
            "${build_args[@]}"
            
    elif command -v podman >/dev/null 2>&1; then
        log "Using podman with space optimization"
        log "Storage root: ${CONTAINER_STORAGE_ROOT}"
        log "Temp directory: ${BUILD_TEMP_DIR}"
        
        # Use podman with complete storage redirection
        podman build \
            --storage-driver "${STORAGE_DRIVER}" \
            --root "${CONTAINER_STORAGE_ROOT}/storage" \
            --runroot "${CONTAINER_STORAGE_ROOT}/run" \
            --format docker \
            --layers \
            --squash \
            --network=host \
            "${build_args[@]}"
            
    else
        log "Using docker build with space optimization"
        log "Temp directory: ${BUILD_TEMP_DIR}"
        
        # Configure Docker to use home directory for everything
        export DOCKER_BUILDKIT=1
        export BUILDKIT_HOST="unix://${CONTAINER_STORAGE_ROOT}/buildkit.sock"
        
        # Try to use --squash if supported, otherwise build normally
        if docker build --help | grep -q "\-\-squash"; then
            docker build --squash --network=host "${build_args[@]}"
        else
            docker build --network=host "${build_args[@]}"
        fi
    fi
}

# Build the image
log "Starting container image build..."
build_image

if [ $? -eq 0 ]; then
    success "Container image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"
    
    # Save image to home directory for backup/transfer
    IMAGE_EXPORT_PATH="${HOME}/k8s-ai-images"
    mkdir -p "${IMAGE_EXPORT_PATH}"
    
    log "Saving image to ${IMAGE_EXPORT_PATH}..."
    if command -v podman >/dev/null 2>&1; then
        podman save "${IMAGE_NAME}:${IMAGE_TAG}" -o "${IMAGE_EXPORT_PATH}/${IMAGE_NAME}-${IMAGE_TAG}.tar"
    else
        docker save "${IMAGE_NAME}:${IMAGE_TAG}" -o "${IMAGE_EXPORT_PATH}/${IMAGE_NAME}-${IMAGE_TAG}.tar"
    fi
    success "Image saved to: ${IMAGE_EXPORT_PATH}/${IMAGE_NAME}-${IMAGE_TAG}.tar"
    
    # Tag with registry if specified
    if [ -n "${REGISTRY}" ]; then
        FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
        log "Tagging image for registry: ${FULL_IMAGE}"
        
        if command -v podman >/dev/null 2>&1; then
            podman tag "${IMAGE_NAME}:${IMAGE_TAG}" "${FULL_IMAGE}"
        else
            docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${FULL_IMAGE}"
        fi
        
        # Also tag as latest if not already latest
        if [ "${IMAGE_TAG}" != "latest" ]; then
            if command -v podman >/dev/null 2>&1; then
                podman tag "${IMAGE_NAME}:${IMAGE_TAG}" "${REGISTRY}/${IMAGE_NAME}:latest"
            else
                docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${REGISTRY}/${IMAGE_NAME}:latest"
            fi
        fi
        
        success "Tagged for registry: ${FULL_IMAGE}"
    fi
    
    # Display image info
    log "Image build completed successfully!"
    log "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
    log "Dockerfile: ${DOCKERFILE}"
    
    # Cleanup temporary build directory
    if [[ -d "${BUILD_TEMP_DIR}" ]]; then
        log "Cleaning up temporary build directory: ${BUILD_TEMP_DIR}"
        rm -rf "${BUILD_TEMP_DIR}"
    fi
    
else
    error "Container image build failed"
    # Cleanup on failure
    if [[ -d "${BUILD_TEMP_DIR}" ]]; then
        warn "Cleaning up temporary build directory after failure: ${BUILD_TEMP_DIR}"
        rm -rf "${BUILD_TEMP_DIR}"
    fi
    exit 1
fi

#!/bin/bash

# Optimized build script for Kubernetes AI Assistant
# Includes space optimization and container runtime auto-detection

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
# Detect if running in Jenkins and adjust paths accordingly
if [ -n "${JENKINS_HOME:-}" ] || [ -n "${BUILD_NUMBER:-}" ]; then
    log "Detected Jenkins environment, using Jenkins-optimized paths"
    BUILD_TEMP_DIR=${BUILD_TEMP_DIR:-"/home/jenkins/k8s-ai-build"}
    CONTAINER_STORAGE_ROOT=${CONTAINER_STORAGE_ROOT:-"/home/jenkins/.containers"}
else
    BUILD_TEMP_DIR=${BUILD_TEMP_DIR:-"$HOME/k8s-ai-build"}
    CONTAINER_STORAGE_ROOT=${CONTAINER_STORAGE_ROOT:-"$HOME/.containers"}
fi

STORAGE_DRIVER=${STORAGE_DRIVER:-"overlay"}

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

# Choose the appropriate Dockerfile based on build requirements
DOCKERFILE_PATH="Dockerfile"
if [ -f "Dockerfile.optimized" ]; then
    log "Using optimized Dockerfile for LLaMA support (avoids build issues)"
    DOCKERFILE_PATH="Dockerfile.optimized"
elif [ -f "Dockerfile" ]; then
    log "Using standard Dockerfile"
    DOCKERFILE_PATH="Dockerfile"
else
    error "No Dockerfile found!"
    exit 1
fi

# Clean branch name to ensure Docker tag compatibility (remove */ prefix and sanitize)
CLEAN_BRANCH=$(echo "${BRANCH}" | sed 's|^*/||' | sed 's/[^a-zA-Z0-9._-]/-/g')
IMAGE_TAG="${VERSION}-${CLEAN_BRANCH}-${BUILD_NUMBER}"

# If main/master branch, use simpler tag
if [[ "${CLEAN_BRANCH}" == "main" || "${CLEAN_BRANCH}" == "master" ]]; then
    IMAGE_TAG="${VERSION}-${BUILD_NUMBER}"
fi

# Use ARTIFACTORY_IMAGE if provided (for Jenkins), otherwise build standard image name
if [ -n "${ARTIFACTORY_IMAGE:-}" ]; then
    FULL_IMAGE_NAME="${ARTIFACTORY_IMAGE}"
    log "Using provided ARTIFACTORY_IMAGE: ${FULL_IMAGE_NAME}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
    log "Using standard image name: ${FULL_IMAGE_NAME}"
fi

# Use standard Dockerfile (already OCI compatible)
DOCKERFILE="Dockerfile"
log "Using standard Dockerfile (OCI compatible, no HEALTHCHECK)"

log "Build Configuration:"
log "  Image Name: ${IMAGE_NAME}"
log "  Image Tag: ${IMAGE_TAG}"
log "  Full Image: ${FULL_IMAGE_NAME}"
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
        -t "${FULL_IMAGE_NAME}"
        -f "${DOCKERFILE_PATH}"
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
        
        # Use buildah with complete storage redirection and security options
        buildah build \
            --storage-driver "${STORAGE_DRIVER}" \
            --root "${CONTAINER_STORAGE_ROOT}/storage" \
            --runroot "${CONTAINER_STORAGE_ROOT}/run" \
            --format docker \
            --layers \
            --squash \
            --isolation chroot \
            --network=host \
            --no-cache \
            --pull \
            --security-opt label=disable \
            --security-opt seccomp=unconfined \
            --security-opt apparmor=unconfined \
            --cap-add=ALL \
            "${build_args[@]}"
            
    elif command -v podman >/dev/null 2>&1; then
        log "Using podman with space optimization"
        log "Storage root: ${CONTAINER_STORAGE_ROOT}"
        log "Temp directory: ${BUILD_TEMP_DIR}"
        
        # Use podman with complete storage redirection and security options
        podman build \
            --storage-driver "${STORAGE_DRIVER}" \
            --root "${CONTAINER_STORAGE_ROOT}/storage" \
            --runroot "${CONTAINER_STORAGE_ROOT}/run" \
            --format docker \
            --layers \
            --squash \
            --network=host \
            --no-cache \
            --pull \
            --isolation=chroot \
            --security-opt label=disable \
            --security-opt seccomp=unconfined \
            --security-opt apparmor=unconfined \
            --cap-add=ALL \
            "${build_args[@]}"
            
    else
        log "Using docker build with space optimization"
        log "Temp directory: ${BUILD_TEMP_DIR}"
        
        # Configure Docker to use home directory for everything
        export DOCKER_BUILDKIT=1
        export BUILDKIT_HOST="unix://${CONTAINER_STORAGE_ROOT}/buildkit.sock"
        
        # Try to use --squash if supported, otherwise build normally with security options
        if docker build --help | grep -q "\-\-squash"; then
            docker build \
                --squash \
                --network=host \
                --no-cache \
                --pull \
                --security-opt seccomp=unconfined \
                --security-opt apparmor=unconfined \
                --cap-add=ALL \
                --privileged \
                "${build_args[@]}"
        else
            docker build \
                --network=host \
                --no-cache \
                --pull \
                --security-opt seccomp=unconfined \
                --security-opt apparmor=unconfined \
                --cap-add=ALL \
                --privileged \
                "${build_args[@]}"
        fi
    fi
}

# Build the image
log "Starting container image build..."
build_image

if [ $? -eq 0 ]; then
    success "Container image built successfully: ${FULL_IMAGE_NAME}"
    
    # Show final image information
    log "Verifying built image..."
    if command -v buildah >/dev/null 2>&1; then
        buildah images "${FULL_IMAGE_NAME}" || true
    elif command -v podman >/dev/null 2>&1; then
        podman images "${FULL_IMAGE_NAME}" || true
    else
        docker images "${FULL_IMAGE_NAME}" || true
    fi
    
    # Display image info
    log "Image build completed successfully!"
    log "Image: ${FULL_IMAGE_NAME}"
    log "Dockerfile: ${DOCKERFILE}"
    
else
    error "Container image build failed"
    exit 1
fi

log "Build process completed. Image: ${FULL_IMAGE_NAME}"

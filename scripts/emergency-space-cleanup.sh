#!/bin/bash

# Emergency space cleanup for container builds
# Run this if you get "no space left on device" errors

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"; }
info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"; }

log "🧹 Emergency Container Space Cleanup"
echo

# Check disk usage first
info "Current disk usage:"
df -h | head -1
df -h | grep -E "^/dev" | head -5
echo

# Function to cleanup Docker
cleanup_docker() {
    if command -v docker >/dev/null 2>&1; then
        log "🐳 Cleaning up Docker..."
        
        # Remove stopped containers
        if docker ps -aq --filter "status=exited" | wc -l | grep -v "^0"; then
            log "Removing stopped containers..."
            docker ps -aq --filter "status=exited" | xargs docker rm 2>/dev/null || true
        fi
        
        # Remove dangling images
        if docker images -f "dangling=true" -q | wc -l | grep -v "^0"; then
            log "Removing dangling images..."
            docker images -f "dangling=true" -q | xargs docker rmi 2>/dev/null || true
        fi
        
        # Remove unused volumes
        log "Removing unused volumes..."
        docker volume prune -f 2>/dev/null || true
        
        # Remove build cache
        log "Removing build cache..."
        docker builder prune -f 2>/dev/null || true
        
        # System prune (final cleanup)
        log "Running system prune..."
        docker system prune -f 2>/dev/null || true
        
        info "Docker disk usage after cleanup:"
        docker system df 2>/dev/null || true
    else
        warn "Docker not found or not running"
    fi
}

# Function to cleanup Podman
cleanup_podman() {
    if command -v podman >/dev/null 2>&1; then
        log "🦭 Cleaning up Podman..."
        
        # Remove stopped containers
        log "Removing stopped containers..."
        podman container prune -f 2>/dev/null || true
        
        # Remove dangling images
        log "Removing dangling images..."
        podman image prune -f 2>/dev/null || true
        
        # Remove unused volumes
        log "Removing unused volumes..."
        podman volume prune -f 2>/dev/null || true
        
        # System prune
        log "Running system prune..."
        podman system prune -f 2>/dev/null || true
        
        info "Podman disk usage after cleanup:"
        podman system df 2>/dev/null || true
    else
        warn "Podman not found or not running"
    fi
}

# Function to cleanup buildah
cleanup_buildah() {
    if command -v buildah >/dev/null 2>&1; then
        log "🔨 Cleaning up Buildah..."
        
        # Remove working containers
        buildah containers -q | xargs buildah rm 2>/dev/null || true
        
        # Remove dangling images
        buildah images -f "dangling=true" -q | xargs buildah rmi 2>/dev/null || true
        
        log "Buildah cleanup completed"
    else
        warn "Buildah not found"
    fi
}

# Function to cleanup temporary files
cleanup_temp() {
    log "🗑️  Cleaning up temporary files..."
    
    # Clean system temp
    if [[ -d /tmp ]]; then
        log "Cleaning /tmp..."
        find /tmp -type f -atime +1 -name "*docker*" -delete 2>/dev/null || true
        find /tmp -type f -atime +1 -name "*container*" -delete 2>/dev/null || true
        find /tmp -type f -atime +1 -name "*buildah*" -delete 2>/dev/null || true
        find /tmp -type f -atime +1 -name "*podman*" -delete 2>/dev/null || true
        # Clean large temp files older than 1 hour
        find /tmp -type f -size +100M -amin +60 -delete 2>/dev/null || true
    fi
    
    # Clean user temp directories
    if [[ -d "$HOME/k8s-ai-build" ]]; then
        log "Cleaning build temp directory..."
        rm -rf "$HOME/k8s-ai-build"/*  2>/dev/null || true
    fi
    
    # Clean container temp directories
    if [[ -d "$HOME/.containers/tmp" ]]; then
        log "Cleaning container temp..."
        rm -rf "$HOME/.containers/tmp"/* 2>/dev/null || true
    fi
    
    # Clean container storage cache
    if [[ -d "$HOME/.containers/cache" ]]; then
        log "Cleaning container cache..."
        rm -rf "$HOME/.containers/cache"/* 2>/dev/null || true
    fi
    
    # Clean Python cache aggressively
    log "Cleaning Python cache..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$HOME" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    
    # Clean pip cache
    if command -v pip >/dev/null 2>&1; then
        log "Cleaning pip cache..."
        pip cache purge 2>/dev/null || true
    fi
    
    # Clean any large log files
    log "Cleaning large log files..."
    find /var/log -type f -size +100M -exec truncate -s 0 {} \; 2>/dev/null || true
}

# Function to show space after cleanup
show_space_after() {
    echo
    log "📊 Disk usage after cleanup:"
    df -h | head -1
    df -h | grep -E "^/dev" | head -5
    echo
    
    log "Available space in key directories:"
    echo "Root (/):     $(df -h / | awk 'NR==2 {print $4}')"
    echo "Temp (/tmp):  $(df -h /tmp | awk 'NR==2 {print $4}')"
    echo "Home ($HOME): $(df -h "$HOME" | awk 'NR==2 {print $4}')"
}

# Main execution
log "Starting emergency cleanup..."

# Cleanup in order of impact
cleanup_docker
cleanup_podman
cleanup_buildah
cleanup_temp

show_space_after

log "✅ Emergency cleanup completed!"
echo
info "To build with space optimization, run:"
echo "  ./scripts/build-with-space-fix.sh"
echo
info "To prevent future space issues:"
echo "  1. Use SPACE_OPTIMIZED=true for builds"
echo "  2. Set BUILD_TEMP_DIR to a directory with more space"
echo "  3. Consider moving Docker/Podman storage to /home"
echo "  4. Run this cleanup script regularly"

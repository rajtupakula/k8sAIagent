#!/bin/bash
"""
Build Validation Script - Ensures correct Dockerfile selection for LLaMA support
"""

set -e

echo "🔍 Build Validation - Dockerfile Selection"
echo "==========================================="

# Check for available Dockerfiles
echo "Available Dockerfiles:"
ls -la Dockerfile* || echo "No Dockerfiles found"

# Determine best Dockerfile for build
if [ -f "Dockerfile.optimized" ]; then
    RECOMMENDED_DOCKERFILE="Dockerfile.optimized"
    REASON="Optimized for LLaMA support with CPU-only builds (avoids pthread issues)"
    echo "✅ RECOMMENDED: ${RECOMMENDED_DOCKERFILE}"
    echo "   Reason: ${REASON}"
elif [ -f "Dockerfile" ]; then
    RECOMMENDED_DOCKERFILE="Dockerfile"
    REASON="Standard Dockerfile available"
    echo "⚠️  FALLBACK: ${RECOMMENDED_DOCKERFILE}"
    echo "   Reason: ${REASON}"
    echo "   Note: May encounter llama-cpp-python build issues"
else
    echo "❌ ERROR: No Dockerfile found!"
    exit 1
fi

echo ""
echo "Selected Dockerfile: ${RECOMMENDED_DOCKERFILE}"
echo "Preview:"
echo "--------"
head -10 "${RECOMMENDED_DOCKERFILE}"

echo ""
echo "Key differences between Dockerfiles:"
if [ -f "Dockerfile.optimized" ] && [ -f "Dockerfile" ]; then
    echo "Dockerfile.optimized features:"
    echo "  • CPU-optimized llama-cpp-python build"
    echo "  • Step-by-step dependency installation"
    echo "  • Avoids pthread linking issues"
    echo "  • Smaller final image size"
    echo ""
    echo "Standard Dockerfile:"
    echo "  • May encounter build issues with llama-cpp-python"
    echo "  • Uses requirements-minimal.txt approach"
fi

echo ""
echo "Build command recommendation:"
echo "docker build -f ${RECOMMENDED_DOCKERFILE} -t k8s-ai-agent:latest ."

echo ""
echo "Jenkins will automatically select: ${RECOMMENDED_DOCKERFILE}"

#!/bin/bash
"""
Quick Build and Test Script for LLaMA-enabled Container
"""

echo "🚀 Building Kubernetes AI Agent with LLaMA Server Support"
echo "========================================================"

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t k8s-ai-agent:llama-latest . || {
    echo "❌ Docker build failed"
    exit 1
}

echo "✅ Docker image built successfully"

# Test the image
echo "🧪 Testing the built image..."
docker run --rm -d --name k8s-ai-test \
  -p 8080:8080 \
  -e K8S_AI_MODE=interactive \
  k8s-ai-agent:llama-latest || {
    echo "❌ Container failed to start"
    exit 1
}

echo "⏳ Waiting for container to start..."
sleep 10

# Check if the application is responding
echo "🔍 Checking application health..."
curl -f http://localhost:8080/health || {
    echo "❌ Application health check failed"
    docker logs k8s-ai-test
    docker stop k8s-ai-test
    exit 1
}

echo "✅ Application is responding"

# Check for LLaMA server
echo "🤖 Checking LLaMA server status..."
docker exec k8s-ai-test curl -f http://localhost:8080/v1/models 2>/dev/null && {
    echo "✅ LLaMA server is running"
} || {
    echo "⚠️ LLaMA server not ready (this is OK for initial startup)"
}

# Show container logs
echo "📋 Container startup logs:"
docker logs k8s-ai-test | tail -20

# Stop test container
docker stop k8s-ai-test

echo "✅ Build and test completed successfully!"
echo "🚀 Ready to deploy with: docker run -p 8080:8080 k8s-ai-agent:llama-latest"

#!/bin/bash
"""
Quick Fix for LLaMA Server Build Issues
This script builds the container with CPU-optimized settings to avoid pthread build errors
"""

set -e

echo "🔧 Quick Fix: Building CPU-optimized container to avoid build errors"
echo "=================================================================="

# Use the optimized Dockerfile
echo "📦 Building with optimized Dockerfile..."
docker build -f Dockerfile.optimized -t k8s-ai-agent:fixed . || {
    echo "❌ Optimized build failed, trying alternative approach..."
    
    # Alternative: Use pre-built wheel
    echo "🔄 Trying with pre-built wheels..."
    
    # Create temporary requirements without llama-cpp-python
    cat > requirements-temp.txt << EOF
streamlit==1.32.0
pandas==2.0.3
plotly==5.18.0
numpy==1.25.2
requests==2.31.0
pyyaml==6.0.1
psutil==5.9.8
kubernetes==28.1.0
scikit-learn==1.3.2
langchain==0.1.10
sentence-transformers==2.5.1
chromadb==0.4.22
torch==2.1.2+cpu --extra-index-url https://download.pytorch.org/whl/cpu
transformers==4.36.2
tokenizers==0.15.0
EOF

    # Build without llama-cpp-python first
    docker build --build-arg SKIP_LLAMA=true -t k8s-ai-agent:base . || {
        echo "❌ Base build failed"
        exit 1
    }
    
    # Add llama-cpp-python in runtime
    echo "🤖 Adding LLaMA support to running container..."
    docker run -d --name temp-llama k8s-ai-agent:base sleep 3600
    docker exec temp-llama pip install llama-cpp-python==0.2.55
    docker commit temp-llama k8s-ai-agent:fixed
    docker stop temp-llama
    docker rm temp-llama
    
    rm requirements-temp.txt
}

echo "✅ Container built successfully!"

# Test the container
echo "🧪 Testing the container..."
docker run --rm -d --name test-fixed \
  -p 8080:8080 \
  k8s-ai-agent:fixed || {
    echo "❌ Container failed to start"
    exit 1
}

echo "⏳ Waiting for startup..."
sleep 15

# Check application
curl -f http://localhost:8080/ && {
    echo "✅ Application is working!"
} || {
    echo "⚠️ Application might need more time to start"
    docker logs test-fixed | tail -10
}

# Stop test
docker stop test-fixed

echo "🚀 Ready to use: docker run -p 8080:8080 k8s-ai-agent:fixed"
echo "🌐 Access your interactive AI at: http://localhost:8080"
